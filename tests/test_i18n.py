"""Tarjima (uz/en) testlari — tashqi paketsiz ishlaydi."""
from app.i18n import TRANSLATIONS, t


def test_both_languages_exist():
    assert "uz" in TRANSLATIONS
    assert "en" in TRANSLATIONS


def test_key_coverage_matches():
    """uz va en bir xil kalitlarga ega bo'lishi kerak."""
    uz_keys = set(TRANSLATIONS["uz"].keys())
    en_keys = set(TRANSLATIONS["en"].keys())
    assert uz_keys == en_keys, f"Farq: {uz_keys ^ en_keys}"


def test_translation_lookup():
    assert t("btn_login", "uz") == "🔑 Kirish"
    assert t("btn_login", "en") == "🔑 Login"


def test_fallback_to_uz_for_unknown_lang():
    # Noma'lum til -> uz
    assert t("btn_login", "ru") == t("btn_login", "uz")


def test_format_substitution():
    out = t("bot_support_text", "uz", support="TestSupport")
    assert "TestSupport" in out


def test_account_created_never_contains_password():
    """Akkaunt yaratildi xabarida parol ko'rsatilmasligi kafolatlanadi."""
    msg_uz = t("bot_account_created", "uz", username="alice")
    msg_en = t("bot_account_created", "en", username="alice")
    assert "alice" in msg_uz and "alice" in msg_en
    # 'password' so'zi bor, lekin HAQIQIY parol qiymati yo'q (faqat username format qilinadi)
    assert "{password}" not in msg_uz
