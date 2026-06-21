import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

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
        s = self.cog._get_guild_settings(self.guild_id)
        s["esik"] = sayi
        self.cog._save_guild_settings(self.guild_id, s)
        await self._refresh(interaction)

    async def _refresh(self, interaction):
        s = self.cog._get_guild_settings(self.guild_id)
        durum = "✅ Aktif" if s["aktif"] else "❌ Devre Dışı"
        embed = discord.Embed(title="Antibot Koruması", description="Sunucuya katılan botları izler, spam durumunda otomatik banlar.", color=discord.Color.blue())
        embed.add_field(name="Durum", value=durum, inline=True)
        embed.add_field(name="Ban Eşiği", value=f"{s['esik']} mesaj", inline=True)
        kanal = self.cog._get_kanal(s)
        embed.add_field(name="Bildirim Kanalı", value=kanal.mention if kanal else "Ayarlanmamış", inline=False)
        guvenli_sayisi = len(s.get("guvenli_botlar", []))
        embed.add_field(name="Güvenli Bot", value=f"{guvenli_sayisi} bot listede" if guvenli_sayisi else "Yok", inline=False)
        await interaction.response.edit_message(embed=embed)

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
        s = self.cog._get_guild_settings(self.guild_id)
        s["kanal_id"] = str(kanal.id)
        self.cog._save_guild_settings(self.guild_id, s)
        await self._refresh(interaction)

    async def _refresh(self, interaction):
        s = self.cog._get_guild_settings(self.guild_id)
        durum = "✅ Aktif" if s["aktif"] else "❌ Devre Dışı"
        embed = discord.Embed(title="Antibot Koruması", color=discord.Color.blue())
        embed.add_field(name="Durum", value=durum, inline=True)
        embed.add_field(name="Ban Eşiği", value=f"{s['esik']} mesaj", inline=True)
        kanal = self.cog._get_kanal(s)
        embed.add_field(name="Bildirim Kanalı", value=kanal.mention if kanal else "Ayarlanmamış", inline=False)
        guvenli_sayisi = len(s.get("guvenli_botlar", []))
        embed.add_field(name="Güvenli Bot", value=f"{guvenli_sayisi} bot listede" if guvenli_sayisi else "Yok", inline=False)
        await interaction.response.edit_message(embed=embed)

class GuvenliEkleModal(discord.ui.Modal, title="Güvenli Bot Ekle"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.bot_id = discord.ui.TextInput(label="Bot ID", placeholder="Eklemek istediğin botun ID'si", required=True, max_length=30)
        self.add_item(self.bot_id)

    async def on_submit(self, interaction: discord.Interaction):
        s = self.cog._get_guild_settings(self.guild_id)
        bid = self.bot_id.value.strip()
        if bid in s.get("guvenli_botlar", []):
            await interaction.response.send_message("Bu bot zaten güvenli listesinde.", ephemeral=True)
            return
        if "guvenli_botlar" not in s:
            s["guvenli_botlar"] = []
        s["guvenli_botlar"].append(bid)
        self.cog._save_guild_settings(self.guild_id, s)
        embed = discord.Embed(title="Güvenli Bot Eklendi", description=f"Bot `{bid}` güvenli listesine eklendi.", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed)

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
        self.bot_sayac = {}
        self.settings_file = "antibot_settings.json"
        self._init_settings()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, "w") as f:
                json.dump({}, f)

    def _get_guild_settings(self, guild_id: int):
        try:
            with open(self.settings_file, "r") as f:
                settings = json.load(f)
        except:
            settings = {}
        gid = str(guild_id)
        if gid not in settings:
            settings[gid] = {"aktif": False, "esik": 6, "kanal_id": None, "guvenli_botlar": []}
        return settings[gid]

    def _save_guild_settings(self, guild_id: int, settings: dict):
        try:
            with open(self.settings_file, "r") as f:
                all_settings = json.load(f)
        except:
            all_settings = {}
        all_settings[str(guild_id)] = settings
        with open(self.settings_file, "w") as f:
            json.dump(all_settings, f, indent=4)

    def _get_kanal(self, settings):
        kanal_id = settings.get("kanal_id")
        if kanal_id:
            kanal = self.bot.get_channel(int(kanal_id))
            if kanal:
                return kanal
        return None

    @app_commands.command(name="antibot", description="Bot koruma sistemini yönet (butonlu menü)")
    @app_commands.guild_only()
    async def antibot(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)
            return
        s = self._get_guild_settings(interaction.guild.id)
        durum = "✅ Aktif" if s["aktif"] else "❌ Devre Dışı"
        embed = discord.Embed(title="Antibot Koruması", description="Sunucuya katılan botları izler, spam durumunda otomatik banlar.", color=discord.Color.blue() if s["aktif"] else discord.Color.red())
        embed.add_field(name="Durum", value=durum, inline=True)
        embed.add_field(name="Ban Eşiği", value=f"{s['esik']} mesaj", inline=True)
        kanal = self._get_kanal(s)
        embed.add_field(name="Bildirim Kanalı", value=kanal.mention if kanal else "Ayarlanmamış", inline=False)
        guvenli_sayisi = len(s.get("guvenli_botlar", []))
        embed.add_field(name="Güvenli Bot", value=f"{guvenli_sayisi} bot listede" if guvenli_sayisi else "Yok", inline=False)
        embed.set_footer(text="Butonları kullanarak ayarları değiştirebilirsin")
        view = AntibotView(self, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not member.bot:
            return
        settings = self._get_guild_settings(member.guild.id)
        if not settings["aktif"]:
            return
        if str(member.id) in settings.get("guvenli_botlar", []):
            return
        if not member.guild.me.guild_permissions.ban_members:
            return

        kanal = self._get_kanal(settings)
        if not kanal:
            kanal = member.guild.system_channel
        if not kanal:
            for ch in member.guild.text_channels:
                if ch.permissions_for(member.guild.me).send_messages:
                    kanal = ch
                    break
        if not kanal:
            return

        embed = discord.Embed(title="Bot Algılandı!", description=f"{member.mention} (`{member.name}`) sunucuya katıldı!", color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="Bot ID", value=member.id, inline=True)
        embed.add_field(name="Hesap Oluşturma", value=member.created_at.strftime("%d.%m.%Y %H:%M"), inline=True)
        embed.add_field(name="Eşik", value=f"{settings['esik']} mesajdan sonra banlanır", inline=False)
        embed.set_footer(text="Antibot Sistemi")
        await kanal.send(embed=embed)

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
        if str(message.author.id) in settings.get("guvenli_botlar", []):
            return
        if not settings["aktif"]:
            return
        if not message.guild.me.guild_permissions.ban_members:
            return

        bid = message.author.id
        self.bot_sayac[bid] = self.bot_sayac.get(bid, 0) + 1
        sayac = self.bot_sayac[bid]

        if sayac == 1:
            try:
                await message.author.send(f"**{message.guild.name}** sunucusunda bot koruma aktif. {settings['esik']} mesajdan sonra otomatik banlanacaksınız.")
            except:
                pass

        if sayac >= settings["esik"]:
            try:
                await message.guild.ban(message.author, reason=f"Antibot - {settings['esik']} mesaj sınırı aşıldı")

                kanal = self._get_kanal(settings)
                if not kanal:
                    kanal = message.guild.system_channel
                if not kanal:
                    for ch in message.guild.text_channels:
                        if ch.permissions_for(message.guild.me).send_messages:
                            kanal = ch
                            break
                if kanal:
                    embed = discord.Embed(title="Bot Banlandı", description=f"{message.author.mention} (`{message.author.name}`) **{settings['esik']}** mesaj sınırını aşınca otomatik banlandı.", color=discord.Color.red(), timestamp=datetime.now())
                    embed.set_footer(text="Antibot Sistemi")
                    await kanal.send(embed=embed)
            except:
                pass
            finally:
                self.bot_sayac.pop(bid, None)

async def setup(bot):
    await bot.add_cog(Antibot(bot))
