#!/usr/bin/env python3
"""
检查当前持仓和账户状态
"""

import sys
import json
import logging
from core.okx_client import OKXClient

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """加载配置文件"""
    import os
    
    possible_paths = [
        'config/trading_config.json',
        'live_trading/config/trading_config.json',
        os.path.join(os.path.dirname(__file__), 'config', 'trading_config.json'),
        'D:/VSC/live_trading/config/trading_config.json'
    ]
    
    for config_path in possible_paths:
        try:
            if os.path.exists(config_path):
                logger.info(f"找到配置文件: {config_path}")
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config
        except Exception as e:
            continue
    
    logger.error("找不到配置文件")
    return None

def main():
    logger.info("检查账户状态和持仓...")
    
    # 加载配置
    config = load_config()
    if not config:
        return
    
    # 初始化客户端
    try:
        client = OKXClient(
            api_key=config['okx']['api_key'],
            secret_key=config['okx']['secret_key'],
            passphrase=config['okx']['passphrase'],
            sandbox=config['okx']['sandbox']
        )
        logger.info("客户端初始化成功")
    except Exception as e:
        logger.error(f"客户端初始化失败: {e}")
        return
    
    # 检查账户余额
    try:
        balance_info = client.get_account_balance()
        if balance_info.get('code') == '0':
            logger.info("=== 账户余额信息 ===")
            account_data = balance_info['data'][0]
            
            # 主要信息
            total_eq = account_data.get('totalEq', '0')
            avail_eq = account_data.get('availEq', '0')
            
            if total_eq and total_eq != '':
                logger.info(f"账户总权益: ${float(total_eq):.2f}")
            if avail_eq and avail_eq != '':
                logger.info(f"可用权益: ${float(avail_eq):.2f}")
            
            # USDT详情
            for detail in account_data['details']:
                if detail['ccy'] == 'USDT':
                    logger.info(f"USDT余额: {detail['cashBal']}")
                    logger.info(f"USDT可用: {detail['availBal']}")
                    logger.info(f"USDT冻结: {detail['frozenBal']}")
                    logger.info(f"USDT占用保证金: {detail['eq']} - {detail['availEq']} = {float(detail['eq']) - float(detail['availEq']):.2f}")
                    break
    except Exception as e:
        logger.error(f"获取余额失败: {e}")
    
    # 检查当前持仓
    try:
        # 使用 OKX API 获取持仓
        positions = client.account_api.get_positions()
        logger.info(f"=== 当前持仓 ===")
        logger.info(f"持仓响应: {positions}")
        
        if positions.get('code') == '0':
            position_data = positions.get('data', [])
            if position_data:
                for pos in position_data:
                    if float(pos.get('pos', 0)) != 0:  # 有持仓
                        logger.info(f"合约: {pos['instId']}")
                        logger.info(f"持仓方向: {pos['posSide']}")
                        logger.info(f"持仓数量: {pos['pos']} 张")
                        logger.info(f"平均价格: ${pos['avgPx']}")
                        logger.info(f"持仓价值: ${pos['notionalUsd']}")
                        logger.info(f"占用保证金: ${pos['margin']}")
                        logger.info(f"未实现盈亏: ${pos['upl']}")
                        logger.info("-" * 40)
            else:
                logger.info("暂无持仓")
        else:
            logger.error(f"获取持仓失败: {positions}")
            
    except Exception as e:
        logger.error(f"获取持仓异常: {e}")
    
    # 检查未成交订单
    try:
        orders = client.trade_api.get_order_list(instType="SWAP", state="live")
        logger.info(f"=== 未成交订单 ===")
        
        if orders.get('code') == '0':
            order_data = orders.get('data', [])
            if order_data:
                for order in order_data:
                    logger.info(f"订单ID: {order['ordId']}")
                    logger.info(f"合约: {order['instId']}")
                    logger.info(f"方向: {order['side']}")
                    logger.info(f"数量: {order['sz']} 张")
                    logger.info(f"价格: ${order.get('px', 'Market')}")
                    logger.info(f"状态: {order['state']}")
                    logger.info("-" * 40)
            else:
                logger.info("暂无未成交订单")
    except Exception as e:
        logger.error(f"获取订单异常: {e}")

if __name__ == "__main__":
    main()