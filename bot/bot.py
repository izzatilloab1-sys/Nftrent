"""
NFT Rent — Telegram bot (aiogram 3).

Boshlang'ich sahifa: logo, banner, Boshlash / Kirish / Support tugmalari,
so'm va TON haqida qisqa ma'lumot, WebApp'ni ochish tugmasi.

Ishga tushirish:  python -m bot.bot
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from app.config import settings
from app.i18n import t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nftrent.bot")


def main_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Boshlang'ich tugmalar."""
    webapp_btn = InlineKeyboardButton(
        text=t("btn_open_app", lang),
        web_app=WebAppInfo(url=settings.webapp_url),
    )
    rows = [
        [webapp_btn],
        [
            InlineKeyboardButton(text=t("btn_start", lang), callback_data="start_app"),
            InlineKeyboardButton(text=t("btn_login", lang), callback_data="login_app"),
        ],
        [InlineKeyboardButton(text=t("btn_support", lang), callback_data="support")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def detect_lang(message: Message) -> str:
    code = (message.from_user.language_code or "").lower() if message.from_user else ""
    return "en" if code.startswith("en") else "uz"


async def on_start(message: Message):
    lang = detect_lang(message)
    text = (
        f"{t('bot_welcome_title', lang)}\n\n"
        f"{t('bot_welcome_body', lang)}"
    )
    await message.answer(text, reply_markup=main_keyboard(lang))


async def get_support_username() -> str:
    """Support username'ni DB dan oladi (yoki .env default)."""
    try:
        from app.database import AsyncSessionLocal
        from app.services import support_service
        async with AsyncSessionLocal() as db:
            return await support_service.get_support_username(db)
    except Exception:
        return settings.default_support_username


def register_handlers(dp: Dispatcher):
    dp.message.register(on_start, CommandStart())

    @dp.callback_query(F.data == "support")
    async def cb_support(call):
        support = await get_support_username()
        lang = "en" if (call.from_user.language_code or "").startswith("en") else "uz"
        await call.message.answer(t("bot_support_text", lang, support=support))
        await call.answer()

    @dp.callback_query(F.data.in_(["start_app", "login_app"]))
    async def cb_open(call):
        lang = "en" if (call.from_user.language_code or "").startswith("en") else "uz"
        await call.message.answer(
            t("btn_open_app", lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=t("btn_open_app", lang),
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]]),
        )
        await call.answer()


async def notify_account_created(bot: Bot, telegram_id: int, username: str, lang: str = "uz"):
    """Ro'yxatdan o'tgach foydalanuvchiga xabar (haqiqiy parol HECH QACHON ko'rsatilmaydi)."""
    try:
        await bot.send_message(telegram_id, t("bot_account_created", lang, username=username))
    except Exception as e:
        logger.warning("notify_account_created failed: %s", e)


async def main():
    if not settings.bot_token or settings.bot_token.startswith("123456789:"):
        raise RuntimeError(
            "BOT_TOKEN sozlanmagan! .env faylida BOT_TOKEN ni @BotFather dan olingan token bilan to'ldiring."
        )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    register_handlers(dp)

    logger.info("NFT Rent bot ishga tushdi. WebApp: %s", settings.webapp_url)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
