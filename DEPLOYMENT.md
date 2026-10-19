# 🚀 NFT Rent — Serverga joylashtirish yo'riqnomasi

Bu yo'riqnoma botni **Ubuntu 24.04 VPS** serverida 24/7 ishga tushirishni **qadam-baqadam** tushuntiradi.
Texnik bilim kam bo'lsa ham, har bir buyruqni ketma-ket bajarsangiz, bot ishlaydi.

---

## 📋 Boshlashdan oldin kerak bo'ladigan narsalar

| Narsa | Qayerdan olinadi | Narx |
|---|---|---|
| **VPS server** (Ubuntu 24.04) | Hetzner / DigitalOcean / Contabo / Aeza | ~$4–6/oy |
| **Domen** (masalan `nftrent.uz`) | Namecheap / reg.uz | ~$10/yil |
| **Bot token** | Telegram'da [@BotFather](https://t.me/BotFather) | Bepul |
| **Telegram ID** (admin uchun) | [@userinfobot](https://t.me/userinfobot) | Bepul |
| **Marketapp API kaliti** (ixtiyoriy) | Marketapp hisobingiz | — |
| **TON manzil** (to'lov uchun, ixtiyoriy) | Tonkeeper hamyon manzili (UQ.../EQ...) | Bepul |

> ⚠️ **Bot token, Marketapp kaliti, TON manzil — bularni faqat SERVERdagi `.env` fayliga yozasiz. Hech kimga, hatto bu kodni yozgan AI'ga ham bermang.**

---

## 1-qadam: Bot token olish (@BotFather)

1. Telegram'da [@BotFather](https://t.me/BotFather) ni oching.
2. `/newbot` buyrug'ini yuboring.
3. Botga nom bering (masalan `NFT Rent`).
4. Username bering (masalan `NftRentBot` — `bot` bilan tugashi shart).
5. BotFather sizga **token** beradi: `123456789:AAH....` — buni saqlang.

---

## 2-qadam: VPS serverni tayyorlash

VPS olgach, SSH orqali ulanasiz (parol yoki kalit bilan):

```bash
ssh root@SERVER_IP
```

Keyin kerakli dasturlarni o'rnatamiz:

```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip git nginx certbot python3-certbot-nginx postgresql
```

---

## 3-qadam: Loyihani yuklab olish

```bash
cd /opt
git clone <SIZNING_GIT_REPO_URL> nft-rent
cd nft-rent

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 4-qadam: PostgreSQL ma'lumotlar bazasini sozlash

```bash
sudo -u postgres psql
```

PostgreSQL ichida:

```sql
CREATE DATABASE nftrent;
CREATE USER nftrent WITH PASSWORD 'KUCHLI_PAROL_SHUYERGA';
GRANT ALL PRIVILEGES ON DATABASE nftrent TO nftrent;
\q
```

---

## 5-qadam: `.env` faylini sozlash

```bash
cp .env.example .env
nano .env
```

Quyidagilarni to'ldiring:

```ini
ENV=production
DEBUG=false

# Kuchli tasodifiy kalit yarating:
SECRET_KEY=<quyidagi buyruq natijasini qo'ying>

BOT_TOKEN=123456789:AAH...        # 1-qadamdan
BOT_USERNAME=NftRentBot
WEBAPP_URL=https://nftrent.uz     # sizning domeningiz

ADMIN_TELEGRAM_IDS=123456789      # @userinfobot dan olingan SIZNING ID

DATABASE_URL=postgresql+asyncpg://nftrent:KUCHLI_PAROL_SHUYERGA@localhost:5432/nftrent

DEFAULT_TON_UZS_RATE=40000

# Marketapp (hozircha o'chiq; rasmiy API kaliti bo'lsa yoqasiz)
MARKETAPP_INTEGRATION_ENABLED=false
MARKETAPP_API_BASE=
MARKETAPP_API_KEY=
```

`SECRET_KEY` yaratish:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Natijani `SECRET_KEY=` ga qo'ying.

---

## 6-qadam: Ma'lumotlar bazasini yaratish va demo ma'lumot yuklash

```bash
source .venv/bin/activate
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
python -m app.seed
```

---

## 7-qadam: systemd xizmatlari (bot + web avtomatik ishlashi uchun)

### Web (API + WebApp) xizmati

```bash
nano /etc/systemd/system/nftrent-web.service
```

```ini
[Unit]
Description=NFT Rent Web
After=network.target postgresql.service

[Service]
WorkingDirectory=/opt/nft-rent
ExecStart=/opt/nft-rent/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

### Bot xizmati

```bash
nano /etc/systemd/system/nftrent-bot.service
```

```ini
[Unit]
Description=NFT Rent Bot
After=network.target nftrent-web.service

[Service]
WorkingDirectory=/opt/nft-rent
ExecStart=/opt/nft-rent/.venv/bin/python -m bot.bot
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

Ishga tushirish:

```bash
systemctl daemon-reload
systemctl enable --now nftrent-web nftrent-bot
systemctl status nftrent-web nftrent-bot
```

---

## 8-qadam: Nginx + HTTPS

```bash
nano /etc/nginx/sites-available/nftrent
```

```nginx
server {
    server_name nftrent.uz;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Yoqish va HTTPS sertifikat olish:

```bash
ln -s /etc/nginx/sites-available/nftrent /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# Bepul HTTPS sertifikat (Let's Encrypt)
certbot --nginx -d nftrent.uz
```

Endi `https://nftrent.uz` ochiladi. ✅

---

## 9-qadam: Botni Telegram'da WebApp bilan bog'lash

1. [@BotFather](https://t.me/BotFather) → `/mybots` → botingiz → **Bot Settings** → **Menu Button** → URL sifatida `https://nftrent.uz` ni kiriting.
2. Endi botni oching, `/start` bosing — pastda WebApp ochiladigan tugma chiqadi.

---

## 10-qadam: TON Connect manifestini sozlash (to'lov uchun)

1. `web/tonconnect-manifest.json` faylida `url` ni o'z domeningizga o'zgartiring:
   ```json
   { "url": "https://nftrent.uz", "name": "NFT Rent", "iconUrl": "https://nftrent.uz/static/img/placeholder.svg" }
   ```
2. Admin panelga kiring: `https://nftrent.uz/admin`
3. **🪙 TON to'lov** bo'limida:
   - **Qabul qiluvchi manzil**: Tonkeeper'dagi manzilingiz (`UQ...` / `EQ...`)
   - **Manifest URL**: `https://nftrent.uz/tonconnect-manifest.json`
   - **To'lovni yoqish** ✅
   - Saqlash

> ⚠️ **Seed phrase (24 so'z) yoki private key'ni HECH QACHON kiritmang.** Faqat ochiq manzil.

---

## 🔁 Yangilanish (kodни yangilaganда)

```bash
cd /opt/nft-rent
git pull
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
systemctl restart nftrent-web nftrent-bot
```

---

## 🧪 Loglarни ko'rish (nimadir ishlamasa)

```bash
journalctl -u nftrent-bot -f     # bot loglari
journalctl -u nftrent-web -f     # web loglari
```

---

## 🔐 Marketapp integratsiyasini yoqish (rasmiy API kaliti bo'lganda)

Hozirda katalog **demo NFT'lar** bilan ishlaydi. Marketapp'ning rasmiy API kaliti bo'lsa:

1. `.env` da:
   ```ini
   MARKETAPP_INTEGRATION_ENABLED=true
   MARKETAPP_API_BASE=<rasmiy API bazasi>
   MARKETAPP_API_KEY=<sizning kalitingiz>
   ```
2. `app/services/marketapp_adapter.py` dagi `_fetch_from_marketapp()` ni rasmiy API spetsifikatsiyasiga ko'ra to'ldiring.
3. `systemctl restart nftrent-web`.

> Integratsiya haqiqatan ulanmaguncha, tizim demo ma'lumotlarни haqiqiy deb ko'rsatmaydi — bu ataylab shunday qilingan.
