import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio

KEYWORD_KATEGORILER = {
    "kufur": ["amk", "aq", "sik", "sikerim", "ananı", "orospu", "piç", "göt", "yarrak", "amcık"],
    "reklam": ["discord.gg/", "discord.com/invite/", "youtube.com/c/", "twitch.tv/", "reklam", ".gg/"],
    "spam_kelime": ["@everyone", "@here", "deneme", "asd", "asdasd"],
    "nsfw": ["porno", "sex", "xxx", "onlyfans", "nsfw"],
    "siddet": ["öl", "intihar", "kendini as", "öldür", "bombala"]
}

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _kural_kur(self, guild, kural_adi, trigger_kwargs, actions, enabled=True):
        try:
            trigger = discord.AutoModTrigger(**trigger_kwargs)
            action_objs = []
            for a in actions:
                action_objs.append(discord.AutoModRuleAction(**a))

            await guild.create_automod_rule(
                name=kural_adi,
                event_type=discord.AutoModRuleEventType.message_send,
                trigger=trigger,
                actions=action_objs,
                enabled=enabled
            )
            print(f"[AUTOMOD] '{kural_adi}' kuruldu ✅")
            return True
        except discord.Forbidden:
            print(f"[AUTOMOD] '{kural_adi}' - Yetki yok ❌")
            return False
        except discord.HTTPException as e:
            print(f"[AUTOMOD] '{kural_adi}' - HTTP: {e} ❌")
            return False
        except Exception as e:
            print(f"[AUTOMOD] '{kural_adi}' - HATA: {e} ❌")
            return False

    async def _kurallari_kur(self, guild):
        print(f"[AUTOMOD] {guild.name}: Kural kurulumu basliyor...")
        if not guild.me.guild_permissions.manage_guild:
            print(f"[AUTOMOD] MANAGE_GUILD yetkisi yok!")
            return 0

        try:
            for rule in await guild.fetch_automod_rules():
                if rule.name == "Hakaret Korumasi":
                    await rule.delete()
                    print(f"[AUTOMOD] Hakaret Korumasi silindi")
        except:
            pass

        sayac = 0

        sonuc = await self._kural_kur(
            guild, "Kufur Korumasi",
            {"type": discord.AutoModRuleTriggerType.keyword, "keyword_filter": KEYWORD_KATEGORILER["kufur"]},
            [{"type": discord.AutoModRuleActionType.block_message}]
        )
        if sonuc: sayac += 1
        await asyncio.sleep(1)

        sonuc = await self._kural_kur(
            guild, "Reklam Korumasi",
            {"type": discord.AutoModRuleTriggerType.keyword, "keyword_filter": KEYWORD_KATEGORILER["reklam"]},
            [{"type": discord.AutoModRuleActionType.block_message}]
        )
        if sonuc: sayac += 1
        await asyncio.sleep(1)

        sonuc = await self._kural_kur(
            guild, "Spam Kelime Korumasi",
            {"type": discord.AutoModRuleTriggerType.keyword, "keyword_filter": KEYWORD_KATEGORILER["spam_kelime"]},
            [{"type": discord.AutoModRuleActionType.block_message}]
        )
        if sonuc: sayac += 1
        await asyncio.sleep(1)

        sonuc = await self._kural_kur(
            guild, "NSFW Korumasi",
            {"type": discord.AutoModRuleTriggerType.keyword, "keyword_filter": KEYWORD_KATEGORILER["nsfw"]},
            [{"type": discord.AutoModRuleActionType.block_message}]
        )
        if sonuc: sayac += 1
        await asyncio.sleep(1)

        sonuc = await self._kural_kur(
            guild, "Siddet Korumasi",
            {"type": discord.AutoModRuleTriggerType.keyword, "keyword_filter": KEYWORD_KATEGORILER["siddet"]},
            [{"type": discord.AutoModRuleActionType.block_message}]
        )
        if sonuc: sayac += 1
        await asyncio.sleep(1)

        sonuc = await self._kural_kur(
            guild, "Mention Spam Korumasi",
            {"type": discord.AutoModRuleTriggerType.mention_spam, "mention_limit": 5},
            [{"type": discord.AutoModRuleActionType.block_message}]
        )
        if sonuc: sayac += 1
        await asyncio.sleep(1)

        sonuc = await self._kural_kur(
            guild, "Link Spam Korumasi",
            {"type": discord.AutoModRuleTriggerType.harmful_link},
            [{"type": discord.AutoModRuleActionType.block_message}]
        )
        if sonuc: sayac += 1
        await asyncio.sleep(1)

        sonuc = await self._kural_kur(
            guild, "Hazir Kufur Listesi",
            {"type": discord.AutoModRuleTriggerType.keyword_preset, "presets": discord.AutoModPresets.profanity},
            [{"type": discord.AutoModRuleActionType.block_message}]
        )
        if sonuc: sayac += 1

        return sayac

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        print(f"[AUTOMOD] {guild.name}: Otomatik kural kurulumu basliyor...")
        toplam = await self._kurallari_kur(guild)
        print(f"[AUTOMOD] {guild.name}: {toplam}/9 kural kuruldu.")

    @app_commands.command(name="setup_automod", description="AutoMod kurallarini manuel kur")
    @app_commands.guild_only()
    async def setup_automod(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        print(f"[AUTOMOD] {interaction.guild.name}: Manuel kurulum basladi...")
        toplam = await self._kurallari_kur(interaction.guild)
        print(f"[AUTOMOD] {interaction.guild.name}: {toplam}/9 kuruldu.")
        await interaction.followup.send(f"**{toplam}/9** AutoMod kurali kuruldu!")

    @app_commands.command(name="automod_kurallar", description="Bu sunucudaki AutoMod kurallarini listele")
    @app_commands.guild_only()
    async def automod_kurallar(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            rules = await interaction.guild.fetch_automod_rules()
            if not rules:
                await interaction.followup.send("Bu sunucuda AutoMod kurali yok.")
                return
            embed = discord.Embed(title="AutoMod Kurallari", description=f"{interaction.guild.name} - {len(rules)} kural", color=discord.Color.blue())
            for rule in rules:
                durum = "✅" if rule.enabled else "❌"
                trigger_adi = str(rule.trigger.type).split(".")[-1]
                embed.add_field(name=f"{durum} {rule.name}", value=f"Tur: {trigger_adi}", inline=False)
            embed.set_footer(text=f"ID: {interaction.guild.id}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"Kurallar alinamadi: {e}")

    @app_commands.command(name="automod_stats", description="Toplam AutoMod kural sayisini goster")
    async def automod_stats(self, interaction: discord.Interaction):
        await interaction.response.defer()
        toplam_kural = 0
        sunucu_liste = []
        for guild in self.bot.guilds:
            try:
                rules = await guild.fetch_automod_rules()
                sayi = len(rules)
                toplam_kural += sayi
                sunucu_liste.append(f"**{guild.name}**: {sayi} kural")
            except:
                sunucu_liste.append(f"**{guild.name}**: ❌")

        embed = discord.Embed(
            title="AutoMod Istatistikleri",
            description=f"**Toplam Kural:** {toplam_kural}/100\n\n" + "\n".join(sunucu_liste[:25]),
            color=discord.Color.green() if toplam_kural >= 100 else discord.Color.orange()
        )
        embed.add_field(name="Badge Durumu", value="✅ Badge alindi!" if toplam_kural >= 100 else "Henuz 100 kural yok", inline=False)
        embed.set_footer(text=f"{len(self.bot.guilds)} sunucu - {toplam_kural} toplam kural")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
