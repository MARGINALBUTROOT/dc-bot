import discord
from discord.ext import commands, tasks
from discord import app_commands
import urllib.request
import json
import os

class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "instagram_settings.json"
        self._init_settings()
        self.check_instagram.start()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, "w") as f:
                json.dump({}, f)

    def _get_settings(self, guild_id):
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
            return data.get(str(guild_id), {"hesaplar": []})
        except:
            return {"hesaplar": []}

    def _save_all(self, data):
        with open(self.settings_file, "w") as f:
            json.dump(data, f, indent=4)

    def _fetch_son_paylasim(self, kullanici):
        url = "https://www.instagram.com/" + kullanici + "/embed/"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="ignore")
        start = html.find('"contextJSON":"')
        if start == -1:
            return None
        nav = html.find("NavigationMetrics", start)
        if nav == -1:
            return None
        close_mark = html.rfind('"}]],', start, nav)
        if close_mark == -1:
            return None
        ham = html[start+15:close_mark]
        cozuldu = json.loads('"' + ham + '"')
        data = json.loads(cozuldu)
        context = data.get("context", {})
        media_list = context.get("graphql_media", [])
        if not media_list:
            return None
        ilk = media_list[0].get("shortcode_media", {})
        typename = ilk.get("__typename", "")
        tur = "Fotoğraf"
        if typename == "GraphVideo":
            tur = "Video"
        elif typename == "GraphSidecar":
            tur = "Albüm"
        return {
            "shortcode": ilk.get("shortcode"),
            "baslik": (
                ilk.get("edge_media_to_caption", {})
                .get("edges", [{}])[0]
                .get("node", {})
                .get("text", "")
            ),
            "timestamp": ilk.get("taken_at_timestamp"),
            "tur": tur,
        }

    @app_commands.command(name="instagram", description="Instagram hesap bildirimleri")
    @app_commands.describe(
        kullanici="Instagram kullanici adi (ornek: natgeotr)",
        kanal="Yeni post atildiginda bildirim gidecek kanal",
        mesaj="Posttan once gonderilecek ozel mesaj (opsiyonel)",
        listele="Mevcut takipleri listele"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def instagram(
        self,
        interaction: discord.Interaction,
        kullanici: str = None,
        kanal: discord.TextChannel = None,
        mesaj: str = None,
        listele: bool = False
    ):
        settings = self._get_settings(interaction.guild.id)

        if listele or (not kullanici and not kanal):
            embed = discord.Embed(title="Instagram Bildirimler", color=discord.Color(0xE1306C))
            hesaplar = settings.get("hesaplar", [])
            if hesaplar:
                for h in hesaplar:
                    deger = f"Kanal: <#{h['kanal_id']}>"
                    if h.get("mesaj"):
                        deger += f"\nMesaj: {h['mesaj']}"
                    embed.add_field(name=f"@{h['kullanici']}", value=deger, inline=False)
            else:
                embed.description = "Henuz takip edilen hesap yok.\n`/instagram kullanici:hesap kanal:#kanal mesaj:opsiyonel`"
            await interaction.response.send_message(embed=embed)
            return

        if not kullanici or not kanal:
            await interaction.response.send_message("Kullanici adi ve kanal gerekli!", ephemeral=True)
            return

        kullanici = kullanici.strip().lstrip("@").lower()
        hesaplar = settings.get("hesaplar", [])

        for h in hesaplar:
            if h["kullanici"] == kullanici:
                if mesaj:
                    h["mesaj"] = mesaj
                    self._save_all(self._get_all() | {str(interaction.guild.id): settings})
                    await interaction.response.send_message(f"@{kullanici} icin mesaj guncellendi: {mesaj}")
                else:
                    await interaction.response.send_message("Bu hesap zaten takip ediliyor! Mesaj degistirmek icin `mesaj` parametresini kullan.")
                return

        yeni = {"kullanici": kullanici, "kanal_id": str(kanal.id), "son_post_id": None}
        if mesaj:
            yeni["mesaj"] = mesaj
        hesaplar.append(yeni)
        settings["hesaplar"] = hesaplar
        all_data = {}
        try:
            with open(self.settings_file, "r") as f:
                all_data = json.load(f)
        except:
            pass
        all_data[str(interaction.guild.id)] = settings
        self._save_all(all_data)

        embed = discord.Embed(title="Instagram Eklendi", color=discord.Color(0xE1306C))
        embed.add_field(name="Hesap", value=f"@{kullanici}", inline=False)
        embed.add_field(name="Bildirim Kanal", value=kanal.mention, inline=False)
        if mesaj:
            embed.add_field(name="Mesaj", value=mesaj, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="testinstagram", description="Instagram bildirimlerini test et")
    @app_commands.describe(kullanici="Test edilecek kullanici adi (opsiyonel, bos = tumu)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def testinstagram(self, interaction: discord.Interaction, kullanici: str = None):
        settings = self._get_settings(interaction.guild.id)
        hesaplar = settings.get("hesaplar", [])
        if kullanici:
            hesaplar = [h for h in hesaplar if h["kullanici"].lower() == kullanici.strip().lstrip("@").lower()]
        if not hesaplar:
            await interaction.response.send_message("Henuz takip edilen hesap yok veya kullanici bulunamadi!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        gonderildi = 0
        for h in hesaplar:
            try:
                son = self._fetch_son_paylasim(h["kullanici"])
                if son:
                    kanal_obj = interaction.guild.get_channel(int(h["kanal_id"]))
                    if kanal_obj:
                        mesaj_gonder = h.get("mesaj")
                        if mesaj_gonder:
                            await kanal_obj.send(mesaj_gonder)
                        embed = discord.Embed(
                            title=f"📸 [TEST] @{h['kullanici']} - {son['tur']}",
                            url=f"https://www.instagram.com/p/{son['shortcode']}/",
                            color=discord.Color(0xE1306C)
                        )
                        if son["baslik"]:
                            embed.description = son["baslik"][:200]
                        embed.set_footer(text="Bu bir test bildirimdir")
                        await kanal_obj.send(embed=embed)
                        gonderildi += 1
                    if son.get("shortcode"):
                        h["son_post_id"] = son["shortcode"]
            except Exception as e:
                print(f"[INSTAGRAM TEST HATA] {e}")
        if gonderildi > 0:
            try:
                self._save_all(self._get_all() | {str(interaction.guild.id): settings})
            except Exception as e:
                print(f"[INSTAGRAM KAYIT HATA] {e}")
        await interaction.followup.send(f"Test bildirimi {gonderildi} kanala gonderildi.", ephemeral=True)

    def _get_all(self):
        try:
            with open(self.settings_file, "r") as f:
                return json.load(f)
        except:
            return {}

    @tasks.loop(minutes=5)
    async def check_instagram(self):
        all_data = self._get_all()
        for gid, settings in all_data.items():
            guild = self.bot.get_guild(int(gid))
            if not guild:
                continue
            for h in settings.get("hesaplar", []):
                try:
                    son = self._fetch_son_paylasim(h["kullanici"])
                    if not son:
                        continue
                    post_id = son["shortcode"]
                    kanal_id = int(h["kanal_id"])
                    bildirim_kanal = guild.get_channel(kanal_id)
                    if not bildirim_kanal:
                        continue
                    if post_id and post_id != h.get("son_post_id"):
                        embed = discord.Embed(
                            title=f"📸 @{h['kullanici']} yeni {son['tur']}",
                            url=f"https://www.instagram.com/p/{post_id}/",
                            color=discord.Color(0xE1306C)
                        )
                        if son["baslik"]:
                            embed.description = son["baslik"][:200]
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

    @check_instagram.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Instagram(bot))
