import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from utils_json import read_json, write_json

class EsikModal(discord.ui.Modal, title="Ban Eşiği Ayarla"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.sayi = discord.ui.TextInput(label="Eşik (2-20)", placeholder="Kaç mesajdan sonra banlansın?", required=True, max_length=2)
        self.add_item(self.sayi)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            sayi = int(self.sayi.value)
            if sayi < 2 or sayi > 20:
                await interaction.response.send_message("2-20 arası bir sayı girin!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Geçerli bir sayı girin!", ephemeral=True)
            return
        try:
            s = self.cog._get_guild_settings(self.guild_id)
            s["esik"] = sayi
            self.cog._save_guild_settings(self.guild_id, s)
            await self._update_message(interaction)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {e}", ephemeral=True)

    async def _update_message(self, interaction):
        try:
            s = self.cog._get_guild_settings(self.guild_id)
            embed = await self.cog._refresh_embed(s, interaction.guild)
            await interaction.response.edit_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {e}", ephemeral=True)

class KanalModal(discord.ui.Modal, title="Bildirim Kanalı Ayarla"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.kanal = discord.ui.TextInput(label="Kanal ID veya mention", placeholder="#kanal veya kanal ID'si", required=True, max_length=50)
        self.add_item(self.kanal)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        val = self.kanal.value.strip()
        kanal = None
        if val.startswith("<#") and val.endswith(">"):
            try:
                kanal = guild.get_channel(int(val[2:-1]))
            except:
                pass
        else:
            try:
                kanal = guild.get_channel(int(val))
            except ValueError:
                kanal = discord.utils.get(guild.text_channels, name=val.lstrip("#"))
        if not kanal:
            await interaction.response.send_message("Kanal bulunamadı!", ephemeral=True)
            return
        try:
            s = self.cog._get_guild_settings(self.guild_id)
            s["kanal_id"] = str(kanal.id)
            self.cog._save_guild_settings(self.guild_id, s)
            await self._update_message(interaction)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {e}", ephemeral=True)

    async def _update_message(self, interaction):
        try:
            s = self.cog._get_guild_settings(self.guild_id)
            embed = await self.cog._refresh_embed(s, interaction.guild)
            await interaction.response.edit_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {e}", ephemeral=True)

class GuvenliEkleModal(discord.ui.Modal, title="Güvenli Bot Ekle"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.bot_id = discord.ui.TextInput(label="Bot ID", placeholder="Eklemek istediğin botun ID'si", required=True, max_length=30)
        self.add_item(self.bot_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            s = self.cog._get_guild_settings(self.guild_id)
            bid = self.bot_id.value.strip()
            if not bid.isdigit():
                await interaction.response.send_message("Geçerli bir bot ID girin.", ephemeral=True)
                return
            try:
                bot_user = interaction.guild.get_member(int(bid)) or await self.cog.bot.fetch_user(int(bid))
            except (discord.NotFound, discord.HTTPException):
                bot_user = None
            if not bot_user or not bot_user.bot:
                await interaction.response.send_message("Bu ID geçerli bir Discord botuna ait değil.", ephemeral=True)
                return
            if bid in s.get("guvenli_botlar", []):
                await interaction.response.send_message("Bu bot zaten güvenli listesinde.", ephemeral=True)
                return
            if "guvenli_botlar" not in s:
                s["guvenli_botlar"] = []
            s["guvenli_botlar"].append(bid)
            self.cog._save_guild_settings(self.guild_id, s)
            embed = discord.Embed(title="Güvenli Bot Eklendi", description=f"Bot `{bid}` güvenli listesine eklendi.", color=discord.Color.green())
            await interaction.response.edit_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {e}", ephemeral=True)


class UyariRolModal(discord.ui.Modal, title="Uyarı Rolleri Ayarla"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.roller = discord.ui.TextInput(
            label="Rol ID'leri",
            placeholder="ID'leri virgülle ayır (boş bırak: temizle)",
            required=False,
            max_length=500,
        )
        self.add_item(self.roller)

    async def on_submit(self, interaction: discord.Interaction):
        role_ids = []
        raw = self.roller.value.strip()
        for value in raw.replace("<@&", "").replace(">", "").split(","):
            value = value.strip()
            if not value:
                continue
            if not value.isdigit():
                await interaction.response.send_message("Sadece rol ID veya rol mention girin.", ephemeral=True)
                return
            role = interaction.guild.get_role(int(value))
            if not role or role.is_default() or role >= interaction.guild.me.top_role:
                await interaction.response.send_message("Geçersiz veya bot rolünün üstündeki bir rol seçildi.", ephemeral=True)
                return
            role_ids.append(str(role.id))

        settings = self.cog._get_guild_settings(self.guild_id)
        settings["uyari_rolleri"] = role_ids
        self.cog._save_guild_settings(self.guild_id, settings)
        await interaction.response.send_message(
            f"Uyarı rolleri güncellendi: {len(role_ids)} rol.", ephemeral=True
        )

class AntibotView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Aç/Kapat", style=discord.ButtonStyle.success, emoji="🔛")
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        s = self.cog._get_guild_settings(self.guild_id)
        s["aktif"] = not s["aktif"]
        self.cog._save_guild_settings(self.guild_id, s)
        embed = await self._build_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Eşik Ayarla", style=discord.ButtonStyle.primary, emoji="⚡")
    async def esik(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EsikModal(self.cog, self.guild_id))

    @discord.ui.button(label="Kanal Ayarla", style=discord.ButtonStyle.primary, emoji="📢")
    async def kanal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KanalModal(self.cog, self.guild_id))

    @discord.ui.button(label="Güvenli Ekle", style=discord.ButtonStyle.secondary, emoji="➕")
    async def guvenli_ekle(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GuvenliEkleModal(self.cog, self.guild_id))

    @discord.ui.button(label="Güvenli Liste", style=discord.ButtonStyle.secondary, emoji="📋")
    async def guvenli_liste(self, interaction: discord.Interaction, button: discord.ui.Button):
        s = self.cog._get_guild_settings(self.guild_id)
        guvenliler = s.get("guvenli_botlar", [])
        if not guvenliler:
            await interaction.response.send_message("Güvenli listede hiç bot yok.", ephemeral=True)
            return
        liste = "\n".join([f"• `{bid}`" for bid in guvenliler])
        embed = discord.Embed(title="Güvenli Botlar", description=liste, color=discord.Color.green())
        embed.set_footer(text=f"Toplam {len(guvenliler)} bot")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Uyarı Rolleri", style=discord.ButtonStyle.danger, emoji="🚨")
    async def uyari_rolleri(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UyariRolModal(self.cog, self.guild_id))

    @discord.ui.button(label="Kalkanı Başlat", style=discord.ButtonStyle.success, emoji="🛡️")
    async def kalkan_baslat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._run_system1(interaction)

    async def _build_embed(self, guild):
        s = self.cog._get_guild_settings(self.guild_id)
        durum = "✅ Aktif" if s["aktif"] else "❌ Devre Dışı"
        embed = discord.Embed(title="Antibot Koruması", description="Sunucuya katılan botları izler, spam durumunda otomatik banlar.", color=discord.Color.blue() if s["aktif"] else discord.Color.red())
        embed.add_field(name="Durum", value=durum, inline=True)
        embed.add_field(name="Ban Eşiği", value=f"{s['esik']} mesaj", inline=True)
        kanal = self.cog._get_kanal(s)
        embed.add_field(name="Bildirim Kanalı", value=kanal.mention if kanal else "Ayarlanmamış", inline=False)
        guvenli_sayisi = len(s.get("guvenli_botlar", []))
        embed.add_field(name="Güvenli Bot", value=f"{guvenli_sayisi} bot listede" if guvenli_sayisi else "Yok", inline=False)
        uyari_sayisi = len(s.get("uyari_rolleri", []))
        embed.add_field(name="Uyarı Rolleri", value=f"{uyari_sayisi} rol" if uyari_sayisi else "Ayarlanmamış", inline=False)
        embed.set_footer(text="Butonları kullanarak ayarları değiştirebilirsin")
        return embed

    async def on_timeout(self):
        if self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except:
                pass

class Antibot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "antibot_settings.json"
        self._init_settings()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            write_json(self.settings_file, {})

    def _get_guild_settings(self, guild_id: int):
        # Safe default: only explicitly approved bots may join.
        defaults = {"aktif": True, "mutlak": False, "esik": 6, "kanal_id": None, "guvenli_botlar": [], "uyari_rolleri": []}
        settings = read_json(self.settings_file, {})
        gid = str(guild_id)
        if gid not in settings:
            settings[gid] = defaults
        else:
            for k, v in defaults.items():
                settings[gid].setdefault(k, v)
        return settings[gid]

    def _save_guild_settings(self, guild_id: int, settings: dict):
        all_settings = read_json(self.settings_file, {})
        all_settings[str(guild_id)] = settings
        write_json(self.settings_file, all_settings)

    def _get_kanal(self, settings):
        kanal_id = settings.get("kanal_id")
        if kanal_id:
            try:
                kanal = self.bot.get_channel(int(kanal_id))
                if kanal:
                    return kanal
            except (ValueError, TypeError):
                pass
        return None

    def _is_trusted_bot(self, member, settings):
        return str(member.id) in {str(bot_id) for bot_id in settings.get("guvenli_botlar", [])}

    def _get_alert_roles(self, guild, settings):
        roles = []
        for role_id in settings.get("uyari_rolleri", []):
            role = guild.get_role(int(role_id))
            if role:
                roles.append(role)
        return roles

    async def _alert(self, guild, settings, title, description, color=discord.Color.orange()):
        channel = self._get_kanal(settings) or guild.system_channel
        if not channel or not channel.permissions_for(guild.me).send_messages:
            return
        roles = self._get_alert_roles(guild, settings)
        mentions = " ".join(role.mention for role in roles)
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
        embed.set_footer(text="System1 güvenlik kalkanı")
        try:
            await channel.send(
                content=mentions or None,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(roles=True, users=False, everyone=False),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _refresh_embed(self, s, guild):
        durum = "✅ Aktif" if s["aktif"] else "❌ Devre Dışı"
        embed = discord.Embed(title="Antibot Koruması", description="Sunucuya katılan botları izler, spam durumunda otomatik banlar.", color=discord.Color.blue() if s["aktif"] else discord.Color.red())
        embed.add_field(name="Durum", value=durum, inline=True)
        embed.add_field(name="Ban Eşiği", value=f"{s['esik']} mesaj", inline=True)
        kanal = self._get_kanal(s)
        embed.add_field(name="Bildirim Kanalı", value=kanal.mention if kanal else "Ayarlanmamış", inline=False)
        guvenli_sayisi = len(s.get("guvenli_botlar", []))
        embed.add_field(name="Güvenli Bot", value=f"{guvenli_sayisi} bot listede" if guvenli_sayisi else "Yok", inline=False)
        uyari_sayisi = len(s.get("uyari_rolleri", []))
        embed.add_field(name="Uyarı Rolleri", value=f"{uyari_sayisi} rol" if uyari_sayisi else "Ayarlanmamış", inline=False)
        embed.set_footer(text="Butonları kullanarak ayarları değiştirebilirsin")
        return embed

    @app_commands.command(name="antibot", description="Bot koruma sistemini yönet (butonlu menü)")
    @app_commands.guild_only()
    async def antibot(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)
            return
        s = self._get_guild_settings(interaction.guild.id)
        embed = await self._refresh_embed(s, interaction.guild)
        view = AntibotView(self, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    async def _ban_untrusted_bots(self, guild):
        settings = self._get_guild_settings(guild.id)
        trusted = {str(bot_id) for bot_id in settings.get("guvenli_botlar", [])}
        try:
            await guild.chunk(cache=True)
        except (discord.Forbidden, discord.HTTPException):
            pass
        targets = [
            member for member in guild.members
            if member.bot
            and member.id != self.bot.user.id
            and str(member.id) not in trusted
            and member.top_role < guild.me.top_role
        ]

        async def ban(member):
            try:
                await guild.ban(member, reason="System1 - güvenli listede olmayan bot")
                return member, None
            except (discord.Forbidden, discord.HTTPException) as error:
                return member, error

        results = await asyncio.gather(*(ban(member) for member in targets))
        banned = [member for member, error in results if error is None]
        failed = [member for member, error in results if error is not None]
        return banned, failed

    @app_commands.command(name="system1", description="Tüm yabancı botları hızlıca temizle ve bot korumasını aç")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def system1(self, interaction: discord.Interaction):
        s = self._get_guild_settings(interaction.guild.id)
        embed = await self._refresh_embed(s, interaction.guild)
        embed.title = "System1 Güvenlik Kalkanı"
        embed.description = "Önce güvenli botları ekle ve uyarı rollerini ayarla. Sonra kalkanı başlat."
        view = AntibotView(self, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    async def _run_system1(self, interaction: discord.Interaction):
        guild = interaction.guild
        me = guild.me
        if not me.guild_permissions.ban_members or not me.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "System1 için botta `Ban Members` ve `Manage Channels` yetkileri olmalı.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        settings = self._get_guild_settings(guild.id)
        settings["aktif"] = True
        # System1 uses the allowlist: every bot outside it is suspicious.
        settings["mutlak"] = False
        self._save_guild_settings(guild.id, settings)

        locked = []
        try:
            for channel in guild.text_channels:
                try:
                    previous = channel.overwrites_for(guild.default_role)
                    await channel.set_permissions(
                        guild.default_role,
                        send_messages=False,
                        reason="System1 - bot temizliği sırasında kanal kilidi",
                    )
                    locked.append((channel, previous))
                except (discord.Forbidden, discord.HTTPException):
                    pass

            banned, failed = await self._ban_untrusted_bots(guild)
        finally:
            for channel, previous in locked:
                try:
                    await channel.set_permissions(
                        guild.default_role,
                        overwrite=None if previous.is_empty() else previous,
                        reason="System1 - bot temizliği tamamlandı",
                    )
                except (discord.Forbidden, discord.HTTPException):
                    pass

        if banned or failed:
            names = ", ".join(f"`{member.name}`" for member in (banned + failed)[:15])
            await self._alert(
                guild,
                settings,
                "System1 mevcut bot taraması tamamlandı",
                f"Şüpheli bot: **{len(banned) + len(failed)}** | Banlanan: **{len(banned)}** | Başarısız: **{len(failed)}**\n{names}",
                discord.Color.red() if failed else discord.Color.orange(),
            )

        await interaction.followup.send(
            f"System1 tamamlandı. {len(locked)} kanal kilitlendi/açıldı, "
            f"{len(banned)} yabancı bot banlandı, {len(failed)} bot banlanamadı. "
            "Sürekli antibot koruması aktif.",
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = self._get_guild_settings(member.guild.id)
        if not settings["aktif"]:
            return

        if not member.bot:
            account_age = datetime.now(timezone.utc) - member.created_at
            if account_age < timedelta(days=7):
                await self._alert(
                    member.guild,
                    settings,
                    "Şüpheli hesap tespit edildi",
                    f"{member.mention} sunucuya yeni açılmış hesapla katıldı.\n"
                    f"Hesap yaşı: `{account_age.days} gün`\nKullanıcı ID: `{member.id}`",
                    discord.Color.orange(),
                )
            return

        if self._is_trusted_bot(member, settings):
            return
        if not member.guild.me.guild_permissions.ban_members:
            return

        # Do not wait for spam. An unapproved bot must not get a chance to post.
        if member.id == self.bot.user.id or member.top_role >= member.guild.me.top_role:
            return
        try:
            await member.guild.ban(member, reason="Antibot - güvenli listede olmayan bot")
        except (discord.Forbidden, discord.HTTPException):
            return

        await self._alert(
            member.guild,
            settings,
            "Şüpheli bot engellendi",
            f"{member.mention} (`{member.name}`) güvenli listede olmadığı için anında banlandı.\nBot ID: `{member.id}`",
            discord.Color.red(),
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        settings = self._get_guild_settings(member.guild.id)
        if not settings["aktif"] or not member.bot or self._is_trusted_bot(member, settings):
            return
        await self._alert(
            member.guild,
            settings,
            "Şüpheli bot sunucudan ayrıldı",
            f"{member.mention} (`{member.name}`) sunucudan ayrıldı.\nBot ID: `{member.id}`",
            discord.Color.dark_orange(),
        )

    @commands.Cog.listener()
    async def on_ready(self):
        """Catch bots that joined while this process was offline."""
        for guild in self.bot.guilds:
            settings = self._get_guild_settings(guild.id)
            if not settings["aktif"] or not guild.me.guild_permissions.ban_members:
                continue
            trusted = {str(bot_id) for bot_id in settings.get("guvenli_botlar", [])}
            for member in guild.members:
                if member.bot and member.id != self.bot.user.id and str(member.id) not in trusted:
                    if member.top_role < guild.me.top_role:
                        try:
                            await guild.ban(member, reason="Antibot - güvenli listede olmayan bot")
                        except (discord.Forbidden, discord.HTTPException):
                            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if not message.author.bot:
            return
        if message.author == self.bot.user:
            return
        if message.author.guild_permissions.administrator:
            return

        settings = self._get_guild_settings(message.guild.id)
        if self._is_trusted_bot(message.author, settings):
            return
        if not settings["aktif"]:
            return
        if not message.guild.me.guild_permissions.ban_members:
            return

        if message.author.id == message.guild.owner_id:
            return
        if message.author.top_role >= message.guild.me.top_role:
            return

        # The join event normally handles this. This is a fallback for bots
        # whose join event was missed during a reconnect.
        try:
            await message.guild.ban(message.author, reason="Antibot - güvenli listede olmayan bot")
        except (discord.Forbidden, discord.HTTPException):
            pass

async def setup(bot):
    await bot.add_cog(Antibot(bot))
