import discord
from discord.ext import commands
from discord import app_commands

class Anket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="anket", description="Emoji oylamalı anket oluştur")
    @app_commands.describe(
        soru="Anket sorusu",
        secenekler="Seçenekler (virgülle ayırın, örn: Evet,Hayır,Belki)",
        kanal="Anketin gönderileceği kanal (varsayılan: bu kanal)"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def anket(
        self,
        interaction: discord.Interaction,
        soru: str,
        secenekler: str,
        kanal: discord.TextChannel = None
    ):
        emojiler = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        sec_liste = [s.strip() for s in secenekler.split(",") if s.strip()]
        if len(sec_liste) < 2:
            await interaction.response.send_message("En az 2 seçenek girmelisin! Örn: `Evet,Hayır`", ephemeral=True)
            return
        if len(sec_liste) > 10:
            await interaction.response.send_message("En fazla 10 seçenek girebilirsin!", ephemeral=True)
            return

        kullanilan_emoji = emojiler[:len(sec_liste)]

        embed = discord.Embed(title=soru, color=discord.Color.blue())
        for i, sec in enumerate(sec_liste):
            embed.add_field(name=f"{kullanilan_emoji[i]} {sec}", value="\u200b", inline=False)
        embed.set_footer(text=f"{interaction.user.name} tarafından oluşturuldu", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

        hedef_kanal = kanal or interaction.channel
        mesaj = await hedef_kanal.send(embed=embed)

        for e in kullanilan_emoji:
            await mesaj.add_reaction(e)

        await interaction.response.send_message(f"Anket {hedef_kanal.mention} kanalına gönderildi.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Anket(bot))
