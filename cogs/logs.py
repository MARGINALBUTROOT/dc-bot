import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

LOG_TYPES = {
    "all": "Tüm Loglar",
    "message_delete": "Mesaj Silme",
    "message_edit": "Mesaj Düzenleme",
    "voice": "Ses Kanalları",
    "member": "Üye Katılma/Ayrılma",
    "channel": "Kanal Oluşturma/Silme/Düzenleme",
    "role": "Rol Değişiklikleri",
    "moderation": "Moderasyon İşlemleri"
}

LOG_EMOJIS = {
    "all": "📋", "message_delete": "🗑️", "message_edit": "✏️", "voice": "🔊",
    "member": "👤", "channel": "📁", "role": "🎖️", "moderation": "🛡️"
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

        embed = discord.Embed(
            title="Log Kanalı Ayarlandı",
            description=f"**{LOG_TYPES.get(self.log_type, self.log_type)}** → {kanal.mention}",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=interaction.message.view if hasattr(interaction, 'message') else None)

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
            embed = discord.Embed(title="Kullanıcı Adı Değişti", color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=after.display_name, icon_url=after.avatar.url if after.avatar else None)
            embed.add_field(name="Kullanıcı", value=after.mention, inline=True)
            embed.add_field(name="Önce", value=before.nick or before.name, inline=True)
            embed.add_field(name="Sonra", value=after.nick or after.name, inline=True)
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

async def setup(bot):
    await bot.add_cog(LogSistemi(bot))
