import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime
from collections import defaultdict, deque

LOG_TYPES = {
    "all": "Tüm Loglar",
    "message_delete": "Mesaj Silme",
    "message_edit": "Mesaj Düzenleme",
    "voice": "Ses Kanalları",
    "member": "Üye Değişiklikleri",
    "channel": "Kanal/Thread İşlemleri",
    "role": "Rol Değişiklikleri",
    "moderation": "Moderasyon İşlemleri",
    "invite": "Davet",
    "event": "Etkinlik",
    "pins": "Sabit Mesaj",
    "stage": "Ses Sahnesi",
    "automod": "AutoMod",
    "audit": "Denetim Kaydı",
    "user": "Kullanıcı Güncelleme",
    "sticker": "Sticker/Soundboard",
    "integration": "Entegrasyon",
    "anomaly": "Anomali Tespiti"
}

LOG_EMOJIS = {
    "all": "📋", "message_delete": "🗑️", "message_edit": "✏️", "voice": "🔊",
    "member": "👤", "channel": "📁", "role": "🎖️", "moderation": "🛡️",
    "invite": "📨", "event": "📅", "pins": "📌", "stage": "🎤", "automod": "🤖",
    "audit": "📜", "user": "🆔", "sticker": "🏷️", "integration": "🔗",
    "anomaly": "🚨"
}

class KanalModal(discord.ui.Modal, title="Log Kanalı Ayarla"):
    def __init__(self, cog, guild_id, log_type):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.log_type = log_type
        self.kanal_input = discord.ui.TextInput(
            label=f"{LOG_TYPES.get(log_type, log_type)} kanalı",
            placeholder="Kanal ID'si veya #kanal-adı yaz",
            required=True, max_length=50
        )
        self.add_item(self.kanal_input)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        kanal = None
        val = self.kanal_input.value.strip()

        if val.startswith("<#") and val.endswith(">"):
            try:
                kid = int(val[2:-1])
                kanal = guild.get_channel(kid)
            except:
                pass
        else:
            try:
                kid = int(val)
                kanal = guild.get_channel(kid)
            except ValueError:
                kanal = discord.utils.get(guild.text_channels, name=val.lstrip("#"))

        if not kanal:
            await interaction.response.send_message("Kanal bulunamadı! ID, mention (#kanal) veya kanal adı gir.", ephemeral=True)
            return

        settings = self.cog._get_guild_settings(self.guild_id)
        settings[self.log_type] = str(kanal.id)
        self.cog._save_guild_settings(self.guild_id, settings)

        await interaction.response.send_message(
            f"✅ **{LOG_TYPES.get(self.log_type, self.log_type)}** → {kanal.mention} olarak ayarlandı.",
            ephemeral=True
        )

class LogView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id
        self.message = None

        for lt, lt_name in LOG_TYPES.items():
            btn = discord.ui.Button(
                label=lt_name[:20],
                emoji=LOG_EMOJIS.get(lt, "📝"),
                style=discord.ButtonStyle.secondary,
                custom_id=f"log_{lt}"
            )
            async def callback(interaction: discord.Interaction, lt=lt):
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
                    return
                await interaction.response.send_modal(KanalModal(self.cog, self.guild_id, lt))
            btn.callback = callback
            self.add_item(btn)

    async def on_timeout(self):
        if self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except:
                pass

class LogSistemi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "log_settings.json"
        self._init_settings()
        self.ban_takip = defaultdict(lambda: deque(maxlen=10))
        self.kick_takip = defaultdict(lambda: deque(maxlen=10))
        self.kanal_takip = defaultdict(lambda: deque(maxlen=10))
        self.rol_takip = defaultdict(lambda: deque(maxlen=10))
        self.webhook_takip = defaultdict(lambda: deque(maxlen=10))
        self.join_takip = defaultdict(lambda: deque(maxlen=10))
        self.uyarilan = set()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, "w") as f:
                json.dump({}, f)

    def _get_guild_settings(self, guild_id: int):
        try:
            with open(self.settings_file, "r") as f:
                settings = json.load(f)
            return settings.get(str(guild_id), {})
        except:
            return {}

    def _save_guild_settings(self, guild_id: int, data: dict):
        try:
            with open(self.settings_file, "r") as f:
                settings = json.load(f)
        except:
            settings = {}
        settings[str(guild_id)] = data
        with open(self.settings_file, "w") as f:
            json.dump(settings, f, indent=4)

    def _get_log_channel(self, guild_id: int, log_type: str):
        settings = self._get_guild_settings(guild_id)
        channel_id = settings.get(log_type) or settings.get("all")
        return channel_id

    async def _send_log(self, guild_id: int, log_type: str, embed: discord.Embed):
        channel_id = self._get_log_channel(guild_id, log_type)
        if not channel_id:
            return
        try:
            channel = self.bot.get_channel(int(channel_id))
        except (TypeError, ValueError):
            return
        if channel:
            try:
                await channel.send(embed=embed)
            except:
                pass

    @app_commands.command(name="testlog", description="Log sisteminin çalıştığını test et")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def test_log(self, interaction: discord.Interaction):
        await interaction.response.send_message("Log sistemi çalışıyor!", ephemeral=True)

    @app_commands.command(name="setlog", description="Log kanallarını ayarla (butonlu menü)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def set_log(self, interaction: discord.Interaction):
        settings = self._get_guild_settings(interaction.guild.id)
        embed = discord.Embed(
            title="Log Sistemi",
            description="Aşağıdaki butonlara tıklayarak her log türü için kanal belirleyebilirsin.\nButona tıklayınca kanal ID veya mention girmen için bir pencere açılır.",
            color=discord.Color.blue()
        )
        ayarlanan = []
        for key in LOG_TYPES:
            val = settings.get(key)
            if val:
                k = interaction.guild.get_channel(int(val))
                ayarlanan.append(f"{LOG_EMOJIS.get(key, '📝')} **{LOG_TYPES[key]}** → {k.mention if k else 'silinmiş kanal'}")
        if ayarlanan:
            embed.add_field(name="Mevcut Ayarlar", value="\n".join(ayarlanan), inline=False)
        else:
            embed.add_field(name="Mevcut Ayarlar", value="Henüz hiçbir log kanalı ayarlanmamış.", inline=False)

        view = LogView(self, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @app_commands.command(name="logayarlari", description="Mevcut log ayarlarını göster")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def log_ayarlari(self, interaction: discord.Interaction):
        settings = self._get_guild_settings(interaction.guild.id)
        if not settings:
            await interaction.response.send_message("Henüz hiç log kanalı ayarlanmamış.", ephemeral=True)
            return

        embed = discord.Embed(title="Log Ayarları", description="Hangi log türünün hangi kanala gittiği aşağıda listelenmiştir.", color=discord.Color.blue())

        for key, value in settings.items():
            log_name = LOG_TYPES.get(key, key)
            channel = interaction.guild.get_channel(int(value))
            channel_mention = channel.mention if channel else "silinmiş-kanal"
            embed.add_field(name=log_name, value=channel_mention, inline=False)

        embed.set_footer(text=interaction.guild.name)
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or not message.author or message.author.bot:
            return

        embed = discord.Embed(title="Mesaj Silindi", color=discord.Color.red(), timestamp=datetime.now())
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url if message.author.avatar else None)
        embed.add_field(name="Kullanıcı", value=message.author.mention, inline=True)
        embed.add_field(name="Kanal", value=message.channel.mention, inline=True)
        if message.content:
            embed.add_field(name="İçerik", value=f"```{message.content[:1000]}```", inline=False)
        if message.attachments:
            embed.add_field(name="Ekler", value=f"{len(message.attachments)} dosya", inline=True)
        embed.set_footer(text=f"ID: {message.author.id} • {message.guild.name}")
        await self._send_log(message.guild.id, "message_delete", embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list):
        if not messages or not messages[0].guild:
            return
        guild = messages[0].guild
        channel = messages[0].channel
        embed = discord.Embed(
            title="Toplu Mesaj Silindi",
            description=f"**{len(messages)}** mesaj silindi",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Kanal", value=channel.mention, inline=True)
        metinler = []
        for m in messages[:5]:
            if m.author and m.content:
                metinler.append(f"{m.author.name}: {m.content[:100]}")
        if metinler:
            embed.add_field(name="Son Mesajlar", value="```" + "\n".join(metinler) + "```", inline=False)
        if len(messages) > 5:
            embed.set_footer(text=f"+{len(messages)-5} mesaj daha • {guild.name}")
        else:
            embed.set_footer(text=guild.name)
        await self._send_log(guild.id, "message_delete", embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or not before.author or before.author.bot:
            return
        if before.content == after.content:
            return

        embed = discord.Embed(title="Mesaj Düzenlendi", color=discord.Color.gold(), timestamp=datetime.now())
        embed.set_author(name=before.author.display_name, icon_url=before.author.avatar.url if before.author.avatar else None)
        embed.add_field(name="Kullanıcı", value=before.author.mention, inline=True)
        embed.add_field(name="Kanal", value=before.channel.mention, inline=True)
        embed.add_field(name="Önce", value=f"```{before.content[:500]}```", inline=False)
        embed.add_field(name="Sonra", value=f"```{after.content[:500]}```", inline=False)
        embed.set_footer(text=f"ID: {before.author.id} • {before.guild.name}")
        await self._send_log(before.guild.id, "message_edit", embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot or not member.guild:
            return

        embed = None

        if before.channel is None and after.channel is not None:
            embed = discord.Embed(title="Sese Katıldı", description=f"{member.mention} bir ses kanalına katıldı", color=discord.Color.green(), timestamp=datetime.now())
            embed.set_author(name=member.display_name, icon_url=member.avatar.url if member.avatar else None)
            embed.add_field(name="Kanal", value=after.channel.mention, inline=True)
            embed.add_field(name="Üye Sayısı", value=len(after.channel.members), inline=True)

        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(title="Sesten Ayrıldı", description=f"{member.mention} ses kanalından ayrıldı", color=discord.Color.red(), timestamp=datetime.now())
            embed.set_author(name=member.display_name, icon_url=member.avatar.url if member.avatar else None)
            embed.add_field(name="Kanal", value=before.channel.mention, inline=True)

        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            embed = discord.Embed(title="Ses Kanalı Değiştirdi", description=f"{member.mention} kanal değiştirdi", color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=member.display_name, icon_url=member.avatar.url if member.avatar else None)
            embed.add_field(name="Önce", value=before.channel.mention, inline=True)
            embed.add_field(name="Sonra", value=after.channel.mention, inline=True)

        if embed:
            embed.set_footer(text=f"ID: {member.id} • {member.guild.name}")
            await self._send_log(member.guild.id, "voice", embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        embed = discord.Embed(title="Üye Katıldı", description=f"{member.mention} sunucuya katıldı!", color=discord.Color.green(), timestamp=datetime.now())
        embed.set_author(name=member.display_name, icon_url=member.avatar.url if member.avatar else None)
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        embed.add_field(name="Hesap Oluşturma", value=member.created_at.strftime("%d.%m.%Y %H:%M"), inline=True)
        embed.add_field(name="Üye Sayısı", value=f"{member.guild.member_count}", inline=True)
        embed.set_footer(text=f"ID: {member.id} • {member.guild.name}")
        await self._send_log(member.guild.id, "member", embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return

        try:
            if member.guild.me.guild_permissions.view_audit_log:
                async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                    if entry.target and entry.target.id == member.id:
                        now = datetime.now().timestamp()
                        if entry.created_at and (now - entry.created_at.timestamp()) < 10:
                            embed = discord.Embed(title="Üye Atıldı", description=f"{member.mention} sunucudan atıldı", color=discord.Color.orange(), timestamp=datetime.now())
                            embed.set_author(name=member.display_name, icon_url=member.avatar.url if member.avatar else None)
                            if member.avatar:
                                embed.set_thumbnail(url=member.avatar.url)
                            embed.add_field(name="Kullanıcı", value=member.mention, inline=True)
                            embed.add_field(name="Atan", value=entry.user.mention if entry.user else "Bilinmiyor", inline=True)
                            if entry.reason:
                                embed.add_field(name="Sebep", value=entry.reason, inline=False)
                            embed.set_footer(text=f"ID: {member.id} • {member.guild.name}")
                            await self._send_log(member.guild.id, "member", embed)
                            return
        except discord.Forbidden:
            pass

        embed = discord.Embed(title="Üye Ayrıldı", description=f"{member.mention} sunucudan ayrıldı", color=discord.Color.red(), timestamp=datetime.now())
        embed.set_author(name=member.display_name, icon_url=member.avatar.url if member.avatar else None)
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        embed.add_field(name="Katılma Tarihi", value=member.joined_at.strftime("%d.%m.%Y %H:%M") if member.joined_at else "Bilinmiyor", inline=True)
        embed.add_field(name="Roller", value=", ".join([r.mention for r in member.roles if r.name != "@everyone"]) or "Yok", inline=False)
        embed.set_footer(text=f"ID: {member.id} • {member.guild.name}")
        await self._send_log(member.guild.id, "member", embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        embed = discord.Embed(title="Kanal Oluşturuldu", description=f"{channel.mention} kanalı oluşturuldu", color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="Kanal", value=channel.mention, inline=True)
        embed.add_field(name="Tür", value=str(channel.type).capitalize(), inline=True)
        embed.set_footer(text=f"ID: {channel.id} • {channel.guild.name}")
        await self._send_log(channel.guild.id, "channel", embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        embed = discord.Embed(title="Kanal Silindi", description=f"`{channel.name}` kanalı silindi", color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="Kanal Adı", value=f"`{channel.name}`", inline=True)
        embed.add_field(name="Tür", value=str(channel.type).capitalize(), inline=True)
        embed.set_footer(text=f"ID: {channel.id} • {channel.guild.name}")
        await self._send_log(channel.guild.id, "channel", embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        embed = discord.Embed(title="Rol Oluşturuldu", description=f"{role.mention} rolü oluşturuldu", color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="Rol", value=role.mention, inline=True)
        embed.add_field(name="Renk", value=str(role.color) if role.color.value else "Yok", inline=True)
        embed.set_footer(text=f"ID: {role.id} • {role.guild.name}")
        await self._send_log(role.guild.id, "role", embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        embed = discord.Embed(title="Rol Silindi", description=f"`{role.name}` rolü silindi", color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="Rol Adı", value=f"`{role.name}`", inline=True)
        embed.set_footer(text=f"ID: {role.id} • {role.guild.name}")
        await self._send_log(role.guild.id, "role", embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.name == after.name and before.color == after.color:
            return
        embed = discord.Embed(title="Rol Güncellendi", description=f"{after.mention} rolü güncellendi", color=discord.Color.blue(), timestamp=datetime.now())
        if before.name != after.name:
            embed.add_field(name="İsim Değişikliği", value=f"`{before.name}` → `{after.name}`", inline=False)
        if before.color != after.color:
            embed.add_field(name="Renk Değişikliği", value=f"`{before.color}` → `{after.color}`", inline=False)
        embed.set_footer(text=f"ID: {after.id} • {after.guild.name}")
        await self._send_log(after.guild.id, "role", embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before, after):
        eklenen = [e for e in after if e not in before]
        cikan = [e for e in before if e not in after]
        embed = discord.Embed(title="Emoji / Sticker Güncellendi", color=discord.Color.blue(), timestamp=datetime.now())
        if eklenen:
            embed.add_field(name="Eklenen", value=", ".join(str(e) for e in eklenen[:10]), inline=False)
        if cikan:
            embed.add_field(name="Kaldırılan", value=", ".join(f":{e.name}:" for e in cikan[:10]), inline=False)
        if not eklenen and not cikan:
            embed.add_field(name="Değişiklik", value="Emoji/sticker güncellendi", inline=False)
        embed.set_footer(text=f"ID: {guild.id} • {guild.name}")
        await self._send_log(guild.id, "role", embed)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        embed = discord.Embed(
            title="Webhook Güncellendi",
            description=f"{channel.mention} kanalında webhook değişikliği",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"ID: {channel.id} • {channel.guild.name}")
        await self._send_log(channel.guild.id, "channel", embed)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        embed = discord.Embed(title="Thread Oluşturuldu", description=thread.mention, color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="Kanal", value=thread.parent.mention if thread.parent else "Bilinmiyor", inline=True)
        embed.add_field(name="İsim", value=thread.name, inline=True)
        embed.set_footer(text=f"ID: {thread.id} • {thread.guild.name}")
        await self._send_log(thread.guild.id, "channel", embed)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        embed = discord.Embed(title="Thread Silindi", description=f"`{thread.name}` silindi", color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="İsim", value=f"`{thread.name}`", inline=True)
        embed.set_footer(text=f"ID: {thread.id} • {thread.guild.name}")
        await self._send_log(thread.guild.id, "channel", embed)

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        if before.name == after.name and before.locked == after.locked and before.archived == after.archived:
            return
        embed = discord.Embed(title="Thread Güncellendi", description=after.mention, color=discord.Color.blue(), timestamp=datetime.now())
        if before.name != after.name:
            embed.add_field(name="İsim", value=f"`{before.name}` → `{after.name}`", inline=False)
        if before.locked != after.locked:
            embed.add_field(name="Durum", value="🔒 Kilitlendi" if after.locked else "🔓 Kilidi açıldı", inline=True)
        if before.archived != after.archived:
            embed.add_field(name="Arşiv", value="📦 Arşivlendi" if after.archived else "📭 Arşivden çıkarıldı", inline=True)
        embed.set_footer(text=f"ID: {after.id} • {after.guild.name}")
        await self._send_log(after.guild.id, "channel", embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        embed = discord.Embed(title="Üye Yasaklandı", description=f"{user.mention} sunucudan yasaklandı", color=discord.Color.red(), timestamp=datetime.now())
        embed.set_author(name=user.name, icon_url=user.avatar.url if user.avatar else None)
        embed.add_field(name="Kullanıcı", value=user.mention, inline=True)
        embed.add_field(name="Kullanıcı ID", value=f"`{user.id}`", inline=True)
        embed.set_footer(text=guild.name)
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                embed.add_field(name="Moderatör", value=entry.user.mention if entry.user else "Bilinmiyor", inline=True)
                if entry.reason:
                    embed.add_field(name="Sebep", value=entry.reason, inline=False)
        await self._send_log(guild.id, "moderation", embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        embed = discord.Embed(title="Üyenin Yasağı Kaldırıldı", description=f"{user.mention} kullanıcısının yasağı kaldırıldı", color=discord.Color.green(), timestamp=datetime.now())
        embed.set_author(name=user.name, icon_url=user.avatar.url if user.avatar else None)
        embed.add_field(name="Kullanıcı", value=user.mention, inline=True)
        embed.add_field(name="Kullanıcı ID", value=f"`{user.id}`", inline=True)
        embed.set_footer(text=guild.name)
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
            if entry.target.id == user.id:
                embed.add_field(name="Moderatör", value=entry.user.mention if entry.user else "Bilinmiyor", inline=True)
        await self._send_log(guild.id, "moderation", embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.bot:
            return
        embed = None
        if before.nick != after.nick:
            embed = discord.Embed(title="Takma Ad Değişti", color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=after.display_name, icon_url=after.avatar.url if after.avatar else None)
            embed.add_field(name="Kullanıcı", value=after.mention, inline=True)
            embed.add_field(name="Önce", value=before.nick or before.name, inline=True)
            embed.add_field(name="Sonra", value=after.nick or after.name, inline=True)
            embed.set_footer(text=f"ID: {after.id} • {after.guild.name}")
        elif before.display_avatar != after.display_avatar:
            embed = discord.Embed(title="Profil Resmi Değişti", color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=after.display_name, icon_url=after.avatar.url if after.avatar else None)
            embed.add_field(name="Kullanıcı", value=after.mention, inline=True)
            if after.avatar:
                embed.set_image(url=after.avatar.url)
            embed.set_footer(text=f"ID: {after.id} • {after.guild.name}")
        elif before.banner != after.banner:
            embed = discord.Embed(title="Banner Değişti", color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=after.display_name, icon_url=after.avatar.url if after.avatar else None)
            embed.add_field(name="Kullanıcı", value=after.mention, inline=True)
            if after.banner:
                embed.set_image(url=after.banner.url)
            embed.set_footer(text=f"ID: {after.id} • {after.guild.name}")
        elif before.global_name != after.global_name:
            embed = discord.Embed(title="Discord Adı Değişti", color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=after.display_name, icon_url=after.avatar.url if after.avatar else None)
            embed.add_field(name="Kullanıcı", value=after.mention, inline=True)
            embed.add_field(name="Önce", value=before.global_name or before.name, inline=True)
            embed.add_field(name="Sonra", value=after.global_name or after.name, inline=True)
            embed.set_footer(text=f"ID: {after.id} • {after.guild.name}")
        elif before.roles != after.roles:
            eklenen = [r.mention for r in after.roles if r not in before.roles and r.name != "@everyone"]
            cikarilan = [r.mention for r in before.roles if r not in after.roles and r.name != "@everyone"]
            if eklenen or cikarilan:
                embed = discord.Embed(title="Roller Güncellendi", color=discord.Color.gold(), timestamp=datetime.now())
                embed.set_author(name=after.display_name, icon_url=after.avatar.url if after.avatar else None)
                embed.add_field(name="Kullanıcı", value=after.mention, inline=True)
                if eklenen:
                    embed.add_field(name="Eklenen Roller", value=", ".join(eklenen), inline=False)
                if cikarilan:
                    embed.add_field(name="Çıkarılan Roller", value=", ".join(cikarilan), inline=False)
                embed.set_footer(text=f"ID: {after.id} • {after.guild.name}")
        if embed:
            await self._send_log(after.guild.id, "member", embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        if before.name == after.name and before.icon == after.icon and before.banner == after.banner and before.description == after.description:
            return
        embed = discord.Embed(title="Sunucu Güncellendi", color=discord.Color.blue(), timestamp=datetime.now())
        if before.name != after.name:
            embed.add_field(name="İsim Değişikliği", value=f"`{before.name}` → `{after.name}`", inline=False)
        if before.icon != after.icon:
            embed.add_field(name="Sunucu İkonu", value="Sunucu ikonu değiştirildi", inline=False)
            if after.icon:
                embed.set_thumbnail(url=after.icon.url)
        if before.banner != after.banner:
            embed.add_field(name="Sunucu Bannerı", value="Sunucu bannerı değiştirildi", inline=False)
        if before.description != after.description:
            embed.add_field(name="Açıklama Değişikliği", value=f"`{before.description or 'Yok'}` → `{after.description or 'Yok'}`", inline=False)
        embed.set_footer(text=f"ID: {after.id} • {after.name}")
        await self._send_log(after.id, "channel", embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if before.name == after.name:
            return
        embed = discord.Embed(title="Kanal Düzenlendi", description=f"{after.mention} kanalı düzenlendi", color=discord.Color.blue(), timestamp=datetime.now())
        embed.add_field(name="Kanal", value=after.mention, inline=True)
        embed.add_field(name="İsim Değişikliği", value=f"`{before.name}` → `{after.name}`", inline=False)
        embed.set_footer(text=f"ID: {after.id} • {after.guild.name}")
        await self._send_log(after.guild.id, "channel", embed)

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, channel: discord.abc.GuildChannel, last_pin: datetime):
        embed = discord.Embed(title="Sabit Mesaj Güncellendi", color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="Kanal", value=channel.mention, inline=True)
        embed.add_field(name="Son Sabitlenme", value=last_pin.strftime("%d/%m/%Y %H:%M") if last_pin else "Bilinmiyor", inline=True)
        embed.set_footer(text=f"ID: {channel.id} • {channel.guild.name}")
        await self._send_log(channel.guild.id, "pins", embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        embed = discord.Embed(title="Davet Oluşturuldu", color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="Kanal", value=invite.channel.mention if invite.channel else "Bilinmiyor", inline=True)
        embed.add_field(name="Davet Kodu", value=invite.code, inline=True)
        embed.add_field(name="Süre", value=f"{invite.max_age} sn" if invite.max_age else "Sınırsız", inline=True)
        embed.add_field(name="Maks. Kullanım", value=invite.max_uses if invite.max_uses else "Sınırsız", inline=True)
        if invite.inviter:
            embed.set_author(name=invite.inviter.display_name, icon_url=invite.inviter.avatar.url if invite.inviter.avatar else None)
        embed.set_footer(text=f"ID: {invite.guild.id if invite.guild else '?'} • {invite.guild.name if invite.guild else '?'}")
        if invite.guild:
            await self._send_log(invite.guild.id, "invite", embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        embed = discord.Embed(title="Davet Silindi", color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="Kanal", value=invite.channel.mention if invite.channel else "Bilinmiyor", inline=True)
        embed.add_field(name="Davet Kodu", value=invite.code, inline=True)
        embed.set_footer(text=f"ID: {invite.guild.id if invite.guild else '?'}")
        if invite.guild:
            await self._send_log(invite.guild.id, "invite", embed)

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        embed = discord.Embed(title="Etkinlik Oluşturuldu", description=event.name, color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="Konum", value=event.location if event.location else "Ses Kanalı", inline=True)
        embed.add_field(name="Başlangıç", value=event.start_time.strftime("%d/%m/%Y %H:%M"), inline=True)
        if event.end_time:
            embed.add_field(name="Bitiş", value=event.end_time.strftime("%d/%m/%Y %H:%M"), inline=True)
        if event.description:
            embed.add_field(name="Açıklama", value=event.description[:200], inline=False)
        embed.set_footer(text=f"ID: {event.id} • {event.guild.name}")
        await self._send_log(event.guild.id, "event", embed)

    @commands.Cog.listener()
    async def on_scheduled_event_delete(self, event: discord.ScheduledEvent):
        embed = discord.Embed(title="Etkinlik Silindi", description=event.name, color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="Başlangıç", value=event.start_time.strftime("%d/%m/%Y %H:%M"), inline=True)
        embed.set_footer(text=f"ID: {event.id} • {event.guild.name}")
        await self._send_log(event.guild.id, "event", embed)

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent):
        if before.name == after.name and before.description == after.description and before.start_time == after.start_time:
            return
        embed = discord.Embed(title="Etkinlik Düzenlendi", description=after.name, color=discord.Color.gold(), timestamp=datetime.now())
        if before.name != after.name:
            embed.add_field(name="İsim", value=f"`{before.name}` → `{after.name}`", inline=False)
        if before.description != after.description:
            embed.add_field(name="Açıklama", value=f"`{before.description or 'Yok'}` → `{after.description or 'Yok'}`", inline=False)
        if before.start_time != after.start_time:
            embed.add_field(name="Başlangıç", value=f"{before.start_time.strftime('%d/%m/%Y %H:%M')} → {after.start_time.strftime('%d/%m/%Y %H:%M')}", inline=False)
        embed.set_footer(text=f"ID: {after.id} • {after.guild.name}")
        await self._send_log(after.guild.id, "event", embed)

    @commands.Cog.listener()
    async def on_stage_instance_create(self, stage: discord.StageInstance):
        embed = discord.Embed(title="Ses Sahnesi Açıldı", description=stage.topic, color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="Kanal", value=stage.channel.mention, inline=True)
        embed.add_field(name="Konu", value=stage.topic, inline=False)
        embed.set_footer(text=f"ID: {stage.id} • {stage.guild.name}")
        await self._send_log(stage.guild.id, "stage", embed)

    @commands.Cog.listener()
    async def on_stage_instance_delete(self, stage: discord.StageInstance):
        embed = discord.Embed(title="Ses Sahnesi Kapatıldı", description=stage.topic, color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="Kanal", value=stage.channel.mention, inline=True)
        embed.set_footer(text=f"ID: {stage.id} • {stage.guild.name}")
        await self._send_log(stage.guild.id, "stage", embed)

    @commands.Cog.listener()
    async def on_stage_instance_update(self, before: discord.StageInstance, after: discord.StageInstance):
        if before.topic == after.topic:
            return
        embed = discord.Embed(title="Ses Sahnesi Düzenlendi", color=discord.Color.gold(), timestamp=datetime.now())
        embed.add_field(name="Kanal", value=after.channel.mention, inline=True)
        embed.add_field(name="Konu", value=f"`{before.topic}` → `{after.topic}`", inline=False)
        embed.set_footer(text=f"ID: {after.id} • {after.guild.name}")
        await self._send_log(after.guild.id, "stage", embed)

    @commands.Cog.listener()
    async def on_automod_rule_create(self, rule: discord.AutoModRule):
        embed = discord.Embed(title="AutoMod Kuralı Oluşturuldu", description=rule.name, color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="Kural Türü", value=str(rule.event_type).split(".")[-1] if rule.event_type else "Bilinmiyor", inline=True)
        embed.add_field(name="Aksiyon", value=str(rule.actions[0].type).split(".")[-1] if rule.actions else "Bilinmiyor", inline=True)
        if rule.creator:
            embed.set_author(name=rule.creator.display_name, icon_url=rule.creator.avatar.url if rule.creator.avatar else None)
        embed.set_footer(text=f"ID: {rule.id} • {rule.guild.name}")
        await self._send_log(rule.guild.id, "automod", embed)

    @commands.Cog.listener()
    async def on_automod_rule_delete(self, rule: discord.AutoModRule):
        embed = discord.Embed(title="AutoMod Kuralı Silindi", description=rule.name, color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="Kural Türü", value=str(rule.event_type).split(".")[-1] if rule.event_type else "Bilinmiyor", inline=True)
        embed.set_footer(text=f"ID: {rule.id} • {rule.guild.name}")
        await self._send_log(rule.guild.id, "automod", embed)

    @commands.Cog.listener()
    async def on_automod_rule_update(self, before: discord.AutoModRule, after: discord.AutoModRule):
        if before.name == after.name and before.actions == after.actions:
            return
        embed = discord.Embed(title="AutoMod Kuralı Düzenlendi", color=discord.Color.gold(), timestamp=datetime.now())
        if before.name != after.name:
            embed.add_field(name="Kural Adı", value=f"`{before.name}` → `{after.name}`", inline=False)
        if before.actions != after.actions:
            embed.add_field(name="Aksiyon Değişti", value=f"Yeni aksiyon: {str(after.actions[0].type).split('.')[-1] if after.actions else 'Yok'}", inline=False)
        embed.set_footer(text=f"ID: {after.id} • {after.guild.name}")
        await self._send_log(after.guild.id, "automod", embed)

    @commands.Cog.listener()
    async def on_automod_action(self, execution: discord.AutoModAction):
        embed = discord.Embed(title="AutoMod İşlemi", color=discord.Color.orange(), timestamp=datetime.now())
        embed.add_field(name="Kural ID", value=execution.rule_id, inline=True)
        embed.add_field(name="Kullanıcı", value=execution.member.mention if execution.member else f"<@{execution.user_id}>", inline=True)
        if execution.channel:
            embed.add_field(name="Kanal", value=execution.channel.mention, inline=True)
        embed.add_field(name="İçerik", value=f"```{(execution.matched_content or execution.content or 'Yok')[:200]}```", inline=False)
        embed.add_field(name="Aksiyon", value=str(execution.action.type).split(".")[-1] if execution.action else "Bilinmiyor", inline=True)
        embed.set_footer(text=f"ID: {execution.guild.id} • {execution.guild.name}")
        await self._send_log(execution.guild.id, "automod", embed)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        if before.bot:
            return
        embed = None
        if before.global_name != after.global_name:
            embed = discord.Embed(title="Kullanıcı Adı Değişti (Global)", color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=after.display_name, icon_url=after.avatar.url if after.avatar else None)
            embed.add_field(name="Önce", value=before.global_name or before.name, inline=True)
            embed.add_field(name="Sonra", value=after.global_name or after.name, inline=True)
            embed.set_footer(text=f"ID: {after.id}")
        elif before.avatar != after.avatar:
            embed = discord.Embed(title="Profil Resmi Değişti (Global)", color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=after.display_name, icon_url=after.avatar.url if after.avatar else None)
            embed.add_field(name="Kullanıcı", value=after.mention, inline=True)
            if after.avatar:
                embed.set_image(url=after.avatar.url)
            embed.set_footer(text=f"ID: {after.id}")
        if embed:
            for guild in self.bot.guilds:
                if guild.get_member(after.id):
                    await self._send_log(guild.id, "user", embed)

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        try:
            if not entry.guild:
                return
            embed = discord.Embed(title="Denetim Kaydı", color=discord.Color.gold(), timestamp=datetime.now())
            embed.add_field(name="İşlem", value=str(entry.action).split(".")[-1] if entry.action else "Bilinmiyor", inline=True)
            embed.add_field(name="Hedef", value=str(entry.target) if entry.target else "Bilinmiyor", inline=True)
            if entry.user:
                embed.add_field(name="Yetkili", value=entry.user.mention, inline=True)
            if entry.reason:
                embed.add_field(name="Sebep", value=entry.reason[:200], inline=False)
            embed.set_footer(text=f"ID: {entry.id} • {entry.guild.name}")
            await self._send_log(entry.guild.id, "audit", embed)
        except:
            pass

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild: discord.Guild, before, after):
        if len(before) < len(after):
            eklenen = [s for s in after if s not in before]
            for s in eklenen:
                embed = discord.Embed(title="Sticker Eklendi", description=s.name, color=discord.Color.green(), timestamp=datetime.now())
                if s.emoji:
                    embed.add_field(name="Emoji", value=s.emoji, inline=True)
                if s.description:
                    embed.add_field(name="Açıklama", value=s.description[:100], inline=True)
                embed.set_footer(text=f"ID: {s.id} • {guild.name}")
                await self._send_log(guild.id, "sticker", embed)
        elif len(before) > len(after):
            silinen = [s for s in before if s not in after]
            for s in silinen:
                embed = discord.Embed(title="Sticker Silindi", description=s.name, color=discord.Color.red(), timestamp=datetime.now())
                embed.set_footer(text=f"ID: {s.id} • {guild.name}")
                await self._send_log(guild.id, "sticker", embed)
        else:
            for old_s in before:
                for new_s in after:
                    if old_s.id == new_s.id and (old_s.name != new_s.name or old_s.description != new_s.description):
                        embed = discord.Embed(title="Sticker Düzenlendi", color=discord.Color.gold(), timestamp=datetime.now())
                        if old_s.name != new_s.name:
                            embed.add_field(name="İsim", value=f"`{old_s.name}` → `{new_s.name}`", inline=False)
                        if old_s.description != new_s.description:
                            embed.add_field(name="Açıklama", value=f"`{old_s.description or 'Yok'}` → `{new_s.description or 'Yok'}`", inline=False)
                        embed.set_footer(text=f"ID: {new_s.id} • {guild.name}")
                        await self._send_log(guild.id, "sticker", embed)
                        break

    @commands.Cog.listener()
    async def on_integration_create(self, integration: discord.Integration):
        embed = discord.Embed(title="Entegrasyon Eklendi", description=integration.name, color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="Tür", value=integration.type, inline=True)
        if integration.user:
            embed.set_author(name=integration.user.display_name, icon_url=integration.user.avatar.url if integration.user.avatar else None)
        embed.set_footer(text=f"ID: {integration.id} • {integration.guild.name}")
        await self._send_log(integration.guild.id, "integration", embed)

    @commands.Cog.listener()
    async def on_integration_delete(self, integration: discord.Integration):
        embed = discord.Embed(title="Entegrasyon Silindi", description=integration.name, color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="Tür", value=integration.type, inline=True)
        embed.set_footer(text=f"ID: {integration.id} • {integration.guild.name}")
        await self._send_log(integration.guild.id, "integration", embed)

    @commands.Cog.listener()
    async def on_scheduled_event_user_add(self, event: discord.ScheduledEvent, user: discord.User):
        embed = discord.Embed(title="Etkinliğe Katıldı", color=discord.Color.green(), timestamp=datetime.now())
        embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
        embed.add_field(name="Etkinlik", value=event.name, inline=True)
        embed.add_field(name="Kullanıcı", value=user.mention, inline=True)
        embed.set_footer(text=f"ID: {event.id} • {event.guild.name}")
        await self._send_log(event.guild.id, "event", embed)

    @commands.Cog.listener()
    async def on_scheduled_event_user_remove(self, event: discord.ScheduledEvent, user: discord.User):
        embed = discord.Embed(title="Etkinlikten Ayrıldı", color=discord.Color.red(), timestamp=datetime.now())
        embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
        embed.add_field(name="Etkinlik", value=event.name, inline=True)
        embed.add_field(name="Kullanıcı", value=user.mention, inline=True)
        embed.set_footer(text=f"ID: {event.id} • {event.guild.name}")
        await self._send_log(event.guild.id, "event", embed)

    @commands.Cog.listener()
    async def on_soundboard_sound_create(self, sound: discord.SoundboardSound):
        embed = discord.Embed(title="Soundboard Ses Eklendi", description=sound.name, color=discord.Color.green(), timestamp=datetime.now())
        if sound.emoji:
            embed.add_field(name="Emoji", value=sound.emoji, inline=True)
        embed.set_footer(text=f"ID: {sound.id} • {sound.guild.name}")
        await self._send_log(sound.guild.id, "sticker", embed)

    @commands.Cog.listener()
    async def on_soundboard_sound_delete(self, sound: discord.SoundboardSound):
        embed = discord.Embed(title="Soundboard Ses Silindi", description=sound.name, color=discord.Color.red(), timestamp=datetime.now())
        embed.set_footer(text=f"ID: {sound.id} • {sound.guild.name}")
        await self._send_log(sound.guild.id, "sticker", embed)

    @commands.Cog.listener()
    async def on_soundboard_sound_update(self, before: discord.SoundboardSound, after: discord.SoundboardSound):
        if before.name == after.name and before.emoji == after.emoji:
            return
        embed = discord.Embed(title="Soundboard Ses Düzenlendi", color=discord.Color.gold(), timestamp=datetime.now())
        if before.name != after.name:
            embed.add_field(name="İsim", value=f"`{before.name}` → `{after.name}`", inline=False)
        if before.emoji != after.emoji:
            embed.add_field(name="Emoji", value=f"`{before.emoji or 'Yok'}` → `{after.emoji or 'Yok'}`", inline=False)
        embed.set_footer(text=f"ID: {after.id} • {after.guild.name}")
        await self._send_log(after.guild.id, "sticker", embed)

    # ---- Anomali Tespiti ----
    ANOMALI_ESIK = 5
    ANOMALI_ARALIK = 12

    async def _anomali_role_ping(self, guild):
        for rol in guild.roles:
            if rol.permissions.administrator and rol.name != "@everyone":
                return rol.mention
        return "@everyone"

    async def _anomali_kontrol(self, takip, gid, now, tur, saldiran, guild):
        takip[gid].append(now)
        if len(takip[gid]) < self.ANOMALI_ESIK:
            return
        onceki = takip[gid][0]
        if (now - onceki).total_seconds() > self.ANOMALI_ARALIK:
            takip[gid].clear()
            takip[gid].append(now)
            return
        if gid in self.uyarilan:
            return
        self.uyarilan.add(gid)
        sayi = len(takip[gid])
        rol_ping = await self._anomali_role_ping(guild)
        embed = discord.Embed(title=f"🚨 Anomali Tespit Edildi!", color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="Olay", value=tur, inline=True)
        embed.add_field(name="Sayı", value=f"{sayi} kez / {self.ANOMALI_ARALIK} saniye", inline=True)
        embed.add_field(name="Şüpheli", value=f"{saldiran.mention if saldiran else 'Bilinmiyor'} ({saldiran.id if saldiran else '?'})", inline=False)
        embed.set_footer(text=guild.name)
        await self._send_log(guild.id, "anomaly", embed)
        try:
            kanal_id = self._get_log_channel(guild.id, "anomaly") or self._get_log_channel(guild.id, "all")
            if kanal_id:
                kanal = guild.get_channel(int(kanal_id))
                if kanal and kanal.permissions_for(guild.me).send_messages:
                    await kanal.send(f"{rol_ping} • **{tur}** tespit edildi! ({sayi} kez / {self.ANOMALI_ARALIK}sn)")
        except:
            pass
        import asyncio
        async def _temizle():
            await asyncio.sleep(60)
            self.uyarilan.discard(gid)
        asyncio.ensure_future(_temizle())

    @commands.Cog.listener(name="on_member_ban")
    async def on_member_ban_anomali(self, guild: discord.Guild, user: discord.User):
        if not guild.me.guild_permissions.view_audit_log:
            return
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                if entry.user and entry.user.id != self.bot.user.id:
                    await self._anomali_kontrol(self.ban_takip, guild.id, datetime.now(), "Toplu Ban", entry.user, guild)
                break
        except:
            pass

    @commands.Cog.listener(name="on_member_remove")
    async def on_member_remove_anomali(self, member: discord.Member):
        if member.bot or not member.guild.me.guild_permissions.view_audit_log:
            return
        guild = member.guild
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id and entry.user and entry.user.id != self.bot.user.id:
                    await self._anomali_kontrol(self.kick_takip, guild.id, datetime.now(), "Toplu Kick", entry.user, guild)
                break
        except:
            pass

    @commands.Cog.listener(name="on_member_join")
    async def on_member_join_anomali(self, member: discord.Member):
        if member.bot:
            return
        guild = member.guild
        await self._anomali_kontrol(self.join_takip, guild.id, datetime.now(), "Yoğun Üye Katılımı", member, guild)

    @commands.Cog.listener(name="on_guild_channel_delete")
    async def on_guild_channel_delete_anomali(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        if not guild.me.guild_permissions.view_audit_log:
            return
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                if entry.user and entry.user.id != self.bot.user.id:
                    await self._anomali_kontrol(self.kanal_takip, guild.id, datetime.now(), "Toplu Kanal Silme", entry.user, guild)
                break
        except:
            pass

    @commands.Cog.listener(name="on_guild_role_delete")
    async def on_guild_role_delete_anomali(self, role: discord.Role):
        guild = role.guild
        if not guild.me.guild_permissions.view_audit_log:
            return
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                if entry.user and entry.user.id != self.bot.user.id:
                    await self._anomali_kontrol(self.rol_takip, guild.id, datetime.now(), "Toplu Rol Silme", entry.user, guild)
                break
        except:
            pass

    @commands.Cog.listener(name="on_webhooks_update")
    async def on_webhooks_update_anomali(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        if not guild.me.guild_permissions.view_audit_log:
            return
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.webhook_create):
                if entry.user and entry.user.id != self.bot.user.id:
                    await self._anomali_kontrol(self.webhook_takip, guild.id, datetime.now(), "Toplu Webhook Oluşturma", entry.user, guild)
                break
        except:
            pass

async def setup(bot):
    await bot.add_cog(LogSistemi(bot))
