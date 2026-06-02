import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import json
import os

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active = {}
        self.file = "giveaways.json"
        self._load_active()
        self.bot.loop.create_task(self._checker())

    def _save_active(self):
        with open(self.file, "w") as f:
            json.dump({str(k): v for k, v in self.active.items()}, f, indent=4)

    def _load_active(self):
        if not os.path.exists(self.file):
            return
        try:
            with open(self.file, "r") as f:
                raw = json.load(f)
            self.active = {int(k): v for k, v in raw.items()}
        except:
            self.active = {}

    async def _checker(self):
        await self.bot.wait_until_ready()
        while True:
            await asyncio.sleep(30)
            now = discord.utils.utcnow().timestamp()
            bitenler = [mid for mid, g in self.active.items() if now >= g["bitis"]]
            for mid in bitenler:
                g_data = self.active[mid]
                kanal = self.bot.get_channel(g_data.get("kanal_id"))
                if not kanal:
                    del self.active[mid]
                    continue
                try:
                    mesaj = await kanal.fetch_message(mid)
                except:
                    del self.active[mid]
                    continue
                kazanan_sayisi = g_data.get("kazanan", 1)
                odul = g_data.get("odul", "Ödül")
                katilimcilar = []
                for reaction in mesaj.reactions:
                    if reaction.emoji == "🎉":
                        async for user in reaction.users():
                            if not user.bot:
                                katilimcilar.append(user)
                if not katilimcilar:
                    embed = discord.Embed(title=f"🎉 {odul}", description="Çekilişe katılan olmadı!", color=discord.Color.red())
                    await mesaj.edit(embed=embed)
                else:
                    kazananlar = random.sample(katilimcilar, min(kazanan_sayisi, len(katilimcilar)))
                    kazanan_mentionlari = ", ".join([k.mention for k in kazananlar])
                    embed = discord.Embed(title=f"🎉 {odul}", description=f"**Çekiliş bitti!**\n\nKazanan: {kazanan_mentionlari}", color=discord.Color.green())
                    await mesaj.edit(embed=embed)
                    await kanal.send(f"🎉 Tebrikler {kazanan_mentionlari}! **{odul}** kazandınız!")
                del self.active[mid]
                self._save_active()

    @app_commands.command(name="giveaway", description="Cekilis baslat")
    @app_commands.describe(
        odul="Cekilisi kazanana verilecek odul",
        sure="Sure (orn: 1m, 10m, 1h, 1d)",
        kazanan="Kazanan sayisi (varsayilan: 1)",
        kanal="Cekilisin gonderilecegi kanal (varsayilan: bu kanal)"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def giveaway(
        self,
        interaction: discord.Interaction,
        odul: str,
        sure: str,
        kazanan: int = 1,
        kanal: discord.TextChannel = None
    ):
        sure_saniye = self._parse_sure(sure)
        if sure_saniye <= 0:
            await interaction.response.send_message("Gecersiz sure! Ornek: 1m, 10m, 1h, 1d", ephemeral=True)
            return

        hedef_kanal = kanal or interaction.channel
        bitis = discord.utils.utcnow().timestamp() + sure_saniye

        embed = discord.Embed(
            title=f"🎉 {odul}",
            description=f"Tepki vererek katil!\n\nKazanan: {kazanan}\nBitis: <t:{int(bitis)}:R>",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"{interaction.user.name} tarafindan baslatildi", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

        mesaj = await hedef_kanal.send(embed=embed)
        await mesaj.add_reaction("🎉")

        self.active[mesaj.id] = {"kazanan": kazanan, "bitis": bitis, "odul": odul, "guild_id": interaction.guild.id, "kanal_id": hedef_kanal.id, "baslatan": interaction.user.id}
        self._save_active()

        await interaction.response.send_message(f"Cekilis {hedef_kanal.mention} kanalinda baslatildi!", ephemeral=True)

    def _parse_sure(self, sure: str) -> int:
        sure = sure.lower().strip()
        if sure.endswith("d"):
            try:
                return int(sure[:-1]) * 86400
            except:
                return 0
        elif sure.endswith("h"):
            try:
                return int(sure[:-1]) * 3600
            except:
                return 0
        elif sure.endswith("m"):
            try:
                return int(sure[:-1]) * 60
            except:
                return 0
        elif sure.endswith("s"):
            try:
                return int(sure[:-1])
            except:
                return 0
        else:
            try:
                return int(sure)
            except:
                return 0

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
