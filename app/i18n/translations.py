"""Server tomonidagi tarjimalar (bot xabarlari, xatoliklar).

Frontend tarjimalari web/js/i18n.js da alohida. Bu yerda bot va API xabarlari.
"""
from typing import Any

TRANSLATIONS: dict[str, dict[str, str]] = {
    "uz": {
        # Bot
        "bot_welcome_title": "🎁 <b>NFT Rent</b> — NFT sovg'alarini ijaraga olish platformasi",
        "bot_welcome_body": (
            "NFT Rent orqali Telegram NFT sovg'alarini <b>ijaraga</b> olishingiz mumkin.\n\n"
            "💠 Narxlar <b>TON</b> va <b>so'm</b>da ko'rsatiladi.\n"
            "🔒 Akkauntingiz xavfsiz, parolingiz shifrlanadi.\n\n"
            "Boshlash uchun pastdagi tugmani bosing 👇"
        ),
        "btn_open_app": "🚀 NFT Rent ilovasini ochish",
        "btn_start": "▶️ Boshlash",
        "btn_login": "🔑 Kirish",
        "btn_support": "🆘 Support",
        "bot_support_text": "Yordam kerakmi? Support bilan bog'laning: @{support}",
        "bot_account_created": (
            "✅ <b>NFT Rent akkauntingiz yaratildi!</b>\n\n"
            "👤 Username: <code>{username}</code>\n\n"
            "🔐 Parolingizni xavfsiz joyda saqlang va hech kimga bermang. "
            "Parolingizni unutib qo'ysangiz, akkauntingizni tiklash uchun Support'ga murojaat qiling.\n\n"
            "⚠️ Xavfsizlik uchun parolingizni Telegram xabarlarida saqlamang."
        ),
        # Umumiy API xatolari
        "err_invalid_initdata": "Telegram tasdiqlash ma'lumoti noto'g'ri.",
        "err_username_taken": "Bu username allaqachon band.",
        "err_password_mismatch": "Parollar mos kelmadi.",
        "err_invalid_credentials": "Username yoki parol noto'g'ri.",
        "err_too_many_attempts": "Juda ko'p urinish. Birozdan so'ng qayta urinib ko'ring.",
        "err_old_password_wrong": "Eski parol noto'g'ri.",
        "err_not_authenticated": "Tizimga kirilmagan.",
        "err_forbidden": "Ruxsat yo'q.",
        "err_not_found": "Topilmadi.",
        "err_account_blocked": "Akkaunt vaqtincha bloklangan.",
        "err_invalid_duration": "Noto'g'ri ijara muddati.",
        "err_nft_unavailable": "Bu NFT hozircha mavjud emas.",
        "err_rate_positive": "Kurs musbat son bo'lishi kerak.",
        "ok_registered": "Ro'yxatdan muvaffaqiyatli o'tdingiz.",
        "ok_logged_in": "Tizimga kirdingiz.",
        "ok_password_changed": "Parol muvaffaqiyatli o'zgartirildi.",
        "payment_later": "To'lov tizimi keyingi bosqichda ulanadi.",
    },
    "en": {
        "bot_welcome_title": "🎁 <b>NFT Rent</b> — rent Telegram NFT gifts",
        "bot_welcome_body": (
            "With NFT Rent you can <b>rent</b> Telegram NFT gifts.\n\n"
            "💠 Prices are shown in <b>TON</b> and <b>UZS</b>.\n"
            "🔒 Your account is secure, your password is encrypted.\n\n"
            "Tap the button below to get started 👇"
        ),
        "btn_open_app": "🚀 Open NFT Rent app",
        "btn_start": "▶️ Start",
        "btn_login": "🔑 Login",
        "btn_support": "🆘 Support",
        "bot_support_text": "Need help? Contact Support: @{support}",
        "bot_account_created": (
            "✅ <b>Your NFT Rent account has been created!</b>\n\n"
            "👤 Username: <code>{username}</code>\n\n"
            "🔐 Keep your password safe and never share it. "
            "If you forget it, contact Support to recover your account.\n\n"
            "⚠️ For security, do not store your password in Telegram messages."
        ),
        "err_invalid_initdata": "Invalid Telegram verification data.",
        "err_username_taken": "This username is already taken.",
        "err_password_mismatch": "Passwords do not match.",
        "err_invalid_credentials": "Invalid username or password.",
        "err_too_many_attempts": "Too many attempts. Please try again later.",
        "err_old_password_wrong": "Old password is incorrect.",
        "err_not_authenticated": "Not authenticated.",
        "err_forbidden": "Forbidden.",
        "err_not_found": "Not found.",
        "err_account_blocked": "Account is temporarily blocked.",
        "err_invalid_duration": "Invalid rental duration.",
        "err_nft_unavailable": "This NFT is currently unavailable.",
        "err_rate_positive": "Rate must be a positive number.",
        "ok_registered": "Registered successfully.",
        "ok_logged_in": "Logged in.",
        "ok_password_changed": "Password changed successfully.",
        "payment_later": "Payments will be connected in the next phase.",
    },
}


def t(key: str, lang: str = "uz", **kwargs: Any) -> str:
    lang = lang if lang in TRANSLATIONS else "uz"
    text = TRANSLATIONS[lang].get(key) or TRANSLATIONS["uz"].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
