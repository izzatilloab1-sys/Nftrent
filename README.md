# NFT Rent 🎁

Telegram bot va Telegram WebApp (Mini App) — NFT sovg'alarini **ijaraga olish** platformasi.
Marketapp uslubidagi zamonaviy dizayn, o'ziga xos **NFT Rent** brendi bilan.

> ⚠️ **Muhim:** Bu loyihaning **birinchi bosqichi**. To'lov tizimi (so'm / TON / Tonkeeper)
> ataylab **o'chirilgan**. Interfeys, backend, ma'lumotlar bazasi, foydalanuvchi tizimi,
> admin paneli va ijara hisob-kitoblari **real ishlaydi**. To'lov keyingi bosqichda ulanadi.
>
> ⚠️ **Integratsiya haqida ochiq ogohlantirish:** Hozirda Marketapp bilan haqiqiy,
> rasmiy API integratsiyasi **MAVJUD EMAS**. Katalogdagi NFT'lar — **demo / test ma'lumotlari**.
> Ular haqiqiy, egalik qilish mumkin bo'lgan NFT'lar sifatida taqdim etilmaydi.
> Integratsiya uchun `app/services/marketapp_adapter.py` dagi tayyor adapter interfeysi ishlatiladi.

---

## ✨ Asosiy imkoniyatlar

- **Telegram bot** (aiogram 3): boshlash sahifasi, Boshlash / Kirish / Support tugmalari, WebApp'ni ochish.
- **Telegram WebApp**: to'liq ekranli, mobilга mos NFT katalogi, tafsilotlar, ijara hisob-kitobi.
- **Foydalanuvchi tizimi**: username + parol (bcrypt xesh), login, logout, parol almashtirish, sessiya.
- **Telegram `initData` tekshiruvi**: server tomonida rasmiy HMAC tasdiqlash.
- **Ikki til**: O'zbekcha va English — profilда saqlanadi.
- **NFT katalogi**: kartochkalar, filtrlar, qidiruv, saralash, bo'limlar (Barchasi / Mashhur / Yangi / Mening ijaralarim).
- **Ijara hisob-kitobi**: kunlik narx × muddat + komissiyalar — **backendда** hisoblanadi.
- **TON kursi**: admin boshqaradi; eski buyurtmalar kursi o'zgarmaydi.
- **Komissiyalar**: alohida sozlanadigan modul (marketplace, TON tarmog'i, xizmat, qaytariladigan depozit).
- **Admin panel**: statistika, TON kursi, NFT boshqaruvi, komissiyalar, foydalanuvchilar, Support sozlamasi.
- **Audit log**: muhim admin harakatlari qayd etiladi.
- **Testlar**: pytest bilan asosiy biznes-mantiq va xavfsizlik testlari.

---

## 🧱 Texnologiyalar

| Qatlam | Texnologiya |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Telegram bot | aiogram 3 |
| Frontend | HTML + CSS + Vanilla JS (Telegram WebApp SDK) |
| Ma'lumotlar bazasi | PostgreSQL (prod) / SQLite (dev) |
| ORM | SQLAlchemy 2 (async) |
| Migratsiyalar | Alembic |
| Auth | bcrypt (passlib), JWT sessiya |
| Deploy | Ubuntu 24.04 VPS, Nginx, HTTPS (Let's Encrypt), systemd |

---

## 📁 Loyiha strukturasi

```
nft-rent/
├── app/
│   ├── main.py                 # FastAPI ilovasi (entrypoint)
│   ├── config.py               # Sozlamalar (.env dan)
│   ├── database.py             # DB ulanish (async SQLAlchemy)
│   ├── models/                 # SQLAlchemy modellar (13 ta jadval)
│   ├── schemas/                # Pydantic sxemalar
│   ├── api/                    # API routerlar (auth, nft, orders, admin, profile)
│   ├── services/               # Biznes-mantiq
│   │   ├── pricing.py          # Narx + komissiya hisob-kitobi
│   │   ├── auth_service.py     # Ro'yxat, login, parol
│   │   ├── currency_service.py # TON kursi
│   │   ├── commission_service.py
│   │   └── marketapp_adapter.py# Integratsiya adapteri (hozircha demo)
│   ├── core/                   # Xavfsizlik, Telegram initData, i18n
│   ├── i18n/                   # uz / en tarjimalar
│   └── seed.py                 # Demo NFT ma'lumotlari
├── bot/
│   └── bot.py                  # aiogram 3 Telegram bot
├── web/                        # Telegram WebApp (frontend)
│   ├── index.html
│   ├── admin.html
│   ├── css/
│   └── js/
├── alembic/                    # Migratsiyalar
├── tests/                      # pytest testlar
├── .env.example
├── requirements.txt
├── README.md
└── DEPLOYMENT.md               # Serverga joylash yo'riqnomasi
```

---

## 🚀 Mahalliy ishga tushirish (dev, SQLite)

```bash
# 1. Virtual muhit
python3 -m venv .venv
source .venv/bin/activate

# 2. Kutubxonalar
pip install -r requirements.txt

# 3. .env tayyorlash
cp .env.example .env
# .env ni tahrirlang: BOT_TOKEN, SECRET_KEY, ADMIN_TELEGRAM_IDS, WEBAPP_URL

# 4. Migratsiya va demo ma'lumotlar
alembic upgrade head
python -m app.seed

# 5. Backend (WebApp + API)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Boshqa terminalda — Telegram bot
python -m bot.bot
```

WebApp: `http://localhost:8000/` — Telegram ichidan ochilganda `initData` ishlaydi.
Admin panel: `http://localhost:8000/admin`

---

## 🧪 Testlar

```bash
pytest -v
```

---

## 🔐 Xavfsizlik eslatmalari

- Parollar **bcrypt** bilan xeshlanadi, hech qachon ochiq saqlanmaydi.
- `BOT_TOKEN`, `SECRET_KEY` va boshqa maxfiy kalitlar faqat `.env` da.
- `.env` **Git'ga joylashtirilmaydi** (`.gitignore` da).
- TON hamyon seed/private key hech qayerda saqlanmaydi (to'lov bosqichi kelganda ham foydalanuvchi o'z hamyonida tasdiqlaydi).
- Admin huquqi server tomonida `ADMIN_TELEGRAM_IDS` / `admin_users` orqali tekshiriladi.
- Barcha pul hisob-kitoblari backendда.

Deploy bo'yicha to'liq yo'riqnoma: **[DEPLOYMENT.md](./DEPLOYMENT.md)**
