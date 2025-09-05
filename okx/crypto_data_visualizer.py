"""
CryptoDataVisualizer - 加密货币数据可视化器 (英文 K 线, MA/RSI/ATR 支持)
"""

import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime, timedelta
import logging
import numpy as np
from pathlib import Path
from typing import Optional

from crypto_config import (
    get_data_file_path, validate_symbol, validate_timeframe,
    get_resample_rule, CHART_CONFIG, LOG_CONFIG
)

# 配置日志
logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(__name__)

class CryptoDataVisualizer:
    """Cryptocurrency data visualizer"""

    def __init__(self):
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False

    def load_data(self, symbol: str, timeframe: str = '5m') -> Optional[pd.DataFrame]:
        if not validate_symbol(symbol):
            logger.error(f"Unsupported pair: {symbol}")
            return None
        file_path = get_data_file_path(symbol, '5m')  # always load 5m base data
        if not Path(file_path).exists():
            logger.error(f"Data file not found: {file_path}")
            return None
        try:
            df = pd.read_parquet(file_path)
            if 'timestamp' in df.columns:
                df.index = pd.to_datetime(df['timestamp'])
            else:
                df.index = pd.to_datetime(df.index)
            return df
        except Exception as e:
            logger.error(f"Failed to read data: {e}")
            return None

    def resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        if timeframe == '5m':
            return df
        if not validate_timeframe(timeframe):
            logger.error(f"Unsupported timeframe: {timeframe}")
            return df
        rule = get_resample_rule(timeframe)
        try:
            resampled = df.resample(rule).agg({
                'open': 'first',
                'high': 'max', 
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            return resampled
        except Exception as e:
            logger.error(f"Resample failed: {e}")
            return df

    def load_and_resample(self, symbol: str, timeframe: str = '5m', 
                         start: Optional[str] = None, end: Optional[str] = None) -> Optional[pd.DataFrame]:
        df = self.load_data(symbol)
        if df is None:
            return None
        if start:
            start_time = pd.to_datetime(start)
            df = df[df.index >= start_time]
        if end:
            end_time = pd.to_datetime(end)
            df = df[df.index <= end_time]
        df = self.resample_data(df, timeframe)
        return df

    def calculate_ma(self, df: pd.DataFrame, periods: list) -> pd.DataFrame:
        df_ma = df.copy()
        for period in periods:
            if len(df) >= period:
                df_ma[f'ma{period}'] = df['close'].rolling(window=period).mean()
        return df_ma

    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> Optional[pd.Series]:
        if len(df) < period:
            return None
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Optional[pd.Series]:
        if len(df) < period:
            return None
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr

    def plot_candlestick(self, symbol: str, timeframe: str = '5m', 
                         start: Optional[str] = None, end: Optional[str] = None,
                         show_ma: bool = True, show_rsi: bool = False, show_atr: bool = False) -> bool:
        df = self.load_and_resample(symbol, timeframe, start, end)
        if df is None or df.empty:
            return False

        plot_data = df[['open', 'high', 'low', 'close', 'volume']].copy()
        plot_data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

        addplot_list = []

        # MA lines
        if show_ma:
            ma_periods = [20, 50, 200]
            colors = ['green', 'red', 'purple']
            df_ma = self.calculate_ma(df, ma_periods)
            for i, period in enumerate(ma_periods):
                col_name = f'ma{period}'
                if col_name in df_ma.columns:
                    addplot_list.append(
                        mpf.make_addplot(df_ma[col_name], color=colors[i], width=1.2)
                    )

        # RSI panel
        if show_rsi:
            rsi = self.calculate_rsi(df)
            if rsi is not None:
                addplot_list.append(
                    mpf.make_addplot(rsi, panel=1, color='blue', ylabel='RSI', ylim=(0,100))
                )

        # ATR panel
        if show_atr:
            atr = self.calculate_atr(df)
            if atr is not None:
                panel_index = 2 if show_rsi else 1
                addplot_list.append(
                    mpf.make_addplot(atr, panel=panel_index, color='orange', ylabel='ATR')
                )

        mc = mpf.make_marketcolors(up='green', down='red', volume='grey', edge='inherit')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='-', facecolor='white')

        # 主图比例3，副图比例1（Volume自动）、RSI/ATR各1
        panel_ratios = [3]
        if show_rsi:
            panel_ratios.append(1)
        if show_atr:
            panel_ratios.append(1)

        title = f"{symbol} {timeframe.upper()} Candlestick Chart | {len(plot_data)} bars"
        mpf.plot(plot_data,
                 type='candle',
                 style=s,
                 addplot=addplot_list if addplot_list else None,
                 volume=True,
                 title=title,
                 figsize=CHART_CONFIG['figsize'],
                 ylabel='Price (USDT)',
                 tight_layout=True,
                 panel_ratios=panel_ratios)
        plt.show()
        return True

    def plot_price_comparison(self, symbols: list, timeframe: str = '1d', days: int = 30, normalize: bool = True) -> bool:
        plt.figure(figsize=CHART_CONFIG['figsize'])
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime('%Y-%m-%d')
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']

        for i, symbol in enumerate(symbols):
            df = self.load_and_resample(symbol, timeframe, start=start_str)
            if df is None or df.empty:
                continue
            close_prices = df['close']
            if normalize:
                close_prices = (close_prices / close_prices.iloc[0]) * 100
            plt.plot(close_prices.index, close_prices, label=symbol, color=colors[i % len(colors)], linewidth=2)

        plt.title(f"Cryptocurrency Price Comparison - {timeframe.upper()} ({days} days)")
        plt.xlabel('Date')
        plt.ylabel('Normalized Price (Start=100)' if normalize else 'Price (USDT)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
        return True

    def get_data_summary(self, symbol: str, timeframe: str = '5m') -> Optional[dict]:
        df = self.load_and_resample(symbol, timeframe)
        if df is None:
            return None
        latest_price = df['close'].iloc[-1]
        price_change_24h = ((latest_price - df['close'].iloc[-288]) / df['close'].iloc[-288] * 100
                            if len(df) >= 288 else 0)
        summary = {
            'symbol': symbol,
            'timeframe': timeframe,
            'total_records': len(df),
            'date_range': {'start': df.index.min().strftime('%Y-%m-%d %H:%M:%S'),
                           'end': df.index.max().strftime('%Y-%m-%d %H:%M:%S')},
            'latest_price': latest_price,
            'price_stats': {
                'high_24h': df['high'].tail(288).max() if len(df) >= 288 else df['high'].max(),
                'low_24h': df['low'].tail(288).min() if len(df) >= 288 else df['low'].min(),
                'change_24h_pct': price_change_24h
            },
            'volume_stats': {
                'avg_volume': df['volume'].mean(),
                'total_volume_24h': df['volume'].tail(288).sum() if len(df) >= 288 else df['volume'].sum()
            }
        }
        return summary
