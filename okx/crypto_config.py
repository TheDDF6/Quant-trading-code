"""
加密货币数据管理系统 - 配置文件
"""
import os
from pathlib import Path

# =========================
# 基础配置
# =========================

# 数据存储路径
DATA_DIR = Path("crypto_data")
DATA_DIR.mkdir(exist_ok=True)

# 支持的交易对
SUPPORTED_PAIRS = [
    "BTC-USDT", "ETH-USDT", "BNB-USDT", "ADA-USDT", "XRP-USDT",
    "SOL-USDT", "DOGE-USDT", "MATIC-USDT", "DOT-USDT", "AVAX-USDT",
    "LINK-USDT", "UNI-USDT", "LTC-USDT", "BCH-USDT", "ATOM-USDT"
]

# 支持的时间周期
TIMEFRAMES = {
    '5m': '5T',    # 5分钟
    '15m': '15T',  # 15分钟  
    '1h': '1H',    # 1小时
    '4h': '4H',    # 4小时
    '1d': '1D'     # 1天
}

# 基础时间周期（用于数据获取）
BASE_TIMEFRAME = '5m'

# =========================
# API配置
# =========================

# OKX API配置
OKX_CONFIG = {
    'base_url': 'https://www.okx.com/api/v5',
    'endpoints': {
        'history_candles': '/market/history-candles',
        'candles': '/market/candles'
    },
    'rate_limit': 0.2,  # 请求间隔（秒）
    'timeout': 15,      # 请求超时（秒）
    'max_limit': 300    # 单次最大请求数量
}

# =========================
# 数据配置
# =========================

# Parquet文件配置
PARQUET_CONFIG = {
    'compression': 'snappy',  # 压缩算法
    'index': True,           # 保存索引
}

# 数据列名映射
COLUMN_MAPPING = {
    'ts': 'timestamp',
    'o': 'open',
    'h': 'high', 
    'l': 'low',
    'c': 'close',
    'vol': 'volume',
    'volCcy': 'volume_currency',
    'volCcyQuote': 'volume_quote',
    'confirm': 'confirm'
}

# 数据类型定义
DTYPE_CONFIG = {
    'open': 'float64',
    'high': 'float64',
    'low': 'float64', 
    'close': 'float64',
    'volume': 'float64',
    'volume_currency': 'float64',
    'volume_quote': 'float64'
}

# =========================
# 可视化配置
# =========================

# 图表样式配置
CHART_CONFIG = {
    'figsize': (16, 10),
    'colors': {
        'up': 'red',      # 上涨颜色（中国习惯）
        'down': 'green',  # 下跌颜色
        'volume': 'lightblue',
        'ma5': 'orange',
        'ma20': 'blue'
    },
    'style': {
        'gridstyle': '--',
        'facecolor': 'white',
        'edgecolor': 'black'
    }
}

# 技术指标配置
INDICATOR_CONFIG = {
    'ma_periods': [5, 10, 20, 60],  # 移动平均线周期
    'rsi_period': 14,               # RSI周期
    'macd_config': {
        'fast': 12,
        'slow': 26, 
        'signal': 9
    }
}

# =========================
# 日志配置
# =========================

LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'filename': DATA_DIR / 'crypto_data.log'
}

# =========================
# 辅助函数
# =========================

def get_data_file_path(symbol, timeframe=BASE_TIMEFRAME):
    """获取数据文件路径"""
    filename = f"{symbol}_{timeframe}.parquet"
    return DATA_DIR / filename

def validate_symbol(symbol):
    """验证交易对是否支持"""
    return symbol.upper() in SUPPORTED_PAIRS

def validate_timeframe(timeframe):
    """验证时间周期是否支持"""
    return timeframe.lower() in TIMEFRAMES

def get_resample_rule(timeframe):
    """获取重采样规则"""
    return TIMEFRAMES.get(timeframe.lower())

# =========================
# 环境检查
# =========================

def check_dependencies():
    """检查依赖包是否安装"""
    required_packages = [
        'pandas', 'requests', 'pyarrow', 
        'mplfinance', 'matplotlib', 'numpy'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install " + " ".join(missing_packages))
        return False
    
    return True

if __name__ == "__main__":
    print("=== 加密货币数据管理系统配置 ===")
    print(f"数据存储路径: {DATA_DIR.absolute()}")
    print(f"支持的交易对: {len(SUPPORTED_PAIRS)} 个")
    print(f"支持的时间周期: {list(TIMEFRAMES.keys())}")
    print(f"基础时间周期: {BASE_TIMEFRAME}")
    print("=" * 40)
    
    # 检查依赖
    if check_dependencies():
        print("✅ 所有依赖包已安装")
    else:
        print("❌ 缺少必要依赖包")
