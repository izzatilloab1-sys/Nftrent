"""
TON to'lovni tekshirish — "AUTO to'lov" yuragi.

Oqim (xavfsiz usul — TON Connect):
  1. Foydalanuvchi "To'lash" bosadi.
  2. Server buyurtmaga UNIKAL comment (payment memo) biriktiradi, masalan: NR-ORDERNUM.
  3. WebApp TON Connect orqali Tonkeeper'ni ochadi:
        manzil = admin kiritgan receiving_address
        summa  = buyurtma total_ton (nanoTON)
        comment = payment memo
  4. Foydalanuvchi O'Z hamyonida tasdiqlaydi (bizning kalitimiz kerak emas).
  5. Server blockchaindan kelgan tranzaksiyalarni tekshiradi:
        - to'g'ri manzilga
        - yetarli summa (>=)
        - to'g'ri comment
     topilsa -> to'lov tasdiqlanadi -> ijara AVTOMATIK faollashadi.

⚠️ Private key / seed hech qayerda ishlatilmaydi. Biz faqat O'QIYMIZ (read-only).
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

# Public TON indexer. Prod'da API kalit bilan ishlatish tavsiya etiladi.
TONCENTER_MAINNET = "https://toncenter.com/api/v2"
TONCENTER_TESTNET = "https://testnet.toncenter.com/api/v2"

NANO = 1_000_000_000  # 1 TON = 1e9 nanoTON


@dataclass
class PaymentCheckResult:
    confirmed: bool
    tx_hash: str | None = None
    amount_ton: float | None = None
    reason: str | None = None


def ton_to_nano(amount_ton: float) -> int:
    return int(round(amount_ton * NANO))


def payment_memo_for_order(order_number: str) -> str:
    """Buyurtmaning unikal to'lov commenti."""
    return order_number  # NR-YYYYMMDD-XXXXXX — allaqachon unikal


async def check_incoming_payment(
    *,
    receiving_address: str,
    expected_amount_ton: float,
    memo: str,
    testnet: bool = False,
    api_key: str | None = None,
    limit: int = 50,
) -> PaymentCheckResult:
    """
    Qabul qiluvchi manzilga kelgan oxirgi tranzaksiyalarni tekshiradi.
    Mos tranzaksiya topilsa -> confirmed=True.

    Internet talab qiladi (prod serverda ishlaydi). Bu sandbox'da emas.
    """
    base = TONCENTER_TESTNET if testnet else TONCENTER_MAINNET
    params = {"address": receiving_address, "limit": str(limit), "archival": "false"}
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{base}/getTransactions", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return PaymentCheckResult(confirmed=False, reason=f"network_error: {e}")

    if not data.get("ok"):
        return PaymentCheckResult(confirmed=False, reason="api_error")

    expected_nano = ton_to_nano(expected_amount_ton)

    for tx in data.get("result", []):
        in_msg = tx.get("in_msg") or {}
        value_nano = int(in_msg.get("value", 0) or 0)
        comment = (in_msg.get("message") or "").strip()

        # Comment mos va summa yetarli bo'lsa -> tasdiqlandi
        if comment == memo and value_nano >= expected_nano:
            tx_hash = tx.get("transaction_id", {}).get("hash")
            return PaymentCheckResult(
                confirmed=True,
                tx_hash=tx_hash,
                amount_ton=value_nano / NANO,
            )

    return PaymentCheckResult(confirmed=False, reason="not_found_yet")


def build_tonconnect_transaction(
    *, receiving_address: str, amount_ton: float, memo: str
) -> dict:
    """
    WebApp'da TON Connect SDK'ga beriladigan tranzaksiya obyekti.
    Foydalanuvchi hamyoni shuni imzolaydi.
    """
    return {
        "validUntil": None,  # frontend to'ldiradi (now + 5 min)
        "messages": [
            {
                "address": receiving_address,
                "amount": str(ton_to_nano(amount_ton)),  # nanoTON (string)
                "payload_comment": memo,  # frontend comment payload'ga aylantiradi
            }
        ],
    }
