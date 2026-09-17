import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import sys
import json
import time
import threading
import asyncio
from config import DISCORD_TOKEN, DATA_DIR
from app import app

from utils_json import read_json as _read_json, write_json as _write_json

SYNC_FILE = os.path.join(DATA_DIR, "sync_pending.json") if DATA_DIR else "sync_pending.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True
intents.presences = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    chunk_guilds_at_startup=True
)

BOT_PERMISSIONS = discord.Permissions()
for permission in (
    "view_channel", "send_messages", "manage_messages", "embed_links", "attach_files",
    "read_message_history", "add_reactions", "connect", "speak", "move_members",
    "manage_channels", "manage_roles", "kick_members", "ban_members", "moderate_members",
    "view_audit_log", "manage_guild", "manage_webhooks", "create_instant_invite"
):
    setattr(BOT_PERMISSIONS, permission, True)

MEMBER_CACHE_FILE = "members_cache.json"
MODLOGS_FILE = "modlogs.json"

async def load_cogs():
    cogs_dir = "cogs"
    if not os.path.exists(cogs_dir):
        os.makedirs(cogs_dir)
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"  -> {filename} yuklendi")
            except Exception as e:
                print(f"  -> {filename} HATA: {e}")

@tasks.loop(seconds=30)
async def guild_update_loop():
    try:
        guild_list = []
        for guild in bot.guilds:
            guild_list.append({
                "id": str(guild.id),
                "name": guild.name,
                "member_count": guild.member_count,
                "icon_url": guild.icon.url if guild.icon else None,
                "owner_name": str(guild.owner) if guild.owner else "Bilinmiyor",
                "created_at": guild.created_at.strftime("%d.%m.%Y"),
                "bot_perms": str(guild.me.guild_permissions.value)
            })
        _write_json("guilds.json", guild_list)
    except:
        pass

@guild_update_loop.before_loop
async def before_guild_update():
    await bot.wait_until_ready()

def init_modlogs():
    data = _read_json(MODLOGS_FILE, {})
    if not data:
        _write_json(MODLOGS_FILE, {})

def _modlog_ekle(guild_id, action, moderator, target, reason):
    logs = _read_json(MODLOGS_FILE, {})
    gid = str(guild_id)
    if gid not in logs:
        logs[gid] = []
    logs[gid].append({
        "action": action, "moderator": moderator, "target": target,
        "reason": reason, "timestamp": int(time.time())
    })
    _write_json(MODLOGS_FILE, logs)

@tasks.loop(seconds=60)
async def member_cache_loop():
    try:
        cache = []
        for guild in bot.guilds:
            members = []
            for member in guild.members:
                members.append({
                    "id": str(member.id),
                    "name": member.name,
                    "display_name": member.display_name,
                    "avatar_url": member.avatar.url if member.avatar else None
                })
            cache.append({
                "id": str(guild.id),
                "name": guild.name,
                "members": members
            })
        _write_json(MEMBER_CACHE_FILE, cache)
    except:
        pass

@member_cache_loop.before_loop
async def before_member_cache():
    await bot.wait_until_ready()

@tasks.loop(seconds=20)
async def guild_sync_loop():
    try:
        if not os.path.exists(SYNC_FILE):
            return
        with open(SYNC_FILE, "r") as f:
            pending = json.load(f)
        if not pending:
            return
        to_process = pending[:3]
        remaining = pending[3:]
        for gid in to_process:
            try:
                guild = bot.get_guild(int(gid))
                if guild:
                    bot.tree.clear_commands(guild=guild)
                    await bot.tree.sync(guild=guild)
                    print(f"[SYNC] {guild.name} sunucuya ozel komutlar temizlendi.")
            except Exception as e:
                print(f"[SYNC] {gid} hatasi: {e}")
        with open(SYNC_FILE, "w") as f:
            json.dump(remaining, f)
        if not remaining:
            print("[SYNC] Tum sunucular senkronize edildi.")
    except:
        pass

@guild_sync_loop.before_loop
async def before_guild_sync():
    await bot.wait_until_ready()

@tasks.loop(seconds=10)
async def komut_kontrol_loop():
    try:
        komutlar = _read_json("web_commands.json", [])
        if komutlar:
            processed = []
            for komut in komutlar:
                try:
                    cmd_type = komut.get("type")
                    if cmd_type == "leave":
                        guild = bot.get_guild(int(komut.get("guild_id")))
                        if guild:
                            await guild.leave()
                            print(f"[WEB] {guild.name} sunucusundan ayrilindi.")
                        processed.append(komut)

                    elif cmd_type == "status":
                        status_str = komut.get("status", "online")
                        status_map = {"online": discord.Status.online, "idle": discord.Status.idle, "dnd": discord.Status.dnd}
                        await bot.change_presence(status=status_map.get(status_str, discord.Status.online))
                        print(f"[WEB] Bot durumu: {status_str}")
                        processed.append(komut)

                    elif cmd_type == "reload":
                        results = {"loaded": [], "failed": []}
                        for filename in os.listdir("cogs"):
                            if filename.endswith(".py") and filename != "__init__.py":
                                cog_name = f"cogs.{filename[:-3]}"
                                try:
                                    await bot.reload_extension(cog_name)
                                    results["loaded"].append(filename)
                                except Exception as e:
                                    results["failed"].append(f"{filename}: {e}")
                        print(f"[WEB] Reload: {len(results['loaded'])} basarili, {len(results['failed'])} basarisiz")
                        for hata in results["failed"]:
                            print(f"[WEB]  -> {hata}")
                        processed.append(komut)

                    elif cmd_type == "shutdown":
                        komutlar.remove(komut)
                        _write_json("web_commands.json", komutlar)
                        print("[WEB] Bot kapatiliyor...")
                        await bot.close()

                    elif cmd_type == "restart":
                        komutlar.remove(komut)
                        _write_json("web_commands.json", komutlar)
                        print("[WEB] Bot yeniden baslatiliyor...")
                        await bot.close()

                    elif cmd_type == "ban":
                        guild = bot.get_guild(int(komut.get("guild_id")))
                        user_id = int(komut.get("user_id"))
                        reason = komut.get("reason", "Web panel")
                        mod_name = komut.get("moderator", "WebPanel")
                        if guild:
                            user = await bot.fetch_user(user_id)
                            await guild.ban(user, reason=reason)
                            print(f"[WEB] {user.name} banlandi: {reason}")
                            _modlog_ekle(komut.get("guild_id"), "BAN", mod_name, user.name, reason)
                        else:
                            print(f"[WEB] Ban icin sunucu bulunamadi: {komut.get('guild_id')}")
                        processed.append(komut)

                    elif cmd_type == "kick":
                        guild = bot.get_guild(int(komut.get("guild_id")))
                        user_id = int(komut.get("user_id"))
                        reason = komut.get("reason", "Web panel")
                        mod_name = komut.get("moderator", "WebPanel")
                        if guild:
                            member = guild.get_member(user_id)
                            if not member:
                                member = await guild.fetch_member(user_id)
                            await guild.kick(member, reason=reason)
                            print(f"[WEB] {member.name} atildi: {reason}")
                            _modlog_ekle(komut.get("guild_id"), "KICK", mod_name, member.name, reason)
                        else:
                            print(f"[WEB] Kick icin sunucu bulunamadi: {komut.get('guild_id')}")
                        processed.append(komut)

                    else:
                        processed.append(komut)
                except Exception as e:
                    print(f"[WEB] Komut islenirken hata: {e}")
                    processed.append(komut)
            remaining = [k for k in komutlar if k not in processed]
            _write_json("web_commands.json", remaining)
    except Exception as e:
        print(f"[WEB] Komut kontrol hatasi: {e}")

@komut_kontrol_loop.before_loop
async def before_komut_kontrol():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f"Bot olarak baglanildi! {bot.user}")

    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name="/help"))

    _write_json("bot_status.json", {
        "status": "online",
        "uptime": int(time.time()),
        "commands_used": 0,
        "bot_name": str(bot.user),
        "bot_id": bot.user.id,
        "guilds": len(bot.guilds),
        "invite_url": f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions={BOT_PERMISSIONS.value}&scope=bot%20applications.commands"
    })

    for loop in (guild_update_loop, member_cache_loop, komut_kontrol_loop, guild_sync_loop):
        if not loop.is_running():
            loop.start()

    print("Komutlar senkronize ediliyor...")
    try:
        await bot.tree.sync()
        print("Global komutlar senkronize edildi.")
    except Exception as e:
        print(f"Global sync hatasi: {e}")

    guild_ids = [str(g.id) for g in bot.guilds]
    with open(SYNC_FILE, "w") as f:
        json.dump(guild_ids, f)
    print(f"{len(guild_ids)} sunucu kuyruga alindi, arkaplanda senkronize edilecek.")

@bot.event
async def on_guild_join(guild):
    try:
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"{guild.name} sunucusuna katildi, komutlar senkronize edildi.")
    except Exception as e:
        print(f"{guild.name} senkronize hatasi: {e}")

    embed = discord.Embed(
        title="rootv1 Komutları",
        description="Sunucunuza hoş geldiniz! Tüm komutlara `/` yazarak ulaşabilirsiniz.",
        color=discord.Color.blue()
    )
    embed.add_field(name="🛡️ Moderasyon", value="`/ban` `/kick` `/purge`", inline=False)
    embed.add_field(name="🤖 Antibot", value="`/antibot`", inline=False)
    embed.add_field(name="⚡ Oto-Koruma", value="`/otokoruma` `/automod-setup` `/automod-kurallar` `/automod-stats`", inline=False)
    embed.add_field(name="📝 Log", value="`/setlog` `/logayarlari`", inline=False)
    embed.add_field(name="✨ Özel Komutlar", value="`/komutekle` `/komutsil` `/komutlistesi`", inline=False)
    embed.add_field(name="ℹ️ Bilgi", value="`/userinfo` `/serverinfo` `/help` `/avatar` `/ping`", inline=False)

    try:
        if guild.system_channel:
            await guild.system_channel.send(embed=embed)
    except:
        pass

@bot.event
async def on_disconnect():
    status = _read_json("bot_status.json", {})
    status["status"] = "offline"
    _write_json("bot_status.json", status)

@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command):
    status = _read_json("bot_status.json", {})
    status["commands_used"] = int(status.get("commands_used", 0)) + 1
    _write_json("bot_status.json", status)

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if interaction.response.is_done():
        return
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Bu komutu kullanmak icin yetkiniz yok!", ephemeral=True)
    elif isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message("Botun yetkisi yetersiz!", ephemeral=True)
    else:
        await interaction.response.send_message(f"Hata: {str(error)}", ephemeral=True)

def run_web_panel():
    port = int(os.getenv("PORT", 5000))
    print(f"[WEB] Admin Panel baslatiliyor: http://localhost:{port}")
    try:
        app.run(debug=False, port=port, host="0.0.0.0", use_reloader=False)
    except Exception as e:
        print(f"[WEB] Panel hatasi: {e}")

async def main():
    if not DISCORD_TOKEN:
        print("HATA: .env dosyasinda DISCORD_TOKEN bulunamadi!")
        sys.exit(1)
    veri_klasoru = DATA_DIR if DATA_DIR else "proje klasoru"
    print(f"[VERI] Dosyalar suraya kaydediliyor: {veri_klasoru}")
    try:
        web_thread = threading.Thread(target=run_web_panel, daemon=True)
        web_thread.start()
        async with bot:
            await load_cogs()
            await bot.start(DISCORD_TOKEN)
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
