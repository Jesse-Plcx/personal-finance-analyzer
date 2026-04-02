from __future__ import annotations

import argparse

from _bootstrap import ROOT_DIR, amount_text, direction_text  # noqa: F401
from finance_core import connect_db

GROUP_FIELDS = {
    "year": "CAST(year AS TEXT)",
    "month": "printf('%04d-%02d', year, month)",
    "source": "source",
    "direction": "direction",
    "category": "category",
    "counterparty": "counterparty",
    "pay_method": "pay_method",
}


def build_filters(args: argparse.Namespace) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []

    if args.year:
        clauses.append("year = ?")
        params.append(args.year)
    if args.month:
        clauses.append("month = ?")
        params.append(args.month)
    if args.source:
        clauses.append("source = ?")
        params.append(args.source)
    if args.direction:
        clauses.append("direction = ?")
        params.append(args.direction)
    if args.category:
        clauses.append("category = ?")
        params.append(args.category)
    if args.counterparty:
        clauses.append("counterparty LIKE ?")
        params.append(f"%{args.counterparty}%")
    if args.keyword:
        clauses.append("(tx_type LIKE ? OR counterparty LIKE ? OR pay_method LIKE ?)")
        params.extend([f"%{args.keyword}%"] * 3)
    if args.refund_only:
        clauses.append("direction = '支出'")
        clauses.append("amount < 0")

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def print_grouped(conn, args: argparse.Namespace) -> None:
    group_expr = GROUP_FIELDS[args.group_by]
    where_sql, params = build_filters(args)
    rows = conn.execute(
        f"""
        SELECT
            {group_expr} AS group_key,
            COUNT(*) AS tx_count,
            SUM(CASE WHEN direction = '收入' THEN amount ELSE 0 END) AS income,
            SUM(CASE WHEN direction = '支出' THEN amount ELSE 0 END) AS expense,
            SUM(CASE WHEN direction NOT IN ('收入', '支出') THEN amount ELSE 0 END) AS other
        FROM transactions
        {where_sql}
        GROUP BY {group_expr}
        ORDER BY expense DESC, income DESC, group_key
        """,
        params,
    ).fetchall()

    print(f"按 {args.group_by} 汇总，共 {len(rows)} 组")
    for row in rows:
        print(
            f"{row['group_key']}: 收入 {amount_text(row['income'], '收入')} | "
            f"支出 {amount_text(row['expense'], '支出')} | 其他 ¥{row['other']:,.2f} | "
            f"笔数 {row['tx_count']}"
        )


def print_transactions(conn, args: argparse.Namespace) -> None:
    where_sql, params = build_filters(args)
    rows = conn.execute(
        f"""
        SELECT
            occurred_at,
            source,
            direction,
            amount,
            category,
            counterparty,
            tx_type,
            pay_method,
            duplicate_count
        FROM transactions
        {where_sql}
        ORDER BY occurred_at DESC, id DESC
        LIMIT ?
        """,
        (*params, args.limit),
    ).fetchall()

    totals = conn.execute(
        f"""
        SELECT
            COUNT(*) AS tx_count,
            SUM(CASE WHEN direction = '收入' THEN amount ELSE 0 END) AS income,
            SUM(CASE WHEN direction = '支出' THEN amount ELSE 0 END) AS expense,
            SUM(CASE WHEN direction NOT IN ('收入', '支出') THEN amount ELSE 0 END) AS other
        FROM transactions
        {where_sql}
        """,
        params,
    ).fetchone()

    print(
        f"匹配 {totals['tx_count']} 笔: 收入 {amount_text(totals['income'] or 0, '收入')} | "
        f"支出 {amount_text(totals['expense'] or 0, '支出')} | 其他 ¥{totals['other'] or 0:,.2f}"
    )

    for row in rows:
        print(
            f"{row['occurred_at']} | {row['source']} | {direction_text(row['direction'])} | "
            f"{amount_text(row['amount'], row['direction'])} | {row['category']} | {row['counterparty']} | "
            f"{row['tx_type']} | {row['pay_method']} | dup={row['duplicate_count']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="按条件查询去重后的个人财务交易")
    parser.add_argument("--year", type=int, help="年份，例如 2026")
    parser.add_argument("--month", type=int, help="月份，例如 3")
    parser.add_argument("--source", choices=["微信", "支付宝", "中行"], help="来源")
    parser.add_argument("--direction", choices=["收入", "支出", "不计收支"], help="方向")
    parser.add_argument("--category", help="分类，例如 餐饮美食")
    parser.add_argument("--counterparty", help="对方关键字")
    parser.add_argument("--keyword", help="搜索交易类型、对方或支付方式")
    parser.add_argument("--refund-only", action="store_true", help="仅查看退款类交易（负支出）")
    parser.add_argument("--group-by", choices=sorted(GROUP_FIELDS), help="按字段聚合汇总")
    parser.add_argument("--limit", type=int, default=30, help="明细模式下展示多少笔")
    args = parser.parse_args()

    conn = connect_db()
    if args.group_by:
        print_grouped(conn, args)
    else:
        print_transactions(conn, args)
    conn.close()


if __name__ == "__main__":
    main()
