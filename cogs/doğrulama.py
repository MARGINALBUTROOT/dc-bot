import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import time
import asyncio

class DogrulamaView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Doğrulamayı Başlat", style=discord.ButtonStyle.success, emoji="✅", custom_id="dogrulama_baslat")
    async def baslat(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = self.cog._get_settings(interaction.guild.id)
        uye_rol_id = settings.get("uye_rol")
        if not uye_rol_id:
            await interaction.response.send_message("Doğrulama sistemi ayarlanmamış! (/üyedoğrulama ayarlar)", ephemeral=True)
            return
        uye_rol = interaction.guild.get_role(int(uye_rol_id))
        if not uye_rol:
            await interaction.response.send_message("Üye rolü bulunamadı!", ephemeral=True)
            return
        if uye_rol in interaction.user.roles:
            await interaction.response.send_message("Zaten doğrulanmışsın!", ephemeral=True)
            return

        sayi1 = random.randint(1, 20)
        sayi2 = random.randint(1, 20)
        cevap = sayi1 + sayi2
        self.cog.captcha_data[interaction.user.id] = {"answer": cevap, "attempts": 0, "time": time.time()}

        modal = DogrulamaModal(self.cog, sayi1, sayi2)
        await interaction.response.send_modal(modal)


class DogrulamaModal(discord.ui.Modal, title="Doğrulama"):
    def __init__(self, cog, sayi1, sayi2):
        super().__init__()
        self.cog = cog
        self.sayi1 = sayi1
        self.sayi2 = sayi2
        self.cevap = sayi1 + sayi2

        self.soru = discord.ui.TextInput(
            label=f"{sayi1} + {sayi2} = ?",
            placeholder="Cevabı yaz...",
            required=True,
            max_length=3
        )
        self.add_item(self.soru)

    async def on_submit(self, interaction: discord.Interaction):
        data = self.cog.captcha_data.get(interaction.user.id)
        if not data:
            await interaction.response.send_message("Süre doldu veya oturum geçersiz. Tekrar dene.", ephemeral=True)
            return

        if time.time() - data["time"] > 120:
            del self.cog.captcha_data[interaction.user.id]
            await interaction.response.send_message("Süre doldu! Lütfen butona tekrar bas.", ephemeral=True)
            return

        try:
            girilen = int(self.soru.value)
        except ValueError:
            data["attempts"] += 1
            if data["attempts"] >= 3:
                del self.cog.captcha_data[interaction.user.id]
                await interaction.response.send_message("Çok fazla hatalı giriş! Butona tekrar basarak yeniden dene.", ephemeral=True)
                return
            await interaction.response.send_message("Geçersiz sayı! Lütfen bir sayı gir.", ephemeral=True)
            return

        if girilen == self.cevap:
            settings = self.cog._get_settings(interaction.guild.id)
            uye_rol_id = settings.get("uye_rol")
            kayitsiz_id = settings.get("kayitsiz_rol")
            kayit_kanal_id = settings.get("kayit_kanal")

            if uye_rol_id:
                uye_rol = interaction.guild.get_role(int(uye_rol_id))
                if uye_rol:
                    await interaction.user.add_roles(uye_rol)
            if kayitsiz_id:
                kayitsiz_rol = interaction.guild.get_role(int(kayitsiz_id))
                if kayitsiz_rol and kayitsiz_rol in interaction.user.roles:
                    await interaction.user.remove_roles(kayitsiz_rol)

            del self.cog.captcha_data[interaction.user.id]

            self.cog._log_dogrulama(interaction.guild.id, interaction.guild.name, interaction.user.id, str(interaction.user), interaction.user.display_name)

            embed = discord.Embed(
                title="Doğrulama Başarılı",
                description=f"{interaction.user.mention} başarıyla doğrulandı!",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.add_field(name="Kullanıcı", value=interaction.user.mention, inline=True)
            embed.add_field(name="ID", value=f"`{interaction.user.id}`", inline=True)
            embed.set_footer(text=interaction.guild.name)

            await interaction.response.send_message("✅ Doğrulama başarılı! Sunucuya hoş geldin.", ephemeral=True)

            if kayit_kanal_id:
                kanal = interaction.guild.get_channel(int(kayit_kanal_id))
                if kanal:
                    await kanal.send(embed=embed)
        else:
            data["attempts"] += 1
            kalan = 3 - data["attempts"]
            if data["attempts"] >= 3:
                del self.cog.captcha_data[interaction.user.id]
                await interaction.response.send_message("Çok fazla hatalı giriş! Butona tekrar basarak yeniden dene.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Yanlış cevap! Kalan hakkın: {kalan}", ephemeral=True)


class Dogrulama(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "dogrulama_settings.json"
        self.captcha_data = {}
        self._init_settings()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, "w") as f:
                json.dump({}, f)

    def _get_settings(self, guild_id):
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
            return data.get(str(guild_id), {})
        except:
            return {}

    def _save_settings(self, guild_id, settings):
        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)
        except:
            data = {}
        data[str(guild_id)] = settings
        with open(self.settings_file, "w") as f:
            json.dump(data, f, indent=4)

    async def cog_load(self):
        self.bot.add_view(DogrulamaView(self))
        for guild in self.bot.guilds:
            settings = self._get_settings(guild.id)
            mesaj_id = settings.get("panel_mesaj_id")
            if mesaj_id:
                kanal_id = settings.get("dogrulama_kanal")
                if kanal_id:
                    kanal = guild.get_channel(int(kanal_id))
                    if kanal:
                        try:
                            await kanal.fetch_message(int(mesaj_id))
                        except:
                            pass

    def _log_dogrulama(self, guild_id, guild_name, user_id, user_tag, display_name):
        try:
            log_file = "dogrulama_logs.json"
            logs = []
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    logs = json.load(f)
            logs.append({
                "guild_id": str(guild_id),
                "guild_name": guild_name,
                "user_id": str(user_id),
                "user_tag": user_tag,
                "display_name": display_name,
                "timestamp": int(time.time())
            })
            logs = logs[-100:]
            with open(log_file, "w") as f:
                json.dump(logs, f, indent=4)
        except:
            pass

    def _rol_mention(self, guild, rid):
        if not rid: return "Ayarlanmamis"
        r = guild.get_role(int(rid))
        return r.mention if r else f"`{rid}` (silindi)"

    def _kanal_mention(self, guild, kid):
        if not kid: return "Ayarlanmamis"
        k = guild.get_channel(int(kid))
        return k.mention if k else f"`{kid}` (silindi)"

    async def _rol_autocomplate(self, interaction: discord.Interaction, current: str):
        roller = []
        for rol in reversed(interaction.guild.roles):
            if rol.is_default():
                continue
            if current.lower() in rol.name.lower():
                roller.append(app_commands.Choice(value=str(rol.id), name=rol.name))
        return roller[:25]

    async def _kanal_autocomplate(self, interaction: discord.Interaction, current: str):
        kanallar = []
        for kanal in interaction.guild.channels:
            if current.lower() in kanal.name.lower():
                tur = "📝" if isinstance(kanal, discord.TextChannel) else "🔊" if isinstance(kanal, discord.VoiceChannel) else "📁" if isinstance(kanal, discord.CategoryChannel) else "💬" if isinstance(kanal, discord.ForumChannel) else "📡" if isinstance(kanal, discord.StageChannel) else "📋"
                kanallar.append(app_commands.Choice(value=str(kanal.id), name=f"{tur} {kanal.name}"))
        return kanallar[:25]

    @app_commands.command(name="üyedoğrulama", description="Üye doğrulama sistemi ayarlari")
    @app_commands.describe(
        kayitsiz_rol="Sunucuya katilanda olacak kayitsiz rol",
        uye_rol="Dogrulama sonrasi verilecek üye rol",
        kayit_kanal="Dogrulanan üyelerin loglanacagi kanal",
        dogrulama_kanal="Dogrulama buton mesajinin oldugu kanal",
        panel="Dogrulama buton mesajini kanala gönder"
    )
    @app_commands.autocomplete(
        kayitsiz_rol=_rol_autocomplate,
        uye_rol=_rol_autocomplate,
        kayit_kanal=_kanal_autocomplate,
        dogrulama_kanal=_kanal_autocomplate
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def uye_dogrulama(
        self,
        interaction: discord.Interaction,
        kayitsiz_rol: str = None,
        uye_rol: str = None,
        kayit_kanal: str = None,
        dogrulama_kanal: str = None,
        panel: bool = False
    ):
        settings = self._get_settings(interaction.guild.id)
        degisti = []

        if kayitsiz_rol:
            settings["kayitsiz_rol"] = kayitsiz_rol
            r = interaction.guild.get_role(int(kayitsiz_rol))
            degisti.append(f"Kayitsiz rol: {r.mention if r else kayitsiz_rol}")
        if uye_rol:
            settings["uye_rol"] = uye_rol
            r = interaction.guild.get_role(int(uye_rol))
            degisti.append(f"Üye rol: {r.mention if r else uye_rol}")
        if kayit_kanal:
            settings["kayit_kanal"] = kayit_kanal
            k = interaction.guild.get_channel(int(kayit_kanal))
            degisti.append(f"Kayit kanal: {k.mention if k else kayit_kanal}")
        if dogrulama_kanal:
            settings["dogrulama_kanal"] = dogrulama_kanal
            k = interaction.guild.get_channel(int(dogrulama_kanal))
            degisti.append(f"Dogrulama kanal: {k.mention if k else dogrulama_kanal}")

        if degisti:
            self._save_settings(interaction.guild.id, settings)

        await interaction.response.defer(ephemeral=False)

        if panel:
            dogrulama_kanal_id = settings.get("dogrulama_kanal")
            if not dogrulama_kanal_id:
                await interaction.followup.send("Önce dogrulama kanali ayarla! (dogrulama_kanal parametresi)", ephemeral=True)
                return
            kanal = interaction.guild.get_channel(int(dogrulama_kanal_id))
            if not kanal:
                await interaction.followup.send("Dogrulama kanali bulunamadi!", ephemeral=True)
                return

            embed = discord.Embed(
                title="Doğrulama",
                description="Sunucuya hoş geldin! Aşağıdaki butona tıklayarak doğrulama işlemini tamamlayabilirsin.",
                color=discord.Color.blue()
            )
            embed.set_footer(text=interaction.guild.name)

            eski_mesaj_id = settings.get("panel_mesaj_id")
            if eski_mesaj_id:
                try:
                    eski_mesaj = await kanal.fetch_message(int(eski_mesaj_id))
                    await eski_mesaj.delete()
                except:
                    pass

            mesaj = await kanal.send(embed=embed, view=DogrulamaView(self))
            settings["panel_mesaj_id"] = str(mesaj.id)
            self._save_settings(interaction.guild.id, settings)

            panel_embed = discord.Embed(title="Panel Gönderildi", description=f"Doğrulama paneli {kanal.mention} kanalına gönderildi.", color=discord.Color.green())
            if degisti:
                ayar_embed = discord.Embed(title="Doğrulama Ayarları Güncellendi", color=discord.Color.green())
                ayar_embed.description = "\n".join(["✅ " + d for d in degisti])
                await interaction.followup.send(embeds=[ayar_embed, panel_embed])
            else:
                await interaction.followup.send(embed=panel_embed)
            return

        if degisti:
            embed = discord.Embed(title="Doğrulama Ayarları Güncellendi", color=discord.Color.green())
            embed.description = "\n".join(["✅ " + d for d in degisti])
            await interaction.followup.send(embed=embed)
        else:
            if not settings:
                await interaction.followup.send("Henüz ayar yapılmamış.", ephemeral=True)
            else:
                embed = discord.Embed(title="Doğrulama Ayarları", color=discord.Color.blue())
                embed.add_field(name="Kayıtsız Rol", value=self._rol_mention(interaction.guild, settings.get("kayitsiz_rol")), inline=False)
                embed.add_field(name="Üye Rolü", value=self._rol_mention(interaction.guild, settings.get("uye_rol")), inline=False)
                embed.add_field(name="Kayıt Log", value=self._kanal_mention(interaction.guild, settings.get("kayit_kanal")), inline=False)
                embed.add_field(name="Doğrulama Kanal", value=self._kanal_mention(interaction.guild, settings.get("dogrulama_kanal")), inline=False)
                await interaction.followup.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        settings = self._get_settings(member.guild.id)
        kayitsiz_id = settings.get("kayitsiz_rol")
        if kayitsiz_id:
            role = member.guild.get_role(int(kayitsiz_id))
            if role:
                try:
                    await member.add_roles(role, reason="Doğrulama sistemi - kayıtsız rolü")
                except:
                    pass

async def setup(bot):
    await bot.add_cog(Dogrulama(bot))
