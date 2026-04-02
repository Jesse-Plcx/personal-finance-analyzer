from __future__ import annotations

import argparse

from _bootstrap import ROOT_DIR  # noqa: F401
from finance_core import connect_db, fetch_duplicate_groups


def main() -> None:
    parser = argparse.ArgumentParser(description="查看数据库中的重复交易分组")
    parser.add_argument("--source", choices=["微信", "支付宝", "中行"], help="仅查看某个来源")
    parser.add_argument("--limit", type=int, default=50, help="最多展示多少组重复交易")
    args = parser.parse_args()

    conn = connect_db()
    duplicates = fetch_duplicate_groups(conn, source=args.source, limit=args.limit)

    print(f"共发现 {len(duplicates)} 组重复交易")
    if not duplicates:
        return

    for row in duplicates:
        print(
            f"\n时间: {row['occurred_at']}  金额: ¥{row['amount']:,.2f}  "
            f"方向: {row['direction']}  对方: {row['counterparty']}"
        )
        print(f"类型: {row['tx_type']}")
        print(f"重复次数: {row['duplicate_count']}")
        print("涉及文件:")
        for file_path in str(row["file_paths"]).split(" || "):
            print(f"  {file_path}")
    conn.close()


if __name__ == "__main__":
    main()
