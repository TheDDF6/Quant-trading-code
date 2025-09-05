import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from strategies.rsi_divergence_unified_adapter import RSIDivergenceUnifiedAdapter
from unified_strategies.base_unified_strategy import UnifiedSignal


def test_rsi_adapter_avoids_duplicate_signals():
    adapter = RSIDivergenceUnifiedAdapter("rsi", {})

    latest_ts = pd.Timestamp("2024-01-01 00:00:00")

    def fake_analyze_market(df, symbol):
        return [UnifiedSignal(
            symbol=symbol,
            signal_type="buy",
            timestamp=latest_ts,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=105.0,
            strategy_id="rsi",
            strength=0.8,
        )]

    adapter.unified_strategy.analyze_market = fake_analyze_market

    df = pd.DataFrame(
        {
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.0],
            "volume": [1000.0],
        },
        index=[latest_ts],
    )

    signals1 = adapter.analyze_market(df, "BTC-USDT-SWAP")
    signals2 = adapter.analyze_market(df, "BTC-USDT-SWAP")

    assert len(signals1) == 1
    assert len(signals2) == 0
