import discord
from discord.ext import commands
from discord import app_commands
import urllib.request
import urllib.parse
import json as json_module

DILLER = {
    "tr": "Turkce", "en": "Ingilizce", "de": "Almanca", "fr": "Fransizca",
    "es": "Ispanyolca", "it": "Italyanca", "pt": "Portekizce", "ru": "Rusca",
    "ar": "Arapca", "ja": "Japonca", "zh": "Cince", "ko": "Korece",
    "nl": "Flemenkce", "pl": "Lehce", "sv": "Isvecce", "da": "Danca",
    "fi": "Fince", "no": "Norvecce", "cs": "Cekce", "hu": "Macarca",
    "ro": "Romence", "el": "Yunanca", "hi": "Hintce", "th": "Tayca",
    "vi": "Vietnamca", "id": "Endonezce", "ms": "Malayca", "fa": "Farsça",
    "uk": "Ukraynaca", "he": "Ibranice", "bn": "Bengalce", "sr": "Sirpca",
    "hr": "Hirvatca", "sk": "Slovakca", "bg": "Bulgarca", "lt": "Litvanca",
    "lv": "Letonca", "et": "Estonca", "sl": "Slovence", "tl": "Filipince"
}

async def dil_autocomplate(interaction: discord.Interaction, current: str):
    d = []
    for kod, isim in DILLER.items():
        if current.lower() in kod.lower() or current.lower() in isim.lower():
            d.append(app_commands.Choice(value=kod, name=f"{isim} ({kod})"))
    return d[:25]

class Ceviri(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="dil", description="Desteklenen dilleri listele")
    async def dil(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Desteklenen Diller", color=discord.Color.blue())
        diller_liste = [f"`{kod}` = {isim}" for kod, isim in sorted(DILLER.items())]
        embed.description = "\n".join(diller_liste)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Ceviri(bot))
