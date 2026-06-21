import discord
from discord.ext import commands
from discord import app_commands
import re
import json
import os
from datetime import timedelta, datetime

class SpamSureModal(discord.ui.Modal, title="Spam Susturma Süresi"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.sure = discord.ui.TextInput(label="Süre (dakika, 1-40320)", placeholder="Örn: 5", required=True, max_length=5)
        self.add_item(self.sure)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            dakika = int(self.sure.value)
            if dakika < 1 or dakika > 40320:
                await interaction.response.send_message("1-40320 arası girin!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Geçerli bir sayı girin!", ephemeral=True)
            return
        s = self.cog._get_guild_settings(self.guild_id)
        s["spam_mute_duration"] = dakika
        self.cog._save_guild_settings(self.guild_id, s)
        await self._refresh(interaction)

    async def _refresh(self, interaction):
        s = self.cog._get_guild_settings(self.guild_id)
        embed = self.cog._build_embed(s)
        await interaction.response.edit_message(embed=embed)

class OtoKorumaView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Bu menüyü kullanmak için yetkiniz yok!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Link Filtresi", style=discord.ButtonStyle.primary, emoji="🔗")
    async def link_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        s = self.cog._get_guild_settings(self.guild_id)
        s["link_filter"] = not s["link_filter"]
        self.cog._save_guild_settings(self.guild_id, s)
        embed = self.cog._build_embed(s)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Spam Filtresi", style=discord.ButtonStyle.primary, emoji="⚠️")
    async def spam_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        s = self.cog._get_guild_settings(self.guild_id)
        s["spam_filter"] = not s["spam_filter"]
        self.cog._save_guild_settings(self.guild_id, s)
        embed = self.cog._build_embed(s)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Spam Süre", style=discord.ButtonStyle.secondary, emoji="⏱️")
    async def spam_sure(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SpamSureModal(self.cog, self.guild_id))

    async def on_timeout(self):
        if self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except:
                pass

class Otomoderasyon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "autmod_settings.json"
        self._init_settings()
        self.link_pattern = re.compile(r'https?://[^\s]+|www\.[^\s]+')
        self.mesaj_izleme = {}

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, "w") as f:
                json.dump({}, f)

    def _get_guild_settings(self, guild_id: int):
        defaults = {"link_filter": False, "spam_filter": False, "spam_mute_duration": 5}
        try:
            with open(self.settings_file, "r") as f:
                settings = json.load(f)
        except:
            settings = {}
        gid = str(guild_id)
        if gid not in settings:
            settings[gid] = defaults
        else:
            for k, v in defaults.items():
                settings[gid].setdefault(k, v)
        return settings[gid]

    def _save_guild_settings(self, guild_id: int, settings: dict):
        try:
            with open(self.settings_file, "r") as f:
                all_settings = json.load(f)
        except:
            all_settings = {}
        all_settings[str(guild_id)] = settings
        with open(self.settings_file, "w") as f:
            json.dump(all_settings, f, indent=4)

    def _build_embed(self, s):
        embed = discord.Embed(title="Oto Koruma Sistemi", description="Link ve spam filtrelerini butonlarla yönetebilirsin.", color=discord.Color.blue())
        link_durum = "✅ Açık" if s.get("link_filter", False) else "❌ Kapalı"
        spam_durum = "✅ Açık" if s.get("spam_filter", False) else "❌ Kapalı"
        embed.add_field(name="🔗 Link Filtresi", value=link_durum, inline=True)
        embed.add_field(name="⚠️ Spam Filtresi", value=spam_durum, inline=True)
        embed.add_field(name="⏱️ Spam Süre", value=f"{s.get('spam_mute_duration', 5)} dk", inline=True)
        embed.set_footer(text="Her filtreyi açıp/kapatmak için butonlara tıkla")
        return embed

    @app_commands.command(name="otokoruma", description="Oto-koruma (link/spam filtrelerini) yönet")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def otokoruma(self, interaction: discord.Interaction):
        s = self._get_guild_settings(interaction.guild.id)
        embed = self._build_embed(s)
        view = OtoKorumaView(self, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if message.author == self.bot.user:
            return
        if message.author.guild_permissions.administrator:
            return

        yetki = message.guild.me.guild_permissions
        settings = self._get_guild_settings(message.guild.id)

        if not message.author.bot and settings.get("link_filter", False):
            if self.link_pattern.search(message.content) and yetki.manage_messages:
                try:
                    await message.delete()
                    await message.author.send(f"Bu kanalda link göndermek yasak! Kanal: {message.channel.mention}")
                except:
                    pass

        if not message.author.bot and settings.get("spam_filter", False) and yetki.moderate_members:
            simdi = datetime.now()
            uid = message.author.id
            if uid not in self.mesaj_izleme:
                self.mesaj_izleme[uid] = []
            self.mesaj_izleme[uid].append(simdi)
            self.mesaj_izleme[uid] = [t for t in self.mesaj_izleme[uid] if (simdi - t).total_seconds() < 5]
            if len(self.mesaj_izleme[uid]) >= 4:
                mute_dk = settings.get("spam_mute_duration", 5)
                try:
                    await message.author.timeout(timedelta(minutes=mute_dk), reason="Hızlı mesaj (spam)")
                    await message.author.send(f"{mute_dk} dk susturuldunuz (hızlı mesaj).")
                except:
                    pass
                self.mesaj_izleme[uid] = []

async def setup(bot):
    await bot.add_cog(Otomoderasyon(bot))
