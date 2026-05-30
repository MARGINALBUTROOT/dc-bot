import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import re
import asyncio
from datetime import datetime

COOKIES_FILE = "facebook_cookies.json"
COOKIES_ENV = "FACEBOOK_COOKIES"

def _cookies_yukle():
    if os.path.exists(COOKIES_FILE):
        return True
    env_val = os.getenv(COOKIES_ENV)
    if env_val:
        try:
            data = json.loads(env_val)
            with open(COOKIES_FILE, "w") as f:
                json.dump(data, f)
            print(f"[Facebook] Cookies env'den yuklendi -> {COOKIES_FILE}")
            return True
        except:
            print(f"[Facebook] {COOKIES_ENV} env hatasi")
    return False

class Facebook(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "facebook_settings.json"
        self._init_settings()
        _cookies_yukle()
        self.browser = None
        self.check_facebook.start()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, "w") as f:
                json.dump({}, f)

    def _get_settings(self, guild_id):
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
            return data.get(str(guild_id), {"sayfalar": []})
        except:
            return {"sayfalar": []}

    def _save_all(self, data):
        with open(self.settings_file, "w") as f:
            json.dump(data, f, indent=4)

    def _get_all(self):
        try:
            with open(self.settings_file, "r") as f:
                return json.load(f)
        except:
            return {}

    async def _get_browser(self):
        if self.browser and self.browser.is_connected():
            return self.browser
        from playwright.async_api import async_playwright
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=True)
        return self.browser

    async def _sayfa_scrape(self, girilen):
        if not _cookies_yukle():
            return girilen, girilen, None

        girilen = girilen.strip().strip("/")
        for prefix in ["https://www.facebook.com/", "http://www.facebook.com/", "https://facebook.com/", "http://facebook.com/", "www.facebook.com/", "facebook.com/"]:
            if girilen.startswith(prefix):
                girilen = girilen[len(prefix):]
                break
        girilen = girilen.split("/")[0].split("?")[0].lower()

        try:
            browser = await self._get_browser()
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )

            with open(COOKIES_FILE, "r") as f:
                raw_cookies = json.load(f)
            for c in raw_cookies:
                if c.get("domain", "").endswith("facebook.com") or c.get("domain", "").endswith(".facebook.com"):
                    try:
                        await context.add_cookies([{
                            "name": c["name"],
                            "value": c["value"],
                            "domain": c.get("domain", ".facebook.com"),
                            "path": c.get("path", "/"),
                            "secure": c.get("secure", True),
                            "httpOnly": c.get("httpOnly", False),
                            "sameSite": c.get("sameSite", "Lax"),
                        }])
                    except:
                        pass

            page = await context.new_page()
            await page.goto(f"https://www.facebook.com/{girilen}", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            title = await page.title()
            sayfa_adi = title if title else girilen

            posts = await page.evaluate("""
                () => {
                    const items = [];
                    const articles = document.querySelectorAll('[data-pagelet^="FeedUnit"], article, [role="article"]');
                    articles.forEach(el => {
                        const textEl = el.querySelector('[dir="auto"]');
                        const text = textEl ? textEl.innerText : '';
                        const links = el.querySelectorAll('a[href*="/posts/"], a[href*="/photo/"], a[href*="/video/"]');
                        let url = '';
                        if (links.length > 0) url = links[0].href.split('?')[0];
                        const imgs = el.querySelectorAll('img[src*="scontent"]');
                        const imgUrl = imgs.length > 0 ? imgs[0].src : '';
                        const id = url.split('/').pop().split('?')[0] || text.slice(0, 50);
                        items.push({ post_id: id, mesaj: text.slice(0, 500), resim: imgUrl, url: url });
                    });
                    return items.slice(0, 5);
                }
            """)

            await context.close()
            return girilen, sayfa_adi, posts if posts else []

        except Exception as e:
            print(f"[FACEBOOK SCRAPE HATA] {e}")
            try: await context.close()
            except: pass
            return girilen, girilen, None

    @app_commands.command(name="facebook", description="Facebook sayfa bildirimleri")
    @app_commands.describe(
        sayfa="Facebook sayfa kullanici adi veya URL (ornek: natgeo)",
        kanal="Yeni post atildiginda bildirim gidecek kanal",
        mesaj="Posttan once gonderilecek ozel mesaj (opsiyonel)",
        listele="Mevcut takipleri listele"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def facebook(
        self,
        interaction: discord.Interaction,
        sayfa: str = None,
        kanal: discord.TextChannel = None,
        mesaj: str = None,
        listele: bool = False
    ):
        settings = self._get_settings(interaction.guild.id)

        if listele:
            embed = discord.Embed(title="Facebook Bildirimler", color=discord.Color(0x1877F2))
            sayfalar = settings.get("sayfalar", [])
            if sayfalar:
                for h in sayfalar:
                    deger = f"Kanal: <#{h['kanal_id']}>"
                    if h.get("mesaj"):
                        deger += f"\nMesaj: {h['mesaj']}"
                    embed.add_field(name=h.get("page_name", h["sayfa"]), value=deger, inline=False)
            else:
                embed.description = "Henuz takip edilen sayfa yok."
            await interaction.response.send_message(embed=embed)
            return

        if not sayfa and not kanal:
            embed = discord.Embed(title="Facebook Bildirimler", color=discord.Color(0x1877F2))
            embed.description = "Kullanım: `/facebook sayfa:sayfa_adi kanal:#kanal mesaj:opsiyonel`"
            await interaction.response.send_message(embed=embed)
            return

        if not sayfa or not kanal:
            await interaction.response.send_message("Sayfa adi ve kanal gerekli!", ephemeral=True)
            return

        sayfa_adi = sayfa.strip().lower()
        for prefix in ["https://www.facebook.com/", "http://www.facebook.com/", "https://facebook.com/", "http://facebook.com/", "www.facebook.com/", "facebook.com/"]:
            if sayfa_adi.startswith(prefix):
                sayfa_adi = sayfa_adi[len(prefix):]
                break
        sayfa_adi = sayfa_adi.split("/")[0].split("?")[0]

        sayfalar = settings.get("sayfalar", [])
        for h in sayfalar:
            if h["sayfa"] == sayfa_adi:
                if mesaj:
                    h["mesaj"] = mesaj
                    self._save_all(self._get_all() | {str(interaction.guild.id): settings})
                    await interaction.response.send_message(f"Sayfa icin mesaj guncellendi: {mesaj}")
                else:
                    await interaction.response.send_message("Bu sayfa zaten takip ediliyor!")
                return

        yeni = {"sayfa": sayfa_adi, "page_id": sayfa_adi, "page_name": sayfa_adi, "kanal_id": str(kanal.id), "son_post_id": None}
        if mesaj:
            yeni["mesaj"] = mesaj
        sayfalar.append(yeni)
        settings["sayfalar"] = sayfalar
        all_data = {}
        try:
            with open(self.settings_file, "r") as f:
                all_data = json.load(f)
        except:
            pass
        all_data[str(interaction.guild.id)] = settings
        self._save_all(all_data)

        embed = discord.Embed(title="Facebook Sayfa Eklendi", color=discord.Color(0x1877F2))
        embed.add_field(name="Sayfa", value=sayfa_adi, inline=False)
        embed.add_field(name="Bildirim Kanal", value=kanal.mention, inline=False)
        if mesaj:
            embed.add_field(name="Mesaj", value=mesaj, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="testfacebook", description="Facebook bildirimlerini test et")
    @app_commands.describe(sayfa="Test edilecek sayfa adi (opsiyonel, bos = tumu)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def testfacebook(self, interaction: discord.Interaction, sayfa: str = None):
        if not _cookies_yukle():
            await interaction.response.send_message("Facebook cookie dosyasi bulunamadi!\n`FACEBOOK_COOKIES` env degiskenini de dene.", ephemeral=True)
            return
        settings = self._get_settings(interaction.guild.id)
        sayfalar = settings.get("sayfalar", [])
        if sayfa:
            sayfalar = [h for h in sayfalar if h["sayfa"].lower() == sayfa.strip().lower()]
        if not sayfalar:
            await interaction.response.send_message("Henuz takip edilen sayfa yok veya sayfa bulunamadi!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        gonderildi = 0
        for h in sayfalar:
            try:
                _, _, posts = await self._sayfa_scrape(h["sayfa"])
                if posts:
                    son = posts[0]
                    kanal_obj = interaction.guild.get_channel(int(h["kanal_id"]))
                    if kanal_obj:
                        mesaj_gonder = h.get("mesaj")
                        if mesaj_gonder:
                            await kanal_obj.send(mesaj_gonder)
                        embed = discord.Embed(
                            title=f"📘 [TEST] {h.get('page_name', h['sayfa'])}",
                            url=son["url"] or f"https://www.facebook.com/{h['sayfa']}",
                            color=discord.Color(0x1877F2)
                        )
                        if son.get("mesaj"):
                            embed.description = son["mesaj"][:200]
                        if son.get("resim"):
                            embed.set_image(url=son["resim"])
                        embed.set_footer(text="Bu bir test bildirimdir")
                        await kanal_obj.send(embed=embed)
                        gonderildi += 1
                    if son.get("post_id"):
                        h["son_post_id"] = son["post_id"]
            except Exception as e:
                print(f"[FACEBOOK TEST HATA] {e}")
        if gonderildi > 0:
            try:
                self._save_all(self._get_all() | {str(interaction.guild.id): settings})
            except Exception as e:
                print(f"[FACEBOOK KAYIT HATA] {e}")
        await interaction.followup.send(f"Test bildirimi {gonderildi} kanala gonderildi.", ephemeral=True)

    @tasks.loop(minutes=5)
    async def check_facebook(self):
        if not _cookies_yukle():
            return
        all_data = self._get_all()
        for gid, settings in all_data.items():
            guild = self.bot.get_guild(int(gid))
            if not guild:
                continue
            for h in settings.get("sayfalar", []):
                try:
                    _, _, posts = await self._sayfa_scrape(h["sayfa"])
                    if not posts:
                        continue
                    son = posts[0]
                    post_id = son["post_id"]
                    kanal_id = int(h["kanal_id"])
                    bildirim_kanal = guild.get_channel(kanal_id)
                    if not bildirim_kanal:
                        continue
                    if post_id and post_id != h.get("son_post_id"):
                        embed = discord.Embed(
                            title=f"📘 {h.get('page_name', h['sayfa'])} yeni post",
                            url=son["url"] or f"https://www.facebook.com/{h['sayfa']}",
                            color=discord.Color(0x1877F2)
                        )
                        if son.get("mesaj"):
                            embed.description = son["mesaj"][:200]
                        if son.get("resim"):
                            embed.set_image(url=son["resim"])
                        try:
                            mesaj_gonder = h.get("mesaj")
                            if mesaj_gonder:
                                await bildirim_kanal.send(mesaj_gonder)
                            await bildirim_kanal.send(embed=embed)
                        except:
                            pass
                        h["son_post_id"] = post_id
                        all_data[gid] = settings
                        self._save_all(all_data)
                except:
                    pass

    @check_facebook.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Facebook(bot))
