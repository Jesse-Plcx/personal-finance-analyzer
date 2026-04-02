from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
GENERATED_DATA_DIR = DATA_DIR / "generated"
DOCS_DIR = BASE_DIR / "docs"

SOURCE_DIRS = {
    "微信": RAW_DATA_DIR / "微信",
    "支付宝": RAW_DATA_DIR / "支付宝",
    "中行": RAW_DATA_DIR / "中行",
}

DB_PATH = GENERATED_DATA_DIR / "finance.db"
ANALYSIS_JSON_PATH = GENERATED_DATA_DIR / "analysis_data.json"
LEGACY_CACHE_PATH = GENERATED_DATA_DIR / "parsed_cache.json"

PARSER_VERSION = "2026-04-01-v1"
