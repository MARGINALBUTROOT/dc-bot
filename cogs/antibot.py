import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
import time
from collections import defaultdict, deque
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


class GuvenliSilModal(discord.ui.Modal, title="Güvenli Bot Çıkar"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.bot_id = discord.ui.TextInput(label="Bot ID", placeholder="Güvenli listeden çıkarılacak bot ID'si", required=True, max_length=30)
        self.add_item(self.bot_id)

    async def on_submit(self, interaction: discord.Interaction):
        bid = self.bot_id.value.strip()
        settings = self.cog._get_guild_settings(self.guild_id)
        if bid not in settings.get("guvenli_botlar", []):
            await interaction.response.send_message("Bu bot güvenli listede değil.", ephemeral=True)
            return
        settings["guvenli_botlar"].remove(bid)
        self.cog._save_guild_settings(self.guild_id, settings)
        await interaction.response.send_message(f"Bot `{bid}` güvenli listeden çıkarıldı.", ephemeral=True)


class YetkiliEkleModal(discord.ui.Modal, title="İzinli Yönetici Ekle"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = discord.ui.TextInput(label="Yönetici kullanıcı ID", placeholder="Bot eklemesine izin verilecek yönetici ID'si", required=True, max_length=30)
        self.add_item(self.user_id)

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.user_id.value.strip()
        if not uid.isdigit():
            await interaction.response.send_message("Geçerli bir kullanıcı ID gir.", ephemeral=True)
            return
        member = interaction.guild.get_member(int(uid))
        if not member or not member.guild_permissions.administrator:
            await interaction.response.send_message("Bu kullanıcı sunucuda olmalı ve Administrator yetkisine sahip olmalı.", ephemeral=True)
            return
        settings = self.cog._get_guild_settings(self.guild_id)
        if uid not in settings["izinli_yetkililer"]:
            settings["izinli_yetkililer"].append(uid)
            self.cog._save_guild_settings(self.guild_id, settings)
        await interaction.response.send_message(f"{member.mention} bot ekleme izinlileri listesine eklendi.", ephemeral=True)


class YetkiliSilModal(discord.ui.Modal, title="İzinli Yönetici Çıkar"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = discord.ui.TextInput(label="Yönetici kullanıcı ID", required=True, max_length=30)
        self.add_item(self.user_id)

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.user_id.value.strip()
        settings = self.cog._get_guild_settings(self.guild_id)
        if uid not in settings["izinli_yetkililer"]:
            await interaction.response.send_message("Bu kullanıcı izinli listede değil.", ephemeral=True)
            return
        settings["izinli_yetkililer"].remove(uid)
        self.cog._save_guild_settings(self.guild_id, settings)
        await interaction.response.send_message(f"`{uid}` izinli yönetici listesinden çıkarıldı.", ephemeral=True)


class ManuelKanalModal(discord.ui.Modal, title="Manuel Kanal Kilidi"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.kanal = discord.ui.TextInput(label="Yazı kanalı ID veya mention", placeholder="123456789012345678 veya #kanal", required=True, max_length=50)
        self.islem = discord.ui.TextInput(label="İşlem", placeholder="kilitle veya aç", required=True, max_length=10)
        self.add_item(self.kanal)
        self.add_item(self.islem)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.kanal.value.strip()
        if value.startswith("<#") and value.endswith(">"):
            value = value[2:-1]
        if not value.isdigit():
            await interaction.response.send_message("Geçerli bir kanal ID veya mention gir.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(int(value))
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Bu ID bir yazı kanalına ait değil.", ephemeral=True)
            return
        action = self.islem.value.strip().lower()
        if action not in {"kilitle", "kitle", "lock", "aç", "ac", "unlock"}:
            await interaction.response.send_message("İşlem olarak `kilitle` veya `aç` yaz.", ephemeral=True)
            return
        locked = action in {"kilitle", "kitle", "lock"}
        try:
            await self.cog._set_channel_lock(interaction.guild, channel, locked)
        except (discord.Forbidden, discord.HTTPException, RuntimeError):
            await interaction.response.send_message("Kanal izni değiştirilemedi. Botta Manage Channels yetkisi olmalı.", ephemeral=True)
            return
        await interaction.response.send_message(f"{channel.mention} {'kilitlendi' if locked else 'açıldı'}.", ephemeral=True)


class OnayView(discord.ui.View):
    def __init__(self, cog, guild_id, user_id, is_bot=True):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id
        self.message = None
        self.is_bot = is_bot
        self.guvenli_al.disabled = not is_bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.cog._can_approve(interaction):
            await interaction.response.send_message("Bu işlem için yetkili değilsiniz.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Banla", style=discord.ButtonStyle.danger, emoji="🔨")
    async def banla(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._approve_ban(interaction, self.guild_id, self.user_id, self)

    @discord.ui.button(label="Sunucudan At", style=discord.ButtonStyle.danger, emoji="👢")
    async def at(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = self.cog.bot.get_guild(self.guild_id)
        member = guild.get_member(self.user_id) if guild else None
        if not guild or not member:
            await interaction.response.edit_message(content="Üye artık sunucuda değil.", view=None)
            return
        try:
            await guild.kick(member, reason=f"Antibot - {interaction.user} tarafından onaylandı")
            self.cog.pending_reviews.pop((self.guild_id, self.user_id), None)
            self.cog.quarantine_overwrites.pop((self.guild_id, self.user_id), None)
            await interaction.response.edit_message(content=f"👢 `{member}` sunucudan atıldı.", view=None)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message("Üye atılamadı. Botta Kick Members yetkisi olmalı.", ephemeral=True)

    @discord.ui.button(label="Güvenli Listeye Al", style=discord.ButtonStyle.success, emoji="✅")
    async def guvenli_al(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = self.cog._get_guild_settings(self.guild_id)
        bid = str(self.user_id)
        if bid not in settings["guvenli_botlar"]:
            settings["guvenli_botlar"].append(bid)
            self.cog._save_guild_settings(self.guild_id, settings)
        await self.cog._release_quarantine(self.guild_id, self.user_id)
        await interaction.response.edit_message(content="✅ Bot güvenli listeye alındı.", view=None)
        self.cog.pending_reviews.pop((self.guild_id, self.user_id), None)

    @discord.ui.button(label="Yoksay / Karantinada Tut", style=discord.ButtonStyle.secondary, emoji="⏸️")
    async def yoksay(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="⏸️ İşlem yoksayıldı; hesap karantinada tutuluyor.", view=None)
        self.cog.pending_reviews.pop((self.guild_id, self.user_id), None)


class BotTaramaView(discord.ui.View):
    def __init__(self, cog, guild_id, members):
        super().__init__(timeout=900)
        self.cog = cog
        self.guild_id = guild_id
        self.members = {str(member.id): member for member in members}
        self.selected_id = None
        options = [
            discord.SelectOption(
                label=member.name[:100],
                value=str(member.id),
                description=f"ID: {member.id}",
            )
            for member in members[:25]
        ]
        select = discord.ui.Select(placeholder="İşlem yapılacak botu seç", options=options, custom_id=f"bot_scan_{guild_id}")
        select.callback = self._select_callback
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.cog._can_approve(interaction):
            await interaction.response.send_message("Bu işlem için yetkiniz yok.", ephemeral=True)
            return False
        return True

    async def _select_callback(self, interaction: discord.Interaction):
        self.selected_id = interaction.data.get("values", [None])[0]
        member = self.members.get(self.selected_id)
        await interaction.response.send_message(f"Seçildi: `{member.name if member else self.selected_id}`", ephemeral=True)

    def _selected_member(self):
        return self.members.get(self.selected_id)

    @discord.ui.button(label="Seçili Botu Banla", style=discord.ButtonStyle.danger, emoji="🔨")
    async def banla(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = self._selected_member()
        if not member:
            await interaction.response.send_message("Önce listeden bir bot seç.", ephemeral=True)
            return
        try:
            await interaction.guild.ban(member, reason=f"Antibot taraması - {interaction.user} onayı")
            self.members.pop(str(member.id), None)
            self.cog.pending_reviews.pop((self.guild_id, member.id), None)
            self.cog.quarantine_overwrites.pop((self.guild_id, member.id), None)
            await interaction.response.send_message(f"🔨 `{member}` banlandı.", ephemeral=True)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message("Bot banlanamadı. Rol hiyerarşisini ve Ban Members yetkisini kontrol et.", ephemeral=True)

    @discord.ui.button(label="Seçili Botu At", style=discord.ButtonStyle.danger, emoji="👢")
    async def at(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = self._selected_member()
        if not member:
            await interaction.response.send_message("Önce listeden bir bot seç.", ephemeral=True)
            return
        try:
            await interaction.guild.kick(member, reason=f"Antibot taraması - {interaction.user} onayı")
            self.members.pop(str(member.id), None)
            self.cog.pending_reviews.pop((self.guild_id, member.id), None)
            self.cog.quarantine_overwrites.pop((self.guild_id, member.id), None)
            await interaction.response.send_message(f"👢 `{member}` sunucudan atıldı.", ephemeral=True)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message("Bot atılamadı. Kick Members yetkisini ve rol hiyerarşisini kontrol et.", ephemeral=True)

    @discord.ui.button(label="Güvenli Listeye Al", style=discord.ButtonStyle.success, emoji="✅")
    async def guvenli_al(self, interaction: discord.Interaction, button: discord.Button):
        member = self._selected_member()
        if not member:
            await interaction.response.send_message("Önce listeden bir bot seç.", ephemeral=True)
            return
        settings = self.cog._get_guild_settings(self.guild_id)
        if str(member.id) not in settings["guvenli_botlar"]:
            settings["guvenli_botlar"].append(str(member.id))
            self.cog._save_guild_settings(self.guild_id, settings)
        await self.cog._release_quarantine(self.guild_id, member.id)
        self.cog.pending_reviews.pop((self.guild_id, member.id), None)
        await interaction.response.send_message(f"✅ `{member}` güvenli listeye alındı.", ephemeral=True)

    @discord.ui.button(label="Karantinada Tut", style=discord.ButtonStyle.secondary, emoji="⏸️")
    async def karantinada_tut(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = self._selected_member()
        if not member:
            await interaction.response.send_message("Önce listeden bir bot seç.", ephemeral=True)
            return
        await interaction.response.send_message(f"⏸️ `{member}` karantinada tutuluyor.", ephemeral=True)

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
        s["system1_aktif"] = s["aktif"]
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

    @discord.ui.button(label="Güvenli Çıkar", style=discord.ButtonStyle.secondary, emoji="➖")
    async def guvenli_cikar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GuvenliSilModal(self.cog, self.guild_id))

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

    @discord.ui.button(label="Yönetici Ekle", style=discord.ButtonStyle.secondary, emoji="👤")
    async def yetkili_ekle(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(YetkiliEkleModal(self.cog, self.guild_id))

    @discord.ui.button(label="Yönetici Çıkar", style=discord.ButtonStyle.secondary, emoji="🚫")
    async def yetkili_cikar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(YetkiliSilModal(self.cog, self.guild_id))

    @discord.ui.button(label="Yönetici Listesi", style=discord.ButtonStyle.secondary, emoji="📋")
    async def yetkili_liste(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = self.cog._get_guild_settings(self.guild_id)
        ids = settings.get("izinli_yetkililer", [])
        await interaction.response.send_message(
            "\n".join(f"• <@{uid}> (`{uid}`)" for uid in ids) if ids else "İzinli yönetici yok.",
            ephemeral=True,
        )

    @discord.ui.button(label="Kalkanı Başlat", style=discord.ButtonStyle.success, emoji="🛡️")
    async def kalkan_baslat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._run_shield(interaction)

    @discord.ui.button(label="Dış Giriş Kilidini Aç", style=discord.ButtonStyle.primary, emoji="🔓")
    async def dis_giris_ac(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.cog._set_join_lockdown(interaction.guild, False)
            await interaction.response.send_message("Dış giriş kilidi açıldı; sunucu eski doğrulama seviyesine döndü.", ephemeral=True)
        except (discord.Forbidden, discord.HTTPException, RuntimeError):
            await interaction.response.send_message("Dış giriş kilidi açılamadı. Botta Manage Server yetkisi olmalı.", ephemeral=True)

    @discord.ui.button(label="Kanalları Kilitle/Aç", style=discord.ButtonStyle.danger, emoji="🔒")
    async def kanallari_kilitle(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ManuelKanalModal(self.cog, self.guild_id))

    async def _build_embed(self, guild):
        s = self.cog._get_guild_settings(self.guild_id)
        durum = "✅ Aktif" if s["aktif"] else "❌ Devre Dışı"
        embed = discord.Embed(title="Antibot Koruması", description="Şüpheli botları karantinaya alır ve yetkili onayı olmadan banlamaz.", color=discord.Color.blue() if s["aktif"] else discord.Color.red())
        embed.add_field(name="Durum", value=durum, inline=True)
        embed.add_field(name="Ban Eşiği", value=f"{s['esik']} mesaj", inline=True)
        kanal = self.cog._get_kanal(s)
        embed.add_field(name="Bildirim Kanalı", value=kanal.mention if kanal else "Ayarlanmamış", inline=False)
        guvenli_sayisi = len(s.get("guvenli_botlar", []))
        embed.add_field(name="Güvenli Bot", value=f"{guvenli_sayisi} bot listede" if guvenli_sayisi else "Yok", inline=False)
        yetkili_sayisi = len(s.get("izinli_yetkililer", []))
        embed.add_field(name="Bot Ekleyebilen Yöneticiler", value=f"{yetkili_sayisi} kişi" if yetkili_sayisi else "Yok", inline=False)
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
        self.bot_sayac = defaultdict(deque)
        self.pending_reviews = {}
        self.quarantine_overwrites = {}
        self.channel_lock_backups = {}
        self._init_settings()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            write_json(self.settings_file, {})

    def _get_guild_settings(self, guild_id: int):
        # Safe default: only explicitly approved bots may join.
        defaults = {"aktif": False, "system1_aktif": False, "mutlak": False, "esik": 6, "kanal_id": None, "guvenli_botlar": [], "izinli_yetkililer": [], "kanal_kilitli": False, "kanal_kilitleri": {}, "join_lockdown": False, "onceki_dogrulama": None}
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

    def _can_approve(self, interaction):
        if interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_guild:
            return True
        settings = self._get_guild_settings(interaction.guild.id)
        return str(interaction.user.id) in {str(uid) for uid in settings.get("izinli_yetkililer", [])}

    async def _quarantine(self, member):
        key = (member.guild.id, member.id)
        if key in self.quarantine_overwrites:
            return
        previous = {}
        for channel in member.guild.text_channels:
            try:
                old = channel.overwrites_for(member)
                await channel.set_permissions(
                    member,
                    send_messages=False,
                    add_reactions=False,
                    create_public_threads=False,
                    create_private_threads=False,
                    reason="Antibot - yetkili onayı bekleniyor",
                )
                previous[channel.id] = old
            except (discord.Forbidden, discord.HTTPException):
                pass
        self.quarantine_overwrites[key] = previous

    async def _release_quarantine(self, guild_id, user_id):
        previous = self.quarantine_overwrites.pop((guild_id, user_id), {})
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        member = guild.get_member(user_id)
        if not member:
            return
        for channel_id, overwrite in previous.items():
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                await channel.set_permissions(
                    member,
                    overwrite=None if overwrite.is_empty() else overwrite,
                    reason="Antibot - karantina kaldırıldı",
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

    async def _approve_ban(self, interaction, guild_id, user_id, view):
        guild = self.bot.get_guild(guild_id)
        member = guild.get_member(user_id) if guild else None
        if not guild or not member:
            await interaction.response.edit_message(content="Üye artık sunucuda değil.", view=None)
            self.pending_reviews.pop((guild_id, user_id), None)
            return
        try:
            await guild.ban(member, reason=f"Antibot - {interaction.user} tarafından onaylandı")
            await interaction.response.edit_message(content=f"🔨 `{member}` yetkili onayıyla banlandı.", view=None)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message("Ban başarısız. Botun rolü hedefin üstünde ve Ban Members yetkisi açık olmalı.", ephemeral=True)
            return
        self.pending_reviews.pop((guild_id, user_id), None)
        self.quarantine_overwrites.pop((guild_id, user_id), None)

    async def _alert(self, guild, settings, title, description, color=discord.Color.orange(), view=None):
        channel = self._get_kanal(settings) or guild.system_channel
        if not channel or not channel.permissions_for(guild.me).send_messages:
            return
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
        embed.set_footer(text="System1 güvenlik kalkanı")
        try:
            await channel.send(
                embed=embed,
                view=view,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _set_channel_lock(self, guild, channel, locked):
        if not guild.me.guild_permissions.manage_channels:
            raise RuntimeError("Manage Channels yetkisi gerekli")
        settings = self._get_guild_settings(guild.id)
        backups = self.channel_lock_backups.setdefault(guild.id, {})
        if locked:
            if channel.id not in backups:
                backups[channel.id] = channel.overwrites_for(guild.default_role)
            await channel.set_permissions(
                guild.default_role,
                send_messages=False,
                reason="Antibot paneli - manuel kanal kilidi",
            )
            settings["kanal_kilitli"] = True
            settings.setdefault("kanal_kilitleri", {})[str(channel.id)] = backups[channel.id].send_messages
        else:
            overwrite = backups.pop(channel.id, None)
            saved_map = settings.setdefault("kanal_kilitleri", {})
            channel_key = str(channel.id)
            if overwrite is None and channel_key not in saved_map:
                raise RuntimeError("Bu kanal panel tarafından kilitlenmemiş")
            saved = saved_map.pop(channel_key, None)
            if overwrite is not None:
                await channel.set_permissions(
                    guild.default_role,
                    overwrite=None if overwrite.is_empty() else overwrite,
                    reason="Antibot paneli - manuel kanal kilidi açıldı",
                )
            else:
                await channel.set_permissions(
                    guild.default_role,
                    send_messages=saved,
                    reason="Antibot paneli - manuel kanal kilidi açıldı",
                )
            settings["kanal_kilitli"] = bool(settings.get("kanal_kilitleri"))
        self._save_guild_settings(guild.id, settings)

    async def _set_join_lockdown(self, guild, locked):
        if not guild.me.guild_permissions.manage_guild:
            raise RuntimeError("Manage Server yetkisi gerekli")
        settings = self._get_guild_settings(guild.id)
        if locked:
            if settings.get("join_lockdown"):
                return
            settings["onceki_dogrulama"] = guild.verification_level.value
            await guild.edit(
                verification_level=discord.VerificationLevel.highest,
                reason="Antibot kalkanı - dış girişler geçici olarak kapatıldı",
            )
            try:
                invites = await guild.invites()
                await asyncio.gather(*(invite.delete(reason="Antibot kalkanı raid kilidi") for invite in invites))
            except (discord.Forbidden, discord.HTTPException):
                pass
            settings["join_lockdown"] = True
        else:
            previous = settings.get("onceki_dogrulama")
            if previous is not None:
                await guild.edit(
                    verification_level=discord.VerificationLevel(previous),
                    reason="Antibot kalkanı - dış giriş kilidi açıldı",
                )
            settings["join_lockdown"] = False
            settings["onceki_dogrulama"] = None
        self._save_guild_settings(guild.id, settings)

    async def _bot_inviter(self, guild, bot_id):
        if not guild.me.guild_permissions.view_audit_log:
            return None
        try:
            async for entry in guild.audit_logs(limit=10, action=discord.AuditLogAction.bot_add):
                if entry.target and entry.target.id == bot_id:
                    age = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
                    if age < 30:
                        return entry.user
        except (discord.Forbidden, discord.HTTPException):
            pass
        return None

    async def _allowed_bot_inviter(self, guild, member, settings):
        inviter = await self._bot_inviter(guild, member.id)
        allowed = {str(uid) for uid in settings.get("izinli_yetkililer", [])}
        return inviter, inviter is not None and str(inviter.id) in allowed

    async def _queue_review(self, member):
        key = (member.guild.id, member.id)
        if key in self.pending_reviews:
            return
        await self._quarantine(member)
        self.pending_reviews[key] = True

    async def _request_review(self, member, settings, reason):
        await self._queue_review(member)
        view = OnayView(self, member.guild.id, member.id, member.bot)
        await self._alert(
            member.guild,
            settings,
            "Yetkili Onayı Bekleniyor",
            f"{member.mention} (`{member.name}`) şüpheli hesap olarak karantinaya alındı.\n"
            f"Sebep: {reason}\nID: `{member.id}`\nBan için aşağıdaki butona yetkili basmalı.",
            discord.Color.red(),
            view,
        )

    async def _send_scan_review(self, guild, settings, members):
        if not members:
            return
        view = BotTaramaView(self, guild.id, members)
        names = "\n".join(
            f"• `{member.name}` (`{member.id}`) - Karantinada"
            for member in members[:25]
        )
        await self._alert(
            guild,
            settings,
            "Bot Tarama Sonucu - İşlem Seç",
            f"Toplam **{len(members)}** şüpheli bot bulundu.\n\n{names}\n\nListeden botu seçip yapılacak işlemi belirle.",
            discord.Color.orange(),
            view,
        )

    async def _refresh_embed(self, s, guild):
        durum = "✅ Aktif" if s["aktif"] else "❌ Devre Dışı"
        embed = discord.Embed(title="Antibot Koruması", description="Şüpheli botları karantinaya alır ve yetkili onayı olmadan banlamaz.", color=discord.Color.blue() if s["aktif"] else discord.Color.red())
        embed.add_field(name="Durum", value=durum, inline=True)
        embed.add_field(name="Ban Eşiği", value=f"{s['esik']} mesaj", inline=True)
        kanal = self._get_kanal(s)
        embed.add_field(name="Bildirim Kanalı", value=kanal.mention if kanal else "Ayarlanmamış", inline=False)
        guvenli_sayisi = len(s.get("guvenli_botlar", []))
        embed.add_field(name="Güvenli Bot", value=f"{guvenli_sayisi} bot listede" if guvenli_sayisi else "Yok", inline=False)
        yetkili_sayisi = len(s.get("izinli_yetkililer", []))
        embed.add_field(name="Bot Ekleyebilen Yöneticiler", value=f"{yetkili_sayisi} kişi" if yetkili_sayisi else "Yok", inline=False)
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

    async def _review_untrusted_bots(self, guild):
        settings = self._get_guild_settings(guild.id)
        trusted = {str(bot_id) for bot_id in settings.get("guvenli_botlar", [])}
        try:
            await guild.chunk(cache=True)
        except (discord.Forbidden, discord.HTTPException):
            pass
        targets = []
        for member in guild.members:
            if not member.bot or member.id == self.bot.user.id or str(member.id) in trusted:
                continue
            _, allowed = await self._allowed_bot_inviter(guild, member, settings)
            if not allowed and member.top_role < guild.me.top_role:
                targets.append(member)

        await asyncio.gather(*(self._queue_review(member) for member in targets))
        return targets

    async def _run_shield(self, interaction: discord.Interaction):
        guild = interaction.guild
        me = guild.me
        if not me.guild_permissions.ban_members or not me.guild_permissions.manage_channels or not me.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "Kalkan için botta `Ban Members`, `Manage Channels` ve `Manage Server` yetkileri olmalı.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        settings = self._get_guild_settings(guild.id)
        settings["aktif"] = True
        settings["system1_aktif"] = True
        # System1 uses the allowlist: every bot outside it is suspicious.
        settings["mutlak"] = False
        self._save_guild_settings(guild.id, settings)

        try:
            await self._set_join_lockdown(guild, True)
        except (discord.Forbidden, discord.HTTPException, RuntimeError):
            await interaction.followup.send("Kalkan başladı ancak dış giriş kilidi açılamadı. Botta Manage Server yetkisini kontrol et.", ephemeral=True)

        targets = await self._review_untrusted_bots(guild)

        if targets:
            await self._send_scan_review(guild, settings, targets)

        await interaction.followup.send(
            f"Kalkan aktif. {len(targets)} şüpheli bot karantinaya alındı, yetkili onayı bekleniyor. "
            "Sürekli antibot koruması aktif.",
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = self._get_guild_settings(member.guild.id)
        if not settings.get("system1_aktif", False):
            return

        if not member.bot:
            account_age = datetime.now(timezone.utc) - member.created_at
            if account_age < timedelta(days=7):
                await self._request_review(member, settings, f"Yeni hesap (yaş: {account_age.days} gün)")
            return

        if self._is_trusted_bot(member, settings):
            return
        if member.id == self.bot.user.id:
            return
        inviter, allowed = await self._allowed_bot_inviter(member.guild, member, settings)
        if allowed:
            await self._alert(
                member.guild,
                settings,
                "İzinli yönetici bot ekledi",
                f"{member.mention} (`{member.name}`) {inviter.mention} tarafından eklendi ve otomatik olarak izin verildi.\nBot ID: `{member.id}`",
                discord.Color.green(),
            )
            return
        await self._request_review(member, settings, "Güvenli listede olmayan bot sunucuya katıldı")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        settings = self._get_guild_settings(member.guild.id)
        if not settings.get("system1_aktif", False) or not member.bot or self._is_trusted_bot(member, settings):
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
            if not settings.get("system1_aktif", False) or not guild.me.guild_permissions.ban_members:
                continue
            await self._review_untrusted_bots(guild)

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
        if not settings.get("system1_aktif", False):
            return
        key = (message.guild.id, message.author.id)
        now = time.monotonic()
        timestamps = self.bot_sayac[key]
        while timestamps and now - timestamps[0] > 15:
            timestamps.popleft()
        timestamps.append(now)
        if len(timestamps) >= settings["esik"]:
            await self._request_review(
                message.author,
                settings,
                f"15 saniyede {len(timestamps)} mesaj gönderdi (eşik: {settings['esik']})",
            )
            self.bot_sayac.pop(key, None)

async def setup(bot):
    await bot.add_cog(Antibot(bot))
