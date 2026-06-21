import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import re
import asyncio
from datetime import datetime

class KickClip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "kick_clips_settings.json"
        self._init_settings()
        self.browser = None
        self.check_clips.start()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, "w") as f:
                json.dump({}, f)

    def _get_settings(self, guild_id):
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
            return data.get(str(guild_id), {"kanallar": []})
        except:
            return {"kanallar": []}

    def _save_all(self, data):
        with open(self.settings_file, "w") as f:
            json.dump(data, f, indent=4)

    def _get_all(self):
        try:
            with open(self.settings_file, "r") as f:
                return json.load(f)
        except:
            return {}

    def _temizle(self, ad):
        ad = ad.strip().lower()
        for prefix in ["https://kick.com/", "http://kick.com/", "kick.com/", "https://www.kick.com/", "www.kick.com/"]:
            if ad.startswith(prefix):
                ad = ad[len(prefix):]
                break
        return ad.split("/")[0].split("?")[0]

    async def _get_browser(self):
        if self.browser and self.browser.is_connected():
            return self.browser
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/render/project/.playwright")
        from playwright.async_api import async_playwright
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=True)
        return self.browser

    async def _api_ile_clip(self, channel_name):
        try:
            import urllib.request
            api_url = f"https://kick.com/api/v2/channels/{channel_name}/clips?page=1&per_page=1"
            req = urllib.request.Request(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Origin": "https://kick.com",
                "Referer": "https://kick.com/"
            })
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=15))
            body = await loop.run_in_executor(None, resp.read)
            data = json.loads(body.decode("utf-8"))
            clips = data.get("clips", [])
            if clips and len(clips) > 0:
                c = clips[0]
                clip_id = str(c.get("id", ""))
                return {
                    "id": clip_id,
                    "title": c.get("title") or c.get("slug") or c.get("description") or "",
                    "url": f"https://kick.com/{channel_name}/clips/{clip_id}",
                    "thumbnail": c.get("thumbnail_url") or c.get("thumb_url") or ""
                }
            return None
        except:
            return None

    async def _son_clip(self, channel_name):
        api_result = await self._api_ile_clip(channel_name)
        if api_result:
            return api_result

        try:
            browser = await self._get_browser()
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await ctx.new_page()
            url = f"https://kick.com/{channel_name}/clips"
            try:
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            except:
                await ctx.close()
                return None

            await page.wait_for_timeout(5000)

            clip_data = None
            try:
                hrefs = await page.evaluate("""
                    () => {
                        const links = document.querySelectorAll('a[href*="/clip/"]');
                        return Array.from(links).map(a => a.href);
                    }
                """)
                if hrefs and len(hrefs) > 0:
                    href = hrefs[0]
                    clip_id = href.split("/clip/")[-1].split("?")[0]
                    clip_data = {"id": clip_id, "url": href}
            except:
                pass

            if not clip_data:
                try:
                    html = await page.content()
                    matches = re.findall(r'/clip/([a-f0-9\-]+)', html)
                    if matches:
                        clip_id = matches[0]
                        clip_data = {"id": clip_id, "url": f"https://kick.com/clip/{clip_id}"}
                except:
                    pass

            if clip_data:
                try:
                    thumb = await page.evaluate(f"""
                        () => {{
                            const link = document.querySelector('a[href*="/clip/{clip_data['id']}"]');
                            if (!link) return null;
                            const img = link.querySelector('img');
                            return img ? img.src : null;
                        }}
                    """)
                    if thumb:
                        clip_data["thumbnail"] = thumb
                except:
                    pass

            await ctx.close()
            return clip_data
        except:
            return None

    @tasks.loop(minutes=5)
    async def check_clips(self):
        all_data = self._get_all()
        for gid_str, settings in all_data.items():
            for k in settings.get("kanallar", []):
                try:
                    son = await self._son_clip(k["kick_kanal"])
                    if not son:
                        continue
                    if son["id"] == k.get("son_id"):
                        continue
                    k["son_id"] = son["id"]
                    self._save_all(all_data)
                    guild = self.bot.get_guild(int(gid_str))
                    if not guild:
                        continue
                    kanal = guild.get_channel(int(k["kanal_id"]))
                    if not kanal:
                        continue
                    embed = discord.Embed(
                        title=son.get("title") or f"Yeni Klip — {k['kick_kanal']}",
                        url=son["url"],
                        color=discord.Color.purple(),
                        timestamp=datetime.now()
                    )
                    if son.get("thumbnail"):
                        embed.set_image(url=son["thumbnail"])
                    embed.add_field(name="Kanal", value=k['kick_kanal'], inline=True)
                    embed.add_field(name="Link", value=son["url"], inline=False)
                    mesaj = k.get("mesaj", "@everyone")
                    await kanal.send(content=mesaj, embed=embed)
                except:
                    pass

    @check_clips.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="kick-clip", description="Kick klip bildirimlerini ayarla")
    @app_commands.describe(
        ekle="Kick kanal adi veya URL (ornek: forsen)",
        kanal="Kliplerin atilacagi Discord kanali",
        mesaj="Klipten once yazilacak mesaj",
        listele="Mevcut takipleri listele (True/False)"
    )
    @app_commands.guild_only()
    async def kick_clip(self, interaction: discord.Interaction, ekle: str = None, kanal: discord.TextChannel = None, mesaj: str = None, listele: bool = False):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Yetkin yok!", ephemeral=True)
            return

        settings = self._get_settings(interaction.guild.id)

        if listele:
            if not settings["kanallar"]:
                await interaction.response.send_message("Takip edilen Kick kanali yok.")
                return
            liste = "\n".join([f"`{k['kick_kanal']}` → <#{k['kanal_id']}> — {k.get('mesaj', '@everyone')}" for k in settings["kanallar"]])
            await interaction.response.send_message(f"**Takip edilen kanallar:**\n{liste}")
            return

        if not ekle:
            await interaction.response.send_message("Lutfen bir Kick kanal adi girin!\nOrnek: `burakbilas` (kick.com/burakbilas)")
            return

        ekle = self._temizle(ekle)
        for k in settings["kanallar"]:
            if k["kick_kanal"] == ekle:
                await interaction.response.send_message("Bu kanal zaten takip ediliyor!")
                return

        yeni = {"kick_kanal": ekle, "kanal_id": str(kanal.id) if kanal else None, "mesaj": mesaj or "@everyone", "son_id": None}
        if not yeni["kanal_id"]:
            await interaction.response.send_message("Kanal belirtmelisiniz!")
            return

        settings["kanallar"].append(yeni)
        all_data = self._get_all()
        all_data[str(interaction.guild.id)] = settings
        self._save_all(all_data)
        await interaction.response.send_message(f"✅ `{ekle}` takip ediliyor. Yeni klip → <#{kanal.id}> / Mesaj: {yeni['mesaj']}")

    @app_commands.command(name="kick-clip-sil", description="Kick klip takibini kaldir")
    @app_commands.describe(kick_kanal="Kaldirilacak Kick kanal adi")
    @app_commands.guild_only()
    async def kick_clip_sil(self, interaction: discord.Interaction, kick_kanal: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Yetkin yok!", ephemeral=True)
            return

        settings = self._get_settings(interaction.guild.id)
        kick_kanal = self._temizle(kick_kanal)
        for i, k in enumerate(settings["kanallar"]):
            if k["kick_kanal"] == kick_kanal:
                settings["kanallar"].pop(i)
                all_data = self._get_all()
                all_data[str(interaction.guild.id)] = settings
                self._save_all(all_data)
                await interaction.response.send_message(f"❌ `{kick_kanal}` takipten cikarildi.")
                return
        await interaction.response.send_message("Bu kanal takip edilmiyor.")

    @app_commands.command(name="testkick-clip", description="Kick kanalinin son clipini test et")
    @app_commands.describe(kick_kanal="Kick kanal adi (ornek: forsen)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def testkick_clip(self, interaction: discord.Interaction, kick_kanal: str):
        await interaction.response.defer()
        kick_kanal = self._temizle(kick_kanal)
        son = await self._son_clip(kick_kanal)
        if not son:
            await interaction.followup.send(
                f"Clip bulunamadi. Su adrese bak: https://kick.com/{kick_kanal}/clips\n"
                f"Kanalda clip var mi kontrol et."
            )
            return
        embed = discord.Embed(
            title=son.get("title") or f"Son Klip — {kick_kanal}",
            url=son["url"],
            color=discord.Color.purple()
        )
        if son.get("thumbnail"):
            embed.set_image(url=son["thumbnail"])
        embed.add_field(name="Kanal", value=kick_kanal, inline=True)
        embed.add_field(name="Link", value=son["url"], inline=False)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(KickClip(bot))
