# 🤖 rootv1 - Discord Moderation Bot + Admin Dashboard

Profesyonel Discord moderasyon botu ve web admin paneli.

## ✨ Özellikler

### 🎮 Bot Komutları (Slash Commands)
- `/ban`, `/kick`, `/purge`, `/embed` - Moderasyon ve özel embed mesajları
- `/antibot`, `/otokoruma`, `/automod-setup`, `/automod-kurallar`, `/automod-stats` - Koruma sistemleri
- `/ticket`, `/ticket-yetkili`, `/ticket-log` - Ticket yönetimi
- `/setlog`, `/logayarlari` - Log kanalı yönetimi
- `/karsilama`, `/otorol`, `/sesoda`, `/dogrulama` - Sunucu sistemleri
- `/giveaway`, `/anket` - Etkinlik ve oylama
- `/instagram`, `/testinstagram`, `/instagram-sil` - Instagram bildirimleri
- `/komutekle`, `/komutsil`, `/komutlistesi` - Sunucuya özel `!` komutları
- `/userinfo`, `/serverinfo`, `/help`, `/yazi-tura`, `/zar`, `/espri`, `/avatar`, `/ping` - Bilgi ve eğlence

`/karsilama` sistemi yeni üyeler için ROOTx temalı, avatar içeren bir PNG banner üretir. Banner üretilemezse ayarlanmış yazılı mesaj gönderilmeye devam eder.

### 📊 Admin Dashboard
- **Dashboard:** Bot istatistikleri, son işlemler
- **Moderasyon Logları:** Tüm işlemleri göster, filtrele
- **İstatistikler:** Grafik ve analizler
- **Ayarlar:** Bot kontrolleri

## 🚀 Kurulum

### Local'de Çalıştırma

1. **Python kütüphanelerini yükle:**
```bash
pip install -r requirements.txt
```

2. **`.env` dosyasını oluştur:**
```bash
cp .env.example .env
```

3. **Token'i `.env`'ye ekle:**
```
DISCORD_TOKEN=your_bot_token_here
```


4. **Terminal 1 - Bot'u çalıştır:**
```bash
python main.py
```

5. **Tarayıcıda aç:**
```
http://localhost:5000
```

### Railway'e Deploy

Detaylı talimatlar için [DEPLOYMENT.md](DEPLOYMENT.md) dosyasını oku.

**Özet:**
1. GitHub'a push et
2. Railway.app'a git
3. Repo'yu seç
4. DISCORD_TOKEN ekle
5. Deploy!

## 📋 Dosya Yapısı

```
dc bot/
├── main.py              Bot ana dosyası
├── app.py               Flask web uygulaması
├── config.py            Ayarlar
├── cogs/
│   ├── moderasyon.py   Moderasyon komutları
│   ├── antibot.py      Bot koruması
│   ├── ticket.py       Ticket sistemi
│   └── ...             Diğer cog modülleri
├── templates/
│   └── dashboard.html  Web interface
├── requirements.txt    Python kütüphaneleri
├── Procfile           Railway deploy dosyası
├── runtime.txt        Python versiyonu
├── .env.example       Environment örneği
└── .gitignore
```

## 🔧 Teknolojiler

- **discord.py** - Discord API
- **Flask** - Web framework
- **HTML/CSS/JS** - Frontend

## 📝 Lisans

MIT License

## 👤 Geliştirici

rootv1 Bot - 2026
