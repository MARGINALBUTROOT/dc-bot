import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class Karsilama(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "karsilama_settings.json"
        self._init_settings()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, "w") as f:
                json.dump({}, f)

    def _get_settings(self, guild_id):
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
            return data.get(str(guild_id), {})
        except:
            return {}

    def _save_settings(self, guild_id, settings):
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
        except:
            data = {}
        data[str(guild_id)] = settings
        with open(self.settings_file, "w") as f:
            json.dump(data, f, indent=4)

    @app_commands.command(name="karsilama", description="Karsilama/ayrilma mesaji ayarlari")
    @app_commands.describe(
        kanal="Mesajlarin gonderilecegi kanal",
        hosgeldin="Hos geldin mesaji ({user}, {server}, {sayi})",
        gulegule="Gule gule mesaji ({user}, {server})"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def karsilama(
        self,
        interaction: discord.Interaction,
        kanal: discord.TextChannel = None,
        hosgeldin: str = None,
        gulegule: str = None
    ):
        settings = self._get_settings(interaction.guild.id)
        degisti = []

        if kanal:
            settings["kanal"] = str(kanal.id)
            degisti.append(f"Kanal: {kanal.mention}")
        if hosgeldin:
            settings["hosgeldin"] = hosgeldin
            degisti.append("Hos geldin mesaji ayarlandi")
        if gulegule:
            settings["gulegule"] = gulegule
            degisti.append("Gule gule mesaji ayarlandi")

        if degisti:
            self._save_settings(interaction.guild.id, settings)

        if not settings:
            await interaction.response.send_message("Henuz ayar yapilmamis. `/karsilama kanal:#kanal hosgeldin:... gulegule:...`", ephemeral=True)
            return

        embed = discord.Embed(title="Karsilama Ayarlari", color=discord.Color.blue())
        kanal_id = settings.get("kanal")
        embed.add_field(name="Kanal", value=f"<#{kanal_id}>" if kanal_id else "Ayarlanmamis", inline=False)
        embed.add_field(name="Hos Geldin", value=settings.get("hosgeldin", "Ayarlanmamis")[:100], inline=False)
        embed.add_field(name="Gule Gule", value=settings.get("gulegule", "Ayarlanmamis")[:100], inline=False)
        embed.set_footer(text="{user}=kullanici adi {server}=sunucu {sayi}=uye sayisi")
        if degisti:
            embed.description = "\n".join(["✅ " + d for d in degisti])
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        settings = self._get_settings(member.guild.id)
        kanal_id = settings.get("kanal")
        mesaj = settings.get("hosgeldin", "")
        if not kanal_id or not mesaj:
            return
        kanal = member.guild.get_channel(int(kanal_id))
        if not kanal:
            return
        mesaj = mesaj.replace("{user}", member.mention).replace("{server}", member.guild.name).replace("{sayi}", str(member.guild.member_count))
        try:
            await kanal.send(mesaj)
        except:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return
        settings = self._get_settings(member.guild.id)
        kanal_id = settings.get("kanal")
        mesaj = settings.get("gulegule", "")
        if not kanal_id or not mesaj:
            return
        kanal = member.guild.get_channel(int(kanal_id))
        if not kanal:
            return
        mesaj = mesaj.replace("{user}", member.mention).replace("{server}", member.guild.name)
        try:
            await kanal.send(mesaj)
        except:
            pass

async def setup(bot):
    await bot.add_cog(Karsilama(bot))
