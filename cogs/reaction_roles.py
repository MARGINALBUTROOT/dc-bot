import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class RolPanelView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id
        self._load_buttons()

    def _load_buttons(self):
        self.clear_items()
        settings = self.cog._get_settings(self.guild_id)
        roller = settings.get("roller", [])
        for r in roller:
            rol_id = int(r["rol_id"])
            button = discord.ui.Button(
                label=r.get("isim", f"Rol {rol_id}"),
                style=discord.ButtonStyle.secondary,
                custom_id=f"rol_panel_{self.guild_id}_{rol_id}"
            )
            async def callback(interaction: discord.Interaction, rol_id=rol_id):
                rol = interaction.guild.get_role(rol_id)
                if not rol:
                    await interaction.response.send_message("Bu rol silinmis!", ephemeral=True)
                    return
                if rol in interaction.user.roles:
                    await interaction.user.remove_roles(rol, reason="Rol paneli")
                    await interaction.response.send_message(f"{rol.mention} rolu kaldirildi.", ephemeral=True)
                else:
                    await interaction.user.add_roles(rol, reason="Rol paneli")
                    await interaction.response.send_message(f"{rol.mention} rolu verildi.", ephemeral=True)
            button.callback = callback
            self.add_item(button)

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "reaction_roles.json"
        self._init_settings()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, "w") as f:
                json.dump({}, f)

    def _get_settings(self, guild_id):
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
            return data.get(str(guild_id), {"kanal": None, "mesaj_id": None, "roller": []})
        except:
            return {"kanal": None, "mesaj_id": None, "roller": []}

    def _save_settings(self, guild_id, settings):
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
        except:
            data = {}
        data[str(guild_id)] = settings
        with open(self.settings_file, "w") as f:
            json.dump(data, f, indent=4)

    async def _panel_guncelle(self, guild_id):
        settings = self._get_settings(guild_id)
        kanal_id = settings.get("kanal")
        mesaj_id = settings.get("mesaj_id")
        if not kanal_id:
            return
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return
        kanal = guild.get_channel(int(kanal_id))
        if not kanal:
            return
        roller = settings.get("roller", [])
        if roller:
            liste = []
            for r in roller:
                rol_obj = guild.get_role(int(r["rol_id"]))
                liste.append(f"{rol_obj.mention if rol_obj else 'Silinmis rol'}")
            embed = discord.Embed(
                title=settings.get("baslik", "Rol Paneli"),
                description="Asagidaki butonlara tiklayarak rollerini alabilir/kaldirabilirsin.\n\n" + "\n".join(liste),
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title=settings.get("baslik", "Rol Paneli"),
                description="Henuz rol eklenmemis. `/rol-paneli ekle:@rol`",
                color=discord.Color.blue()
            )
        view = RolPanelView(self, guild_id)
        try:
            mesaj = await kanal.fetch_message(int(mesaj_id))
            await mesaj.edit(embed=embed, view=view)
        except:
            mesaj = await kanal.send(embed=embed, view=view)
            settings["mesaj_id"] = str(mesaj.id)
            self._save_settings(guild_id, settings)

    async def cog_load(self):
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
        except:
            return
        for gid, settings in data.items():
            mesaj_id = settings.get("mesaj_id")
            if mesaj_id:
                self.bot.add_view(RolPanelView(self, int(gid)))

    @app_commands.command(name="rol-paneli", description="Rol paneli sistemi")
    @app_commands.describe(
        ekle="Panele eklenecek rol",
        kaldir="Panelden cikarilacak rol",
        kanal="Panelin gonderilecegi kanal (ilk kurulum)",
        baslik="Panel basligi (opsiyonel)"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def rol_paneli(
        self,
        interaction: discord.Interaction,
        ekle: discord.Role = None,
        kaldir: discord.Role = None,
        kanal: discord.TextChannel = None,
        baslik: str = None
    ):
        settings = self._get_settings(interaction.guild.id)

        if ekle:
            roller = settings.get("roller", [])
            for r in roller:
                if int(r["rol_id"]) == ekle.id:
                    await interaction.response.send_message(f"{ekle.mention} zaten panelde!", ephemeral=True)
                    return
            roller.append({"rol_id": str(ekle.id), "isim": ekle.name})
            settings["roller"] = roller
            if baslik:
                settings["baslik"] = baslik
            if kanal:
                settings["kanal"] = str(kanal.id)
            self._save_settings(interaction.guild.id, settings)
            await self._panel_guncelle(interaction.guild.id)
            await interaction.response.send_message(f"{ekle.mention} panele eklendi.", ephemeral=True)
            return

        if kaldir:
            roller = settings.get("roller", [])
            for r in roller[:]:
                if int(r["rol_id"]) == kaldir.id:
                    roller.remove(r)
            settings["roller"] = roller
            if baslik:
                settings["baslik"] = baslik
            self._save_settings(interaction.guild.id, settings)
            await self._panel_guncelle(interaction.guild.id)
            await interaction.response.send_message(f"{kaldir.mention} panelden cikarildi.", ephemeral=True)
            return

        if kanal:
            settings["kanal"] = str(kanal.id)
            if baslik:
                settings["baslik"] = baslik
            self._save_settings(interaction.guild.id, settings)
            await self._panel_guncelle(interaction.guild.id)
            await interaction.response.send_message(f"Panel kanali {kanal.mention} olarak ayarlandi.", ephemeral=True)
            return

        roller = settings.get("roller", [])
        embed = discord.Embed(title="Rol Paneli Ayarlari", color=discord.Color.blue())
        if roller:
            liste = []
            for r in roller:
                rol_obj = interaction.guild.get_role(int(r["rol_id"]))
                liste.append(f"{rol_obj.mention if rol_obj else 'Silinmis'}")
            embed.add_field(name="Mevcut Roller", value="\n".join(liste), inline=False)
        else:
            embed.description = "Henuz rol eklenmemis. `/rol-paneli ekle:@rol`"
        embed.add_field(name="Kanal", value=f"<#{settings['kanal']}>" if settings.get("kanal") else "Ayarlanmamis", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
