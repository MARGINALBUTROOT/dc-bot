import discord
from discord.ext import commands
import json
import os

OZEL_KOMUT_FILE = "ozel_komutlar.json"

def _load():
    if not os.path.exists(OZEL_KOMUT_FILE):
        return {}
    with open(OZEL_KOMUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data):
    with open(OZEL_KOMUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class KomutEkleModal(discord.ui.Modal, title="Özel Komut Ekle"):
    komut_adi = discord.ui.TextInput(label="Komut Adı", placeholder="örnek: !merhaba", required=True, max_length=50)
    yanit = discord.ui.TextInput(label="Yanıt Mesajı", placeholder="Botun vereceği yanıt", required=True, max_length=2000, style=discord.TextStyle.paragraph)

    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        ad = self.komut_adi.value.strip().lower()
        if not ad.startswith("!"):
            ad = "!" + ad
        data = _load()
        gid = str(self.guild_id)
        if gid not in data:
            data[gid] = {}
        if ad in data[gid]:
            await interaction.response.send_message(f"`{ad}` komutu zaten mevcut!", ephemeral=True)
            return
        data[gid][ad] = self.yanit.value
        _save(data)
        embed = discord.Embed(title="Özel Komut Eklendi", color=discord.Color.green())
        embed.add_field(name="Komut", value=f"`{ad}`", inline=True)
        embed.add_field(name="Yanıt", value=self.yanit.value[:500], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class KomutSilSelect(discord.ui.Select):
    def __init__(self, cog, guild_id, komutlar):
        self.cog = cog
        self.guild_id = guild_id
        options = [discord.SelectOption(label=k, value=k) for k in komutlar[:25]]
        super().__init__(placeholder="Silinecek komutu seçin", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        ad = self.values[0]
        data = _load()
        gid = str(self.guild_id)
        if gid in data and ad in data[gid]:
            del data[gid][ad]
            if not data[gid]:
                del data[gid]
            _save(data)
            await interaction.response.send_message(f"`{ad}` komutu silindi.", ephemeral=True)
        else:
            await interaction.response.send_message("Komut bulunamadı.", ephemeral=True)

class KomutSilView(discord.ui.View):
    def __init__(self, cog, guild_id, komutlar):
        super().__init__(timeout=60)
        self.add_item(KomutSilSelect(cog, guild_id, komutlar))

class OzelKomutView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.button(label="Ekle", style=discord.ButtonStyle.green, emoji="➕")
    async def ekle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu butonu sadece yöneticiler kullanabilir!", ephemeral=True)
            return
        await interaction.response.send_modal(KomutEkleModal(self.cog, self.guild_id))

    @discord.ui.button(label="Sil", style=discord.ButtonStyle.red, emoji="🗑️")
    async def sil(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu butonu sadece yöneticiler kullanabilir!", ephemeral=True)
            return
        data = _load()
        gid = str(self.guild_id)
        komutlar = list(data.get(gid, {}).keys())
        if not komutlar:
            await interaction.response.send_message("Hiç özel komut yok.", ephemeral=True)
            return
        await interaction.response.send_message("Silinecek komutu seç:", view=KomutSilView(self.cog, self.guild_id, komutlar), ephemeral=True)

    @discord.ui.button(label="Liste", style=discord.ButtonStyle.blurple, emoji="📋")
    async def liste(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = _load()
        gid = str(self.guild_id)
        komutlar = data.get(gid, {})
        if not komutlar:
            await interaction.response.send_message("Hiç özel komut yok.", ephemeral=True)
            return
        embed = discord.Embed(title="Özel Komutlar", color=discord.Color.blue())
        for ad, yanit in sorted(komutlar.items()):
            embed.add_field(name=ad, value=yanit[:100] + ("..." if len(yanit) > 100 else ""), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class OzelKomut(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._komut_cache = None
        self._cache_time = 0

    def _get_komutlar(self):
        import time
        now = time.time()
        if self._komut_cache is None or now - self._cache_time > 60:
            self._komut_cache = _load()
            self._cache_time = now
        return self._komut_cache

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        if not message.content.startswith("!"):
            return
        data = self._get_komutlar()
        gid = str(message.guild.id)
        komutlar = data.get(gid, {})
        if not komutlar:
            return
        cmd = message.content.strip().lower()
        if cmd in komutlar:
            await message.channel.send(komutlar[cmd])

async def setup(bot):
    await bot.add_cog(OzelKomut(bot))
