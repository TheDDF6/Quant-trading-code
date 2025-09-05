# okx_client.py - 基于官方 python-okx SDK 的客户端
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from okx.Account import AccountAPI
from okx.Trade import TradeAPI
from okx.MarketData import MarketAPI
from okx.PublicData import PublicAPI

class OKXClient:
    """OKX交易所API客户端 - 基于官方SDK"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str, sandbox: bool = True):
        """
        初始化OKX客户端
        
        Args:
            api_key: API密钥
            secret_key: 密钥
            passphrase: 口令
            sandbox: 是否使用沙盒环境（测试用）
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.sandbox_mode = sandbox
        
        # 初始化logger
        self.logger = logging.getLogger(__name__)
        
        # 时间同步相关
        self.server_time_offset = 0  # 服务器时间与本地时间的偏移（毫秒）
        self.last_sync_time = 0  # 上次同步时间
        self.beijing_tz = timezone(timedelta(hours=8))  # 北京时区
        
        # 初始化官方SDK客户端
        try:
            # 通用参数
            common_params = {
                'api_key': api_key,
                'api_secret_key': secret_key,
                'passphrase': passphrase,
                'domain': 'https://www.okx.com',
                'debug': False
            }
            
            # 减少HTTP请求日志噪音
            logging.getLogger("httpx").setLevel(logging.WARNING)
            
            if sandbox:
                # 沙盒环境
                common_params['flag'] = '1'  # 1表示demo trading (沙盒模式)
                self.sandbox_balance = 1000.0  # 沙盒模式虚拟余额
                self.logger.info("初始化沙盒模式客户端（模拟交易）")
            else:
                # 实盘环境
                common_params['flag'] = '0'  # 0表示live trading (实盘模式)
                self.logger.info("初始化实盘模式客户端（真实资金）")
            
            # 初始化各个API模块
            self.account_api = AccountAPI(**common_params)
            self.trade_api = TradeAPI(**common_params)
            self.market_api = MarketAPI(**common_params)
            self.public_api = PublicAPI(**common_params)
                
        except Exception as e:
            self.logger.error(f"初始化OKX客户端失败: {e}")
            raise
    
    def get_account_balance(self) -> Dict:
        """获取账户余额"""
        try:
            if self.sandbox_mode:
                # 沙盒环境使用虚拟余额
                self.logger.info("沙盒模式：使用模拟账户余额")
                balance_str = f"{self.sandbox_balance:.2f}"
                return {
                    'code': '0',
                    'msg': '',
                    'data': [{
                        'details': [{
                            'ccy': 'USDT',
                            'bal': balance_str,
                            'availBal': balance_str
                        }]
                    }]
                }
            else:
                # 实盘环境使用官方SDK
                response = self.account_api.get_account_balance()
                self.logger.debug(f"账户余额响应: {response}")
                return response
                
        except Exception as e:
            self.logger.error(f"获取账户余额失败: {e}")
            raise
    
    def get_positions(self, instType: str = "SWAP") -> Dict:
        """
        获取持仓信息
        
        Args:
            instType: 产品类型 SPOT现货 SWAP永续合约
        """
        try:
            if self.sandbox_mode:
                # 沙盒环境返回空持仓
                self.logger.info("沙盒模式：返回空持仓信息")
                return {
                    'code': '0',
                    'msg': '',
                    'data': []
                }
            else:
                # 实盘环境使用官方SDK
                response = self.account_api.get_positions(instType=instType)
                self.logger.debug(f"持仓信息响应: {response}")
                return response
                
        except Exception as e:
            self.logger.error(f"获取持仓信息失败: {e}")
            # 网络错误不抛出异常，返回空结果
            return {'code': '1', 'msg': str(e), 'data': []}
    
    def get_orders(self, instType: str = "SWAP", state: str = "live") -> Dict:
        """
        获取订单信息
        
        Args:
            instType: 产品类型 SPOT现货 SWAP永续合约
            state: 订单状态 live活跃 filled已成交 canceled已撤销
        """
        try:
            if self.sandbox_mode:
                # 沙盒环境返回空订单
                self.logger.info("沙盒模式：返回空订单信息")
                return {
                    'code': '0',
                    'msg': '',
                    'data': []
                }
            else:
                # 实盘环境使用官方SDK - 使用正确的方法名
                response = self.trade_api.get_order_list(instType=instType, state=state)
                self.logger.debug(f"订单信息响应: {response}")
                return response
                
        except Exception as e:
            self.logger.error(f"获取订单信息失败: {e}")
            # 网络错误不抛出异常，返回空结果
            return {'code': '1', 'msg': str(e), 'data': []}
    
    def get_ticker(self, instId: str) -> Dict:
        """获取单个产品行情信息"""
        try:
            response = self.market_api.get_ticker(instId=instId)
            self.logger.debug(f"行情数据响应: {response}")
            return response
        except Exception as e:
            self.logger.error(f"获取行情数据失败: {e}")
            raise
    
    def place_order(self, instId: str, tdMode: str, side: str, ordType: str, 
                   sz: str, px: Optional[str] = None, lever: Optional[str] = None,
                   tpTriggerPx: Optional[str] = None, tpOrdPx: Optional[str] = None,
                   slTriggerPx: Optional[str] = None, slOrdPx: Optional[str] = None,
                   reduceOnly: Optional[bool] = None, posSide: Optional[str] = None) -> Dict:
        """
        下单
        
        Args:
            instId: 产品ID 如 BTC-USDT-SWAP
            tdMode: 交易模式 cross全仓 isolated逐仓 cash现金
            side: 订单方向 buy买入 sell卖出
            ordType: 订单类型 market市价 limit限价
            sz: 委托数量
            px: 委托价格（限价单必填）
            lever: 杠杆倍数
            tpTriggerPx: 止盈触发价
            tpOrdPx: 止盈委托价
            slTriggerPx: 止损触发价
            slOrdPx: 止损委托价
            reduceOnly: 是否只减仓（平仓时使用）
            posSide: 持仓方向（net净持仓/long多/short空）
        """
        try:
            if self.sandbox_mode:
                # 沙盒环境模拟下单成功
                import uuid
                order_id = str(uuid.uuid4())
                
                # 检查是否有止盈止损
                stop_info = ""
                if tpTriggerPx:
                    stop_info += f", 止盈: {tpTriggerPx}"
                if slTriggerPx:
                    stop_info += f", 止损: {slTriggerPx}"
                    
                self.logger.info(f"沙盒模式：模拟下单成功，订单ID: {order_id}{stop_info}")
                return {
                    'code': '0',
                    'msg': '',
                    'data': [{
                        'ordId': order_id,
                        'sCode': '0',
                        'sMsg': 'success'
                    }]
                }
            else:
                # 构建下单参数
                order_params = {
                    "instId": instId,
                    "tdMode": tdMode,
                    "side": side,
                    "ordType": ordType,
                    "sz": sz
                }
                
                # 添加可选参数
                if px:
                    order_params["px"] = px
                if reduceOnly is not None:
                    order_params["reduceOnly"] = reduceOnly
                if posSide:
                    order_params["posSide"] = posSide
                
                # 处理止盈止损 - 使用attachAlgoOrds参数
                attach_algo_ords = []
                
                if tpTriggerPx or slTriggerPx:
                    # 创建单个止盈止损对象
                    algo_ord = {}
                    
                    if tpTriggerPx:
                        algo_ord["tpTriggerPx"] = str(tpTriggerPx)
                        algo_ord["tpOrdPx"] = str(tpOrdPx or tpTriggerPx)
                        algo_ord["tpTriggerPxType"] = "last"  # 使用最新价格触发
                    
                    if slTriggerPx:
                        algo_ord["slTriggerPx"] = str(slTriggerPx)
                        algo_ord["slOrdPx"] = str(slOrdPx or slTriggerPx)
                        algo_ord["slTriggerPxType"] = "last"  # 使用最新价格触发
                    
                    attach_algo_ords.append(algo_ord)
                    order_params["attachAlgoOrds"] = attach_algo_ords
                    
                    self.logger.info("下单附带止盈止损:")
                    if tpTriggerPx:
                        self.logger.info(f"  止盈触发价: {tpTriggerPx}")
                    if slTriggerPx:
                        self.logger.info(f"  止损触发价: {slTriggerPx}")
                
                # 使用官方SDK下单（包含止盈止损）
                response = self.trade_api.place_order(**order_params)
                self.logger.debug(f"下单响应: {response}")
                
                return response
                
        except Exception as e:
            self.logger.error(f"下单失败: {e}")
            raise
    
    def set_leverage(self, instId: str, lever: str, mgnMode: str = "cross") -> Dict:
        """
        设置杠杆倍数
        
        Args:
            instId: 产品ID
            lever: 杠杆倍数
            mgnMode: 保证金模式
        """
        try:
            if self.sandbox_mode:
                # 沙盒环境模拟设置杠杆成功
                self.logger.info(f"沙盒模式：模拟设置杠杆 {lever}x 成功")
                return {
                    'code': '0',
                    'msg': '',
                    'data': [{
                        'instId': instId,
                        'lever': lever,
                        'mgnMode': mgnMode
                    }]
                }
            else:
                # 使用官方SDK设置杠杆
                response = self.account_api.set_leverage(
                    instId=instId,
                    lever=lever,
                    mgnMode=mgnMode
                )
                self.logger.debug(f"设置杠杆响应: {response}")
                return response
                
        except Exception as e:
            self.logger.error(f"设置杠杆失败: {e}")
            raise
    
    def get_candlesticks(self, instId: str, bar: str = "5m", limit: int = 100) -> Dict:
        """
        获取K线数据
        
        Args:
            instId: 产品ID
            bar: K线粒度 1m 3m 5m 15m 30m 1H 2H 4H 6H 12H 1D 1W 1M
            limit: 返回数量
        """
        try:
            response = self.market_api.get_candlesticks(
                instId=instId,
                bar=bar,
                limit=str(limit)
            )
            self.logger.debug(f"K线数据响应: {response}")
            return response
        except Exception as e:
            self.logger.error(f"获取K线数据失败: {e}")
            raise
    
    def get_instrument_info(self, instId: str) -> Dict:
        """
        获取交易产品基础信息（用于获取合约面值等）
        
        Args:
            instId: 产品ID，如 BTC-USDT-SWAP
            
        Returns:
            产品信息字典
        """
        try:
            if self.sandbox_mode:
                # 沙盒模式返回模拟的合约信息
                self.logger.info("沙盒模式：返回模拟合约信息")
                
                # BTC-USDT-SWAP的标准配置
                if "BTC-USDT-SWAP" in instId:
                    return {
                        'success': True,
                        'data': {
                            'instId': instId,
                            'instType': 'SWAP',
                            'ctVal': '0.01',  # 0.01 BTC
                            'ctValCcy': 'BTC',
                            'tickSz': '0.1',  # 价格精度
                            'lotSz': '1',     # 数量精度（张）
                            'minSz': '1',     # 最小下单数量
                            'source': 'sandbox_simulation'
                        }
                    }
                else:
                    # 通用模拟配置
                    return {
                        'success': True,
                        'data': {
                            'instId': instId,
                            'ctVal': '0.01',
                            'ctValCcy': 'BTC',
                            'source': 'sandbox_simulation'
                        }
                    }
            else:
                # 实盘环境获取真实产品信息
                instType = "SWAP" if "SWAP" in instId else "SPOT"
                response = self.account_api.get_instruments(instType=instType, instId=instId)
                
                if response.get('code') == '0' and response.get('data'):
                    instrument_data = response['data'][0]
                    
                    result = {
                        'success': True,
                        'data': {
                            'instId': instrument_data.get('instId'),
                            'instType': instrument_data.get('instType'),
                            'ctVal': instrument_data.get('ctVal', '1'),      # 合约面值
                            'ctValCcy': instrument_data.get('ctValCcy'),     # 面值币种
                            'tickSz': instrument_data.get('tickSz'),         # 价格精度
                            'lotSz': instrument_data.get('lotSz'),           # 数量精度
                            'minSz': instrument_data.get('minSz'),           # 最小数量
                            'lever': instrument_data.get('lever'),           # 最大杠杆
                            'source': 'okx_api',
                            'raw_data': instrument_data
                        }
                    }
                    
                    self.logger.info(f"获取产品信息成功 - {instId}, 面值: {result['data']['ctVal']} {result['data'].get('ctValCcy', '')}")
                    return result
                else:
                    self.logger.error(f"获取产品信息失败: {response}")
                    return {"success": False, "error": "API响应异常", "response": response}
                    
        except Exception as e:
            self.logger.error(f"获取产品信息失败: {e}")
            return {"success": False, "error": str(e)}
    
    def update_sandbox_balance(self, pnl: float):
        """
        更新沙盒模式下的虚拟余额
        
        Args:
            pnl: 盈亏金额（正数为盈利，负数为亏损）
        """
        if self.sandbox_mode:
            self.sandbox_balance += pnl
            self.logger.info(f"沙盒模式：余额更新 {pnl:+.2f} USDT，当前余额: {self.sandbox_balance:.2f} USDT")
    
    def test_api_permissions(self) -> Dict:
        """
        测试API权限 - 使用最基础的账户信息接口
        """
        try:
            # 使用官方SDK测试基础权限
            response = self.account_api.get_account_config()
            
            self.logger.info("API基础权限测试成功")
            return {"success": True, "data": response}
            
        except Exception as e:
            self.logger.error(f"❌ API权限测试失败: {e}")
            return {"success": False, "error": str(e)}
            
    def test_derivatives_permissions(self) -> Dict:
        """
        测试衍生品交易权限
        """
        try:
            # 测试获取持仓信息（需要衍生品权限）
            response = self.account_api.get_positions(instType="SWAP")
            
            self.logger.info("衍生品权限测试成功")
            return {"success": True, "data": response}
            
        except Exception as e:
            self.logger.error(f"❌ 衍生品权限测试失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_trading_fee_rates(self, instType: str = "SWAP", instId: str = None) -> Dict:
        """
        获取当前账户的实际交易手续费费率
        
        Args:
            instType: 产品类型 SPOT/MARGIN/SWAP/FUTURES/OPTION
            instId: 产品ID（可选），如 BTC-USDT
            
        Returns:
            包含手续费信息的字典
        """
        try:
            if self.sandbox_mode:
                # 沙盒模式返回模拟费率
                self.logger.info("沙盒模式：返回模拟手续费费率")
                return {
                    'success': True,
                    'data': {
                        'level': 'VIP_1',
                        'maker_rate': 0.0002,  # 0.02% - 用户实际费率
                        'taker_rate': 0.0005,  # 0.05% - 用户实际费率  
                        'instType': instType,
                        'source': 'sandbox_simulation_actual_rates'
                    }
                }
            else:
                # 实盘环境获取真实费率
                params = {
                    "instType": instType
                }
                if instId:
                    params["instId"] = instId
                
                response = self.account_api.get_fee_rates(**params)
                
                if response.get('code') == '0' and response.get('data'):
                    fee_data = response['data'][0]
                    
                    # 解析费率数据
                    level = fee_data.get('level', 'unknown')
                    maker_rate = float(fee_data.get('maker', 0))
                    taker_rate = float(fee_data.get('taker', 0))
                    
                    # 对于USDT合约，优先使用U合约费率
                    if instType in ['SWAP', 'FUTURES'] and fee_data.get('makerU'):
                        maker_rate = float(fee_data.get('makerU', maker_rate))
                        taker_rate = float(fee_data.get('takerU', taker_rate))
                    
                    # 转换费率（OKX返回的可能是负数表示返佣，正数表示收费）
                    # 统一转换为正数表示费率大小
                    maker_rate = abs(maker_rate)
                    taker_rate = abs(taker_rate)
                    
                    result = {
                        'success': True,
                        'data': {
                            'level': level,
                            'maker_rate': maker_rate,
                            'taker_rate': taker_rate,
                            'instType': instType,
                            'source': 'okx_api',
                            'raw_response': fee_data
                        }
                    }
                    
                    self.logger.info(f"获取手续费费率成功 - 等级: {level}, 挂单: {maker_rate*100:.4f}%, 吃单: {taker_rate*100:.4f}%")
                    return result
                else:
                    self.logger.error(f"获取手续费费率失败: {response}")
                    return {"success": False, "error": "API响应异常", "response": response}
                    
        except Exception as e:
            self.logger.error(f"获取手续费费率失败: {e}")
            return {"success": False, "error": str(e)}
    
    def sync_server_time(self) -> bool:
        """
        同步服务器时间
        
        Returns:
            bool: 同步是否成功
        """
        try:
            # 记录请求前的本地时间
            local_time_before = int(time.time() * 1000)
            
            # 获取服务器时间
            response = self.public_api.get_system_time()
            
            # 记录响应后的本地时间
            local_time_after = int(time.time() * 1000)
            
            if response.get('code') == '0' and response.get('data'):
                server_time = int(response['data'][0]['ts'])
                
                # 估算网络延迟
                network_delay = (local_time_after - local_time_before) // 2
                
                # 计算时间偏移（考虑网络延迟）
                self.server_time_offset = server_time - local_time_before - network_delay
                self.last_sync_time = time.time()
                
                self.logger.info(f"服务器时间同步成功，偏移: {self.server_time_offset}ms，网络延迟: {network_delay}ms")
                return True
            else:
                self.logger.error(f"获取服务器时间失败: {response}")
                return False
                
        except Exception as e:
            self.logger.error(f"同步服务器时间失败: {e}")
            return False
    
    def get_server_time(self) -> datetime:
        """
        获取同步的服务器时间（北京时间）
        
        Returns:
            datetime: 服务器时间（北京时区）
        """
        # 如果超过5分钟没有同步，重新同步
        if time.time() - self.last_sync_time > 300:
            self.sync_server_time()
        
        # 计算当前的服务器时间
        local_time_ms = int(time.time() * 1000)
        server_time_ms = local_time_ms + self.server_time_offset
        server_time_s = server_time_ms / 1000
        
        # 转换为北京时间
        server_dt = datetime.fromtimestamp(server_time_s, tz=self.beijing_tz)
        return server_dt
    
    def get_beijing_time(self) -> datetime:
        """
        获取北京时间（基于服务器时间同步）
        
        Returns:
            datetime: 北京时间
        """
        return self.get_server_time()
    
    def should_sync_time(self) -> bool:
        """
        检查是否需要重新同步时间
        
        Returns:
            bool: 是否需要同步
        """
        return time.time() - self.last_sync_time > 300  # 5分钟重新同步一次
    
    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 尝试获取系统时间来测试连接
            response = self.public_api.get_system_time()
            
            if response.get('code') == '0':
                self.logger.info("API连接测试成功")
                return True
            else:
                self.logger.error(f"API连接测试失败: {response}")
                return False
                
        except Exception as e:
            # More defensive logging to avoid encoding issues
            try:
                self.logger.error(f"API连接测试失败: {str(e)}")
            except:
                print(f"API连接测试失败: {e}")
            return False