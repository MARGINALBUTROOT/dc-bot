import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta, datetime
import json
import os

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

EMBED_RENKLERI = {
    "mavi": discord.Color.blue, "yeşil": discord.Color.green, "kırmızı": discord.Color.red,
    "altın": discord.Color.gold, "mor": discord.Color.purple, "turuncu": discord.Color.orange,
    "pembe": discord.Color.magenta, "beyaz": discord.Color.default, "siyah": discord.Color.dark_grey,
}

class Moderasyon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logs_file = "modlogs.json"
        self.warns_file = "warns_storage.json"
        self._init_logs()
        self._init_warns()

    def _init_logs(self):
        if not os.path.exists(self.logs_file):
            with open(self.logs_file, "w") as f:
                json.dump({}, f)

    def _init_warns(self):
        if not os.path.exists(self.warns_file):
            with open(self.warns_file, "w") as f:
                json.dump({}, f)

    def _log_action(self, guild_id: int, action: str, mod: str, target: str, reason: str):
        with open(self.logs_file, "r") as f:
            logs = json.load(f)
        gid = str(guild_id)
        if gid not in logs:
            logs[gid] = []
        logs[gid].append({
            "action": action, "moderator": mod, "target": target,
            "reason": reason, "timestamp": int(datetime.now().timestamp())
        })
        with open(self.logs_file, "w") as f:
            json.dump(logs, f, indent=4)

    def _add_warn(self, guild_id, user_id, user_name, moderator, reason, puan=1):
        with open(self.warns_file, "r") as f:
            warns = json.load(f)
        gid = str(guild_id)
        if gid not in warns:
            warns[gid] = {"next_id": 1, "users": {}}
        if str(user_id) not in warns[gid]["users"]:
            warns[gid]["users"][str(user_id)] = {"name": user_name, "warns": [], "total_puan": 0}
        warns[gid]["users"][str(user_id)]["warns"].append({
            "id": warns[gid]["next_id"], "moderator": moderator, "reason": reason,
            "puan": puan, "timestamp": int(datetime.now().timestamp()), "active": True
        })
        warns[gid]["users"][str(user_id)]["total_puan"] += puan
        warns[gid]["next_id"] += 1
        with open(self.warns_file, "w") as f:
            json.dump(warns, f, indent=4)
        return warns[gid]["next_id"] - 1, warns[gid]["users"][str(user_id)]["total_puan"]

    def _get_user_warns(self, guild_id, user_id):
        with open(self.warns_file, "r") as f:
            warns = json.load(f)
        gid = str(guild_id)
        if gid not in warns or str(user_id) not in warns[gid]["users"]:
            return [], 0
        user_data = warns[gid]["users"][str(user_id)]
        return [w for w in user_data["warns"] if w["active"]], user_data["total_puan"]

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

    @app_commands.command(name="warn", description="Üyeyi uyar (puanlı sistem)")
    @app_commands.describe(uye="Uyarılacak üye", sebep="Uyarma sebebi", puan="Ceza puanı (1-10, varsayılan: 1)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def uyar(self, interaction: discord.Interaction, uye: discord.Member, sebep: str, puan: int = 1):
        if puan < 1 or puan > 10:
            await interaction.response.send_message("Puan 1-10 arası olmalıdır!", ephemeral=True)
            return
        warn_id, toplam_puan = self._add_warn(interaction.guild.id, uye.id, uye.name, interaction.user.name, sebep, puan)
        self._log_action(interaction.guild.id, "WARN", interaction.user.name, uye.name, f"{sebep} (puan: {puan})")
        embed = discord.Embed(title="Uyarı Verildi", description=f"{uye.mention} uyarıldı", color=discord.Color.red(), timestamp=datetime.now())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_thumbnail(url=uye.avatar.url if uye.avatar else None)
        embed.add_field(name="Kullanıcı", value=uye.mention, inline=True)
        embed.add_field(name="Sebep", value=sebep, inline=True)
        embed.add_field(name="Puan", value=f"{puan} (Toplam: {toplam_puan})", inline=True)
        embed.add_field(name="Uyarı No", value=f"#{warn_id}", inline=True)
        embed.set_footer(text=f"ID: {uye.id}")
        await interaction.response.send_message(embed=embed)
        try:
            dm_embed = discord.Embed(title="Uyarı Aldınız", description=f"**{interaction.guild.name}** sunucusunda uyarıldınız", color=discord.Color.red(), timestamp=datetime.now())
            dm_embed.add_field(name="Sebep", value=sebep, inline=False)
            dm_embed.add_field(name="Ceza Puanı", value=str(puan), inline=True)
            dm_embed.set_footer(text=interaction.guild.name)
            await uye.send(embed=dm_embed)
        except:
            pass

    @app_commands.command(name="uyarılar", description="Bir üyenin uyarılarını listele")
    @app_commands.describe(uye="Uyarıları görüntülecek üye")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def uyarilar(self, interaction: discord.Interaction, uye: discord.User):
        warns, toplam_puan = self._get_user_warns(interaction.guild.id, uye.id)
        embed = discord.Embed(title=f"{uye.name} - Uyarıları", color=discord.Color.orange())
        embed.set_thumbnail(url=uye.avatar.url if uye.avatar else None)
        embed.add_field(name="Toplam Puan", value=str(toplam_puan), inline=True)
        embed.add_field(name="Aktif Uyarı", value=str(len(warns)), inline=True)
        if warns:
            warn_text = ""
            for w in warns[-10:]:
                warn_text += f"`#{w['id']}` | {w['reason'][:40]} | {w['puan']}p | <t:{w['timestamp']}:R>\n"
            embed.add_field(name="Son Uyarılar", value=warn_text[:1024], inline=False)
        embed.set_footer(text=f"ID: {uye.id}")
        await interaction.response.send_message(embed=embed)

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

    @app_commands.command(name="lock", description="Kanalı kilitle")
    @app_commands.describe(sebep="Kilitleme sebebi", kanal="Kilitlenecek kanal (varsayılan: bu kanal)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def kanal_kilitle(self, interaction: discord.Interaction, sebep: str = "Sebep belirtilmedi", kanal: discord.TextChannel = None):
        await interaction.response.defer()
        hedef = kanal or interaction.channel
        try:
            await hedef.set_permissions(interaction.guild.default_role, send_messages=False)
            self._log_action(interaction.guild.id, "LOCK", interaction.user.name, f"#{hedef.name}", sebep)
            embed = discord.Embed(title="Kanal Kilitlendi", description=f"{hedef.mention} kanalı kilitlendi", color=discord.Color.red(), timestamp=datetime.now())
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.add_field(name="Sebep", value=sebep, inline=False)
            embed.set_footer(text=interaction.guild.name)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"Hata: {e}", ephemeral=True)

    @app_commands.command(name="unlock", description="Kanalı aç")
    @app_commands.describe(kanal="Açılacak kanal (varsayılan: bu kanal)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def kanal_ac(self, interaction: discord.Interaction, kanal: discord.TextChannel = None):
        await interaction.response.defer()
        hedef = kanal or interaction.channel
        try:
            await hedef.set_permissions(interaction.guild.default_role, send_messages=True)
            self._log_action(interaction.guild.id, "UNLOCK", interaction.user.name, f"#{hedef.name}", "Kanal açıldı")
            embed = discord.Embed(title="Kanal Açıldı", description=f"{hedef.mention} kanalının kilidi kaldırıldı", color=discord.Color.green(), timestamp=datetime.now())
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.set_footer(text=interaction.guild.name)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"Hata: {e}", ephemeral=True)

    @app_commands.command(name="slowmode", description="Yavaş modu ayarla")
    @app_commands.describe(saniye="Yavaş mod süresi (saniye, 0=devre dışı)", kanal="Hedef kanal (varsayılan: bu kanal)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def yavas_mod(self, interaction: discord.Interaction, saniye: int, kanal: discord.TextChannel = None):
        if saniye < 0 or saniye > 21600:
            await interaction.response.send_message("0-21600 arası girin!", ephemeral=True)
            return
        await interaction.response.defer()
        hedef = kanal or interaction.channel
        try:
            await hedef.edit(slowmode_delay=saniye)
            self._log_action(interaction.guild.id, "SLOWMODE", interaction.user.name, f"#{hedef.name}", f"{saniye} sn")
            embed = discord.Embed(title="Yavaş Mod", description=f"{hedef.mention} için yavaş mod **{saniye}s** olarak ayarlandı" if saniye else f"{hedef.mention} için yavaş mod devre dışı bırakıldı", color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.set_footer(text=interaction.guild.name)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"Hata: {e}", ephemeral=True)

    @app_commands.command(name="embed", description="Özelleştirilmiş embed mesajı gönder")
    @app_commands.describe(
        baslik="Embed başlığı",
        aciklama="Embed açıklaması",
        renk="Embed rengi (mavi, yeşil, kırmızı, altın, mor, turuncu, pembe, beyaz, siyah)",
        kanal="Gönderilecek kanal (varsayılan: bu kanal)",
        footer="Alt metin (opsiyonel)"
    )
    @app_commands.choices(renk=[
        app_commands.Choice(name="Mavi", value="mavi"), app_commands.Choice(name="Yeşil", value="yeşil"),
        app_commands.Choice(name="Kırmızı", value="kırmızı"), app_commands.Choice(name="Altın", value="altın"),
        app_commands.Choice(name="Mor", value="mor"), app_commands.Choice(name="Turuncu", value="turuncu"),
        app_commands.Choice(name="Pembe", value="pembe"), app_commands.Choice(name="Beyaz", value="beyaz"),
        app_commands.Choice(name="Siyah", value="siyah"),
    ])
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def embed_gonder(self, interaction: discord.Interaction, baslik: str, aciklama: str, renk: str = "mavi", kanal: discord.TextChannel = None, footer: str = None):
        try:
            renk_func = EMBED_RENKLERI.get(renk, discord.Color.blue)
            embed = discord.Embed(title=baslik, description=aciklama, color=renk_func(), timestamp=datetime.now())
            if footer:
                embed.set_footer(text=footer)
            else:
                embed.set_footer(text=f"{interaction.user.name} tarafından", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            hedef = kanal or interaction.channel
            await hedef.send(embed=embed)
            await interaction.response.send_message(f"Embed mesaj {hedef.mention} kanalına gönderildi.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderasyon(bot))
