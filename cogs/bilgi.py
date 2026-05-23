import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
import os

KATEGORILER = {
    "moderasyon": {"emoji": "🛡️", "name": "Moderasyon", "desc": "Sunucu moderasyon komutları",
        "cmds": ["`/ban`", "`/kick`", "`/warn`", "`/uyarılar`", "`/purge`", "`/lock`", "`/unlock`", "`/slowmode`", "`/embed`", "`/ozel-komut`", "`/yedek-yukle`"]},
    "ticket": {"emoji": "🎫", "name": "Ticket", "desc": "Destek ticket sistemi",
        "cmds": ["`/ticket`", "`/ticket_yetkili`", "`/ticket_log`"]},
    "koruma": {"emoji": "🛡️", "name": "Koruma", "desc": "Bot koruma ve otomatik moderasyon",
        "cmds": ["`/antibot`", "`/otokoruma`", "`/setup_automod`", "`/automod_kurallar`"]},
    "log": {"emoji": "📝", "name": "Log", "desc": "Sunucu log sistemi",
        "cmds": ["`/setlog`", "`/logayarlari`", "`/testlog`"]},
    "karsilama": {"emoji": "👋", "name": "Karşılama", "desc": "Karşılama/uğurlama mesajları",
        "cmds": ["`/karsilama`"]},
    "rol": {"emoji": "🎭", "name": "Roller", "desc": "Oto-rol ve reaksiyon rolleri",
        "cmds": ["`/otorol`", "`/rol-paneli`"]},
    "ses": {"emoji": "🔊", "name": "Ses Odaları", "desc": "Geçici ses odaları",
        "cmds": ["`/sesoda`"]},
    "cekilis": {"emoji": "🎉", "name": "Çekiliş", "desc": "Çekiliş sistemi",
        "cmds": ["`/giveaway`"]},
    "anket": {"emoji": "📊", "name": "Anket", "desc": "Oylama anketleri",
        "cmds": ["`/anket`"]},
    "sosyal": {"emoji": "🌐", "name": "Sosyal Medya", "desc": "Sosyal medya takip",
        "cmds": ["`/instagram`", "`/facebook`", "`/x-twitter`", "`/testinstagram`", "`/testfacebook`", "`/x-twitter-test`", "`/dil`"]},
    "dogrulama": {"emoji": "✅", "name": "Doğrulama", "desc": "Üye doğrulama sistemi",
        "cmds": ["`/üyedoğrulama`"]},
    "bilgi": {"emoji": "ℹ️", "name": "Bilgi", "desc": "Bilgi komutları",
        "cmds": ["`/userinfo`", "`/serverinfo`", "`/help`"]},
    "eglence": {"emoji": "🎮", "name": "Eğlence", "desc": "Eğlence komutları",
        "cmds": ["`/yazı-tura`", "`/zar`", "`/espri`", "`/avatar`", "`/ping`"]},
}

class HelpView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=120)
        self.bot = bot
        self.message = None
        for kid, kat in KATEGORILER.items():
            btn = discord.ui.Button(label=kat["name"], emoji=kat["emoji"], style=discord.ButtonStyle.secondary, custom_id=f"help_{kid}")
            async def callback(interaction: discord.Interaction, kid=kid, kat=kat):
                embed = self._build_embed(kid, kat, interaction.guild.name if interaction.guild else "rootv1")
                await interaction.response.edit_message(embed=embed, view=self)
            btn.callback = callback
            self.add_item(btn)

    def _build_embed(self, kid, kat, guild_name):
        embed = discord.Embed(
            title=f"{kat['emoji']} {kat['name']} Komutları",
            description=kat["desc"],
            color=discord.Color.blue()
        )
        embed.add_field(name="Komutlar", value=" ".join(kat["cmds"]), inline=False)
        embed.set_footer(text=f"{guild_name} • Kategori seçmek için butonlara tıkla")
        return embed

    async def on_timeout(self):
        if self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except:
                pass

class Bilgi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="userinfo", description="Kullanıcı bilgisini göster")
    @app_commands.describe(kullanıcı="Bilgisi gösterilecek kullanıcı (opsiyonel)")
    @app_commands.guild_only()
    async def kullanıcıinfo(self, interaction: discord.Interaction, kullanıcı: discord.Member = None):
        try:
            target_user = kullanıcı or interaction.user
            if target_user.id in [m.id for m in interaction.guild.members]:
                user = interaction.guild.get_member(target_user.id)
            else:
                user = await interaction.guild.fetch_member(target_user.id)

            embed = discord.Embed(
                title=f"{user.name}#{user.discriminator}",
                color=user.color if user.color != discord.Color.default() else discord.Color.blue()
            )

            if user.avatar:
                embed.set_thumbnail(url=user.avatar.url)

            if user.status == discord.Status.online:
                status_emoji, status_text = "🟢", "Online"
            elif user.status == discord.Status.idle:
                status_emoji, status_text = "🟡", "Boşta"
            elif user.status == discord.Status.dnd:
                status_emoji, status_text = "🔴", "Rahatsız Etmeyin"
            else:
                status_emoji, status_text = "⚫", "Offline"

            activity_text = user.activity.name if user.activity else "Yok"

            embed.add_field(
                name="Genel Bilgi",
                value=f"**ID:** {user.id}\n**Durum:** {status_emoji} {status_text}\n**Oyun:** {activity_text}",
                inline=False
            )

            embed.add_field(
                name="Tarih Bilgileri",
                value=f"**Hesap Oluşturma:** {user.created_at.strftime('%d.%m.%Y %H:%M')}\n**Sunucuya Katılma:** {user.joined_at.strftime('%d.%m.%Y %H:%M') if user.joined_at else 'Bilinmiyor'}",
                inline=False
            )

            roles = [r.mention for r in user.roles if r.name != "@everyone"]
            if roles:
                embed.add_field(
                    name=f"Roller ({len(roles)})",
                    value=" ".join(roles[:10]),
                    inline=False
                )

            top_perms = []
            if user.guild_permissions.administrator:
                top_perms.append("Yönetici")
            if user.guild_permissions.manage_guild:
                top_perms.append("Sunucu Yönetimi")
            if user.guild_permissions.ban_members:
                top_perms.append("Ban Atma")
            if user.guild_permissions.kick_members:
                top_perms.append("Sunucudan Çıkarma")
            if user.guild_permissions.manage_messages:
                top_perms.append("Mesaj Yönetimi")

            if top_perms:
                embed.add_field(
                    name="Önemli İzinler",
                    value=" | ".join(top_perms),
                    inline=False
                )

            embed.set_footer(text=f"İstenen: {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {str(e)}", ephemeral=True)

    @app_commands.command(name="serverinfo", description="Sunucu bilgisini göster")
    @app_commands.guild_only()
    async def sunucuinfo(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
            embed = discord.Embed(title=guild.name, color=discord.Color.purple())

            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)

            embed.add_field(
                name="Genel Bilgi",
                value=f"**ID:** {guild.id}\n**Sahip:** {guild.owner.mention if guild.owner else 'Bilinmiyor'}\n**Oluşturma Tarihi:** {guild.created_at.strftime('%d.%m.%Y')}",
                inline=False
            )

            member_count = guild.member_count
            bot_count = sum(1 for m in guild.members if m.bot)
            embed.add_field(
                name="Üye Bilgileri",
                value=f"**Toplam:** {member_count}\n**Bot:** {bot_count}\n**İnsan:** {member_count - bot_count}",
                inline=False
            )

            text_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
            voice_channels = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
            embed.add_field(
                name="Kanal Bilgileri",
                value=f"**Yazı Kanalları:** {text_channels}\n**Ses Kanalları:** {voice_channels}",
                inline=False
            )

            embed.add_field(
                name="Rol Bilgileri",
                value=f"**Toplam Rol:** {len(guild.roles)}",
                inline=False
            )

            verification_levels = {
                discord.VerificationLevel.none: "Yok",
                discord.VerificationLevel.low: "Düşük",
                discord.VerificationLevel.medium: "Orta",
                discord.VerificationLevel.high: "Yüksek",
                discord.VerificationLevel.highest: "En Yüksek"
            }

            embed.add_field(
                name="Güvenlik",
                value=f"**Doğrulama Seviyesi:** {verification_levels.get(guild.verification_level, 'Bilinmiyor')}\n**2FA:** {'Gerekli' if guild.mfa_level == 1 else 'Gerekli Değil'}",
                inline=False
            )

            embed.set_footer(text=f"İstenen: {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {str(e)}", ephemeral=True)

    @app_commands.command(name="help", description="Tüm komutları kategorilere göre göster")
    async def yardim(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="rootv1 Komutları",
            description="Aşağıdaki butonlara tıklayarak kategorilere göre komutları görebilirsin.",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{interaction.guild.name if interaction.guild else 'rootv1'} • Kategori seçmek için butonlara tıkla")
        view = HelpView(self.bot)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @app_commands.command(name="reload", description="Tüm komut dosyalarını yeniden yükle (sadece bot sahibi)")
    @app_commands.guild_only()
    async def reload(self, interaction: discord.Interaction):
        owner = (await self.bot.application_info()).owner
        if interaction.user.id != owner.id:
            await interaction.response.send_message("Bu komutu sadece bot sahibi kullanabilir!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        results = {"loaded": [], "failed": []}

        for filename in os.listdir("cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.bot.reload_extension(cog_name)
                    results["loaded"].append(filename)
                except Exception as e:
                    results["failed"].append(f"{filename}: {e}")

        try:
            self.bot.tree.clear_commands(guild=interaction.guild)
            await self.bot.tree.sync(guild=interaction.guild)
        except:
            pass

        try:
            await self.bot.tree.sync()
        except:
            pass

        embed = discord.Embed(title="Komutlar Yeniden Yüklendi", color=discord.Color.green() if not results["failed"] else discord.Color.orange())
        embed.add_field(name="Başarılı", value=str(len(results["loaded"])), inline=True)
        embed.add_field(name="Başarısız", value=str(len(results["failed"])), inline=True)
        if results["failed"]:
            embed.add_field(name="Hatalar", value="\n".join(results["failed"][:5]), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="forcesync", description="Komutları manuel senkronize et (bot sahibi)")
    @app_commands.guild_only()
    async def forcesync(self, interaction: discord.Interaction):
        owner = (await self.bot.application_info()).owner
        if interaction.user.id != owner.id:
            await interaction.response.send_message("Bu komutu sadece bot sahibi kullanabilir!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            self.bot.tree.clear_commands(guild=interaction.guild)
            await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send("Komutlar bu sunucu için senkronize edildi. Birkaç dakika içinde görünür olmalı.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Sync hatası: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Bilgi(bot))
