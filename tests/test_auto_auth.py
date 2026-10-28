"""
Avtomatik autentifikatsiya yordamchilari testlari.

generate_random_password va username mantig'i — bular standart kutubxonaga
bog'liq (SQLAlchemy'siz), shuning uchun har qanday muhitda ishlaydi.
"""
import re

from app.services.auth_service import USERNAME_RE, generate_random_password


def test_random_password_length_and_charset():
    p = generate_random_password()
    assert len(p) == 10
    # Chalkashmaydigan belgilar: O, 0, I, l bo'lmasligi kerak
    for ch in "O0Il":
        assert ch not in p


def test_random_password_is_random():
    passwords = {generate_random_password() for _ in range(50)}
    # 50 ta parol deyarli har doim turlicha bo'lishi kerak
    assert len(passwords) > 45


def test_generated_password_passes_min_length():
    # Avtomatik parol minimal uzunlik (6) dan uzun
    assert len(generate_random_password()) >= 6


def test_username_regex_accepts_valid():
    assert USERNAME_RE.match("Ali_Valiyev")
    assert USERNAME_RE.match("user12345")


def test_username_regex_rejects_invalid():
    assert not USERNAME_RE.match("ab")          # juda qisqa
    assert not USERNAME_RE.match("has space")   # bo'sh joy
    assert not USERNAME_RE.match("emoji🎁")     # emoji
