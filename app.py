from flask import Flask, render_template, jsonify, request, redirect, session, url_for
from flask_cors import CORS
import json
import os
import secrets
import time

from utils_json import read_json as _read_json, write_json as _write_json

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
CORS(app)

MODLOGS_FILE = "modlogs.json"
BOT_STATUS_FILE = "bot_status.json"
GUILDS_FILE = "guilds.json"
WEB_COMMANDS_FILE = "web_commands.json"

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "rootx123")

def get_modlogs():
    return _read_json(MODLOGS_FILE, {})

def get_bot_status():
    return _read_json(BOT_STATUS_FILE, {"status": "offline", "uptime": 0, "commands_used": 0})

def get_guilds():
    return _read_json(GUILDS_FILE, [])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        return render_template("login.html", hata="Yanlis sifre!")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/api/status")
def api_status():
    status = get_bot_status()
    logs = get_modlogs()
    total_bans = sum(1 for gl in logs.values() for log in gl if log.get("action") == "BAN")
    total_kicks = sum(1 for gl in logs.values() for log in gl if log.get("action") == "KICK")
    total_warns = sum(1 for gl in logs.values() for log in gl if log.get("action") == "WARN")
    total_mutes = sum(1 for gl in logs.values() for log in gl if log.get("action") == "MUTE")
    return jsonify({
        "status": status.get("status", "offline"),
        "uptime": status.get("uptime", 0),
        "commands_used": status.get("commands_used", 0),
        "bot_name": status.get("bot_name", "Bilinmiyor"),
        "bot_id": status.get("bot_id", "Bilinmiyor"),
        "guilds": status.get("guilds", 0),
        "invite_url": status.get("invite_url", ""),
        "stats": {
            "total_bans": total_bans,
            "total_kicks": total_kicks,
            "total_warns": total_warns,
            "total_mutes": total_mutes
        }
    })

@app.route("/api/guilds")
def api_guilds():
    return jsonify(get_guilds())

@app.route("/api/guilds/leave", methods=["POST"])
def api_guild_leave():
    if not session.get("logged_in"):
        return jsonify({"error": "Yetkisiz"}), 401
    data = request.get_json()
    guild_id = data.get("guild_id")
    if not guild_id:
        return jsonify({"error": "guild_id gerekli"}), 400
    komutlar = _read_json(WEB_COMMANDS_FILE, [])
    komutlar.append({"type": "leave", "guild_id": guild_id})
    _write_json(WEB_COMMANDS_FILE, komutlar)
    return jsonify({"success": True, "message": "Sunucudan ayrilma komutu gonderildi."})

@app.route("/api/guilds/<guild_id>")
def api_guild_detail(guild_id):
    guilds = get_guilds()
    guild = next((g for g in guilds if g["id"] == guild_id), None)
    if not guild:
        return jsonify({"error": "Sunucu bulunamadi"}), 404
    logs = get_modlogs()
    guild_logs = logs.get(guild_id, [])
    return jsonify({"guild": guild, "logs": guild_logs})

@app.route("/api/logs")
def api_logs():
    logs = get_modlogs()
    guilds = get_guilds()
    guild_map = {g["id"]: g["name"] for g in guilds}
    all_logs = []
    for guild_id, guild_logs in logs.items():
        for log in guild_logs:
            log["guild_id"] = guild_id
            log["guild_name"] = guild_map.get(guild_id, guild_id)
            all_logs.append(log)
    all_logs.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)
    return jsonify({"logs": all_logs[:50]})

@app.route("/api/logs/filter")
def api_logs_filter():
    action = request.args.get("action", "").upper()
    logs = get_modlogs()
    guilds = get_guilds()
    guild_map = {g["id"]: g["name"] for g in guilds}
    filtered = []
    for guild_id, guild_logs in logs.items():
        for log in guild_logs:
            if action == "" or log.get("action") == action:
                log["guild_id"] = guild_id
                log["guild_name"] = guild_map.get(guild_id, guild_id)
                filtered.append(log)
    filtered.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)
    return jsonify({"logs": filtered[:50]})

@app.route("/api/stats")
def api_stats():
    logs = get_modlogs()
    status = get_bot_status()
    guilds = get_guilds()
    guild_map = {g["id"]: g["name"] for g in guilds}

    by_action = {}
    by_moderator = {}
    by_guild = {}

    for guild_id, guild_logs in logs.items():
        gname = guild_map.get(guild_id, guild_id)
        for log in guild_logs:
            action = log.get("action", "UNKNOWN")
            mod = log.get("moderator", "UNKNOWN")
            by_action[action] = by_action.get(action, 0) + 1
            by_moderator[mod] = by_moderator.get(mod, 0) + 1
            if guild_id not in by_guild:
                by_guild[guild_id] = {"name": gname, "total": 0, "actions": {}}
            by_guild[guild_id]["total"] += 1
            by_guild[guild_id]["actions"][action] = by_guild[guild_id]["actions"].get(action, 0) + 1

    genel = {
        "total_guilds": status.get("guilds", 0),
        "total_actions": sum(by_action.values()),
        "total_bans": by_action.get("BAN", 0),
        "total_kicks": by_action.get("KICK", 0),
        "total_warns": by_action.get("WARN", 0),
        "uptime": status.get("uptime", 0),
        "commands_used": status.get("commands_used", 0),
        "bot_name": status.get("bot_name", "Bilinmiyor")
    }

    top_guilds = sorted(by_guild.items(), key=lambda x: x[1]["total"], reverse=True)[:5]
    top_guilds_list = [{"id": gid, "name": data["name"], "total": data["total"], "actions": data["actions"]} for gid, data in top_guilds]

    return jsonify({
        "genel": genel,
        "by_action": by_action,
        "by_moderator": by_moderator,
        "by_guild": by_guild,
        "top_guilds": top_guilds_list
    })

@app.route("/api/logs/user/<name>")
def api_logs_user(name):
    logs = get_modlogs()
    guilds = get_guilds()
    guild_map = {g["id"]: g["name"] for g in guilds}
    filtered = []
    for guild_id, guild_logs in logs.items():
        for log in guild_logs:
            if name.lower() in log.get("target", "").lower() or name.lower() in log.get("moderator", "").lower():
                log["guild_id"] = guild_id
                log["guild_name"] = guild_map.get(guild_id, guild_id)
                filtered.append(log)
    filtered.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)
    return jsonify({"logs": filtered[:50]})

def write_web_command(data):
    komutlar = _read_json(WEB_COMMANDS_FILE, [])
    komutlar.append(data)
    write_json(WEB_COMMANDS_FILE, komutlar)

def get_warns():
    return _read_json("warns_storage.json", {})

def get_members_cache():
    return _read_json("members_cache.json", [])

@app.route("/api/bot/status", methods=["POST"])
def api_bot_status():
    if not session.get("logged_in"):
        return jsonify({"error": "Yetkisiz"}), 401
    data = request.get_json()
    status = data.get("status", "online")
    if status not in ("online", "idle", "dnd"):
        return jsonify({"error": "Gecersiz durum"}), 400
    write_web_command({"type": "status", "status": status})
    return jsonify({"success": True, "message": f"Durum {status} olarak degistiriliyor."})

@app.route("/api/bot/shutdown", methods=["POST"])
def api_bot_shutdown():
    if not session.get("logged_in"):
        return jsonify({"error": "Yetkisiz"}), 401
    write_web_command({"type": "shutdown"})
    return jsonify({"success": True, "message": "Bot kapatiliyor."})

@app.route("/api/bot/restart", methods=["POST"])
def api_bot_restart():
    if not session.get("logged_in"):
        return jsonify({"error": "Yetkisiz"}), 401
    write_web_command({"type": "restart"})
    return jsonify({"success": True, "message": "Bot yeniden baslatiliyor."})

@app.route("/api/bot/reload", methods=["POST"])
def api_bot_reload():
    if not session.get("logged_in"):
        return jsonify({"error": "Yetkisiz"}), 401
    write_web_command({"type": "reload"})
    return jsonify({"success": True, "message": "Komutlar yeniden yukleniyor."})

@app.route("/api/mod/action", methods=["POST"])
def api_mod_action():
    if not session.get("logged_in"):
        return jsonify({"error": "Yetkisiz"}), 401
    data = request.get_json()
    guild_id = data.get("guild_id")
    user_id = data.get("user_id")
    action = data.get("action")
    reason = data.get("reason", "Web panel")
    user_name = data.get("user_name", "Bilinmiyor")
    if not all([guild_id, user_id, action]):
        return jsonify({"error": "guild_id, user_id ve action gerekli"}), 400
    if action not in ("ban", "kick", "warn"):
        return jsonify({"error": "Gecersiz islem"}), 400
    write_web_command({
        "type": action,
        "guild_id": guild_id,
        "user_id": user_id,
        "user_name": user_name,
        "reason": reason,
        "moderator": "WebPanel"
    })
    return jsonify({"success": True, "message": f"{action} islemi gonderildi."})

@app.route("/api/mod/unwarn", methods=["POST"])
def api_mod_unwarn():
    if not session.get("logged_in"):
        return jsonify({"error": "Yetkisiz"}), 401
    data = request.get_json()
    guild_id = data.get("guild_id")
    user_id = data.get("user_id")
    warn_id = data.get("warn_id")
    if not all([guild_id, user_id, warn_id is not None]):
        return jsonify({"error": "guild_id, user_id ve warn_id gerekli"}), 400
    write_web_command({
        "type": "unwarn",
        "guild_id": guild_id,
        "user_id": user_id,
        "warn_id": warn_id,
        "moderator": "WebPanel"
    })
    return jsonify({"success": True, "message": "Uyari kaldirma islemi gonderildi."})

@app.route("/api/members/<guild_id>")
def api_members(guild_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Yetkisiz"}), 401
    cache = get_members_cache()
    for g in cache:
        if g["id"] == guild_id:
            return jsonify({"members": g["members"]})
    return jsonify({"members": []})

@app.route("/api/warns/<guild_id>/<user_id>")
def api_warns(guild_id, user_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Yetkisiz"}), 401
    warns = get_warns()
    guild_data = warns.get(guild_id, {})
    if isinstance(guild_data, dict) and "users" in guild_data:
        user_data = guild_data["users"].get(user_id, {})
        user_warns = [w for w in user_data.get("warns", []) if w.get("active", True)]
    elif isinstance(guild_data, list):
        user_warns = [w for w in guild_data if w["user_id"] == user_id and w.get("active", True)]
    else:
        user_warns = []
    return jsonify({"warns": user_warns})

def get_dogrulama_settings():
    return _read_json("dogrulama_settings.json", {})

@app.route("/api/dogrulama")
def api_dogrulama():
    if not session.get("logged_in"):
        return jsonify({"error": "Yetkisiz"}), 401
    settings = get_dogrulama_settings()
    guilds = get_guilds()
    result = []
    for g in guilds:
        gid = g["id"]
        s = settings.get(gid, {})
        result.append({
            "id": gid,
            "name": g["name"],
            "kayitsiz_rol": s.get("kayitsiz_rol"),
            "uye_rol": s.get("uye_rol"),
            "kayit_kanal": s.get("kayit_kanal"),
            "dogrulama_kanal": s.get("dogrulama_kanal"),
            "panel_mesaj_id": s.get("panel_mesaj_id"),
            "aktif": all([s.get("kayitsiz_rol"), s.get("uye_rol"), s.get("dogrulama_kanal")])
        })
    return jsonify(result)

@app.route("/api/dogrulama/logs")
def api_dogrulama_logs():
    if not session.get("logged_in"):
        return jsonify({"error": "Yetkisiz"}), 401
    logs = _read_json("dogrulama_logs.json", [])
    logs.reverse()
    return jsonify({"logs": logs[:50]})

def _json_oku(dosya, varsayilan=None):
    return _read_json(dosya, varsayilan if varsayilan is not None else {})

@app.route("/api/ayarlar")
def api_ayarlar():
    if not session.get("logged_in"):
        return jsonify({"error": "Yetkisiz"}), 401
    guilds = get_guilds()
    guild_map = {g["id"]: g["name"] for g in guilds}
    logs = get_modlogs()

    karsilama = _json_oku("karsilama_settings.json")
    otorol = _json_oku("otorol_settings.json")
    reaction = _json_oku("reaction_roles.json")
    voice = _json_oku("voice_settings.json")
    instagram = _json_oku("instagram_settings.json")
    facebook = _json_oku("facebook_settings.json")
    twitter = _json_oku("twitter_settings.json")
    dogrulama = _json_oku("dogrulama_settings.json")

    sonuc = []
    for g in guilds:
        gid = g["id"]
        gname = g["name"]
        k = karsilama.get(gid, {})
        o = otorol.get(gid, {})
        r = reaction.get(gid, {"roller": []})
        v = voice.get(gid, {})
        i = instagram.get(gid, {"hesaplar": []})
        f = facebook.get(gid, {"sayfalar": []})
        t = twitter.get(gid, {"hesaplar": []})
        d = dogrulama.get(gid, {})
        guild_logs = logs.get(gid, [])[-5:]
        guild_logs.reverse()
        sonuc.append({
            "id": gid,
            "name": gname,
            "karsilama": {
                "kanal": k.get("kanal"),
                "hosgeldin": bool(k.get("hosgeldin")),
                "gulegule": bool(k.get("gulegule"))
            },
            "otorol": {
                "rol": o.get("rol")
            },
            "reaction_rol": {
                "kanal": r.get("kanal"),
                "rol_sayisi": len(r.get("roller", []))
            },
            "ses_odasi": {
                "kanal": v.get("kanal"),
                "kategori": v.get("kategori"),
                "panel": v.get("panel"),
                "aktif": bool(v.get("kanal") and v.get("kategori"))
            },
            "instagram": {
                "hesap_sayisi": len(i.get("hesaplar", [])),
                "hesaplar": i.get("hesaplar", [])
            },
            "facebook": {
                "sayfa_sayisi": len(f.get("sayfalar", [])),
                "sayfalar": f.get("sayfalar", [])
            },
            "twitter": {
                "hesap_sayisi": len(t.get("hesaplar", [])),
                "hesaplar": t.get("hesaplar", [])
            },
            "dogrulama": {
                "aktif": all([d.get("kayitsiz_rol"), d.get("uye_rol"), d.get("dogrulama_kanal")])
            },
            "son_islemler": guild_logs
        })
    return jsonify(sonuc)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Admin Panel: http://localhost:{port}")
    print(f"Sifre: {ADMIN_PASSWORD}")
    app.run(debug=False, port=port, host="0.0.0.0")
