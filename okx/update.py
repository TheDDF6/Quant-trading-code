"""
update.py - 调用 CryptoDataUpdater 更新数据示例
"""

from crypto_data_updater import CryptoDataUpdater

def main():
    updater = CryptoDataUpdater()

    # ---------- 单币种更新 ----------
    symbol = "BTC-USDT"
    print(f"=== 更新 {symbol} ===")
    success = updater.update_data(symbol)
    status = updater.get_data_status(symbol)
    print(status)

    # ---------- 批量更新 ----------
    symbols = ["BTC-USDT", "ETH-USDT", "BNB-USDT"]
    print("=== 批量更新 ===")
    results = updater.update_multiple_symbols(symbols)

    # 打印每个币对状态
    for sym in symbols:
        status = updater.get_data_status(sym)
        print(status)

if __name__ == "__main__":
    main()
