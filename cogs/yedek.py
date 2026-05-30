import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import shutil
from datetime import datetime

BACKUP_DIR = "backups"

ILGILI_DOSYALAR = [
    "ozel_komutlar.json", "facebook_settings.json", "instagram_settings.json",
    "twitter_settings.json", "voice_settings.json", "log_settings.json",
    "ticket_settings.json", "reaction_roles.json", "otorol_settings.json",
    "karsilama_settings.json", "dogrulama_settings.json", "antibot_settings.json",
    "autmod_settings.json", "kick_clips_settings.json", "warns.json", "warns_storage.json", "modlogs.json",
    "dogrulama_logs.json", "bot_status.json", "facebook_cookies.json", "twitter_cookies.json"
]

def _guild_data_cek(guild_id):
    data = {"guild_id": guild_id, "tarih": datetime.now().isoformat()}
    for dosya in ILGILI_DOSYALAR:
        if not os.path.exists(dosya):
            continue
        with open(dosya, "r", encoding="utf-8") as f:
            icerik = json.load(f)
        if isinstance(icerik, dict):
            if str(guild_id) in icerik:
                data[dosya] = icerik[str(guild_id)]
        elif isinstance(icerik, list):
            guild_entries = [e for e in icerik if str(e.get("guild_id", "")) == str(guild_id)]
            if guild_entries:
                data[dosya] = guild_entries
    return data

def _guild_data_yaz(guild_id, backup_data):
    for dosya in ILGILI_DOSYALAR:
        if dosya not in backup_data:
            continue
        if not os.path.exists(dosya):
            with open(dosya, "w", encoding="utf-8") as f:
                json.dump({} if dosya != "dogrulama_logs.json" else [], f)
        with open(dosya, "r", encoding="utf-8") as f:
            icerik = json.load(f)
        if isinstance(icerik, dict):
            icerik[str(guild_id)] = backup_data[dosya]
        elif isinstance(icerik, list):
            mevcut = [e for e in icerik if str(e.get("guild_id", "")) != str(guild_id)]
            mevcut.extend(backup_data[dosya])
            icerik = mevcut
        with open(dosya, "w", encoding="utf-8") as f:
            json.dump(icerik, f, indent=4, ensure_ascii=False)
    return True

class YedekSilSelect(discord.ui.Select):
    def __init__(self, guild_id, yedekler):
        self.guild_id = guild_id
        options = [discord.SelectOption(label=y["label"], value=y["dosya"], description=y["tarih"]) for y in yedekler[:25]]
        super().__init__(placeholder="Silinecek yedeği seçin", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        dosya = self.values[0]
        dosya_yol = os.path.join(BACKUP_DIR, dosya)
        if os.path.exists(dosya_yol):
            os.remove(dosya_yol)
            await interaction.response.send_message(f"Yedek silindi: `{dosya}`", ephemeral=True)
        else:
            await interaction.response.send_message("Yedek bulunamadı.", ephemeral=True)

class YedekYukleSelect(discord.ui.Select):
    def __init__(self, cog, guild_id, yedekler):
        self.cog = cog
        self.guild_id = guild_id
        options = [discord.SelectOption(label=y["label"], value=y["dosya"], description=y["tarih"]) for y in yedekler[:25]]
        super().__init__(placeholder="Yüklenecek yedeği seçin", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        dosya = self.values[0]
        dosya_yol = os.path.join(BACKUP_DIR, dosya)
        if not os.path.exists(dosya_yol):
            await interaction.response.send_message("Yedek dosyası bulunamadı.", ephemeral=True)
            return
        with open(dosya_yol, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        if _guild_data_yaz(self.guild_id, backup_data):
            await interaction.response.send_message("Yedek başarıyla yüklendi! Tüm ayarlar geri getirildi.", ephemeral=True)
        else:
            await interaction.response.send_message("Yedek yüklenirken hata oluştu.", ephemeral=True)

class YedekListeView(discord.ui.View):
    def __init__(self, guild_id, yedekler):
        super().__init__(timeout=60)
        if yedekler:
            self.add_item(YedekSilSelect(guild_id, yedekler))

class YedekYukleView(discord.ui.View):
    def __init__(self, cog, guild_id, yedekler):
        super().__init__(timeout=60)
        if yedekler:
            self.add_item(YedekYukleSelect(cog, guild_id, yedekler))

class YedekView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.button(label="Yedek Al", style=discord.ButtonStyle.green, emoji="💾")
    async def yedek_al(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu butonu sadece yöneticiler kullanabilir!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        data = _guild_data_cek(self.guild_id)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dosya_adi = f"yedek_{self.guild_id}_{ts}.json"
        with open(os.path.join(BACKUP_DIR, dosya_adi), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        info = []
        for dosya in ILGILI_DOSYALAR:
            if dosya in data:
                val = data[dosya]
                if isinstance(val, list):
                    info.append(f"{dosya}: {len(val)} kayıt")
                elif isinstance(val, dict):
                    info.append(f"{dosya}: {len(val)} alan")
                else:
                    info.append(dosya)
        embed = discord.Embed(title="Yedek Alındı", color=discord.Color.green())
        embed.add_field(name="Dosya", value=f"`{dosya_adi}`", inline=False)
        embed.add_field(name="İçerik", value="\n".join(info) if info else "Veri bulunamadı", inline=False)
        embed.set_footer(text=f"Toplam {len(info)} dosya yedeklendi")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Yedek Listesi", style=discord.ButtonStyle.blurple, emoji="📂")
    async def yedek_liste(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu butonu sadece yöneticiler kullanabilir!", ephemeral=True)
            return
        if not os.path.exists(BACKUP_DIR):
            await interaction.response.send_message("Hiç yedek bulunamadı.", ephemeral=True)
            return
        dosyalar = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".json") and str(self.guild_id) in f], reverse=True)
        if not dosyalar:
            await interaction.response.send_message("Bu sunucuya ait yedek bulunamadı.", ephemeral=True)
            return
        yedekler = []
        embed = discord.Embed(title="Yedek Listesi", color=discord.Color.blue())
        for d in dosyalar[:10]:
            yol = os.path.join(BACKUP_DIR, d)
            boyut = os.path.getsize(yol)
            tarih = d.split("_")[-1].replace(".json", "").replace("_", " ")
            label = f"{tarih} ({boyut/1024:.1f}KB)"
            embed.add_field(name=d[:40], value=label, inline=False)
            yedekler.append({"label": tarih, "dosya": d, "tarih": f"{boyut/1024:.1f}KB"})
        if len(dosyalar) > 10:
            embed.set_footer(text=f"Toplam {len(dosyalar)} yedek (son 10 gösteriliyor)")
        view = YedekListeView(self.guild_id, yedekler)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Yedek Yükle", style=discord.ButtonStyle.gray, emoji="⏫")
    async def yedek_yukle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu butonu sadece yöneticiler kullanabilir!", ephemeral=True)
            return
        if not os.path.exists(BACKUP_DIR):
            await interaction.response.send_message("Hiç yedek bulunamadı.", ephemeral=True)
            return
        dosyalar = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".json") and str(self.guild_id) in f], reverse=True)
        if not dosyalar:
            await interaction.response.send_message("Bu sunucuya ait yedek bulunamadı.", ephemeral=True)
            return
        yedekler = []
        for d in dosyalar[:25]:
            yol = os.path.join(BACKUP_DIR, d)
            boyut = os.path.getsize(yol)
            tarih = d.split("_")[-1].replace(".json", "").replace("_", " ")
            yedekler.append({"label": tarih, "dosya": d, "tarih": f"{boyut/1024:.1f}KB"})
        await interaction.response.send_message("Yüklenecek yedeği seçin:", view=YedekYukleView(self.cog, self.guild_id, yedekler), ephemeral=True)

def _auto_yedek_al(guild_id, guild_name="Bilinmiyor"):
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    data = _guild_data_cek(guild_id)
    data["guild_name"] = guild_name
    data["guild_id"] = str(guild_id)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dosya_adi = f"yedek_{guild_id}_{ts}.json"
    with open(os.path.join(BACKUP_DIR, dosya_adi), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return dosya_adi

class Yedek(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("[YEDEK] Bot basladi, tum sunucular yedekleniyor...")
        say = 0
        for guild in self.bot.guilds:
            try:
                _auto_yedek_al(guild.id, guild.name)
                say += 1
            except Exception as e:
                print(f"[YEDEK] {guild.name} yedeklenirken hata: {e}")
        print(f"[YEDEK] {say} sunucu yedeklendi.")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try:
            dosya = _auto_yedek_al(guild.id, guild.name)
            print(f"[YEDEK] {guild.name} sunucusu yedeklendi: {dosya}")
        except Exception as e:
            print(f"[YEDEK] {guild.name} yedeklenirken hata: {e}")

    @app_commands.command(name="yedek-yukle", description="Yedekten ayarları geri yükle (admin)")
    @app_commands.guild_only()
    async def yedek_yukle(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu komutu sadece yöneticiler kullanabilir!", ephemeral=True)
            return
        if not os.path.exists(BACKUP_DIR):
            await interaction.response.send_message("Hiç yedek bulunamadı.", ephemeral=True)
            return
        dosyalar = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".json") and str(interaction.guild_id) in f], reverse=True)
        if not dosyalar:
            await interaction.response.send_message("Bu sunucuya ait yedek bulunamadı.", ephemeral=True)
            return
        yedekler = []
        for d in dosyalar[:25]:
            yol = os.path.join(BACKUP_DIR, d)
            boyut = os.path.getsize(yol)
            tarih = d.split("_")[-1].replace(".json", "").replace("_", " ")
            yedekler.append({"label": tarih, "dosya": d, "tarih": f"{boyut/1024:.1f}KB"})
        await interaction.response.send_message("Yüklenecek yedeği seçin:", view=YedekYukleView(self, interaction.guild_id, yedekler), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Yedek(bot))
