"""
Narx va komissiya hisob-kitobi — loyihaning MOLIYAVIY YADROSI.

Barcha hisob-kitob SHU YERDA, backendда amalga oshadi.
Brauzerdagi (frontend) qiymatlarga ishonilmaydi.

Komissiya moduli alohida saqlanadi, shunda haqiqiy Marketapp integratsiyasi
kelganda uni oson almashtirish mumkin bo'ladi.
"""
from dataclasses import dataclass, field, asdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from app.models.settings import CommissionKind, CommissionSetting, CommissionType


def _round_ton(value: float) -> float:
    """TON — 4 xona aniqlik."""
    return float(Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def _round_uzs(value: float) -> float:
    """So'm — butun son."""
    return float(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass
class CommissionLine:
    kind: str
    label_uz: str
    label_en: str
    calc_type: str
    value: float          # foiz yoki qat'iy TON
    amount_ton: float     # hisoblangan TON summa
    amount_uzs: float
    refundable: bool = False


@dataclass
class PriceQuote:
    """Bitta ijara hisob-kitobining to'liq natijasi."""
    daily_price_ton: float
    duration_days: int
    base_price_ton: float
    base_price_uzs: float

    commission_ton: float = 0.0       # qaytarilmaydigan komissiyalar yig'indisi
    network_fee_ton: float = 0.0
    service_fee_ton: float = 0.0
    refundable_deposit_ton: float = 0.0

    total_ton: float = 0.0            # yakuniy to'lov (depozit bilan)
    total_uzs: float = 0.0

    ton_uzs_rate: float = 0.0
    lines: list[CommissionLine] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def compute_quote(
    *,
    daily_price_ton: float,
    duration_days: int,
    ton_uzs_rate: float,
    commissions: Iterable[CommissionSetting],
) -> PriceQuote:
    """
    Ijara narxini hisoblaydi.

    - base_price_ton = daily_price_ton * duration_days
    - Har bir komissiya asosiy narxdan foiz yoki qat'iy TON
    - Qaytariladigan depozit alohida ko'rsatiladi
    - So'm narxi: TON * ton_uzs_rate  (server kursi)
    """
    if daily_price_ton < 0:
        raise ValueError("daily_price_ton manfiy bo'lolmaydi")
    if duration_days <= 0:
        raise ValueError("duration_days musbat bo'lishi kerak")
    if ton_uzs_rate <= 0:
        raise ValueError("ton_uzs_rate musbat bo'lishi kerak")

    base_price_ton = _round_ton(daily_price_ton * duration_days)

    commission_ton = 0.0
    network_fee_ton = 0.0
    service_fee_ton = 0.0
    refundable_deposit_ton = 0.0
    lines: list[CommissionLine] = []

    # Hisoblash tartibi bo'yicha saralash
    sorted_comms = sorted(
        [c for c in commissions if c.is_active],
        key=lambda c: c.order_index,
    )

    for c in sorted_comms:
        if c.calc_type == CommissionType.PERCENT:
            amount_ton = _round_ton(base_price_ton * (c.value / 100.0))
        else:  # FLAT_TON
            amount_ton = _round_ton(c.value)

        refundable = c.kind == CommissionKind.REFUNDABLE_DEPOSIT
        amount_uzs = _round_uzs(amount_ton * ton_uzs_rate)

        lines.append(
            CommissionLine(
                kind=c.kind.value,
                label_uz=c.label_uz or c.kind.value,
                label_en=c.label_en or c.kind.value,
                calc_type=c.calc_type.value,
                value=c.value,
                amount_ton=amount_ton,
                amount_uzs=amount_uzs,
                refundable=refundable,
            )
        )

        if c.kind == CommissionKind.MARKETPLACE:
            commission_ton += amount_ton
        elif c.kind == CommissionKind.NETWORK:
            network_fee_ton += amount_ton
        elif c.kind == CommissionKind.SERVICE:
            service_fee_ton += amount_ton
        elif c.kind == CommissionKind.REFUNDABLE_DEPOSIT:
            refundable_deposit_ton += amount_ton

    commission_ton = _round_ton(commission_ton)
    network_fee_ton = _round_ton(network_fee_ton)
    service_fee_ton = _round_ton(service_fee_ton)
    refundable_deposit_ton = _round_ton(refundable_deposit_ton)

    total_ton = _round_ton(
        base_price_ton
        + commission_ton
        + network_fee_ton
        + service_fee_ton
        + refundable_deposit_ton
    )

    return PriceQuote(
        daily_price_ton=_round_ton(daily_price_ton),
        duration_days=duration_days,
        base_price_ton=base_price_ton,
        base_price_uzs=_round_uzs(base_price_ton * ton_uzs_rate),
        commission_ton=commission_ton,
        network_fee_ton=network_fee_ton,
        service_fee_ton=service_fee_ton,
        refundable_deposit_ton=refundable_deposit_ton,
        total_ton=total_ton,
        total_uzs=_round_uzs(total_ton * ton_uzs_rate),
        ton_uzs_rate=ton_uzs_rate,
        lines=lines,
    )
