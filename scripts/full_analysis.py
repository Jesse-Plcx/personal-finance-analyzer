from __future__ import annotations

from pathlib import Path

from _bootstrap import ROOT_DIR, amount_text, direction_text  # noqa: F401
from finance_core import ANALYSIS_JSON_PATH, DB_PATH, connect_db, export_analysis_json, import_workspace


def main() -> None:
    conn = connect_db()
    result = import_workspace(conn)
    report_data = export_analysis_json(conn)

    print("账单导入结果")
    for item in result.file_results:
        file_name = Path(item.path).name
        print(
            f"  [{item.source}] {file_name}: {item.raw_count} 条 {item.status}, "
            f"{item.canonical_count} 条进入主交易表, 去重 {item.deduped_count} 条"
        )

    if result.removed_files:
        print("\n已从数据库移除不存在的源文件")
        for file_path in result.removed_files:
            print(f"  {file_path}")

    summary = report_data["summary"]
    print("\n总体汇总")
    print(f"  总{direction_text('收入')}: {amount_text(summary['total_income'], '收入')} ({summary['n_income']} 笔)")
    print(f"  总{direction_text('支出')}: {amount_text(summary['total_expense'], '支出')} ({summary['n_expense']} 笔)")
    print(f"  不计收支: ¥{summary['total_other']:,.2f} ({summary['n_other']} 笔)")
    print(f"  净收支: {amount_text(summary['net'])}")
    print(f"  原始记录数: {result.total_occurrences}")
    print(f"  去重后记录数: {result.total_transactions}")
    print(f"  查重移除数: {result.total_duplicates}")

    print("\n年度汇总")
    for year, data in sorted(report_data["year_data"].items()):
        print(
            f"  {year}: 收入 {amount_text(data['income'], '收入')}({data['n_income']}笔) | "
            f"支出 {amount_text(data['expense'], '支出')}({data['n_expense']}笔) | "
            f"净额 {amount_text(data['income'] - data['expense'])}"
        )

    print(f"\n数据库已更新: {DB_PATH}")
    print(f"分析 JSON 已更新: {ANALYSIS_JSON_PATH}")
    conn.close()


if __name__ == "__main__":
    main()
