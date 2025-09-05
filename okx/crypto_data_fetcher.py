"""
加密货币数据获取器 - 支持下载进度和中断
"""
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from tqdm import tqdm

from optimized_config import (
    OKX_CONFIG, SUPPORTED_PAIRS, TIMEFRAMES,
    DATA_DIR, LOG_CONFIG, get_legacy_data_path, validate_symbol
)

# =========================
# 日志初始化（轮转 + 控制台）
# =========================
log_file = LOG_CONFIG.get("file", DATA_DIR / "crypto_data.log")
if isinstance(log_file, Path):
    log_file = str(log_file)

max_bytes = LOG_CONFIG.get("max_size_mb", 10) * 1024 * 1024
backup_count = LOG_CONFIG.get("backup_count", 5)

file_handler = RotatingFileHandler(
    filename=log_file,
    maxBytes=max_bytes,
    backupCount=backup_count,
    encoding="utf-8"
)
console_handler = logging.StreamHandler()

formatter = logging.Formatter(LOG_CONFIG.get(
    "format",
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(LOG_CONFIG.get("level", "INFO"))

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

logger.info("✅ 日志初始化完成（支持轮转 + 控制台输出）")

# =========================
# CryptoDataFetcher
# =========================
class CryptoDataFetcher:
    """加密货币数据获取器"""

    def __init__(self):
        self.base_url = OKX_CONFIG['base_url']
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })

    def _make_request(self, symbol: str, limit: int = 300, after: int = None):
        url = self.base_url + OKX_CONFIG['endpoints']['history_candles']
        params = {"instId": symbol, "bar": "5m", "limit": limit}
        if after:
            params["after"] = after
        try:
            resp = self.session.get(url, params=params, timeout=OKX_CONFIG['timeout'])
            resp.raise_for_status()
            data = resp.json()
            if 'data' not in data:
                logger.error(f"API返回格式异常: {data}")
                return None
            return data['data']
        except Exception as e:
            logger.error(f"请求失败 [{symbol}]: {e}")
            return None

    def _process_raw_data(self, raw_data):
        if not raw_data:
            return pd.DataFrame()
        df = pd.DataFrame(raw_data, columns=[
            'ts','o','h','l','c','vol','volCcy','volCcyQuote','confirm'
        ])
        df = df.rename(columns={
            'ts': 'timestamp', 'o':'open','h':'high','l':'low','c':'close',
            'vol':'volume','volCcy':'volume_currency','volCcyQuote':'volume_quote','confirm':'confirm'
        })
        for col in ['open','high','low','close','volume','volume_currency','volume_quote']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=8)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        df = df[~df.index.duplicated(keep='first')]
        return df

    def fetch_batch_data(self, symbol: str, months: int = 6):
        """按批次获取历史数据，显示下载进度并支持中断"""
        if not validate_symbol(symbol):
            logger.error(f"不支持的交易对: {symbol}")
            return None

        end_time = datetime.now()
        start_time = end_time - timedelta(days=30*months)

        batch_minutes = 5 * 300  # 每批最大 300 条 5 分钟数据
        total_batches = ((end_time - start_time).total_seconds() / 60) // batch_minutes + 1

        all_data = []
        current_end_time = end_time

        try:
            with tqdm(total=int(total_batches), desc=f"{symbol} 下载进度") as pbar:
                while current_end_time > start_time:
                    end_ts = int(current_end_time.timestamp() * 1000)
                    batch = self._make_request(symbol, after=end_ts)
                    if not batch:
                        break
                    all_data.extend(batch)
                    last_ts = int(batch[-1][0])
                    current_end_time = datetime.fromtimestamp(last_ts / 1000)
                    time.sleep(OKX_CONFIG['rate_limit'])

                    pbar.update(1)
                    pbar.set_postfix({'已下载条数': len(all_data)})
        except KeyboardInterrupt:
            logger.warning("⚠️ 用户中断下载")
            print("\n下载已中断，部分数据已获取。")

        if not all_data:
            logger.error("未获取到任何数据")
            return None

        df = self._process_raw_data(all_data)
        df = df[df.index >= start_time + pd.Timedelta(hours=8)]
        return df

    def save_data(self, df: pd.DataFrame, symbol: str):
        file_path = get_legacy_data_path(symbol)
        try:
            df.to_parquet(file_path, index=True)
            logger.info(f"数据已保存: {file_path}, 条数: {len(df)}")
            return True
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return False

    def fetch_and_save(self, symbol: str, months: int = 6):
        df = self.fetch_batch_data(symbol, months)
        if df is None or df.empty:
            return False
        return self.save_data(df, symbol)

    def fetch_multiple_symbols(self, symbols: list, months: int = 6):
        results = {}
        for sym in symbols:
            results[sym] = self.fetch_and_save(sym, months)
            time.sleep(1)
        return results
