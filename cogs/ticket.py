import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

class TicketView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Ticket Oluştur", style=discord.ButtonStyle.green, emoji="🎫", custom_id="ticket_olustur")
    async def ticket_olustur(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        settings = TicketSistemi._get_settings(guild.id)

        existing = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.name.lower()}")
        if existing:
            await interaction.response.send_message("Zaten açık bir ticket kanalın var!", ephemeral=True)
            return

        kategori_id = settings.get("kategori_id")
        kategori = guild.get_channel(int(kategori_id)) if kategori_id else None
        if not kategori:
            kategori = discord.utils.get(guild.categories, name="TICKETS")
        if not kategori:
            kategori = await guild.create_category("TICKETS")

        yetkili_rol = guild.default_role
        user = interaction.user

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }

        yetkililer = settings.get("yetkililer", [])
        for rol_id in yetkililer:
            rol = guild.get_role(int(rol_id))
            if rol:
                overwrites[rol] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name.lower()}",
            category=kategori,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="Ticket Oluşturuldu",
            description=f"Hoş geldin {user.mention}! Yetkililer en kısa sürede sana yardımcı olacak.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_footer(text="Sorunun çözüldüyse aşağıdaki butona basarak ticket'ı kapat.")

        close_view = TicketKapatView(guild.id, self.bot)
        await channel.send(f"{user.mention} Yetkililer sizinle ilgilenecek.", embed=embed, view=close_view)

        await interaction.response.send_message(f"Ticket kanalın oluşturuldu: {channel.mention}", ephemeral=True)

        log_kanal_id = settings.get("log_kanal_id")
        if log_kanal_id:
            log_kanal = guild.get_channel(int(log_kanal_id))
            if log_kanal:
                log_embed = discord.Embed(
                    title="Ticket Açıldı",
                    description=f"{user.mention} tarafından ticket oluşturuldu",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                log_embed.add_field(name="Kanal", value=channel.mention, inline=True)
                await log_kanal.send(embed=log_embed)


class TicketKapatView(discord.ui.View):
    def __init__(self, guild_id, bot):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.bot = bot

    @discord.ui.button(label="Ticket Kapat", style=discord.ButtonStyle.red, emoji="🔒", custom_id="ticket_kapat")
    async def ticket_kapat(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = TicketSistemi._get_settings(self.guild_id)
        yetkililer = settings.get("yetkililer", [])
        user_roles = [str(r.id) for r in interaction.user.roles]
        is_admin = interaction.user.guild_permissions.administrator

        if not is_admin and not any(r in yetkililer for r in user_roles):
            yetkili_rol_mention = ""
            for rol_id in yetkililer:
                rol = interaction.guild.get_role(int(rol_id))
                if rol:
                    yetkili_rol_mention = rol.mention
                    break
            await interaction.response.send_message(f"Bu ticket'ı sadece yetkililer kapatabilir! {yetkili_rol_mention}", ephemeral=True)
            return

        await interaction.response.send_message("Ticket **5 saniye** içinde kapatılıyor...")
        await interaction.channel.edit(name=f"kapali-{interaction.channel.name}")
        await interaction.channel.set_permissions(interaction.guild.default_role, view_channel=False)
        for target in interaction.channel.overwrites:
            if isinstance(target, discord.Member) and not target.bot and not target.guild_permissions.administrator:
                await interaction.channel.set_permissions(target, view_channel=False)

        embed = discord.Embed(
            title="Ticket Kapatıldı",
            description=f"{interaction.user.mention} tarafından kapatıldı. Kanal **10 saniye** içinde silinecek.",
            color=discord.Color.red()
        )
        await interaction.channel.send(embed=embed)

        import asyncio
        await asyncio.sleep(10)
        await interaction.channel.delete()

        log_kanal_id = settings.get("log_kanal_id")
        if log_kanal_id:
            log_kanal = interaction.guild.get_channel(int(log_kanal_id))
            if log_kanal:
                log_embed = discord.Embed(
                    title="Ticket Kapatıldı",
                    description=f"Ticket kanalı silindi",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                log_embed.add_field(name="Kapatıldı", value=interaction.user.mention, inline=True)
                await log_kanal.send(embed=log_embed)


class TicketSistemi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "ticket_settings.json"
        self._init_settings()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, "w") as f:
                json.dump({}, f)

    async def cog_load(self):
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
        except:
            return
        for gid, settings in data.items():
            kanal_id = settings.get("kanal_id")
            if kanal_id:
                self.bot.add_view(TicketView(self.bot))
                break

    @staticmethod
    def _get_settings(guild_id: int):
        try:
            with open("ticket_settings.json", "r") as f:
                all_settings = json.load(f)
        except:
            all_settings = {}
        gid = str(guild_id)
        if gid not in all_settings:
            all_settings[gid] = {"kanal_id": None, "kategori_id": None, "yetkililer": [], "log_kanal_id": None}
        return all_settings[gid]

    def _save_settings(self, guild_id: int, settings: dict):
        try:
            with open(self.settings_file, "r") as f:
                all_settings = json.load(f)
        except:
            all_settings = {}
        all_settings[str(guild_id)] = settings
        with open(self.settings_file, "w") as f:
            json.dump(all_settings, f, indent=4)

    @app_commands.command(name="ticket", description="Ticket sistemini kur")
    @app_commands.describe(kanal="Ticket panelinin gönderileceği kanal")
    @app_commands.guild_only()
    async def ticket_kur(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        s = self._get_settings(interaction.guild.id)
        s["kanal_id"] = str(kanal.id)
        self._save_settings(interaction.guild.id, s)

        embed = discord.Embed(
            title="Ticket Sistemi",
            description="Destek almak için aşağıdaki butona tıklayarak ticket oluşturabilirsiniz.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Nasıl Çalışır?", value="Butona tıklayın, size özel bir kanal açılır. Yetkililer bu kanaldan size yardımcı olur.", inline=False)
        embed.set_footer(text="Ticket Sistemi")

        await kanal.send(embed=embed, view=TicketView(self.bot))
        await interaction.followup.send(f"Ticket paneli {kanal.mention} kanalına kuruldu!")

    @app_commands.command(name="ticket-yetkili", description="Ticketları görebilecek yetkili rolü ekle/çıkar")
    @app_commands.describe(rol="Yetkili rol", durum="Ekle veya çıkar")
    @app_commands.guild_only()
    async def ticket_yetkili(self, interaction: discord.Interaction, rol: discord.Role, durum: str = "ekle"):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)
            return
        s = self._get_settings(interaction.guild.id)
        if "yetkililer" not in s:
            s["yetkililer"] = []

        if durum == "ekle":
            if str(rol.id) not in s["yetkililer"]:
                s["yetkililer"].append(str(rol.id))
                self._save_settings(interaction.guild.id, s)
                await interaction.response.send_message(f"{rol.mention} ticket yetkilisi olarak eklendi.", ephemeral=True)
            else:
                await interaction.response.send_message(f"{rol.mention} zaten yetkili listesinde.", ephemeral=True)
        elif durum == "çıkar":
            if str(rol.id) in s["yetkililer"]:
                s["yetkililer"].remove(str(rol.id))
                self._save_settings(interaction.guild.id, s)
                await interaction.response.send_message(f"{rol.mention} ticket yetkililerinden çıkarıldı.", ephemeral=True)
            else:
                await interaction.response.send_message(f"{rol.mention} yetkili listesinde değil.", ephemeral=True)
        else:
            await interaction.response.send_message("`ekle` veya `çıkar` yazın.", ephemeral=True)

    @app_commands.command(name="ticket-log", description="Ticket log kanalını ayarla")
    @app_commands.describe(kanal="Log kanalı")
    @app_commands.guild_only()
    async def ticket_log(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)
            return
        s = self._get_settings(interaction.guild.id)
        s["log_kanal_id"] = str(kanal.id)
        self._save_settings(interaction.guild.id, s)
        await interaction.response.send_message(f"Ticket log kanalı {kanal.mention} olarak ayarlandı.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketSistemi(bot))
