# 获取单个币种的历史数据
from crypto_data_fetcher import CryptoDataFetcher

fetcher = CryptoDataFetcher()

# 获取BTC近6个月的5分钟数据
success = fetcher.fetch_and_save("BTC-USDT", months=12)