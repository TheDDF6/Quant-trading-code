"""
crypto_data_updater.py - 加密货币数据更新器
"""

import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging

# ---------------- 配置 ----------------
DATA_DIR = Path(r"D:\VSC\crypto_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

OKX_CONFIG = {
    "base_url": "https://www.okx.com/api/v5/market/",
    "endpoints": {"candles": "candles"},
    "timeout": 10,
    "rate_limit": 0.2,  # 秒
}

COLUMN_MAPPING = {
    0: "timestamp",
    1: "open",
    2: "high",
    3: "low",
    4: "close",
    5: "volume",
    6: "volume_currency",
    7: "volume_quote"
}

DTYPE_CONFIG = {
    "open": float,
    "high": float,
    "low": float,
    "close": float,
    "volume": float,
    "volume_currency": float,
    "volume_quote": float,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_data_file_path(symbol: str) -> Path:
    return DATA_DIR / f"{symbol}_5m.parquet"


def validate_symbol(symbol: str) -> bool:
    # 这里简单校验
    return "-" in symbol


class CryptoDataUpdater:
    """加密货币数据更新器"""

    def __init__(self):
        self.base_url = OKX_CONFIG["base_url"]
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0"
        })

    def load_existing_data(self, symbol: str) -> pd.DataFrame:
        file_path = get_data_file_path(symbol)
        if not file_path.exists():
            logger.info(f"{symbol} 本地数据不存在: {file_path}")
            return pd.DataFrame()
        try:
            df = pd.read_parquet(file_path)
            if "timestamp" not in df.columns:
                logger.error(f"{symbol} 文件缺少 'timestamp' 列")
                return pd.DataFrame()
            # 转为 datetime, UTC
            df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"], errors="coerce"), unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)
            return df
        except Exception as e:
            logger.error(f"{symbol} 读取失败: {e}")
            return pd.DataFrame()

    def get_latest_timestamp(self, symbol: str) -> pd.Timestamp:
        df = self.load_existing_data(symbol)
        if df.empty:
            return None
        return df.index.max()

    def _make_request(self, symbol: str, limit: int = 300, before: int = None) -> list:
        url = self.base_url + OKX_CONFIG["endpoints"]["candles"]
        params = {"instId": symbol, "bar": "5m", "limit": limit}
        if before:
            params["before"] = before
        try:
            resp = self.session.get(url, params=params, timeout=OKX_CONFIG["timeout"])
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"{symbol} 请求失败: {e}")
            return []

    def _process_raw_data(self, raw_data: list) -> pd.DataFrame:
        if not raw_data:
            return pd.DataFrame()
        df = pd.DataFrame(raw_data)
        df = df.rename(columns=COLUMN_MAPPING)
        for col in ["open", "high", "low", "close", "volume", "volume_currency", "volume_quote"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"], errors="coerce"), unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)
        df = df[~df.index.duplicated(keep="first")]
        return df

    def fetch_missing_data(self, symbol: str, from_time: pd.Timestamp) -> pd.DataFrame:
        logger.info(f"开始获取 {symbol} 从 {from_time} 到现在的新数据...")
        all_data = []
        before_ts = int(datetime.utcnow().timestamp() * 1000)
        while True:
            batch = self._make_request(symbol, before=before_ts)
            if not batch:
                break
            df_batch = self._process_raw_data(batch)
            # 过滤新数据
            df_batch = df_batch[df_batch.index > from_time]
            if df_batch.empty:
                break
            all_data.append(df_batch)
            before_ts = int(df_batch.index.min().timestamp() * 1000)
            time.sleep(OKX_CONFIG["rate_limit"])
        if all_data:
            df_all = pd.concat(all_data)
            df_all = df_all[~df_all.index.duplicated(keep="last")]
            logger.info(f"{symbol} 新增 {len(df_all)} 条数据")
            return df_all
        return pd.DataFrame()

    def update_data(self, symbol: str) -> bool:
        if not validate_symbol(symbol):
            logger.error(f"{symbol} 非法交易对")
            return False
        df_existing = self.load_existing_data(symbol)
        latest_time = df_existing.index.max() if not df_existing.empty else None
        if latest_time is None:
            logger.info(f"{symbol} 无本地数据，将全量拉取")
            latest_time = pd.Timestamp(datetime(2020, 1, 1), tz="UTC")
        new_data = self.fetch_missing_data(symbol, latest_time)
        if new_data.empty:
            logger.info(f"{symbol} 无新数据需要更新")
            return True
        df_combined = pd.concat([df_existing, new_data])
        df_combined = df_combined[~df_combined.index.duplicated(keep="last")]
        df_combined.sort_index(inplace=True)
        # 保存
        file_path = get_data_file_path(symbol)
        for col, dtype in DTYPE_CONFIG.items():
            if col in df_combined.columns:
                df_combined[col] = df_combined[col].astype(dtype)
        df_combined.to_parquet(file_path)
        logger.info(f"{symbol} 数据已保存: {file_path}, 共 {len(df_combined)} 行")
        return True

    def update_multiple_symbols(self, symbols: list) -> dict:
        results = {}
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"[{i}/{len(symbols)}] 更新 {symbol}")
            success = self.update_data(symbol)
            results[symbol] = success
        logger.info(f"批量更新完成: {sum(results.values())}/{len(symbols)} 成功")
        return results

    def get_data_status(self, symbol: str) -> dict:
        df = self.load_existing_data(symbol)
        if df.empty:
            return {"symbol": symbol, "status": "无数据"}
        latest_time = df.index.max()
        time_diff = datetime.utcnow().replace(tzinfo=None) - latest_time.to_pydatetime().replace(tzinfo=None)
        needs_update = time_diff > timedelta(minutes=5)
        return {
            "symbol": symbol,
            "status": "正常",
            "latest_time": str(latest_time),
            "time_diff": str(time_diff),
            "needs_update": needs_update,
            "total_rows": len(df)
        }
