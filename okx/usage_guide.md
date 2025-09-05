# 加密货币数据管理系统使用指南

这是一个完整的加密货币数据获取、更新和可视化系统，支持多种主流加密货币对和多个时间周期。

## 📁 文件结构

```
crypto_system/
├── config.py           # 配置文件
├── data_fetcher.py     # 数据获取模块
├── data_updater.py     # 数据更新模块
├── data_visualizer.py  # 数据可视化模块
├── crypto_data/        # 数据存储目录（自动创建）
│   ├── BTC-USDT_5m.parquet
│   ├── ETH-USDT_5m.parquet
│   └── ...
└── README.md          # 本使用指南
```

## 🚀 快速开始

### 1. 安装依赖包

```bash
pip install pandas requests pyarrow mplfinance matplotlib numpy
```

### 2. 检查配置

```bash
python config.py
```

这会显示系统配置信息并检查所有依赖包是否已安装。

## 📊 基本使用流程

### 第一步：获取历史数据

```python
# 获取单个币种的历史数据
from data_fetcher import CryptoDataFetcher

fetcher = CryptoDataFetcher()

# 获取BTC近6个月的5分钟数据
success = fetcher.fetch_and_save("BTC-USDT", months=6)

# 批量获取多个币种
symbols = ["BTC-USDT", "ETH-USDT", "BNB-USDT"]
results = fetcher.fetch_multiple_symbols(symbols, months=6)
```

### 第二步：更新数据到最新

```python
# 更新数据到最新
from data_updater import CryptoDataUpdater

updater = CryptoDataUpdater()

# 更新单个币种
success = updater.update_data("BTC-USDT")

# 批量更新多个币种
symbols = ["BTC-USDT", "ETH-USDT", "BNB-USDT"]
results = updater.update_multiple_symbols(symbols)

# 检查数据状态
status = updater.get_data_status("BTC-USDT")
print(status)
```

### 第三步：可视化数据

```python
# 数据可视化
from data_visualizer import CryptoDataVisualizer

visualizer = CryptoDataVisualizer()

# 绘制K线图
visualizer.plot_candlestick("BTC-USDT", timeframe="1d", show_ma=True)

# 多币种价格对比
symbols = ["BTC-USDT", "ETH-USDT", "BNB-USDT"]
visualizer.plot_price_comparison(symbols, timeframe="1d", days=30)

# 成交量分析
visualizer.plot_volume_analysis("BTC-USDT", timeframe="1h", days=7)
```

## 🔧 详细功能说明

### 1. 数据获取模块 (data_fetcher.py)

**主要功能：**
- 从OKX交易所获取历史K线数据
- 支持批量获取多个交易对
- 自动数据清洗和格式化
- 保存为高效的Parquet格式

**使用示例：**

```python
from data_fetcher import CryptoDataFetcher

fetcher = CryptoDataFetcher()

# 获取6个月历史数据
fetcher.fetch_and_save("BTC-USDT", months=6)

# 获取指定时间范围的数据
fetcher.fetch_and_save("ETH-USDT", months=3)

# 批量获取
symbols = ["BTC-USDT", "ETH-USDT", "ADA-USDT", "SOL-USDT"]
results = fetcher.fetch_multiple_symbols(symbols, months=6)

# 查看结果
for symbol, success in results.items():
    print(f"{symbol}: {'成功' if success else '失败'}")
```

### 2. 数据更新模块 (data_updater.py)

**主要功能：**
- 增量更新本地数据到最新
- 自动检测需要更新的时间范围
- 避免重复数据下载
- 支持批量更新

**使用示例：**

```python
from data_updater import CryptoDataUpdater

updater = CryptoDataUpdater()

# 检查数据状态
status = updater.get_data_status("BTC-USDT")
print(f"数据存在: {status['exists']}")
print(f"最新时间: {status['latest_time']}")
print(f"需要更新: {status['needs_update']}")

# 更新单个交易对
success = updater.update_data("BTC-USDT")

# 批量更新
symbols = ["BTC-USDT", "ETH-USDT", "BNB-USDT"]
results = updater.update_multiple_symbols(symbols)
```

### 3. 数据可视化模块 (data_visualizer.py)

**主要功能：**
- 自动时间周期转换（5m→15m→1h→4h→1d）
- 多种图表类型：K线图、价格对比图、成交量分析
- 技术指标支持：移动平均线等
- 灵活的时间范围选择

**使用示例：**

```python
from data_visualizer import CryptoDataVisualizer

visualizer = CryptoDataVisualizer()

# 1. 基础K线图
visualizer.plot_candlestick("BTC-USDT", timeframe="1d")

# 2. 带移动平均线的K线图
visualizer.plot_candlestick(
    "BTC-USDT", 
    timeframe="4h", 
    show_ma=True, 
    ma_periods=[5, 20]
)

# 3. 指定时间范围的K线图
visualizer.plot_candlestick(
    "ETH-USDT",
    timeframe="1h",
    start="2024-01-01",
    end="2024-01-31"
)

# 4. 多币种价格对比图（归一化）
symbols = ["BTC-USDT", "ETH-USDT", "BNB-USDT", "ADA-USDT"]
visualizer.plot_price_comparison(symbols, timeframe="1d", days=30)

# 5. 成交量分析图
visualizer.plot_volume_analysis("BTC-USDT", timeframe="1h", days=7)

# 6. 获取数据摘要
summary = visualizer.get_data_summary("BTC-USDT", "1d")
print(summary)
```

## ⏰ 时间周期转换

系统基于5分钟数据，自动转换为其他周期：

| 输入周期 | 转换规则 | 说明 |
|---------|----------|------|
| 5m      | 无转换   | 原始数据 |
| 15m     | 3根合并  | 每3根5分钟K线合并成1根15分钟K线 |
| 1h      | 12根合并 | 每12根5分钟K线合并成1根1小时K线 |
| 4h      | 48根合并 | 每48根5分钟K线合并成1根4小时K线 |
| 1d      | 288根合并| 每288根5分钟K线合并成1根日K线 |

## 🎯 完整工作流程示例

```python
# 完整的数据获取、更新和可视化流程

from data_fetcher import CryptoDataFetcher
from data_updater import CryptoDataUpdater  
from data_visualizer import CryptoDataVisualizer

# === 第一次使用：获取历史数据 ===
print("1. 获取历史数据...")
fetcher = CryptoDataFetcher()
symbols = ["BTC-USDT", "ETH-USDT", "BNB-USDT"]

# 获取6个月历史数据
results = fetcher.fetch_multiple_symbols(symbols, months=6)
print(f"数据获取结果: {results}")

# === 日常使用：更新到最新数据 ===
print("\n2. 更新数据到最新...")
updater = CryptoDataUpdater()

# 检查各币种数据状态
for symbol in symbols:
    status = updater.get_data_status(symbol)
    print(f"{symbol}: 需要更新 = {status['needs_update']}")

# 批量更新
update_results = updater.update_multiple_symbols(symbols)
print(f"更新结果: {update_results}")

# === 数据分析和可视化 ===
print("\n3. 数据可视化...")
visualizer = CryptoDataVisualizer()

# BTC日K线图（带移动平均线）
visualizer.plot_candlestick("BTC-USDT", "1d", show_ma=True)

# 多币种30天价格对比
visualizer.plot_price_comparison(symbols, "1d", days=30)

# BTC小时级成交量分析
visualizer.plot_volume_analysis("BTC-USDT", "1h", days=7)

print("完成！")
```

## 📋 支持的交易对

系统支持15个主流加密货币交易对：

- BTC-USDT, ETH-USDT, BNB-USDT
- ADA-USDT, XRP-USDT, SOL-USDT  
- DOGE-USDT, MATIC-USDT, DOT-USDT
- AVAX-USDT, LINK-USDT, UNI-USDT
- LTC-USDT, BCH-USDT, ATOM-USDT

## 🔧 自定义配置

可以在 `config.py` 中修改：

- 支持的交易对列表
- API请求参数
- 图表样式和颜色
- 技术指标参数
- 数据存储路径

## ⚠️ 注意事项

1. **首次使用**：必须先用 `data_fetcher.py` 获取历史数据
2. **更新频率**：建议每天或每几小时运行一次更新
3. **数据存储**：Parquet文件占用空间较小，读取速度快
4. **网络要求**：需要稳定的网络连接访问OKX API
5. **时区处理**：所有时间都自动转换为北京时间（UTC+8）

## 🆘 常见问题

**Q: 提示"数据文件不存在"？**
A: 请先使用 `data_fetcher.py` 获取历史数据。

**Q: 更新失败？**
A: 检查网络连接，可能是API请求频率过高，等待几分钟后重试。

**Q: 图表显示乱码？**
A: 系统已配置中文字体支持，如仍有问题请安装相应字体。

**Q: 如何添加新的交易对？**
A: 在 `config.py` 的 `SUPPORTED_PAIRS` 列表中添加新的交易对。

## 📈 扩展功能建议

- 添加更多技术指标（RSI、MACD、布林带等）
- 支持其他交易所API
- 添加实时数据推送
- 实现策略回测框架
- 添加数据库存储支持

祝您使用愉快！🎉