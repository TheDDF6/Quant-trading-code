# strategies/ma_cross.py
import pandas as pd

def generate_signals(df, short=10, long=50):
    """
    均线交叉策略信号生成
    返回 [(timestamp, price, action), ...]
    """
    df = df.copy()
    df['ma_fast'] = df['close'].rolling(short).mean()
    df['ma_slow'] = df['close'].rolling(long).mean()
    df['position'] = 0
    df.loc[df['ma_fast'] > df['ma_slow'], 'position'] = 1
    df.loc[df['ma_fast'] <= df['ma_slow'], 'position'] = -1

    signals = []
    position = 0
    for idx, row in df.iterrows():
        if row['position'] == 1 and position <= 0:
            signals.append((idx, row['close'], 'buy'))
            position = 1
        elif row['position'] == -1 and position >= 0:
            signals.append((idx, row['close'], 'sell'))
            position = -1
    return signals
