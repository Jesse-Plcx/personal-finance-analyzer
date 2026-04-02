from __future__ import annotations

from _bootstrap import ROOT_DIR, amount_text, direction_text  # noqa: F401
from finance_core import build_report_data, connect_db, load_transactions


def main() -> None:
    conn = connect_db()
    report = build_report_data(load_transactions(conn))
    summary = report["summary"]

    print("=== SUMMARY ===")
    print(f"总{direction_text('收入')}: {amount_text(summary['total_income'], '收入')}  ({summary['n_income']} 笔)")
    print(f"总{direction_text('支出')}: {amount_text(summary['total_expense'], '支出')}  ({summary['n_expense']} 笔)")
    print(f"净收支: {amount_text(summary['net'])}")
    print(f"总交易: {summary['n_total']} 笔")
    print(f"月均收入: {amount_text(summary['avg_monthly_income'], '收入')}")
    print(f"月均支出: {amount_text(summary['avg_monthly_expense'], '支出')}")

    print("\n=== BY YEAR ===")
    for year, data in sorted(report["year_data"].items()):
        print(
            f"{year}: 收入 {amount_text(data['income'], '收入')}({data['n_income']}) | "
            f"支出 {amount_text(data['expense'], '支出')}({data['n_expense']}) | "
            f"净额 {amount_text(data['income'] - data['expense'])}"
        )

    print("\n=== TOP5 INCOME ===")
    for tx in report["top5_income"]:
        print(f"  {tx['year']}-{tx['month']:02d}  {tx['source']}  {amount_text(tx['amount'], '收入')}  {tx['counterparty']}")

    print("\n=== TOP5 EXPENSE ===")
    for tx in report["top5_expense"]:
        print(f"  {tx['year']}-{tx['month']:02d}  {tx['source']}  {amount_text(tx['amount'], '支出')}  {tx['counterparty']}")

    print("\n=== BANK-ONLY source (中行) ===")
    for year, sources in sorted(report["year_source_data"].items()):
        bank = sources.get("中行", {})
        if bank.get("n_income", 0) + bank.get("n_expense", 0) == 0:
            continue
        print(
            f"  {year}: 收入 {amount_text(bank['income'], '收入')}({bank['n_income']}) | "
            f"支出 {amount_text(bank['expense'], '支出')}({bank['n_expense']})"
        )

    print("\n=== EXPENSE CATEGORIES ===")
    for category, data in report["expense_categories"].items():
        pct = data["amount"] / summary["total_expense"] * 100 if summary["total_expense"] else 0
        print(f"  {category}: {amount_text(data['amount'], '支出')} ({data['count']}笔) {pct:.1f}%")
    conn.close()


if __name__ == "__main__":
    main()
