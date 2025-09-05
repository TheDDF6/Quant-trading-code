# trading_engine_v2.py - 多策略交易引擎
"""
多策略交易引擎 v2.0
支持同时运行多个策略的新版交易引擎

主要改进:
1. 集成策略管理器和风险管理器
2. 支持多策略并行运行
3. 统一的持仓管理和风险控制
4. 增强的监控和日志系统
"""

import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
import pandas as pd
import numpy as np

from core.okx_client import OKXClient
from core.strategy_manager import StrategyManager
from core.risk_manager import RiskManager
from strategies.base_strategy import BaseStrategy, Signal

class Position:
    """增强的持仓信息类"""
    
    def __init__(self, 
                 symbol: str, 
                 side: str, 
                 size: float, 
                 entry_price: float,
                 stop_loss: float, 
                 take_profit: float, 
                 leverage: int,
                 strategy_id: str,
                 order_id: str = None,
                 open_fee: float = 0.0):
        """
        初始化持仓
        
        Args:
            symbol: 交易对
            side: 方向 ('long', 'short') 
            size: 仓位大小
            entry_price: 入场价格
            stop_loss: 止损价格
            take_profit: 止盈价格
            leverage: 杠杆倍数
            strategy_id: 策略ID
            order_id: 订单ID
            open_fee: 开仓手续费
        """
        self.symbol = symbol
        self.side = side
        self.size = size
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.leverage = leverage
        self.strategy_id = strategy_id
        self.order_id = order_id
        self.entry_time = datetime.now()
        
        # 盈亏相关
        self.unrealized_pnl = 0.0
        self.open_fee = open_fee
        self.estimated_close_fee = open_fee
        
        # 风险管理
        self.trailing_stop = None
        self.max_favorable_price = entry_price
        
        # 状态管理
        self.is_closing = False
        self.close_reason = None
        
    def update_pnl(self, current_price: float, close_fee: float = 0.0):
        """更新未实现盈亏"""
        # 合约面值 (不同合约面值不同)
        ct_val = self._get_contract_value()
        
        if self.side == 'long':
            price_pnl = (current_price - self.entry_price) * self.size * ct_val
        else:  # short
            price_pnl = (self.entry_price - current_price) * self.size * ct_val
        
        # 更新最有利价格 (用于追踪止损)
        if self.side == 'long' and current_price > self.max_favorable_price:
            self.max_favorable_price = current_price
        elif self.side == 'short' and current_price < self.max_favorable_price:
            self.max_favorable_price = current_price
        
        # 计算净盈亏 (扣除手续费)
        estimated_close_fee = close_fee if close_fee > 0 else self.estimated_close_fee
        self.unrealized_pnl = price_pnl - self.open_fee - estimated_close_fee
    
    def _get_contract_value(self) -> float:
        """获取合约面值"""
        if 'BTC' in self.symbol:
            return 0.01  # BTC-USDT-SWAP面值
        elif 'ETH' in self.symbol:
            return 0.1   # ETH-USDT-SWAP面值
        else:
            return 1.0   # 其他币种默认面值
    
    def check_exit_conditions(self, current_price: float) -> Tuple[bool, str]:
        """
        检查是否应该退出持仓
        
        Returns:
            (should_exit, reason)
        """
        # 止损检查
        if self.should_stop_loss(current_price):
            return True, 'stop_loss'
        
        # 止盈检查
        if self.should_take_profit(current_price):
            return True, 'take_profit'
        
        # 追踪止损检查
        if self.trailing_stop and self.should_trailing_stop(current_price):
            return True, 'trailing_stop'
        
        return False, None
    
    def should_stop_loss(self, current_price: float) -> bool:
        """检查固定止损"""
        if self.side == 'long':
            return current_price <= self.stop_loss
        else:
            return current_price >= self.stop_loss
    
    def should_take_profit(self, current_price: float) -> bool:
        """检查止盈"""
        if self.side == 'long':
            return current_price >= self.take_profit
        else:
            return current_price <= self.take_profit
    
    def should_trailing_stop(self, current_price: float) -> bool:
        """检查追踪止损"""
        if not self.trailing_stop:
            return False
        
        if self.side == 'long':
            trailing_price = self.max_favorable_price * (1 - self.trailing_stop)
            return current_price <= trailing_price
        else:
            trailing_price = self.max_favorable_price * (1 + self.trailing_stop)
            return current_price >= trailing_price
    
    def set_trailing_stop(self, trailing_pct: float):
        """设置追踪止损"""
        self.trailing_stop = trailing_pct
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'leverage': self.leverage,
            'strategy_id': self.strategy_id,
            'order_id': self.order_id,
            'entry_time': self.entry_time.isoformat(),
            'unrealized_pnl': self.unrealized_pnl,
            'max_favorable_price': self.max_favorable_price,
            'trailing_stop': self.trailing_stop
        }

class MultiStrategyTradingEngine:
    """多策略交易引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化多策略交易引擎
        
        Args:
            config: 交易引擎配置
        """
        self.config = config
        self.logger = self._setup_logging()
        
        # 初始化OKX客户端
        okx_config = config.get('okx', {})
        self.client = OKXClient(
            api_key=okx_config.get('api_key'),
            secret_key=okx_config.get('secret_key'),
            passphrase=okx_config.get('passphrase'),
            sandbox=okx_config.get('sandbox', True)
        )
        
        # 初始化策略管理器
        strategy_config = config.get('strategy_manager', {})
        self.strategy_manager = StrategyManager(strategy_config)
        
        # 初始化风险管理器
        risk_config = config.get('risk_manager', {})
        self.risk_manager = RiskManager(risk_config)
        
        # 持仓管理
        self.positions: Dict[str, Position] = {}  # position_id -> Position
        self.position_counter = 0
        
        # 交易状态
        self.is_running = False
        self.total_balance = 0.0
        self.available_balance = 0.0
        self.total_pnl = 0.0
        
        # 数据缓存
        self.market_data_cache: Dict[str, pd.DataFrame] = {}
        self.price_cache: Dict[str, float] = {}
        
        # 运行控制
        self.main_loop_interval = config.get('main_loop_interval', 10)  # 10秒主循环
        self.data_update_interval = config.get('data_update_interval', 30)  # 30秒数据更新
        
        # 交易记录
        self.trades_file = Path(config.get('trades_file', 'data/trades.json'))
        self.trades_file.parent.mkdir(exist_ok=True)
        
        # 从配置文件加载策略
        try:
            self.logger.info("开始加载策略...")
            self._initialize_strategies_from_config()
            self.logger.info(f"策略加载完成，共注册 {len(self.strategy_manager.strategies)} 个策略")
        except Exception as e:
            self.logger.error(f"策略加载失败: {e}")
            import traceback
            traceback.print_exc()
        
        self.logger.info("多策略交易引擎初始化完成")
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("TradingEngineV2")
        
        if not logger.handlers:
            # 文件日志处理器
            log_file = Path(f"logs/trading_{datetime.now().strftime('%Y%m%d')}.log")
            log_file.parent.mkdir(exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 控制台日志处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 日志格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _initialize_strategies_from_config(self):
        """从配置文件初始化策略"""
        try:
            strategies_config = self.config.get('strategies', {})
            self.logger.info(f"发现配置中的策略: {list(strategies_config.keys())}")
            
            for strategy_id, strategy_config in strategies_config.items():
                self.logger.info(f"处理策略: {strategy_id}, 激活状态: {strategy_config.get('active', False)}")
                
                if not strategy_config.get('active', False):
                    self.logger.info(f"策略 {strategy_id} 未激活，跳过")
                    continue
                
                strategy_class_name = strategy_config.get('class')
                self.logger.info(f"策略类型: {strategy_class_name}")
                
                if strategy_class_name == 'RSIDivergenceUnifiedAdapter':
                    try:
                        self.logger.info(f"正在导入策略类 {strategy_class_name}...")
                        from strategies.rsi_divergence_unified_adapter import RSIDivergenceUnifiedAdapter
                        
                        self.logger.info(f"正在创建策略实例 {strategy_id}...")
                        strategy = RSIDivergenceUnifiedAdapter(
                            strategy_id=strategy_id,
                            config=strategy_config['config']
                        )
                        
                        allocation_ratio = strategy_config.get('allocation_ratio', 0.2)
                        self.logger.info(f"正在注册策略 {strategy_id}，分配比例: {allocation_ratio}")
                        self.add_strategy(strategy, allocation_ratio)
                        
                        self.logger.info(f"策略 {strategy_id} 加载成功")
                        
                    except Exception as e:
                        self.logger.error(f"加载策略 {strategy_id} 失败: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    self.logger.warning(f"未知策略类型: {strategy_class_name}")
                    
        except Exception as e:
            self.logger.error(f"策略初始化失败: {e}")
            import traceback
            traceback.print_exc()
    
    def add_strategy(self, strategy: BaseStrategy, allocation_ratio: float = 0.0):
        """
        添加策略
        
        Args:
            strategy: 策略实例
            allocation_ratio: 资金分配比例
        """
        self.strategy_manager.register_strategy(strategy, allocation_ratio)
        self.logger.info(f"策略 {strategy.strategy_id} 已添加到引擎")
    
    def remove_strategy(self, strategy_id: str):
        """移除策略"""
        # 先平仓该策略的所有持仓
        strategy_positions = [pos for pos in self.positions.values() 
                            if pos.strategy_id == strategy_id]
        
        for position in strategy_positions:
            self._close_position(position, "策略移除")
        
        # 注销策略
        self.strategy_manager.unregister_strategy(strategy_id)
        self.logger.info(f"策略 {strategy_id} 已从引擎移除")
    
    async def start_trading(self):
        """启动交易引擎"""
        if self.is_running:
            self.logger.warning("交易引擎已在运行")
            return
        
        try:
            # 启动前检查
            if not await self._pre_trading_checks():
                return
            
            self.is_running = True
            self.logger.info("多策略交易引擎启动")
            
            # 启动组件
            self.strategy_manager.start_all_strategies()
            self.risk_manager.start_monitoring()
            
            # 启动主循环
            await self._main_trading_loop()
            
        except Exception as e:
            self.logger.error(f"交易引擎启动失败: {e}")
            await self.stop_trading()
    
    async def stop_trading(self):
        """停止交易引擎"""
        self.is_running = False
        self.logger.info("正在停止交易引擎...")
        
        # 停止组件
        self.strategy_manager.stop_all_strategies()
        self.risk_manager.stop_monitoring()
        
        # 记录最终状态
        final_status = self.get_trading_status()
        self.logger.info(f"引擎已停止 - 最终状态: {final_status}")
    
    async def _pre_trading_checks(self) -> bool:
        """交易前检查"""
        try:
            # 检查API连接
            if not self.client.test_connection():
                self.logger.error("API连接测试失败")
                return False
            
            # 检查账户信息
            balance_info = self.client.get_account_balance()
            if not balance_info or balance_info.get('code') != '0':
                self.logger.error("获取账户信息失败")
                return False
            
            # 调试完成，移除详细日志输出
            
            # 解析OKX账户余额格式
            try:
                data = balance_info.get('data', [])
                if data and data[0].get('details'):
                    # 获取USDT余额
                    usdt_balance = None
                    for detail in data[0]['details']:
                        if detail.get('ccy') == 'USDT':
                            usdt_balance = detail
                            break
                    
                    if usdt_balance:
                        # 使用eq(权益)作为总余额，而不是bal(现金余额)
                        self.total_balance = float(usdt_balance.get('eq', 0))
                        self.available_balance = float(usdt_balance.get('availBal', 0))
                    else:
                        self.logger.error("未找到USDT余额信息")
                        return False
                else:
                    self.logger.error("账户余额数据格式异常")
                    return False
            except Exception as e:
                self.logger.error(f"解析账户余额失败: {e}")
                return False
            
            # 检查是否有持仓或挂单
            has_positions = self._check_existing_positions()
            
            # 如果有持仓/挂单，优先进入监控模式
            if has_positions:
                self.logger.info(f"检测到现有持仓/挂单，进入监控模式")
                self.logger.info(f"账户状态 - 总余额: ${self.total_balance:.2f}, 可用余额: ${self.available_balance:.2f}")
                return True
            
            # 无持仓时的余额检查
            if self.total_balance <= 0:
                self.logger.error("账户余额不足")
                return False
            elif self.available_balance <= 0:
                self.logger.error("可用余额不足且无持仓")
                return False
            
            # 检查策略状态
            if len(self.strategy_manager.strategies) == 0:
                self.logger.error("没有注册的策略")
                return False
            
            self.logger.info(f"预检查完成 - 总余额: ${self.total_balance:.2f}, "
                           f"可用余额: ${self.available_balance:.2f}")
            return True
            
        except Exception as e:
            self.logger.error(f"预检查失败: {e}")
            return False
    
    def _check_existing_positions(self) -> bool:
        """检查是否有现有持仓或挂单"""
        try:
            # 检查持仓
            positions_response = self.client.get_positions()
            if positions_response.get('code') == '0' and positions_response.get('data'):
                for position in positions_response['data']:
                    if float(position.get('pos', 0)) != 0:
                        # 减少日志输出，只在首次检测或状态变化时输出
                        return True
            
            # 暂时禁用挂单检查，避免API方法问题
            # orders_response = self.client.get_orders()
            # if orders_response.get('code') == '0' and orders_response.get('data'):
            #     active_orders = [order for order in orders_response['data'] 
            #                    if order.get('state') in ['live', 'partially_filled']]
            #     if active_orders:
            #         self.logger.info(f"检测到 {len(active_orders)} 个活跃挂单")
            #         return True
                    
            return False
            
        except Exception as e:
            # 网络错误时静默处理，不每次都打印警告
            if "getaddrinfo failed" not in str(e) and "10054" not in str(e):
                self.logger.warning(f"检查持仓状态失败: {e}")
            return False
    
    async def _main_trading_loop(self):
        """主交易循环 - 1秒间隔，时间对齐"""
        # 初始化时间同步
        if not self.client.sync_server_time():
            self.logger.warning("初始服务器时间同步失败，使用本地时间")
        
        last_data_update = 0
        last_minute_update = 0
        
        # 立即同步到下一整秒开始
        await self._wait_for_next_second()
        
        while self.is_running:
            try:
                # 获取同步的北京时间
                beijing_time = self.client.get_beijing_time()
                current_timestamp = beijing_time.timestamp()
                
                # 检查是否需要重新同步服务器时间（每5分钟）
                if self.client.should_sync_time():
                    self.client.sync_server_time()
                
                # 在整分钟时执行数据更新和策略分析
                if beijing_time.second == 0 and current_timestamp - last_minute_update >= 55:
                    await self._on_minute_tick(beijing_time)
                    last_minute_update = current_timestamp
                
                # 每30秒更新一次市场数据（保持数据新鲜度）
                if beijing_time.second % 30 == 0 and current_timestamp - last_data_update >= 25:
                    await self._update_market_data()
                    last_data_update = current_timestamp
                
                # 检查风险状态（每秒），API持仓检查采用智能频率
                has_internal_positions = len(self.positions) > 0
                has_api_positions = False
                
                # 智能持仓检查频率：
                # - 有内部持仓时：每分钟整点检查（监控平仓）
                # - 无内部持仓时：每30秒检查（监控新开仓）
                if has_internal_positions:
                    # 有持仓：每分钟检查一次
                    if beijing_time.second == 0:
                        has_api_positions = self._check_existing_positions()
                else:
                    # 无持仓：每30秒检查一次
                    if beijing_time.second % 30 == 0:
                        has_api_positions = self._check_existing_positions()
                
                has_positions = has_internal_positions or has_api_positions
                trading_allowed, reason = self.risk_manager.is_trading_allowed(has_positions)
                if not trading_allowed:
                    if beijing_time.second == 0:  # 只在整分钟输出警告，避免日志刷屏
                        self.logger.warning(f"交易暂停: {reason}")
                    await asyncio.sleep(1)
                    continue
                
                # 更新持仓状态（每秒）
                await self._update_positions()
                
                # 检查平仓条件（每秒）
                await self._check_exit_conditions()
                
                # 精确等待到下一秒
                await self._wait_for_next_second()
                
            except Exception as e:
                self.logger.error(f"主循环异常: {e}")
                await asyncio.sleep(1)
    
    async def _wait_for_next_second(self):
        """等待到下一个整秒"""
        try:
            beijing_time = self.client.get_beijing_time()
            current_microsecond = beijing_time.microsecond
            
            # 计算到下一秒的等待时间
            wait_time = (1000000 - current_microsecond) / 1000000
            
            # 最小等待0.01秒，最大等待1秒
            wait_time = max(0.01, min(1.0, wait_time))
            
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            # 如果时间计算出错，默认等待1秒
            await asyncio.sleep(1)
    
    async def _on_minute_tick(self, beijing_time):
        """整分钟时刻的处理"""
        minute = beijing_time.minute
        
        self.logger.debug(f"整分钟时刻: {beijing_time.strftime('%H:%M:%S')}")
        
        # 强制更新市场数据
        await self._update_market_data()
        
        # 根据不同策略的时间周期执行策略分析
        should_run_strategies = False
        strategy_reasons = []
        
        # 检查各种策略周期
        if minute % 1 == 0:  # 1分钟策略
            should_run_strategies = True
            strategy_reasons.append("1分钟")
        
        if minute % 5 == 0:  # 5分钟策略
            should_run_strategies = True
            strategy_reasons.append("5分钟")
        
        if minute % 15 == 0:  # 15分钟策略
            should_run_strategies = True
            strategy_reasons.append("15分钟")
        
        if minute % 30 == 0:  # 30分钟策略
            should_run_strategies = True
            strategy_reasons.append("30分钟")
        
        if minute == 0:  # 1小时策略
            should_run_strategies = True
            strategy_reasons.append("1小时")
        
        if should_run_strategies:
            self.logger.info(f"执行策略分析 - {beijing_time.strftime('%H:%M')} - 周期: {', '.join(strategy_reasons)}")
            
            # 收集策略信号
            signals = self.strategy_manager.collect_signals(self.market_data_cache)
            
            # 处理信号
            if signals:
                await self._process_signals(signals)
        
        # 更新风险指标
        self._update_risk_metrics()
    
    async def _update_market_data(self):
        """更新市场数据"""
        try:
            # 获取所有策略需要的交易对
            required_symbols = set()
            for strategy in self.strategy_manager.strategies.values():
                required_symbols.update(strategy.get_supported_symbols())
            
            # 批量获取市场数据
            for symbol in required_symbols:
                try:
                    # 获取K线数据 (最近100根)
                    response = self.client.get_candlesticks(symbol, '5m', limit=100)
                    
                    if response and response.get('code') == '0' and response.get('data'):
                        # 处理OKX K线数据格式 [timestamp, open, high, low, close, volume, volCcy]
                        klines_data = response['data']
                        if klines_data:
                            # OKX K线数据格式: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                            df = pd.DataFrame(klines_data)
                            # 只取前7列，重命名
                            df = df.iloc[:, :7]  # 只取前7列
                            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy']
                            # 转换数据类型
                            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
                            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
                            self.market_data_cache[symbol] = df
                            
                            # 更新价格缓存
                            if len(df) > 0:
                                self.price_cache[symbol] = df.iloc[-1]['close']
                            
                except Exception as e:
                    self.logger.error(f"获取 {symbol} 数据失败: {e}")
            
            self.logger.debug(f"市场数据更新完成 - {len(self.market_data_cache)} 个交易对")
            
        except Exception as e:
            self.logger.error(f"市场数据更新失败: {e}")
    
    async def _process_signals(self, signals: List[Signal]):
        """处理交易信号"""
        self.logger.info(f"收到 {len(signals)} 个交易信号")
        
        for signal in signals:
            try:
                # 检查是否已有该品种的持仓
                existing_position = self._get_position_by_symbol(signal.symbol)
                
                if existing_position:
                    # 如果已有持仓，检查是否需要调整或平仓
                    await self._handle_existing_position_signal(existing_position, signal)
                else:
                    # 开新仓
                    await self._open_new_position(signal)
                    
            except Exception as e:
                self.logger.error(f"处理信号失败 {signal.symbol}: {e}")
    
    async def _open_new_position(self, signal: Signal):
        """开新仓"""
        try:
            # 获取策略实例
            strategy = self.strategy_manager.strategies.get(signal.strategy_id)
            if not strategy:
                self.logger.error(f"未找到策略: {signal.strategy_id}")
                return
            
            # 计算仓位大小 - 在共享资金池模式下使用可用余额
            position_size = signal.position_size
            available_funds = self.available_balance if strategy.balance == 0 else strategy.balance
            
            if not position_size:
                position_size = strategy.calculate_position_size(signal, available_funds)
            
            # 对于SWAP合约，将USDT金额转换为合约张数
            if signal.symbol.endswith('-SWAP'):
                position_size = self._convert_usdt_to_contracts(signal.symbol, position_size, signal.entry_price)
                self.logger.info(f"USDT金额转换为合约张数: {position_size:.2f}张")
            
            # 基于1.5%风险目标重新计算合适的仓位大小
            target_risk_rate = 0.015  # 1.5%风险目标
            target_risk_amount = available_funds * target_risk_rate
            
            # 计算基于风险的合理仓位大小
            symbol_config = self.config.get('symbol_settings', {}).get(signal.symbol, {})
            contract_value = symbol_config.get('contract_value', 0.01)
            
            # 基于止损距离计算风险仓位
            # 使用信号中的止损价格计算实际风险
            if hasattr(signal, 'stop_loss') and signal.stop_loss > 0:
                if signal.signal_type == 'buy':
                    price_risk = signal.entry_price - signal.stop_loss
                else:
                    price_risk = signal.stop_loss - signal.entry_price
                
                risk_per_contract = price_risk * contract_value  # 每张合约的风险
                max_contracts_by_risk = target_risk_amount / risk_per_contract
                
                self.logger.info(f"基于止损计算风险: 价格风险={price_risk:.2f}, 每张风险={risk_per_contract:.2f} USDT")
            else:
                # 如果没有止损信息，使用保守的3%价格波动
                price_risk_factor = 0.03  # 3%价格波动风险
                max_position_value_by_risk = target_risk_amount / price_risk_factor
                max_contracts_by_risk = max_position_value_by_risk / (contract_value * signal.entry_price)
                
                self.logger.info(f"使用默认3%风险因子: 最大持仓价值={max_position_value_by_risk:.2f} USDT")
            
            if position_size > max_contracts_by_risk:
                self.logger.warning(f"基于1.5%风险目标调整仓位: {position_size:.2f} -> {max_contracts_by_risk:.2f}张")
                self.logger.info(f"风险分析: 目标风险{target_risk_amount:.2f} USDT, 5%波动保护")
                position_size = max_contracts_by_risk
            
            # 检查仓位不为0
            if position_size <= 0:
                self.logger.error(f"计算出的仓位大小为0，跳过交易: 可用资金={available_funds}")
                return
            
            # 规范化订单数量以符合交易所要求
            normalized_size = self._normalize_order_size(signal.symbol, position_size)
            if normalized_size <= 0:
                self.logger.error(f"规范化后的订单数量为0，跳过交易: 原始={position_size:.2f}, 规范化={normalized_size}")
                return
                
            self.logger.info(f"订单数量规范化: {position_size:.2f} -> {normalized_size}")
            
            # 确定交易方向
            side = 'long' if signal.signal_type == 'buy' else 'short'
            
            # 使用简单的固定杠杆策略
            optimal_leverage = 10  # 固定使用10x杠杆
            
            # 计算所需保证金
            symbol_config = self.config.get('symbol_settings', {}).get(signal.symbol, {})
            contract_value = symbol_config.get('contract_value', 0.01)
            position_value = normalized_size * contract_value * signal.entry_price
            required_margin = position_value / optimal_leverage
            
            self.logger.info(f"简单杠杆策略: {optimal_leverage}x杠杆, 持仓价值={position_value:.2f} USDT, 需要保证金={required_margin:.2f} USDT")
            
            # 检查保证金需求 - 放宽限制到90%，并预留一些手续费
            margin_limit = available_funds * 0.9  # 使用90%资金
            estimated_fees = position_value * 0.001  # 预估0.1%的手续费
            
            if required_margin + estimated_fees > margin_limit:
                self.logger.warning(f"保证金需求过高: 需要{required_margin:.2f} + 手续费{estimated_fees:.2f} = {required_margin+estimated_fees:.2f} USDT")
                self.logger.warning(f"可用限额: {margin_limit:.2f} USDT (账户余额{available_funds:.2f}的90%)")
                self.logger.info("建议: 增加账户余额或等待价格变化降低合约价值")
                return
            
            self.logger.info(f"保证金检查通过: 需要{required_margin:.2f} USDT, 可用{margin_limit:.2f} USDT")
            
            # 下单
            side = 'buy' if signal.signal_type == 'buy' else 'sell'
            posSide = 'long' if signal.signal_type == 'buy' else 'short'  # 持仓方向
            
            # 准备止盈止损参数
            tp_trigger_px = None
            sl_trigger_px = None
            
            if hasattr(signal, 'take_profit') and signal.take_profit > 0:
                tp_trigger_px = str(signal.take_profit)
                
            if hasattr(signal, 'stop_loss') and signal.stop_loss > 0:
                sl_trigger_px = str(signal.stop_loss)
            
            # 下单（附带止盈止损）
            order_result = self.client.place_order(
                instId=signal.symbol,
                tdMode='cross',  # 全仓模式
                side=side,
                ordType='market',
                sz=str(normalized_size),  # 使用实际计算的数量
                posSide=posSide,  # 添加持仓方向
                lever=str(optimal_leverage),  # 使用计算出的最优杠杆
                tpTriggerPx=tp_trigger_px,  # 止盈触发价
                slTriggerPx=sl_trigger_px   # 止损触发价
            )
            
            if tp_trigger_px or sl_trigger_px:
                self.logger.info(f"下单附带止盈止损: 止盈={tp_trigger_px}, 止损={sl_trigger_px}")
            
            if order_result and order_result.get('code') == '0':
                # 创建持仓记录
                position_id = f"{signal.symbol}_{self.position_counter}"
                self.position_counter += 1
                
                # 使用规范化后的数量作为持仓大小
                actual_size = normalized_size  # 使用实际的规范化数量
                
                position = Position(
                    symbol=signal.symbol,
                    side=side,
                    size=actual_size,  # 使用规范化后的数量
                    entry_price=signal.entry_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    leverage=optimal_leverage,  # 使用计算出的杠杆
                    strategy_id=signal.strategy_id,
                    order_id=order_result.get('order_id'),
                    open_fee=order_result.get('fee', 0.0)
                )
                
                self.positions[position_id] = position
                
                # 更新策略余额
                strategy.balance -= position_size
                
                # 记录交易
                await self._record_trade('open', position, signal)
                
                self.logger.info(f"开仓成功: {signal.symbol} {side} {position_size} @ {signal.entry_price}")
                
            else:
                self.logger.error(f"开仓失败: {signal.symbol} - {order_result}")
                
        except Exception as e:
            self.logger.error(f"开仓异常: {e}")
    
    async def _handle_existing_position_signal(self, position: Position, signal: Signal):
        """处理已有持仓的信号"""
        # 如果信号与持仓方向相反，考虑平仓
        signal_side = 'long' if signal.signal_type == 'buy' else 'short'
        
        if signal_side != position.side:
            self.logger.info(f"收到反向信号，考虑平仓: {position.symbol}")
            await self._close_position(position, "反向信号")
    
    async def _update_positions(self):
        """更新持仓状态"""
        for position_id, position in list(self.positions.items()):
            try:
                current_price = self.price_cache.get(position.symbol)
                if current_price:
                    position.update_pnl(current_price)
                    
            except Exception as e:
                self.logger.error(f"更新持仓状态失败 {position_id}: {e}")
    
    async def _check_exit_conditions(self):
        """检查平仓条件"""
        for position_id, position in list(self.positions.items()):
            try:
                if position.is_closing:
                    continue
                
                # 刚开仓的持仓等待5秒再检查平仓条件，避免价格波动误触发
                from datetime import datetime, timedelta
                if datetime.now() - position.entry_time < timedelta(seconds=5):
                    continue
                
                current_price = self.price_cache.get(position.symbol)
                if not current_price:
                    continue
                
                should_exit, reason = position.check_exit_conditions(current_price)
                if should_exit:
                    self.logger.info(f"触发平仓条件: {position.symbol} 方向={position.side} 当前价格={current_price} 原因={reason} 止损={position.stop_loss} 止盈={position.take_profit}")
                    await self._close_position(position, reason)
                    
            except Exception as e:
                self.logger.error(f"检查平仓条件失败 {position_id}: {e}")
    
    async def _close_position(self, position: Position, reason: str):
        """平仓"""
        try:
            position.is_closing = True
            position.close_reason = reason
            
            # 执行平仓 (使用反向下单)
            pos_side = 'long' if position.side == 'long' else 'short'
            close_result = self.client.place_order(
                instId=position.symbol,
                tdMode='cross',
                side='sell' if position.side == 'long' else 'buy',
                ordType='market',
                sz=str(position.size),
                reduceOnly=True,
                posSide=pos_side  # 指定持仓方向，避免OKX接口报错
            )
            
            if close_result and close_result.get('code') == '0':
                # 计算实际盈亏
                close_price = close_result.get('close_price', 0)
                close_fee = close_result.get('fee', 0)
                
                if close_price > 0:
                    position.update_pnl(close_price, close_fee)
                
                # 更新策略余额和统计
                strategy = self.strategy_manager.strategies.get(position.strategy_id)
                if strategy:
                    strategy.balance += position.size + position.unrealized_pnl
                    strategy.update_statistics({
                        'pnl': position.unrealized_pnl,
                        'close_reason': reason
                    })
                
                # 记录交易
                await self._record_trade('close', position)
                
                # 从持仓列表移除
                for pos_id, pos in list(self.positions.items()):
                    if pos is position:
                        del self.positions[pos_id]
                        break
                
                self.logger.info(f"平仓成功: {position.symbol} {reason} 盈亏: {position.unrealized_pnl:.2f}")
                
                # 平仓后重新激活策略信号检测
                await self._reactivate_strategy_after_close(position.strategy_id)
                
            else:
                self.logger.error(f"平仓失败: {position.symbol} - {close_result}")
                position.is_closing = False
                
        except Exception as e:
            self.logger.error(f"平仓异常: {e}")
            position.is_closing = False
    
    async def _reactivate_strategy_after_close(self, strategy_id: str):
        """平仓后重新激活策略信号检测"""
        try:
            strategy = self.strategy_manager.strategies.get(strategy_id)
            if strategy:
                self.logger.info(f"策略 {strategy_id} 平仓完成，重新激活信号检测")
                
                # 更新账户余额信息
                balance_info = self.client.get_account_balance()
                if balance_info and balance_info.get('code') == '0':
                    data = balance_info.get('data', [])
                    if data and data[0].get('details'):
                        for detail in data[0]['details']:
                            if detail.get('ccy') == 'USDT':
                                self.total_balance = float(detail.get('bal', 0))
                                self.available_balance = float(detail.get('availBal', 0))
                                break
                
                self.logger.info(f"更新后余额 - 总余额: ${self.total_balance:.2f}, "
                               f"可用余额: ${self.available_balance:.2f}")
                
                # 如果有可用余额，触发立即信号检测
                if self.available_balance > 100:  # 至少100USDT才能交易
                    self.logger.info("余额充足，将在下次整分钟时重新检测信号")
                else:
                    self.logger.info("可用余额不足，继续监控现有持仓")
                    
        except Exception as e:
            self.logger.error(f"重新激活策略失败: {e}")
    
    def _get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """根据交易对获取持仓"""
        for position in self.positions.values():
            if position.symbol == symbol:
                return position
        return None
    
    def _update_risk_metrics(self):
        """更新风险指标"""
        try:
            # 计算总盈亏
            total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            
            # 计算已用余额
            used_balance = sum(pos.size for pos in self.positions.values())
            
            # 更新风险指标
            position_details = [pos.to_dict() for pos in self.positions.values()]
            
            self.risk_manager.update_risk_metrics(
                total_balance=self.total_balance + total_pnl,
                used_balance=used_balance,
                total_pnl=total_pnl,
                active_positions=len(self.positions),
                position_details=position_details
            )
            
        except Exception as e:
            self.logger.error(f"更新风险指标失败: {e}")
    
    async def _record_trade(self, action: str, position: Position, signal: Signal = None):
        """记录交易"""
        try:
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'action': action,  # 'open' or 'close'
                'symbol': position.symbol,
                'side': position.side,
                'size': position.size,
                'price': position.entry_price,
                'strategy_id': position.strategy_id,
                'pnl': position.unrealized_pnl if action == 'close' else 0,
                'reason': position.close_reason if action == 'close' else 'signal',
                'order_id': position.order_id
            }
            
            if signal:
                trade_record['signal_strength'] = signal.strength
                trade_record['signal_metadata'] = signal.metadata
            
            # 保存到文件
            trades = []
            if self.trades_file.exists():
                with open(self.trades_file, 'r', encoding='utf-8') as f:
                    trades = json.load(f)
            
            trades.append(trade_record)
            
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                json.dump(trades, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"记录交易失败: {e}")
    
    def get_trading_status(self) -> Dict[str, Any]:
        """获取交易状态"""
        # 计算总盈亏
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        return {
            'timestamp': datetime.now().isoformat(),
            'is_running': self.is_running,
            'balance': {
                'total': self.total_balance,
                'available': self.available_balance,
                'unrealized_pnl': total_unrealized_pnl,
                'net_balance': self.total_balance + total_unrealized_pnl
            },
            'positions': {
                'count': len(self.positions),
                'details': [pos.to_dict() for pos in self.positions.values()]
            },
            'strategies': self.strategy_manager.get_strategies_status(),
            'risk': self.risk_manager.get_risk_summary()
        }
    
    def _normalize_order_size(self, symbol: str, size: float) -> float:
        """
        规范化订单数量以符合交易所的最小单位要求
        
        Args:
            symbol: 交易对符号
            size: 原始订单大小
            
        Returns:
            float: 规范化后的订单数量
        """
        try:
            # 对于BTC-USDT-SWAP，使用0.01作为最小单位
            if symbol == "BTC-USDT-SWAP":
                min_size = 0.01
            else:
                # 从配置中获取合约规格
                symbol_config = self.config.get('symbol_settings', {}).get(symbol, {})
                min_size = symbol_config.get('min_size', 1)
            
            # 向上取整到最小单位的倍数（保留2位小数）
            import math
            normalized_size = math.ceil(size / min_size) * min_size
            normalized_size = round(normalized_size, 2)  # 保留2位小数
            
            # 确保至少是最小订单数量
            if normalized_size < min_size:
                normalized_size = min_size
            
            self.logger.info(f"订单数量规范化: {symbol} {size:.4f} -> {normalized_size:.4f} (min_size={min_size})")
            return normalized_size
            
        except Exception as e:
            self.logger.error(f"订单数量规范化失败: {e}")
            # 默认情况下使用原始大小，保留2位小数
            return round(max(0.01, size), 2)
    
    def _convert_usdt_to_contracts(self, symbol: str, usdt_amount: float, price: float) -> float:
        """
        将USDT金额转换为合约张数
        
        Args:
            symbol: 交易对符号
            usdt_amount: USDT金额
            price: 当前价格
            
        Returns:
            float: 合约张数
        """
        try:
            # 获取合约规格
            symbol_config = self.config.get('symbol_settings', {}).get(symbol, {})
            contract_value = symbol_config.get('contract_value', 0.01)  # 默认0.01 BTC/张
            
            # 计算：USDT金额 -> BTC数量 -> 合约张数
            btc_amount = usdt_amount / price
            contracts = btc_amount / contract_value
            
            self.logger.debug(f"仓位转换: {usdt_amount} USDT @ {price} = {btc_amount:.4f} BTC = {contracts:.2f}张")
            return contracts
            
        except Exception as e:
            self.logger.error(f"USDT转合约张数失败: {e}")
            return 0
    
    def _calculate_max_affordable_contracts(self, symbol: str, available_usdt: float, price: float) -> float:
        """
        计算可承受的最大合约张数
        
        Args:
            symbol: 交易对符号
            available_usdt: 可用USDT
            price: 当前价格
            
        Returns:
            float: 最大合约张数
        """
        try:
            # 获取杠杆倍数
            leverage = self.config.get('position_management', {}).get('default_leverage', 10)
            
            # 计算最大可用金额（考虑杠杆）
            max_usdt_with_leverage = available_usdt * leverage
            
            # 转换为合约张数
            max_contracts = self._convert_usdt_to_contracts(symbol, max_usdt_with_leverage, price)
            
            return max_contracts
            
        except Exception as e:
            self.logger.error(f"计算最大合约张数失败: {e}")
            return 0
    
    def _calculate_optimal_leverage(self, symbol: str, contracts: int, price: float, available_funds: float) -> int:
        """
        计算最优杠杆倍数
        目标：风险为总资金的1.5%，尽可能使杠杆小
        
        Args:
            symbol: 交易对符号
            contracts: 合约张数
            price: 当前价格
            available_funds: 可用资金
            
        Returns:
            int: 最优杠杆倍数
        """
        try:
            # 获取配置
            symbol_config = self.config.get('symbol_settings', {}).get(symbol, {})
            contract_value = symbol_config.get('contract_value', 0.01)  # BTC合约价值
            max_leverage = symbol_config.get('max_leverage', 50)
            
            # 获取手续费配置
            fees_config = self.config.get('fees', {})
            taker_fee = fees_config.get('taker_fee', 0.0005)  # 0.05%
            slippage = fees_config.get('slippage_estimate', 0.0001)  # 0.01%
            
            # 计算持仓价值（USDT）
            position_value_btc = contracts * contract_value
            position_value_usdt = position_value_btc * price
            
            # 计算交易成本（开仓+平仓手续费+滑点）
            trading_cost_rate = (taker_fee * 2) + slippage  # 开仓+平仓+滑点
            trading_cost_usdt = position_value_usdt * trading_cost_rate
            
            # 目标风险：总资金的1.5%
            target_risk_rate = 0.015
            target_risk_usdt = available_funds * target_risk_rate
            
            # 检查持仓是否过大
            if position_value_usdt > available_funds * 0.5:  # 持仓超过50%资金
                self.logger.warning(f"持仓价值过大 ({position_value_usdt:.2f} USDT > 50%资金)，使用保守杠杆")
                # 使用保守的计算方式
                conservative_leverage = max(2, min(10, int(available_funds / position_value_usdt * 20)))
                return conservative_leverage
            
            # 可承受的价格变动（扣除交易成本后）
            available_risk_usdt = target_risk_usdt - trading_cost_usdt
            
            if available_risk_usdt <= 0:
                self.logger.warning("交易成本超过风险预算，使用最小杠杆")
                return 2
            
            # 计算所需的保证金来满足风险要求
            # 保证金应该等于可承受风险
            required_margin = available_risk_usdt
            
            # 计算杠杆：持仓价值 / 所需保证金
            calculated_leverage = position_value_usdt / required_margin
            
            # 向上取整并限制范围
            import math
            optimal_leverage = max(2, min(max_leverage, int(math.ceil(calculated_leverage))))
            
            # 计算实际风险
            actual_margin = position_value_usdt / optimal_leverage
            actual_total_risk = actual_margin + trading_cost_usdt
            actual_risk_rate = actual_total_risk / available_funds
            
            # 如果风险仍然过高，降低杠杆
            if actual_risk_rate > target_risk_rate * 1.5:  # 超过目标1.5倍
                self.logger.warning("风险过高，降低杠杆")
                safe_leverage = max(2, int(position_value_usdt / (target_risk_usdt - trading_cost_usdt)))
                optimal_leverage = min(optimal_leverage, safe_leverage)
            
            # 重新计算实际风险
            actual_margin = position_value_usdt / optimal_leverage
            actual_total_risk = actual_margin + trading_cost_usdt
            actual_risk_rate = actual_total_risk / available_funds
            
            self.logger.info(f"杠杆计算: {contracts}张 @ {price}")
            self.logger.info(f"  持仓价值: {position_value_usdt:.2f} USDT")
            self.logger.info(f"  交易成本: {trading_cost_usdt:.2f} USDT ({trading_cost_rate:.3%})")
            self.logger.info(f"  最优杠杆: {optimal_leverage}x")
            self.logger.info(f"  所需保证金: {actual_margin:.2f} USDT")
            self.logger.info(f"  总风险: {actual_total_risk:.2f} USDT ({actual_risk_rate:.2%})")
            
            return optimal_leverage
            
        except Exception as e:
            self.logger.error(f"计算最优杠杆失败: {e}")
            return 10  # 默认杠杆