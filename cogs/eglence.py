import discord
from discord.ext import commands
from discord import app_commands

class Eglence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="Kullanıcının avatarını göster")
    @app_commands.describe(kullanici="Avatarı gösterilecek kullanıcı (opsiyonel)")
    async def avatar(self, interaction: discord.Interaction, kullanici: discord.User = None):
        hedef = kullanici or interaction.user
        if not hedef.avatar:
            await interaction.response.send_message("Bu kullanıcının avatarı yok.", ephemeral=True)
            return
        embed = discord.Embed(title=f"{hedef.name} Avatarı", color=discord.Color.blue())
        embed.set_image(url=hedef.avatar.url)
        embed.set_footer(text=f"ID: {hedef.id}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ping", description="Bot gecikmesini göster")
    async def ping(self, interaction: discord.Interaction):
        gecikme = round(self.bot.latency * 1000)
        renk = discord.Color.green() if gecikme < 100 else discord.Color.orange() if gecikme < 200 else discord.Color.red()
        embed = discord.Embed(title="🏓 Pong!", description=f"Gecikme: **{gecikme}ms**", color=renk)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Eglence(bot))
