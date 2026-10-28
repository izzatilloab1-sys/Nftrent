"""
Web jarayonidan Telegram chatga xabar yuborish.

Bot jarayoni (polling) va web jarayoni alohida ishlaydi. Web jarayoni
ro'yxatdan o'tgach foydalanuvchiga xabar yuborishi kerak, shuning uchun
bu yerda qisqa muddatli Bot instance yaratib, bitta xabar yuboramiz.

⚠️ Haqiqiy parol FAQAT shu bir marta (yangi ro'yxatda) yuboriladi.
Bazada yoki loglarda ochiq parol saqlanmaydi.
"""
import logging

from app.config import settings
from app.i18n import t

logger = logging.getLogger("nftrent.notify")


async def send_credentials(
    telegram_id: int, username: str, password: str, language: str = "uz"
) -> bool:
    """
    Yangi akkaunt yaratilgach username va parolni foydalanuvchi chatiga yuboradi.
    Muvaffaqiyatli bo'lsa True.
    """
    if not settings.bot_token or settings.bot_token.startswith("123456789:"):
        logger.warning("BOT_TOKEN sozlanmagan — credentials yuborilmadi")
        return False

    try:
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode

        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        text = t("bot_account_created_with_password", language, username=username, password=password)
        try:
            await bot.send_message(telegram_id, text)
            return True
        finally:
            await bot.session.close()
    except Exception as e:
        logger.warning("send_credentials failed: %s", e)
        return False
