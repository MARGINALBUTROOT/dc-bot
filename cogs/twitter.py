import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import re
import asyncio

COOKIES_FILE = "twitter_cookies.json"
COOKIES_ENV = "TWITTER_COOKIES"

def _cookies_yukle():
    if os.path.exists(COOKIES_FILE):
        return True
    env_val = os.getenv(COOKIES_ENV)
    if env_val:
        try:
            data = json.loads(env_val)
            with open(COOKIES_FILE, "w") as f:
                json.dump(data, f)
            print(f"[Twitter] Cookies env'den yuklendi -> {COOKIES_FILE}")
            return True
        except:
            print(f"[Twitter] {COOKIES_ENV} env hatasi")
    return False

class Twitter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "twitter_settings.json"
        self._init_settings()
        _cookies_yukle()
        self.browser = None
        self.check_twitter.start()

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

    async def _kullanici_scrape(self, kullanici):
        if not _cookies_yukle():
            return kullanici, kullanici, None

        kullanici = kullanici.strip().strip("@").strip("/")
        for prefix in ["https://x.com/", "http://x.com/", "https://twitter.com/", "http://twitter.com/", "x.com/", "twitter.com/"]:
            if kullanici.lower().startswith(prefix):
                kullanici = kullanici[len(prefix):]
                break
        kullanici = kullanici.split("/")[0].split("?")[0]

        try:
            browser = await self._get_browser()
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )

            with open(COOKIES_FILE, "r") as f:
                raw_cookies = json.load(f)
            for c in raw_cookies:
                if any(d in (c.get("domain", "") or "") for d in ["x.com", "twitter.com"]):
                    try:
                        await context.add_cookies([{
                            "name": c["name"],
                            "value": c["value"],
                            "domain": c.get("domain", ".x.com"),
                            "path": c.get("path", "/"),
                            "secure": c.get("secure", True),
                            "httpOnly": c.get("httpOnly", False),
                            "sameSite": c.get("sameSite", "Lax"),
                        }])
                    except:
                        pass

            page = await context.new_page()
            await page.goto(f"https://x.com/{kullanici}", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)

            sayfa_adi = kullanici

            tweets = await page.evaluate("""
                () => {
                    const items = [];
                    const articles = document.querySelectorAll('article[data-testid="tweet"]');
                    articles.forEach(el => {
                        const textEl = el.querySelector('[data-testid="tweetText"]');
                        const text = textEl ? textEl.innerText : '';
                    const links = el.querySelectorAll('a[href*="/status/"]');
                        let url = '';
                        let tweetId = '';
                        if (links.length > 0) {
                            url = links[0].href.split('?')[0];
                            const match = url.match(/\\/status\\/(\\d+)/);
                            if (match) tweetId = match[1];
                        }
                        const imgs = el.querySelectorAll('img[src*="media"], img[src*="pbs.twimg"]');
                        const imgUrl = imgs.length > 0 ? imgs[imgs.length - 1].src : '';
                        const isRetweet = el.querySelector('[data-testid="socialContext"]') !== null;
                        if (!tweetId) tweetId = text.slice(0, 50);
                        items.push({ tweet_id: tweetId, mesaj: text.slice(0, 500), resim: imgUrl, url: url, rt: isRetweet });
                    });
                    return items.slice(0, 5);
                }
            """)

            await context.close()
            return kullanici, sayfa_adi, tweets if tweets else []

        except Exception as e:
            print(f"[TWITTER SCRAPE HATA] {e}")
            try: await context.close()
            except: pass
            return kullanici, kullanici, None

    @app_commands.command(name="x-twitter", description="X/Twitter hesap bildirimleri")
    @app_commands.describe(
        kullanici="X kullanici adi (@ornek)",
        kanal="Yeni tweet atildiginda bildirim gidecek kanal",
        mesaj="Tweetten once gonderilecek ozel mesaj (opsiyonel)",
        listele="Mevcut takipleri listele"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def x_twitter(
        self,
        interaction: discord.Interaction,
        kullanici: str = None,
        kanal: discord.TextChannel = None,
        mesaj: str = None,
        listele: bool = False
    ):
        if not _cookies_yukle():
            await interaction.response.send_message(
                "Twitter cookie dosyasi bulunamadi!\n\n"
                "**Adim adim kurulum:**\n"
                "1. Chrome web magazadan `EditThisCookie` eklentisini kur\n"
                "2. X.com'a gir ve login ol\n"
                "3. Eklenti ikonuna tikla -> Export tusuna bas (panoya kopyalar)\n"
                "4. Notepad ac -> Ctrl+V -> `twitter_cookies.json` olarak bot klasorune kaydet\n"
                "5. Veya `TWITTER_COOKIES` env degiskenine JSON'u tek satir olarak ekle\n"
                "6. Bu komutu tekrar dene",
                ephemeral=True
            )
            return

        settings = self._get_settings(interaction.guild.id)

        if listele or (not kullanici and not kanal):
            embed = discord.Embed(title="X/Twitter Bildirimler", color=discord.Color(0x1DA1F2))
            hesaplar = settings.get("hesaplar", [])
            if hesaplar:
                for h in hesaplar:
                    deger = f"Kanal: <#{h['kanal_id']}>"
                    if h.get("mesaj"):
                        deger += f"\nMesaj: {h['mesaj']}"
                    embed.add_field(name=f"@{h['kullanici']}", value=deger, inline=False)
            else:
                embed.description = "Henuz takip edilen hesap yok.\n`/x-twitter kullanici:hesap kanal:#kanal mesaj:opsiyonel`"
            await interaction.response.send_message(embed=embed)
            return

        if not kullanici or not kanal:
            await interaction.response.send_message("Kullanici adi ve kanal gerekli!", ephemeral=True)
            return

        await interaction.response.defer()
        page_id, page_name, tweets = await self._kullanici_scrape(kullanici)
        hesaplar = settings.get("hesaplar", [])

        for h in hesaplar:
            if h["kullanici"].lower() == kullanici.strip().lower().lstrip("@"):
                if mesaj:
                    h["mesaj"] = mesaj
                    self._save_all(self._get_all() | {str(interaction.guild.id): settings})
                    await interaction.followup.send(f"@{kullanici} icin mesaj guncellendi: {mesaj}", ephemeral=True)
                else:
                    await interaction.followup.send("Bu hesap zaten takip ediliyor! Mesaj degistirmek icin `mesaj` parametresini kullan.", ephemeral=True)
                return

        yeni = {"kullanici": kullanici.strip().lstrip("@"), "kanal_id": str(kanal.id), "son_tweet_id": None}
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

        embed = discord.Embed(title="X/Twitter Hesap Eklendi", color=discord.Color(0x1DA1F2))
        embed.add_field(name="Kullanici", value=f"@{kullanici}", inline=False)
        embed.add_field(name="Bildirim Kanal", value=kanal.mention, inline=False)
        if mesaj:
            embed.add_field(name="Mesaj", value=mesaj, inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="x-twitter-test", description="X/Twitter bildirimlerini test et")
    @app_commands.describe(kullanici="Test edilecek kullanici adi (opsiyonel, bos = tumu)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def x_twitter_test(self, interaction: discord.Interaction, kullanici: str = None):
        if not _cookies_yukle():
            await interaction.response.send_message("Twitter cookie dosyasi bulunamadi!\n`TWITTER_COOKIES` env degiskenini de dene.", ephemeral=True)
            return
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
                _, _, tweets = await self._kullanici_scrape(h["kullanici"])
                if tweets:
                    son = tweets[0]
                    kanal_obj = interaction.guild.get_channel(int(h["kanal_id"]))
                    if kanal_obj:
                        mesaj_gonder = h.get("mesaj")
                        if mesaj_gonder:
                            await kanal_obj.send(mesaj_gonder)
                        embed = discord.Embed(
                            title=f"🐦 [TEST] @{h['kullanici']}",
                            url=son["url"] or f"https://x.com/{h['kullanici']}",
                            color=discord.Color(0x1DA1F2)
                        )
                        if son.get("mesaj"):
                            embed.description = son["mesaj"][:200]
                        if son.get("resim"):
                            embed.set_image(url=son["resim"])
                        embed.set_footer(text="Bu bir test bildirimdir")
                        await kanal_obj.send(embed=embed)
                        gonderildi += 1
                    if son.get("tweet_id"):
                        h["son_tweet_id"] = son["tweet_id"]
            except Exception as e:
                print(f"[TWITTER TEST HATA] {e}")
        if gonderildi > 0:
            try:
                self._save_all(self._get_all() | {str(interaction.guild.id): settings})
            except Exception as e:
                print(f"[TWITTER KAYIT HATA] {e}")
        await interaction.followup.send(f"Test bildirimi {gonderildi} kanala gonderildi.", ephemeral=True)

    @tasks.loop(minutes=5)
    async def check_twitter(self):
        if not _cookies_yukle():
            return
        all_data = self._get_all()
        for gid, settings in all_data.items():
            guild = self.bot.get_guild(int(gid))
            if not guild:
                continue
            for h in settings.get("hesaplar", []):
                try:
                    _, _, tweets = await self._kullanici_scrape(h["kullanici"])
                    if not tweets:
                        continue
                    son = tweets[0]
                    tweet_id = son["tweet_id"]
                    kanal_id = int(h["kanal_id"])
                    bildirim_kanal = guild.get_channel(kanal_id)
                    if not bildirim_kanal:
                        continue
                    if tweet_id and tweet_id != h.get("son_tweet_id"):
                        embed = discord.Embed(
                            title=f"🐦 @{h['kullanici']} yeni tweet",
                            url=son["url"] or f"https://x.com/{h['kullanici']}",
                            color=discord.Color(0x1DA1F2)
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
                        h["son_tweet_id"] = tweet_id
                        all_data[gid] = settings
                        self._save_all(all_data)
                except:
                    pass

    @check_twitter.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Twitter(bot))
