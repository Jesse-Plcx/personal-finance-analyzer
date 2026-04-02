from __future__ import annotations

from pathlib import Path

import pdfplumber

from .categories import categorize_transaction
from .config import SOURCE_DIRS
from .utils import clean_text, parse_amount, parse_date

_ALIPAY_TABLE_SETTINGS = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "intersection_x_tolerance": 3,
    "intersection_y_tolerance": 3,
}

_BANK_WALLET_PREFIXES = ("财付通", "支付宝", "淘宝平台商户")


def _finalize_transaction(transaction: dict[str, object]) -> dict[str, object]:
    transaction["category"] = categorize_transaction(transaction)
    return transaction


def _make_transaction(
    *,
    source: str,
    year: int,
    month: int,
    day: int,
    occurred_at: str,
    tx_type: str,
    direction: str,
    pay_method: str,
    amount: float,
    counterparty: str,
    dedup_key: str,
) -> dict[str, object]:
    return _finalize_transaction(
        {
            "source": source,
            "year": year,
            "month": month,
            "day": day,
            "full_dt": occurred_at,
            "type": tx_type,
            "direction": direction,
            "pay_method": pay_method,
            "amount": amount,
            "counterparty": counterparty,
            "_dedup_key": dedup_key,
        }
    )


def parse_wechat_file(filepath: Path) -> list[dict[str, object]]:
    transactions: list[dict[str, object]] = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not row or len(row) < 8:
                        continue
                    if row[0] and any(text in str(row[0]) for text in ("交易明细", "具体交易", "交易单号")):
                        continue

                    date_str = clean_text(row[1])
                    tx_type = clean_text(row[2])
                    direction = clean_text(row[3])
                    pay_method = clean_text(row[4])
                    amount = parse_amount(row[5])
                    counterparty = clean_text(row[6])

                    if not date_str or amount == 0:
                        continue
                    if direction == "收入" and "-退款" in tx_type:
                        direction = "支出"
                        amount = -amount

                    date_info = parse_date(date_str)
                    if not date_info:
                        continue
                    year, month, day, full_dt = date_info

                    transactions.append(
                        _make_transaction(
                            source="微信",
                            year=year,
                            month=month,
                            day=day,
                            occurred_at=full_dt,
                            tx_type=tx_type,
                            direction=direction,
                            pay_method=pay_method,
                            amount=amount,
                            counterparty=counterparty,
                            dedup_key=f"微信|{full_dt}|{amount}|{direction}|{counterparty}",
                        )
                    )
    return transactions


def parse_alipay_file(filepath: Path) -> list[dict[str, object]]:
    transactions: list[dict[str, object]] = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables(_ALIPAY_TABLE_SETTINGS):
                for row in table:
                    if not row or len(row) < 8:
                        continue
                    if row[0] and any(
                        text in str(row[0]) for text in ("交易时间段", "交易类型", "收/支")
                    ):
                        continue

                    direction = clean_text(row[0])
                    counterparty = clean_text(row[1])
                    description = clean_text(row[2])
                    pay_method = clean_text(row[3])
                    amount = parse_amount(row[4])
                    date_str = clean_text(row[7])

                    if not direction or amount == 0:
                        continue
                    if "不计" in direction:
                        if description.startswith("退款"):
                            direction = "支出"
                            amount = -amount
                        else:
                            direction = "不计收支"

                    date_info = parse_date(date_str)
                    if not date_info:
                        continue
                    year, month, day, full_dt = date_info

                    tx_type = description or counterparty
                    transactions.append(
                        _make_transaction(
                            source="支付宝",
                            year=year,
                            month=month,
                            day=day,
                            occurred_at=full_dt,
                            tx_type=tx_type,
                            direction=direction,
                            pay_method=pay_method,
                            amount=amount,
                            counterparty=counterparty,
                            dedup_key=f"支付宝|{full_dt}|{amount}|{direction}|{counterparty}",
                        )
                    )
    return transactions


def parse_bank_file(filepath: Path) -> list[dict[str, object]]:
    transactions: list[dict[str, object]] = []
    header_cols = {"记账日期", "记账时间", "金额", "余额", "交易名称", "对方账户名"}
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not row or len(row) < 10:
                        continue
                    if row[0] and (str(row[0]).strip() in header_cols or "记账日期" in str(row[0])):
                        continue

                    date_str = clean_text(row[0])
                    time_str = clean_text(row[1])
                    amount_str = clean_text(row[3])
                    tx_name = clean_text(row[5])
                    remarks = clean_text(row[8])
                    counterparty = clean_text(row[9])

                    if not date_str or not amount_str:
                        continue

                    try:
                        raw_amount = float(amount_str.replace(",", ""))
                    except ValueError:
                        continue
                    if raw_amount == 0:
                        continue

                    cp_clean = counterparty.strip()
                    if cp_clean.startswith(_BANK_WALLET_PREFIXES):
                        continue

                    full_date_str = f"{date_str} {time_str}" if time_str else date_str
                    date_info = parse_date(full_date_str)
                    if not date_info:
                        continue
                    year, month, day, full_dt = date_info

                    amount = abs(raw_amount)
                    direction = "收入" if raw_amount > 0 else "支出"
                    if direction == "收入" and ("退款" in tx_name or "退货" in tx_name):
                        direction = "支出"
                        amount = -amount

                    tx_type = tx_name
                    if remarks and remarks not in {"-------------------", "-"}:
                        tx_type = f"{tx_name}-{remarks}"

                    final_counterparty = cp_clean if cp_clean and cp_clean != "-------------------" else remarks
                    transactions.append(
                        _make_transaction(
                            source="中行",
                            year=year,
                            month=month,
                            day=day,
                            occurred_at=full_dt,
                            tx_type=tx_type,
                            direction=direction,
                            pay_method="中国银行储蓄卡",
                            amount=amount,
                            counterparty=final_counterparty,
                            dedup_key=f"中行|{full_dt}|{amount}|{direction}|{final_counterparty}",
                        )
                    )
    return transactions


def parse_statement_file(source: str, filepath: Path) -> list[dict[str, object]]:
    if source == "微信":
        return parse_wechat_file(filepath)
    if source == "支付宝":
        return parse_alipay_file(filepath)
    if source == "中行":
        return parse_bank_file(filepath)
    raise ValueError(f"不支持的账单来源: {source}")


def scan_statement_files() -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for source, directory in SOURCE_DIRS.items():
        if not directory.is_dir():
            continue
        for filepath in sorted(directory.glob("*.pdf")):
            files.append((source, filepath.resolve()))
    return files
