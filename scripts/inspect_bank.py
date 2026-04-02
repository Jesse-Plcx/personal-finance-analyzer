from __future__ import annotations

import pdfplumber

from _bootstrap import ROOT_DIR  # noqa: F401
from finance_core import SOURCE_DIRS


def main() -> None:
    bank_dir = SOURCE_DIRS["中行"]
    for path in sorted(bank_dir.glob("*.pdf")):
        print("=" * 80)
        print("FILE:", path.name)
        print("=" * 80)
        with pdfplumber.open(path) as pdf:
            for pg_num, page in enumerate(pdf.pages[:2], 1):
                print(f"\n--- Page {pg_num} (text) ---")
                text = page.extract_text() or ""
                print(text[:2000])
                print(f"\n--- Page {pg_num} (tables) ---")
                tables = page.extract_tables()
                if tables:
                    for ti, table in enumerate(tables):
                        print(f"  Table {ti}: {len(table)} rows x {len(table[0]) if table else 0} cols")
                        for row in table[:5]:
                            print("   ", row)
                else:
                    print("  (no tables extracted)")
        print()


if __name__ == "__main__":
    main()
