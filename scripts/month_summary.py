from __future__ import annotations

import argparse
from collections import defaultdict

from _bootstrap import ROOT_DIR, amount_text, direction_text  # noqa: F401
from finance_core import connect_db, load_transactions


def main() -> None:
    parser = argparse.ArgumentParser(description="查看某个月的收入、支出和分类概览")
    parser.add_argument("--year", type=int, help="年份，例如 2026")
    parser.add_argument("--month", type=int, help="月份，例如 3")
    args = parser.parse_args()

    conn = connect_db()
    transactions = load_transactions(conn)
    valid_months = sorted({(tx["year"], tx["month"]) for tx in transactions})
    if not valid_months:
        print("数据库里还没有交易数据")
        return

    year, month = (args.year, args.month) if args.year and args.month else valid_months[-1]
    month_txs = [tx for tx in transactions if tx["year"] == year and tx["month"] == month]
    income_txs = [tx for tx in month_txs if tx["direction"] == "收入"]
    expense_txs = [tx for tx in month_txs if tx["direction"] == "支出"]
    other_txs = [tx for tx in month_txs if tx["direction"] not in ("收入", "支出")]
    refund_txs = [tx for tx in expense_txs if tx["amount"] < 0]
    gross_expense_txs = [tx for tx in expense_txs if tx["amount"] > 0]

    total_income = sum(tx["amount"] for tx in income_txs)
    total_expense = sum(tx["amount"] for tx in expense_txs)
    gross_expense = sum(tx["amount"] for tx in gross_expense_txs)
    total_refund = sum(tx["amount"] for tx in refund_txs)
    total_other = sum(tx["amount"] for tx in other_txs)

    print(f"=== {year}-{month:02d} ===")
    print(f"{direction_text('收入')}: {amount_text(total_income, '收入')} ({len(income_txs)} 笔)")
    print(f"含退款前的原始支出: {amount_text(gross_expense, '支出')} ({len(gross_expense_txs)} 笔)")
    print(f"退款合计: {amount_text(abs(total_refund), '收入')} ({len(refund_txs)} 笔)")
    print(f"扣除退款后的实际支出: {amount_text(total_expense, '支出')} ({len(expense_txs)} 笔, 含退款负值)")
    print(f"不计收支: ¥{total_other:,.2f} ({len(other_txs)} 笔)")
    print(f"净额: {amount_text(total_income - total_expense)}")

    categories = defaultdict(float)
    for tx in expense_txs:
        categories[tx["category"]] += tx["amount"]

    print("\n支出分类（按扣除退款后的实际支出口径）:")
    for category, amount in sorted(categories.items(), key=lambda item: item[1], reverse=True):
        pct = amount / total_expense * 100 if total_expense else 0
        print(f"  {category}: {amount_text(amount, '支出')} ({pct:.1f}%)")

    print("\nTop 10 原始支出:")
    for tx in sorted(gross_expense_txs, key=lambda item: item["amount"], reverse=True)[:10]:
        print(f"  {tx['full_dt']} | {amount_text(tx['amount'], '支出')} | {tx['counterparty']} | {tx['type']}")

    print("\nTop 5 收入:")
    for tx in sorted(income_txs, key=lambda item: item["amount"], reverse=True)[:5]:
        print(f"  {tx['full_dt']} | {amount_text(tx['amount'], '收入')} | {tx['counterparty']} | {tx['type']}")

    if refund_txs:
        print("\n退款明细:")
        for tx in sorted(refund_txs, key=lambda item: item["full_dt"], reverse=True):
            print(f"  {tx['full_dt']} | {amount_text(abs(tx['amount']), '收入')} | {tx['source']} | {tx['counterparty']} | {tx['type']}")
    conn.close()


if __name__ == "__main__":
    main()
