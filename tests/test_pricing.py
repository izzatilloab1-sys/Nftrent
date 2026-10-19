"""
Narx va komissiya hisob-kitobi testlari.

Bu testlar FAQAT standart kutubxonaga bog'liq (app.services.pricing mustaqil),
shuning uchun internet/tashqi paketsiz ham ishga tushadi.

Qamrab oladi (TT 17-bo'lim):
  - Ijara muddatiga qarab narx to'g'ri hisoblanishi
  - Komissiyalar alohida hisoblanishi
  - TON kursi o'zgarganda yangi hisob-kitob yangilanishi
  - Qaytariladigan depozit alohida ko'rsatilishi
"""
from dataclasses import dataclass

from app.models.settings import CommissionKind, CommissionType
from app.services.pricing import compute_quote


# CommissionSetting ni taqlid qiluvchi oddiy obyekt (DB kerak emas)
@dataclass
class FakeCommission:
    kind: object
    calc_type: object
    value: float
    order_index: int = 0
    is_active: bool = True
    label_uz: str = ""
    label_en: str = ""


def _commissions():
    return [
        FakeCommission(CommissionKind.MARKETPLACE, CommissionType.PERCENT, 5.0, 1,
                       label_uz="Marketplace", label_en="Marketplace"),
        FakeCommission(CommissionKind.NETWORK, CommissionType.FLAT_TON, 0.05, 2,
                       label_uz="Tarmoq", label_en="Network"),
        FakeCommission(CommissionKind.SERVICE, CommissionType.PERCENT, 2.0, 3,
                       label_uz="Xizmat", label_en="Service"),
        FakeCommission(CommissionKind.REFUNDABLE_DEPOSIT, CommissionType.PERCENT, 10.0, 4,
                       label_uz="Depozit", label_en="Deposit"),
    ]


def test_base_price_by_duration():
    """base_price = daily * duration."""
    q = compute_quote(daily_price_ton=0.5, duration_days=7, ton_uzs_rate=40000, commissions=[])
    assert q.base_price_ton == 0.5 * 7  # 3.5
    assert q.total_ton == 3.5  # komissiyasiz
    assert q.base_price_uzs == 3.5 * 40000


def test_duration_changes_price():
    q1 = compute_quote(daily_price_ton=1.0, duration_days=1, ton_uzs_rate=40000, commissions=[])
    q30 = compute_quote(daily_price_ton=1.0, duration_days=30, ton_uzs_rate=40000, commissions=[])
    assert q30.base_price_ton == 30 * q1.base_price_ton


def test_commissions_computed_separately():
    """Har bir komissiya alohida hisoblanadi."""
    q = compute_quote(daily_price_ton=1.0, duration_days=10, ton_uzs_rate=40000, commissions=_commissions())
    base = 10.0  # 1.0 * 10
    assert q.base_price_ton == base
    assert q.commission_ton == round(base * 0.05, 4)   # marketplace 5%
    assert q.network_fee_ton == 0.05                    # flat
    assert q.service_fee_ton == round(base * 0.02, 4)   # service 2%
    assert q.refundable_deposit_ton == round(base * 0.10, 4)  # depozit 10%
    # 4 ta qator bo'lishi kerak
    assert len(q.lines) == 4


def test_refundable_deposit_flagged():
    q = compute_quote(daily_price_ton=1.0, duration_days=1, ton_uzs_rate=40000, commissions=_commissions())
    refund_lines = [l for l in q.lines if l.refundable]
    assert len(refund_lines) == 1
    assert refund_lines[0].kind == "refundable_deposit"


def test_total_includes_all():
    q = compute_quote(daily_price_ton=1.0, duration_days=10, ton_uzs_rate=40000, commissions=_commissions())
    expected = (q.base_price_ton + q.commission_ton + q.network_fee_ton
                + q.service_fee_ton + q.refundable_deposit_ton)
    assert abs(q.total_ton - expected) < 1e-6


def test_rate_change_updates_uzs():
    """Kurs o'zgarsa so'm narxi yangilanadi, TON o'zgarmaydi."""
    q1 = compute_quote(daily_price_ton=1.0, duration_days=5, ton_uzs_rate=40000, commissions=[])
    q2 = compute_quote(daily_price_ton=1.0, duration_days=5, ton_uzs_rate=50000, commissions=[])
    assert q1.total_ton == q2.total_ton         # TON o'zgarmaydi
    assert q2.total_uzs > q1.total_uzs          # so'm oshadi
    assert q2.total_uzs == q2.total_ton * 50000


def test_invalid_inputs():
    import pytest
    with pytest.raises(ValueError):
        compute_quote(daily_price_ton=1.0, duration_days=0, ton_uzs_rate=40000, commissions=[])
    with pytest.raises(ValueError):
        compute_quote(daily_price_ton=1.0, duration_days=5, ton_uzs_rate=0, commissions=[])
