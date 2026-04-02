from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path

from .config import ANALYSIS_JSON_PATH


def load_transactions(conn: sqlite3.Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT
            source,
            year,
            month,
            day,
            occurred_at,
            tx_type,
            direction,
            pay_method,
            amount,
            counterparty,
            category,
            duplicate_count
        FROM transactions
        ORDER BY occurred_at, id
        """
    ).fetchall()
    return [
        {
            "source": row["source"],
            "year": row["year"],
            "month": row["month"],
            "day": row["day"],
            "full_dt": row["occurred_at"],
            "type": row["tx_type"],
            "direction": row["direction"],
            "pay_method": row["pay_method"],
            "amount": row["amount"],
            "counterparty": row["counterparty"],
            "category": row["category"],
            "duplicate_count": row["duplicate_count"],
        }
        for row in rows
    ]


def build_report_data(transactions: list[dict[str, object]]) -> dict[str, object]:
    income_txs = [tx for tx in transactions if tx["direction"] == "收入"]
    expense_txs = [tx for tx in transactions if tx["direction"] == "支出"]
    other_txs = [tx for tx in transactions if tx["direction"] not in ("收入", "支出")]

    total_income = sum(float(tx["amount"]) for tx in income_txs)
    total_expense = sum(float(tx["amount"]) for tx in expense_txs)
    total_other = sum(float(tx["amount"]) for tx in other_txs)

    years = sorted({int(tx["year"]) for tx in transactions})
    year_data: dict[int, dict[str, float | int]] = {}
    for year in years:
        yi = sum(float(tx["amount"]) for tx in income_txs if tx["year"] == year)
        ye = sum(float(tx["amount"]) for tx in expense_txs if tx["year"] == year)
        yo = sum(float(tx["amount"]) for tx in other_txs if tx["year"] == year)
        year_data[year] = {
            "income": yi,
            "expense": ye,
            "other": yo,
            "n_income": len([tx for tx in income_txs if tx["year"] == year]),
            "n_expense": len([tx for tx in expense_txs if tx["year"] == year]),
            "n_other": len([tx for tx in other_txs if tx["year"] == year]),
        }

    year_source_data: dict[str, dict[str, dict[str, float | int]]] = {}
    for year in years:
        year_source_data[str(year)] = {}
        for source in ("微信", "支付宝", "中行"):
            yi = sum(float(tx["amount"]) for tx in income_txs if tx["year"] == year and tx["source"] == source)
            ye = sum(float(tx["amount"]) for tx in expense_txs if tx["year"] == year and tx["source"] == source)
            year_source_data[str(year)][source] = {
                "income": yi,
                "expense": ye,
                "n_income": len([tx for tx in income_txs if tx["year"] == year and tx["source"] == source]),
                "n_expense": len([tx for tx in expense_txs if tx["year"] == year and tx["source"] == source]),
            }

    monthly_data = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "n_income": 0, "n_expense": 0})
    for tx in transactions:
        if tx["direction"] not in ("收入", "支出"):
            continue
        key = f"{int(tx['year']):04d}-{int(tx['month']):02d}"
        if tx["direction"] == "收入":
            monthly_data[key]["income"] += float(tx["amount"])
            monthly_data[key]["n_income"] += 1
        else:
            monthly_data[key]["expense"] += float(tx["amount"])
            monthly_data[key]["n_expense"] += 1

    expense_categories = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for tx in expense_txs:
        expense_categories[str(tx["category"])]["amount"] += float(tx["amount"])
        expense_categories[str(tx["category"])]["count"] += 1

    income_categories = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for tx in income_txs:
        income_categories[str(tx["category"])]["amount"] += float(tx["amount"])
        income_categories[str(tx["category"])]["count"] += 1

    cat_year_data = defaultdict(lambda: defaultdict(float))
    for tx in expense_txs:
        cat_year_data[str(tx["category"])][int(tx["year"])] += float(tx["amount"])

    pay_methods = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for tx in expense_txs:
        pay_method = str(tx["pay_method"] or "未知")
        pay_methods[pay_method]["amount"] += float(tx["amount"])
        pay_methods[pay_method]["count"] += 1

    cp_expense = defaultdict(float)
    for tx in expense_txs:
        cp_expense[str(tx["counterparty"])] += float(tx["amount"])

    cp_income = defaultdict(float)
    for tx in income_txs:
        cp_income[str(tx["counterparty"])] += float(tx["amount"])

    wechat_types = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "other": 0.0, "count": 0})
    for tx in transactions:
        if tx["source"] != "微信":
            continue
        key = str(tx["type"])
        wechat_types[key]["count"] += 1
        if tx["direction"] == "收入":
            wechat_types[key]["income"] += float(tx["amount"])
        elif tx["direction"] == "支出":
            wechat_types[key]["expense"] += float(tx["amount"])
        else:
            wechat_types[key]["other"] += float(tx["amount"])

    active_months = len(monthly_data)
    avg_monthly_income = total_income / active_months if active_months else 0.0
    avg_monthly_expense = total_expense / active_months if active_months else 0.0
    avg_income_per_tx = total_income / len(income_txs) if income_txs else 0.0
    avg_expense_per_tx = total_expense / len(expense_txs) if expense_txs else 0.0

    max_income_month = max(monthly_data.items(), key=lambda item: item[1]["income"]) if monthly_data else ("", {"income": 0.0})
    max_expense_month = max(monthly_data.items(), key=lambda item: item[1]["expense"]) if monthly_data else ("", {"expense": 0.0})

    yoy_growth: dict[str, dict[str, float]] = {}
    prev_income = None
    prev_expense = None
    for year in years:
        income = year_data[year]["income"]
        expense = year_data[year]["expense"]
        if prev_income is not None and prev_income > 0:
            yoy_growth[str(year)] = {
                "income_growth": (income - prev_income) / prev_income * 100,
                "expense_growth": (expense - prev_expense) / prev_expense * 100 if prev_expense else 0.0,
            }
        prev_income = income
        prev_expense = expense

    return {
        "summary": {
            "total_income": total_income,
            "total_expense": total_expense,
            "total_other": total_other,
            "net": total_income - total_expense,
            "n_income": len(income_txs),
            "n_expense": len(expense_txs),
            "n_other": len(other_txs),
            "n_total": len(transactions),
            "active_months": active_months,
            "avg_monthly_income": avg_monthly_income,
            "avg_monthly_expense": avg_monthly_expense,
            "savings_rate": (total_income - total_expense) / total_income * 100 if total_income else 0.0,
            "income_expense_ratio": total_income / total_expense if total_expense else 0.0,
            "avg_income_per_tx": avg_income_per_tx,
            "avg_expense_per_tx": avg_expense_per_tx,
        },
        "year_data": {str(year): data for year, data in year_data.items()},
        "year_source_data": year_source_data,
        "monthly_data": {key: monthly_data[key] for key in sorted(monthly_data)},
        "expense_categories": {
            key: value for key, value in sorted(expense_categories.items(), key=lambda item: item[1]["amount"], reverse=True)
        },
        "income_categories": {
            key: value for key, value in sorted(income_categories.items(), key=lambda item: item[1]["amount"], reverse=True)
        },
        "cat_year_data": {
            category: {str(year): amount for year, amount in year_amounts.items()}
            for category, year_amounts in cat_year_data.items()
        },
        "pay_methods": dict(pay_methods),
        "top_expense_counterparties": [
            (counterparty, amount) for counterparty, amount in sorted(cp_expense.items(), key=lambda item: item[1], reverse=True)[:20]
        ],
        "top_income_counterparties": [
            (counterparty, amount) for counterparty, amount in sorted(cp_income.items(), key=lambda item: item[1], reverse=True)[:20]
        ],
        "years": years,
        "max_income_month": max_income_month[0],
        "max_income_month_amount": max_income_month[1]["income"],
        "max_expense_month": max_expense_month[0],
        "max_expense_month_amount": max_expense_month[1]["expense"],
        "top5_income": [
            {
                "amount": tx["amount"],
                "year": tx["year"],
                "month": tx["month"],
                "source": tx["source"],
                "counterparty": tx["counterparty"],
                "type": tx["type"],
            }
            for tx in sorted(income_txs, key=lambda item: float(item["amount"]), reverse=True)[:5]
        ],
        "top5_expense": [
            {
                "amount": tx["amount"],
                "year": tx["year"],
                "month": tx["month"],
                "source": tx["source"],
                "counterparty": tx["counterparty"],
                "type": tx["type"],
            }
            for tx in sorted(expense_txs, key=lambda item: float(item["amount"]), reverse=True)[:5]
        ],
        "wechat_types": {
            key: value for key, value in sorted(wechat_types.items(), key=lambda item: item[1]["count"], reverse=True)
        },
        "yoy_growth": yoy_growth,
    }


def export_analysis_json(
    conn: sqlite3.Connection,
    output_path: Path | str = ANALYSIS_JSON_PATH,
) -> dict[str, object]:
    data = build_report_data(load_transactions(conn))
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
