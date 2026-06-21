import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class OtoRolView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu menüyü kullanmak için yetkiniz yok!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Rol Ayarla", style=discord.ButtonStyle.primary, emoji="🎭")
    async def set_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = OtoRolModal(self.cog, self.guild_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Kapat", style=discord.ButtonStyle.danger, emoji="❌")
    async def disable(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = self.cog._get_settings(self.guild_id)
        if "rol" in settings:
            del settings["rol"]
            self.cog._save_settings(self.guild_id, settings)
        await self._refresh(interaction)

    async def _refresh(self, interaction: discord.Interaction):
        settings = self.cog._get_settings(self.guild_id)
        rol_id = settings.get("rol")
        embed = discord.Embed(title="Oto-Rol Ayarları", color=discord.Color.blue() if rol_id else discord.Color.red())
        if rol_id:
            r = interaction.guild.get_role(int(rol_id))
            embed.add_field(name="Rol", value=r.mention if r else f"`{rol_id}` (silindi)", inline=False)
            embed.add_field(name="Durum", value="✅ Aktif", inline=False)
        else:
            embed.description = "Oto-rol ayarlanmamış. 'Rol Ayarla' butonuna tıklayarak bir rol belirleyin."
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except:
                pass

class OtoRolModal(discord.ui.Modal, title="Oto-Rol Ayarla"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.rol_id = discord.ui.TextInput(label="Rol ID veya adı", placeholder="Rolün ID'sini veya tam adını yaz", required=True, max_length=100)
        self.add_item(self.rol_id)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        rol = None
        try:
            rid = int(self.rol_id.value)
            rol = guild.get_role(rid)
        except ValueError:
            rol = discord.utils.get(guild.roles, name=self.rol_id.value)

        if not rol:
            await interaction.response.send_message("Rol bulunamadı! Doğru ID veya isim girdiğinden emin ol.", ephemeral=True)
            return

        if rol >= guild.me.top_role:
            await interaction.response.send_message("Bu rol botun en yüksek rolünün üstünde! Lütfen bot rolünü yukarı taşı.", ephemeral=True)
            return

        settings = self.cog._get_settings(self.guild_id)
        settings["rol"] = str(rol.id)
        self.cog._save_settings(self.guild_id, settings)

        embed = discord.Embed(title="Oto-Rol Ayarları", color=discord.Color.green())
        embed.add_field(name="Rol", value=rol.mention, inline=False)
        embed.add_field(name="Durum", value="✅ Aktif", inline=False)
        await interaction.response.edit_message(embed=embed)

class OtoRol(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "otorol_settings.json"
        self._init_settings()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, "w") as f:
                json.dump({}, f)

    def _get_settings(self, guild_id):
        defaults = {"rol": None}
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
            gs = data.get(str(guild_id), {})
            for k, v in defaults.items():
                gs.setdefault(k, v)
            return gs
        except:
            return defaults

    def _save_settings(self, guild_id, settings):
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
        except:
            data = {}
        data[str(guild_id)] = settings
        with open(self.settings_file, "w") as f:
            json.dump(data, f, indent=4)

    @app_commands.command(name="otorol", description="Oto-rol ayarlarını yönet")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def otorol(self, interaction: discord.Interaction):
        settings = self._get_settings(interaction.guild.id)
        rol_id = settings.get("rol")
        embed = discord.Embed(title="Oto-Rol Ayarları", color=discord.Color.blue() if rol_id else discord.Color.red())
        if rol_id:
            r = interaction.guild.get_role(int(rol_id))
            embed.add_field(name="Rol", value=r.mention if r else f"`{rol_id}` (silindi)", inline=False)
            embed.add_field(name="Durum", value="✅ Aktif", inline=False)
        else:
            embed.description = "Oto-rol ayarlanmamış. 'Rol Ayarla' butonuna tıklayarak bir rol belirleyin."
        view = OtoRolView(self, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        settings = self._get_settings(member.guild.id)
        rol_id = settings.get("rol")
        if not rol_id:
            return
        rol = member.guild.get_role(int(rol_id))
        if not rol:
            return
        try:
            await member.add_roles(rol, reason="Oto-rol")
        except:
            pass

async def setup(bot):
    await bot.add_cog(OtoRol(bot))
