import sys
from pathlib import Path
import types
import asyncio
import pytest

# 将 live_trading 目录加入路径，便于导入核心模块
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 为 okx 官方SDK创建最小的模拟模块，避免导入错误
okx_pkg = types.ModuleType("okx")
sys.modules.setdefault("okx", okx_pkg)

class DummyAPI:
    def __init__(self, *args, **kwargs):
        pass

for sub, cls_name in [
    ("Account", "AccountAPI"),
    ("Trade", "TradeAPI"),
    ("MarketData", "MarketAPI"),
    ("PublicData", "PublicAPI"),
]:
    mod = types.ModuleType(f"okx.{sub}")
    setattr(mod, cls_name, DummyAPI)
    setattr(okx_pkg, sub, mod)
    sys.modules[f"okx.{sub}"] = mod

from core.trading_engine_v2 import MultiStrategyTradingEngine, Position


class DummyClient:
    """Mock OKX client to capture order parameters."""
    def __init__(self):
        self.last_order = None

    def place_order(self, **kwargs):
        self.last_order = kwargs
        # mimic successful close order
        return {"code": "0", "close_price": 100.0, "fee": 0.0}


class DummyStrategy:
    def __init__(self):
        self.balance = 0

    def update_statistics(self, stats):
        pass


class DummyStrategyManager:
    def __init__(self):
        self.strategies = {"s1": DummyStrategy()}


async def run_close():
    config = {
        "okx": {"api_key": "", "secret_key": "", "passphrase": "", "sandbox": True},
        "strategies": {},
    }
    engine = MultiStrategyTradingEngine(config)
    engine.client = DummyClient()
    engine.strategy_manager = DummyStrategyManager()

    async def noop(*args, **kwargs):
        return None

    engine._record_trade = noop

    pos = Position(
        symbol="BTC-USDT-SWAP",
        side="long",
        size=0.1,
        entry_price=100.0,
        stop_loss=90.0,
        take_profit=110.0,
        leverage=10,
        strategy_id="s1",
    )
    engine.positions["p1"] = pos
    await engine._close_position(pos, "test")
    return engine.client.last_order


@pytest.mark.asyncio
async def test_close_position_includes_pos_side():
    params = await run_close()
    assert params["posSide"] == "long"
    assert params["side"] == "sell"
    assert params["reduceOnly"] is True
