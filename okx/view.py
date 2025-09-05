# view.py - 交互式可视化界面

import os
from datetime import datetime, timedelta
from crypto_data_visualizer import CryptoDataVisualizer

def main():
    # 自动检测 crypto_data 路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
    data_dir = os.path.join(parent_dir, "crypto_data")

    visualizer = CryptoDataVisualizer()

    while True:
        print("\n请选择操作：")
        print("1. 绘制K线图")
        print("2. 多币种价格对比")
        print("0. 退出")
        choice = input("输入序号 (0/1/2): ").strip()

        if choice == '0':
            print("退出程序。")
            break

        elif choice == '1':
            symbol = input("请输入币种交易对（例如 BTC-USDT）: ").strip().upper()
            timeframe = input("请输入时间周期（5m,15m,1h,4h,1d）: ").strip().lower()
            range_type = input("按最近天数显示请输入 D，按日期范围显示请输入 R（D/R）: ").strip().upper()

            start = end = None
            if range_type == 'D':
                days_input = input("请输入最近天数: ").strip()
                days = int(days_input) if days_input.isdigit() else 30
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=days)
                start = start_dt.strftime('%Y-%m-%d')
                end = end_dt.strftime('%Y-%m-%d')
            elif range_type == 'R':
                start = input("请输入开始日期（YYYY-MM-DD）: ").strip()
                end = input("请输入结束日期（YYYY-MM-DD）: ").strip()
            else:
                print("输入无效，默认最近30天")
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=30)
                start = start_dt.strftime('%Y-%m-%d')
                end = end_dt.strftime('%Y-%m-%d')

            # MA/RSI/ATR选择
            show_ma = input("是否显示移动平均线 MA？(Y/N): ").strip().upper() == 'Y'
            show_rsi = input("是否显示 RSI？(Y/N): ").strip().upper() == 'Y'
            show_atr = input("是否显示 ATR？(Y/N): ").strip().upper() == 'Y'

            success = visualizer.plot_candlestick(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
                show_ma=show_ma,
                show_rsi=show_rsi,
                show_atr=show_atr
            )
            if not success:
                print(f"{symbol} 数据加载失败或为空！")

        elif choice == '2':
            symbols_input = input("请输入币种交易对列表，逗号分隔: ").strip().upper()
            symbols = [s.strip() for s in symbols_input.split(',')]
            timeframe = input("请输入时间周期（5m,15m,1h,4h,1d）: ").strip().lower()
            days_input = input("请输入比较天数（默认30）: ").strip()
            days = int(days_input) if days_input.isdigit() else 30

            visualizer.plot_price_comparison(symbols, timeframe=timeframe, days=days)

        else:
            print("输入无效，请重新选择操作")

if __name__ == "__main__":
    main()
