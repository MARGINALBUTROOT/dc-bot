import discord
from discord.ext import commands
from datetime import datetime
from collections import defaultdict, deque
import os

WARN_ESIK = 4
KICK_ESIK = 9
ARALIK = 10

WHITELIST = set()
env_wl = os.getenv("NUKE_WHITELIST", "")
if env_wl:
    for uid in env_wl.split(","):
        uid = uid.strip()
        if uid.isdigit():
            WHITELIST.add(int(uid))

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ban_log = defaultdict(lambda: deque(maxlen=KICK_ESIK))
        self.kick_log = defaultdict(lambda: deque(maxlen=KICK_ESIK))
        self.channel_log = defaultdict(lambda: deque(maxlen=KICK_ESIK))
        self.role_log = defaultdict(lambda: deque(maxlen=KICK_ESIK))
        self.webhook_log = defaultdict(lambda: deque(maxlen=KICK_ESIK))
        self.warned = set()

    async def _yetkili_mi(self, guild, uye_id):
        uye = guild.get_member(uye_id)
        if not uye:
            return False
        if uye_id in WHITELIST:
            return True
        if uye.guild_permissions.administrator:
            return True
        if uye.id == guild.owner_id:
            return True
        return False

    async def _log_gonder(self, guild, baslik, renk, *fields):
        embed = discord.Embed(title=f"🛡️ Anti-Nuke: {baslik}", color=renk, timestamp=datetime.now())
        for name, value in fields:
            embed.add_field(name=name, value=str(value)[:1000], inline=False)
        embed.set_footer(text=guild.name)
        for kanal in guild.text_channels:
            if kanal.permissions_for(guild.me).send_messages and "anti-nuke" in kanal.name.lower():
                try:
                    await kanal.send(embed=embed)
                    return
                except:
                    pass
        try:
            system = guild.system_channel
            if system and system.permissions_for(guild.me).send_messages:
                await system.send(embed=embed)
        except:
            pass

    async def _saldirgani_at(self, guild, saldirgan_id, sebep):
        try:
            uye = guild.get_member(saldirgan_id)
            if uye:
                await uye.kick(reason=sebep)
                await self._log_gonder(guild, f"Saldırgan Atıldı: {uye}", discord.Color.red(),
                    ("Sebep", sebep), ("Kullanıcı", f"{uye} ({uye.id})"))
        except:
            pass

    def _kontrol(self, log, gid, now):
        if len(log) < 2:
            return None
        onceki = log[0]
        if (now - onceki).total_seconds() > ARALIK:
            log.clear()
            log.append(now)
            return None
        sayi = len(log)
        if sayi >= KICK_ESIK:
            return "kick"
        if sayi >= WARN_ESIK and gid not in self.warned:
            self.warned.add(gid)
            return "warn"
        return None

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        if not guild.me.guild_permissions.ban_members:
            return
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                if entry.user == self.bot.user or entry.user.id in WHITELIST:
                    return
                if await self._yetkili_mi(guild, entry.user.id):
                    return
                now = datetime.now()
                gid = (guild.id, entry.user.id)
                self.ban_log[gid].append(now)
                durum = self._kontrol(self.ban_log[gid], gid, now)
                if durum == "warn":
                    await self._log_gonder(guild, "Şüpheli Ban Aktivitesi!", discord.Color.orange(),
                        ("Saldırgan", f"{entry.user} ({entry.user.id})"),
                        ("Ban Sayısı", f"{len(self.ban_log[gid])} / {KICK_ESIK}"),
                        ("Uyarı", f"{KICK_ESIK - len(self.ban_log[gid])} ban daha yaparsa sunucudan atılacak"))
                elif durum == "kick":
                    await self._log_gonder(guild, "Toplu Ban Tespit Edildi!", discord.Color.red(),
                        ("Saldırgan", f"{entry.user} ({entry.user.id})"),
                        ("Ban Sayısı", len(self.ban_log[gid])),
                        ("Süre", f"{ARALIK} saniye içinde {KICK_ESIK}+ ban"),
                        ("Aksiyon", "Sunucudan atıldı + banlananlar geri alındı"))
                    await self._saldirgani_at(guild, entry.user.id, "Anti-Nuke: Toplu ban saldırısı")
                    async for giris in guild.audit_logs(action=discord.AuditLogAction.ban):
                        if (datetime.now() - giris.created_at).total_seconds() > 60:
                            break
                        try:
                            await guild.unban(giris.target, reason="Anti-Nuke: Ban geri alma")
                        except:
                            pass
                    self.ban_log[gid].clear()
                    self.warned.discard(gid)
                break
        except:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot or not member.guild.me.guild_permissions.view_audit_log:
            return
        guild = member.guild
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                if entry.user == self.bot.user or entry.user.id in WHITELIST:
                    return
                if entry.target.id != member.id:
                    return
                if await self._yetkili_mi(guild, entry.user.id):
                    return
                now = datetime.now()
                gid = (guild.id, entry.user.id)
                self.kick_log[gid].append(now)
                durum = self._kontrol(self.kick_log[gid], gid, now)
                if durum == "warn":
                    await self._log_gonder(guild, "Şüpheli Kick Aktivitesi!", discord.Color.orange(),
                        ("Saldırgan", f"{entry.user} ({entry.user.id})"),
                        ("Kick Sayısı", f"{len(self.kick_log[gid])} / {KICK_ESIK}"),
                        ("Uyarı", f"{KICK_ESIK - len(self.kick_log[gid])} kick daha yaparsa sunucudan atılacak"))
                elif durum == "kick":
                    await self._log_gonder(guild, "Toplu Kick Tespit Edildi!", discord.Color.red(),
                        ("Saldırgan", f"{entry.user} ({entry.user.id})"),
                        ("Kick Sayısı", len(self.kick_log[gid])))
                    await self._saldirgani_at(guild, entry.user.id, "Anti-Nuke: Toplu kick saldırısı")
                    self.kick_log[gid].clear()
                    self.warned.discard(gid)
                break
        except:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        if not guild.me.guild_permissions.view_audit_log:
            return
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                if entry.user == self.bot.user or entry.user.id in WHITELIST:
                    return
                if await self._yetkili_mi(guild, entry.user.id):
                    return
                now = datetime.now()
                gid = (guild.id, entry.user.id)
                self.channel_log[gid].append(now)
                durum = self._kontrol(self.channel_log[gid], gid, now)
                if durum == "warn":
                    await self._log_gonder(guild, "Şüpheli Kanal Silme!", discord.Color.orange(),
                        ("Saldırgan", f"{entry.user} ({entry.user.id})"),
                        ("Silinen Kanal Sayısı", f"{len(self.channel_log[gid])} / {KICK_ESIK}"),
                        ("Uyarı", f"{KICK_ESIK - len(self.channel_log[gid])} kanal daha silerse sunucudan atılacak"))
                elif durum == "kick":
                    await self._log_gonder(guild, "Toplu Kanal Silme Tespit Edildi!", discord.Color.red(),
                        ("Saldırgan", f"{entry.user} ({entry.user.id})"),
                        ("Silinen Kanal Sayısı", len(self.channel_log[gid])))
                    await self._saldirgani_at(guild, entry.user.id, "Anti-Nuke: Toplu kanal silme saldırısı")
                    self.channel_log[gid].clear()
                    self.warned.discard(gid)
                break
        except:
            pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        guild = role.guild
        if not guild.me.guild_permissions.view_audit_log:
            return
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                if entry.user == self.bot.user or entry.user.id in WHITELIST:
                    return
                if await self._yetkili_mi(guild, entry.user.id):
                    return
                now = datetime.now()
                gid = (guild.id, entry.user.id)
                self.role_log[gid].append(now)
                durum = self._kontrol(self.role_log[gid], gid, now)
                if durum == "warn":
                    await self._log_gonder(guild, "Şüpheli Rol Silme!", discord.Color.orange(),
                        ("Saldırgan", f"{entry.user} ({entry.user.id})"),
                        ("Silinen Rol Sayısı", f"{len(self.role_log[gid])} / {KICK_ESIK}"),
                        ("Uyarı", f"{KICK_ESIK - len(self.role_log[gid])} rol daha silerse sunucudan atılacak"))
                elif durum == "kick":
                    await self._log_gonder(guild, "Toplu Rol Silme Tespit Edildi!", discord.Color.red(),
                        ("Saldırgan", f"{entry.user} ({entry.user.id})"),
                        ("Silinen Rol Sayısı", len(self.role_log[gid])))
                    await self._saldirgani_at(guild, entry.user.id, "Anti-Nuke: Toplu rol silme saldırısı")
                    self.role_log[gid].clear()
                    self.warned.discard(gid)
                break
        except:
            pass

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        if not guild.me.guild_permissions.view_audit_log:
            return
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.webhook_create):
                if entry.user == self.bot.user or entry.user.id in WHITELIST:
                    return
                if await self._yetkili_mi(guild, entry.user.id):
                    return
                now = datetime.now()
                gid = (guild.id, entry.user.id)
                self.webhook_log[gid].append(now)
                durum = self._kontrol(self.webhook_log[gid], gid, now)
                if durum == "warn":
                    await self._log_gonder(guild, "Şüpheli Webhook Oluşturma!", discord.Color.orange(),
                        ("Saldırgan", f"{entry.user} ({entry.user.id})"),
                        ("Webhook Sayısı", f"{len(self.webhook_log[gid])} / {KICK_ESIK}"),
                        ("Uyarı", f"{KICK_ESIK - len(self.webhook_log[gid])} webhook daha oluşturursa sunucudan atılacak"))
                elif durum == "kick":
                    await self._log_gonder(guild, "Toplu Webhook Oluşturma Tespit Edildi!", discord.Color.red(),
                        ("Saldırgan", f"{entry.user} ({entry.user.id})"),
                        ("Webhook Sayısı", len(self.webhook_log[gid])))
                    await self._saldirgani_at(guild, entry.user.id, "Anti-Nuke: Toplu webhook oluşturma saldırısı")
                    self.webhook_log[gid].clear()
                    self.warned.discard(gid)
                break
        except:
            pass

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.bot or before.roles == after.roles:
            return
        guild = after.guild
        eklenen = [r for r in after.roles if r not in before.roles]
        for rol in eklenen:
            if rol.permissions.administrator:
                try:
                    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                        if entry.user and entry.user.id != self.bot.user.id and entry.user.id not in WHITELIST:
                            if not await self._yetkili_mi(guild, entry.user.id):
                                await self._log_gonder(guild, "Admin Yetkisi Verildi!", discord.Color.orange(),
                                    ("Yetki Veren", f"{entry.user} ({entry.user.id})"),
                                    ("Yetki Alan", f"{after.mention} ({after.id})"),
                                    ("Rol", rol.mention))
                        break
                except:
                    pass

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
