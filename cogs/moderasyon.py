import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta, datetime
import os
from utils_json import read_json, write_json

BAN_SEBEPLERI = [
    app_commands.Choice(name="Reklam yapmak", value="Reklam yapmak"),
    app_commands.Choice(name="Spam yapmak", value="Spam yapmak"),
    app_commands.Choice(name="Küfür/hakaret", value="Küfür/hakaret"),
    app_commands.Choice(name="Toksik davranış", value="Toksik davranış"),
    app_commands.Choice(name="TOU ihlali", value="TOU ihlali"),
    app_commands.Choice(name="Yetkisiz davet", value="Yetkisiz davet"),
    app_commands.Choice(name="Raid saldırısı", value="Raid saldırısı"),
    app_commands.Choice(name="NSFW içerik", value="NSFW içerik"),
]
KICK_SEBEPLERI = [
    app_commands.Choice(name="Kural ihlali", value="Kural ihlali"),
    app_commands.Choice(name="Spam yapmak", value="Spam yapmak"),
    app_commands.Choice(name="Küfür/hakaret", value="Küfür/hakaret"),
    app_commands.Choice(name="Toksik davranış", value="Toksik davranış"),
    app_commands.Choice(name="Uyarıları dikkate almamak", value="Uyarıları dikkate almamak"),
    app_commands.Choice(name="Reklam yapmak", value="Reklam yapmak"),
]

class Moderasyon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logs_file = "modlogs.json"
        self._init_logs()

    def _init_logs(self):
        if not os.path.exists(self.logs_file):
            write_json(self.logs_file, {})

    def _log_action(self, guild_id: int, action: str, mod: str, target: str, reason: str):
        logs = read_json(self.logs_file, {})
        gid = str(guild_id)
        if gid not in logs:
            logs[gid] = []
        logs[gid].append({
            "action": action, "moderator": mod, "target": target,
            "reason": reason, "timestamp": int(datetime.now().timestamp())
        })
        write_json(self.logs_file, logs)

    @app_commands.command(name="ban", description="Üyeyi banla")
    @app_commands.describe(uye="Yasaklanacak üye", sebep="Yasak sebebi", mesaj_sil="Kaç günlük mesajı silinsin? (0-7)")
    @app_commands.choices(sebep=BAN_SEBEPLERI)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    async def yasakla(self, interaction: discord.Interaction, uye: discord.User, sebep: str = "Sebep belirtilmedi", mesaj_sil: int = 0):
        await interaction.response.defer()
        try:
            delete_days = min(max(mesaj_sil, 0), 7)
            await interaction.guild.ban(uye, reason=sebep, delete_message_seconds=delete_days * 86400)
            self._log_action(interaction.guild.id, "BAN", interaction.user.name, uye.name, sebep)
            embed = discord.Embed(title="Üye Yasaklandı", description=f"{uye.mention} sunucudan yasaklandı", color=discord.Color.red(), timestamp=datetime.now())
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.set_thumbnail(url=uye.avatar.url if uye.avatar else None)
            embed.add_field(name="Kullanıcı", value=uye.mention, inline=True)
            embed.add_field(name="Sebep", value=sebep, inline=True)
            embed.set_footer(text=f"ID: {uye.id}")
            await interaction.followup.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send("Bu üyeyi yasaklayamıyorum!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Hata: {e}", ephemeral=True)

    @app_commands.command(name="kick", description="Üyeyi sunucudan çıkar")
    @app_commands.describe(uye="Çıkarılacak üye", sebep="Çıkarma sebebi")
    @app_commands.choices(sebep=KICK_SEBEPLERI)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(kick_members=True)
    async def sunucudan_cikar(self, interaction: discord.Interaction, uye: discord.Member, sebep: str = "Sebep belirtilmedi"):
        await interaction.response.defer()
        try:
            await interaction.guild.kick(uye, reason=sebep)
            self._log_action(interaction.guild.id, "KICK", interaction.user.name, uye.name, sebep)
            embed = discord.Embed(title="Üye Çıkarıldı", description=f"{uye.mention} sunucudan çıkarıldı", color=discord.Color.orange(), timestamp=datetime.now())
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.set_thumbnail(url=uye.avatar.url if uye.avatar else None)
            embed.add_field(name="Kullanıcı", value=uye.mention, inline=True)
            embed.add_field(name="Sebep", value=sebep, inline=True)
            embed.set_footer(text=f"ID: {uye.id}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"Hata: {e}", ephemeral=True)

    @app_commands.command(name="purge", description="Mesajları sil (filtreli)")
    @app_commands.describe(
        miktar="Silinecek mesaj sayısı (1-100)",
        uye="Belirli bir üyenin mesajlarını filtrele",
        kanal="Hedef kanal (varsayılan: bu kanal)",
        secim="Seçimi ekle (sadece eşleşenler) veya çıkar (eşleşmeyenler)",
        filtre="Kullanıcı, bot veya herkes"
    )
    @app_commands.choices(secim=[
        app_commands.Choice(name="Sadece eşleşenler (sil)", value="ekle"),
        app_commands.Choice(name="Eşleşenler hariç (sakla)", value="cikar"),
    ], filtre=[
        app_commands.Choice(name="Kullanıcı", value="user"),
        app_commands.Choice(name="Bot", value="bot"),
        app_commands.Choice(name="Herkes", value="all"),
    ])
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def mesaj_sil(self, interaction: discord.Interaction, miktar: int, uye: discord.Member = None, kanal: discord.TextChannel = None, secim: str = "ekle", filtre: str = "user"):
        if miktar < 1 or miktar > 100:
            await interaction.response.send_message("1-100 arası girin!", ephemeral=True)
            return
        await interaction.response.defer()
        hedef_kanal = kanal or interaction.channel
        try:
            def check(msg):
                if secim == "cikar":
                    if uye and msg.author == uye:
                        return False
                    if filtre == "bot" and msg.author.bot:
                        return False
                    return True
                else:
                    if uye and msg.author != uye:
                        return False
                    if filtre == "bot" and not msg.author.bot:
                        return False
                    if filtre == "user" and msg.author.bot:
                        return False
                    return True

            deleted = await hedef_kanal.purge(limit=miktar, check=check)
            hedef = uye.mention if uye else (filtre if filtre != "all" else "Tümü")
            self._log_action(interaction.guild.id, "PURGE", interaction.user.name, hedef, f"{len(deleted)} mesaj")
            embed = discord.Embed(title="Mesajlar Silindi", description=f"{hedef_kanal.mention} kanalından **{len(deleted)}** mesaj silindi", color=discord.Color.red(), timestamp=datetime.now())
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.add_field(name="Kanal", value=hedef_kanal.mention, inline=True)
            embed.add_field(name="Hedef", value=hedef, inline=True)
            embed.set_footer(text=f"İsteyen: {interaction.user.name}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"Hata: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderasyon(bot))
