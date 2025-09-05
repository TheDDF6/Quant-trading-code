# 在你的回测代码中添加：
from strategy_validator import validate_strategy, create_validation_report

# 运行回测后
df_backtest, trades = backtest_debug(df.copy(), signals)

# 验证策略
validate_strategy(df, signals, symbol)

# 创建详细报告
create_validation_report(df_backtest, signals, trades, symbol)