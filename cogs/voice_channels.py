import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class LimitModal(discord.ui.Modal, title="Kullanıcı Sınırı"):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel
        self.sinir = discord.ui.TextInput(label="Kullanıcı sınırı (0 = sınırsız)", placeholder="0-99 arası", required=True, max_length=3)
        self.add_item(self.sinir)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            limit = int(self.sinir.value)
            if limit < 0 or limit > 99:
                await interaction.response.send_message("0-99 arası bir sayı girin!", ephemeral=True)
                return
            await self.channel.edit(user_limit=limit)
            await interaction.response.send_message(f"Kullanıcı sınırı {'sınırsız' if limit == 0 else str(limit)} olarak ayarlandı.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Geçerli bir sayı girin!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Yetkim yetmiyor!", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"Hata: {e}", ephemeral=True)

class RenameModal(discord.ui.Modal, title="Oda Adı"):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel
        self.isim = discord.ui.TextInput(label="Yeni oda adı", placeholder="Oda adı", required=True, max_length=100)
        self.add_item(self.isim)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.channel.edit(name=self.isim.value)
            await interaction.response.send_message(f"Oda adı '{self.isim.value}' olarak değiştirildi.", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("Oda bulunamadı, silinmiş olabilir.", ephemeral=True)
        except:
            await interaction.response.send_message("Oda adı değiştirilemedi!", ephemeral=True)

class DavetModal(discord.ui.Modal, title="Kullanıcı Davet Et"):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel
        self.kullanici = discord.ui.TextInput(label="Kullanıcı ID", placeholder="Kullanıcının ID'sini girin", required=True, max_length=30)
        self.add_item(self.kullanici)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uye = interaction.guild.get_member(int(self.kullanici.value))
            if not uye:
                await interaction.response.send_message("Kullanıcı bulunamadı!", ephemeral=True)
                return
            await self.channel.set_permissions(uye, connect=True, view_channel=True)
            await interaction.response.send_message(f"{uye.mention} odaya eklendi.", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("Oda bulunamadı, silinmiş olabilir.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Geçerli bir ID girin!", ephemeral=True)

class OdaKontrolView(discord.ui.View):
    def __init__(self, cog, channel_id, owner_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id
        self.owner_id = owner_id

    def _kanal(self, guild):
        return guild.get_channel(self.channel_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Bu panel sadece oda sahibi tarafından kullanılabilir!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Kullanıcı Sınırı", style=discord.ButtonStyle.primary, emoji="👥", custom_id="oda_limit")
    async def set_limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        kanal = self._kanal(interaction.guild)
        if not kanal:
            await interaction.response.send_message("Oda bulunamadı, silinmiş olabilir.", ephemeral=True)
            return
        await interaction.response.send_modal(LimitModal(kanal))

    @discord.ui.button(label="Oda Adı", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="oda_rename")
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        kanal = self._kanal(interaction.guild)
        if not kanal:
            await interaction.response.send_message("Oda bulunamadı, silinmiş olabilir.", ephemeral=True)
            return
        await interaction.response.send_modal(RenameModal(kanal))

    @discord.ui.button(label="Kilitle", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="oda_lock")
    async def toggle_lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        kanal = self._kanal(interaction.guild)
        if not kanal:
            await interaction.response.send_message("Oda bulunamadı, silinmiş olabilir.", ephemeral=True)
            return
        kilitli = kanal.permissions_for(interaction.guild.default_role).connect == False
        if kilitli:
            await kanal.set_permissions(interaction.guild.default_role, connect=True)
            button.style = discord.ButtonStyle.danger
            button.label = "Kilitle"
            button.emoji = "🔒"
        else:
            await kanal.set_permissions(interaction.guild.default_role, connect=False)
            button.style = discord.ButtonStyle.success
            button.label = "Kilit Aç"
            button.emoji = "🔓"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Kullanıcı Ekle", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="oda_davet")
    async def davet(self, interaction: discord.Interaction, button: discord.ui.Button):
        kanal = self._kanal(interaction.guild)
        if not kanal:
            await interaction.response.send_message("Oda bulunamadı, silinmiş olabilir.", ephemeral=True)
            return
        await interaction.response.send_modal(DavetModal(kanal))

    @discord.ui.button(label="Odayı Sil", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="oda_sil")
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        kanal = self._kanal(interaction.guild)
        if not kanal:
            await interaction.response.send_message("Oda bulunamadı, silinmiş olabilir.", ephemeral=True)
            return
        await interaction.response.send_message("Oda siliniyor...", ephemeral=True)
        try:
            await kanal.delete(reason="Oda sahibi sildi")
        except:
            pass
        self.cog.user_channels.pop(self.owner_id, None)

class VoiceChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "voice_settings.json"
        self.user_channels = {}

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

    @app_commands.command(name="sesoda", description="Ses odaları sistemini kur")
    @app_commands.describe(
        kanalismi="Giriş kanalının adı (örn: '➕ Oda Oluştur')",
        izin="True = özel kanal, False = herkese açık"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def sesoda(
        self,
        interaction: discord.Interaction,
        kanalismi: str = "➕ Oda Oluştur",
        izin: bool = True
    ):
        await interaction.response.defer()

        kategori = discord.utils.get(interaction.guild.categories, name="Ses Odaları")
        if not kategori:
            try:
                kategori = await interaction.guild.create_category("Ses Odaları")
            except discord.Forbidden:
                await interaction.followup.send("Kategori oluşturulamadı! Yetkileri kontrol et.", ephemeral=True)
                return

        varolan = discord.utils.get(kategori.voice_channels, name=kanalismi)
        if varolan:
            await interaction.followup.send(f"`{kanalismi}` kanalı zaten mevcut!", ephemeral=True)
            return

        try:
            giris_kanal = await interaction.guild.create_voice_channel(
                name=kanalismi, category=kategori, reason="Ses odaları sistemi"
            )

            self._save_settings(interaction.guild.id, {
                "giris_kanal": str(giris_kanal.id),
                "kategori": str(kategori.id),
                "izin": izin
            })

            embed = discord.Embed(
                title="✅ Ses Odaları Kuruldu",
                description=f"**Giriş Kanalı:** {giris_kanal.mention}\n**Kategori:** {kategori.name}\n**İzin Yönetimi:** {'Açık' if izin else 'Kapalı'}",
                color=discord.Color.green()
            )
            embed.add_field(name="📖 Nasıl Kullanılır?", value=f"1. `{kanalismi}` kanalına katıl\n2. Senin adına özel oda açılır\n3. Ses kanalının sohbetine panel gelir\n4. Odadan çıkınca otomatik silinir", inline=False)
            await interaction.followup.send(embed=embed)

        except discord.Forbidden:
            await interaction.followup.send("Yeterli yetkim yok! `manage_channels` yetkisini kontrol et.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Kurulum hatası: {e}", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        settings = self._get_settings(member.guild.id)
        if not settings:
            return

        giris_kanal_id = settings.get("giris_kanal")
        kategori_id = settings.get("kategori")
        izin_aktif = settings.get("izin", True)

        if not giris_kanal_id or not kategori_id:
            return

        try:
            giris_kanal_id = int(giris_kanal_id)
            kategori_id = int(kategori_id)
        except:
            return

        kategori = member.guild.get_channel(kategori_id)
        if not kategori or not isinstance(kategori, discord.CategoryChannel):
            return

        if before.channel and before.channel.id in self.user_channels.values():
            oda = before.channel
            if len(oda.members) == 0:
                try:
                    uid = None
                    for uid2, vcid in list(self.user_channels.items()):
                        if vcid == oda.id:
                            uid = uid2
                            break
                    await oda.delete(reason="Geçici oda boş")
                    if uid:
                        self.user_channels.pop(uid, None)
                except discord.NotFound:
                    self.user_channels = {k: v for k, v in self.user_channels.items() if v != oda.id}
                except Exception as e:
                    print(f"[SES] Silme hatası: {e}")

        if after.channel and after.channel.id == giris_kanal_id:
            if member.id in self.user_channels:
                onceki = member.guild.get_channel(self.user_channels[member.id])
                if onceki:
                    try:
                        await member.move_to(onceki)
                    except:
                        pass
                    return

            if not member.guild.me.guild_permissions.manage_channels:
                return

            oda_adi = member.display_name
            sayi = 1
            while any(c.name == oda_adi for c in kategori.channels):
                sayi += 1
                oda_adi = f"{member.display_name} {sayi}"

            try:
                yeni_oda = await member.guild.create_voice_channel(
                    name=oda_adi, category=kategori
                )
                self.user_channels[member.id] = yeni_oda.id

                if izin_aktif:
                    await yeni_oda.set_permissions(member.guild.default_role, connect=False)
                    await yeni_oda.set_permissions(member, connect=True, view_channel=True)

                await member.move_to(yeni_oda)

                embed = discord.Embed(
                    title=f"🔊 {oda_adi}",
                    description=f"{member.mention} hoş geldin! Odanı aşağıdaki butonlarla yönetebilirsin.",
                    color=discord.Color.blue()
                )
                view = OdaKontrolView(self, yeni_oda.id, member.id)
                try:
                    await yeni_oda.send(content=member.mention, embed=embed, view=view)
                except discord.HTTPException:
                    try:
                        await member.send(embed=embed, view=view)
                    except:
                        pass

            except discord.HTTPException as e:
                print(f"[SES] Oluşturma hatası: {e}")
                self.user_channels.pop(member.id, None)
            except Exception as e:
                print(f"[SES] Hata: {e}")
                self.user_channels.pop(member.id, None)

async def setup(bot):
    await bot.add_cog(VoiceChannels(bot))
