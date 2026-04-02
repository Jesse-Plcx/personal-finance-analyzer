# 个人财务账单分析框架（自用）

一个基于 PDF 账单解析、SQLite 聚合和命令行报表的个人财务分析项目骨架。

这个公开版本只保留核心架构、解析逻辑和常用脚本入口，不包含任何真实账单、数据库、导出结果或个人分析报告。

## 适合做什么

- 解析微信、支付宝和银行账单 PDF
- 把多来源交易导入本地 SQLite 数据库
- 做去重、分类、汇总和按月统计
- 通过命令行脚本查询交易和生成分析结果

## 项目结构

```text
.
├── README.md
├── requirements.txt
├── finance_core/
│   ├── config.py
│   ├── parsers.py
│   ├── categories.py
│   ├── database.py
│   ├── reports.py
│   └── utils.py
├── scripts/
│   ├── full_analysis.py
│   ├── dump_summary.py
│   ├── month_summary.py
│   ├── query_transactions.py
│   ├── check_dedup.py
│   └── inspect_bank.py
├── data/
│   ├── raw/
│   │   ├── 微信/
│   │   ├── 支付宝/
│   │   └── 中行/
│   └── generated/
└── docs/
    ├── reports/
    └── notes/
```

## 快速开始

### 1. 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 2. 准备本地账单

把你自己的 PDF 账单放到以下目录：

- `data/raw/微信/`
- `data/raw/支付宝/`
- `data/raw/中行/`

账单原件 / 电子账单可通过微信、支付宝、银行 App 的相关渠道申请获得。

。

### 3. 运行全量导入与分析

```bash
python scripts/full_analysis.py
```

这个脚本会：

- 扫描 `data/raw/`
- 解析账单并导入 `data/generated/finance.db`
- 更新 `data/generated/analysis_data.json`

## 常用脚本

```bash
python scripts/dump_summary.py
python scripts/month_summary.py --year 2026 --month 3
python scripts/query_transactions.py --year 2026 --direction 支出 --group-by category
python scripts/check_dedup.py
python scripts/query_transactions.py --counterparty 美团 --group-by year
python scripts/query_transactions.py --category 餐饮美食 --group-by month
python scripts/query_transactions.py --refund-only --year 2026
```

## 架构说明

### `finance_core/`

- `parsers.py`：按来源解析 PDF 账单
- `database.py`：导入、去重、SQLite 存储
- `reports.py`：汇总与 JSON 导出
- `categories.py`：交易分类规则
- `config.py`：目录与文件路径配置

### `scripts/`

面向日常使用的命令行入口，尽量把核心逻辑保持在 `finance_core/` 中，方便后续继续扩展。
