# Railway Deploy Dosyası

Tüm dosyalara bu klasör içinde bulunmalıdır:

```
dc bot/
├── main.py                (Bot)
├── app.py                 (Web Dashboard)
├── config.py
├── cogs/
│   ├── __init__.py
│   └── moderasyon.py
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
├── requirements.txt
├── Procfile              ← İmportant
├── runtime.txt           ← İmportant
├── .env.example
├── .gitignore
└── modlogs.json          (Otomatik oluşturulur)
```

## Railway Kurulum Adımları

### 1. GitHub'a Push Et
```bash
git add .
git commit -m "rootv1 Discord Bot + Admin Dashboard"
git push origin main
```

### 2. Railway'e Git
https://railway.app → "New Project" → "Deploy from GitHub"

### 3. Repository Seç
Botunun olduğu repository'i seç

### 4. Environment Variables Ekle
Railway Dashboard → "Variables" → Ekle:
```
DISCORD_TOKEN=YENİ_TOKEN_BURAYA_GEL
```

### 5. Deploy!
Railway otomatik deploy eder → 2-3 dakika

## URL'ler
- **Web Dashboard:** `https://your-app.railway.app`
- **Bot:** Arka planda 24/7 çalışıyor

## Local Test (Railway'den Önce)
```bash
# Terminal 1
python main.py

# Terminal 2
python app.py

# Tarayıcı
http://localhost:5000
```

Sorular? Sor!
