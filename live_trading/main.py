# main.py - 实盘交易系统主程序
import sys
import os
from pathlib import Path
import logging

# 设置编码，解决Windows下中文显示问题
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
sys.stderr.reconfigure(encoding='utf-8', errors='ignore')

# 设置工作目录为脚本所在目录
script_dir = Path(__file__).parent
os.chdir(script_dir)

# 添加路径
sys.path.append(str(script_dir))

from core.trading_engine_v2 import MultiStrategyTradingEngine
from config.config import config
from core.strategy_registry import strategy_registry
from config.multi_config_manager import MultiStrategyConfigManager, StrategyConfig

def show_banner():
    """显示程序横幅"""
    banner = """
    ================================================================
                        OKX多策略交易系统                         
                   支持多种策略并行自动化交易                    
                                                              
      新功能: 多策略并行、智能资金分配、交互式配置           
      警告: 实盘交易存在风险，可能导致资金损失                
      建议: 先使用沙盒环境测试，确保策略有效性               
                                                              
    ================================================================
    """
    print(banner)

def show_config_status():
    """显示配置状态"""
    print("\n当前配置:")
    print("="*50)
    
    # API配置状态
    if config.validate_api_config():
        print("[OK] API配置: 已设置")
    else:
        print("[X] API配置: 未设置")
        print("   请在 config/trading_config.json 中设置API密钥")
    
    # 交易配置
    print(f"[币] 交易对: {config.get_symbol()}")
    print(f"[险] 单笔风险: {config.get_risk_per_trade()*100:.1f}%")
    print(f"[钱] 初始资金: ${config.get('trading', 'initial_balance'):,.2f}")
    print(f"[杆] 最大杠杆: {config.get('trading', 'max_leverage')}x")
    
    # 环境状态
    if config.is_sandbox():
        print("[测] 运行模式: 沙盒测试环境")
    else:
        print("[实] 运行模式: 实盘环境 (真实资金)")
    
    # 手续费设置
    maker_fee = config.get_maker_fee()
    taker_fee = config.get_taker_fee()
    slippage = config.get_slippage_rate()
    user_level = config.get_user_level()
    print(f"[费] 用户等级: {user_level} (普通用户)")
    print(f"[费] 挂单手续费: {maker_fee*100:.3f}% (Maker)")
    print(f"[费] 吃单手续费: {taker_fee*100:.3f}% (Taker - 主要使用)")
    print(f"[费] 预估滑点: {slippage*100:.3f}%")
    
    # 风控设置
    max_daily_loss = config.get('risk_management', 'max_daily_loss', 0.05)
    max_consecutive_losses = config.get('risk_management', 'max_consecutive_losses', 3)
    print(f"[控] 日亏损限制: {max_daily_loss*100:.1f}%")
    print(f"[控] 连续亏损限制: {max_consecutive_losses}次")
    
    if config.is_emergency_stop():
        print("[停] 紧急停止: 已激活")
    else:
        print("[OK] 紧急停止: 未激活")
        
    # 策略配置状态
    try:
        multi_config = MultiStrategyConfigManager()
        if multi_config.load_config():
            strategies = multi_config.get_all_strategies_config()
            active_strategies = multi_config.get_active_strategies_config()
            
            # 检查资金分配模式
            fund_mode = multi_config._config_data.get('strategy_manager', {}).get('fund_allocation_mode', 'individual')
            
            print(f"[略] 已配置策略: {len(strategies)} 个")
            print(f"[略] 活跃策略: {len(active_strategies)} 个")
            
            if fund_mode == 'shared_pool':
                print(f"[池] 资金模式: 共享资金池 (先到先得)")
            else:
                total_allocation = sum(s.allocation_ratio for s in active_strategies.values()) * 100
                print(f"[略] 资金分配: {total_allocation:.1f}%")
            
            if len(active_strategies) > 0:
                strategy_names = list(active_strategies.keys())[:2]  # 显示前2个
                display_names = strategy_names + (['...'] if len(active_strategies) > 2 else [])
                print(f"[略] 活跃策略: {', '.join(display_names)}")
        else:
            print("[略] 策略配置: 未初始化")
    except Exception:
        print("[略] 策略配置: 单策略模式")
        
    # 验证手续费配置
    if not config.validate_fees_config():
        print("[警告] 手续费配置可能不合理")

def show_menu():
    """显示主菜单"""
    print("\n" + "="*50)
    print("选择操作:")
    print("="*50)
    print("1. 启动交易引擎")
    print("2. 查看配置状态") 
    print("3. 配置向导")
    print("4. 策略管理")
    print("5. 测试API连接")
    print("6. 查看交易历史")
    print("7. 紧急停止开关")
    print("8. 系统文档")
    print("0. 退出")
    print("="*50)

def setup_wizard():
    """配置向导"""
    print("\n配置向导")
    print("="*30)
    
    # API配置
    print("\n1. API配置 (在OKX官网申请)")
    
    # 检查现有配置
    has_api_config = config.validate_api_config()
    if has_api_config:
        current_key = config.get('okx', 'api_key', '')
        masked_key = current_key[:8] + "..." + current_key[-4:] if len(current_key) > 12 else "已配置"
        print(f"[当前] API Key: {masked_key}")
        print(f"[当前] Secret Key: 已配置")
        print(f"[当前] Passphrase: 已配置")
        
        update_api = input("是否更新API配置? (y/N): ").strip().lower()
        if update_api != 'y':
            print("[跳过] 使用现有API配置")
        else:
            api_key = input("新的API Key: ").strip()
            secret_key = input("新的Secret Key: ").strip()
            passphrase = input("新的Passphrase: ").strip()
            
            if api_key and secret_key and passphrase:
                config.set('okx', 'api_key', api_key)
                config.set('okx', 'secret_key', secret_key)
                config.set('okx', 'passphrase', passphrase)
                print("[OK] API配置已更新")
            else:
                print("[X] 输入无效，保持原配置")
    else:
        print("[未配置] 请输入API配置信息:")
        api_key = input("API Key: ").strip()
        secret_key = input("Secret Key: ").strip()
        passphrase = input("Passphrase: ").strip()
        
        if api_key and secret_key and passphrase:
            config.set('okx', 'api_key', api_key)
            config.set('okx', 'secret_key', secret_key)
            config.set('okx', 'passphrase', passphrase)
            print("[OK] API配置已保存")
        else:
            print("[X] API配置无效，请稍后重新配置")
    
    # 环境选择
    print("\n2. 环境选择")
    current_env = "沙盒环境" if config.is_sandbox() else "实盘环境"
    print(f"[当前] 运行环境: {current_env}")
    print("1. 沙盒环境 (推荐，用于测试)")
    print("2. 实盘环境 (真实资金)")
    
    env_choice = input(f"选择环境 (1/2) [当前: {current_env}，直接回车保持]: ").strip()
    if env_choice == '1':
        config.set('okx', 'sandbox', True)
        print("[OK] 已设置为沙盒环境")
    elif env_choice == '2':
        confirm = input("[!] 确认使用实盘环境? 这将使用真实资金! (yes/no): ").strip().lower()
        if confirm == 'yes':
            config.set('okx', 'sandbox', False)
            print("[OK] 已设置为实盘环境")
        else:
            print("[OK] 保持原环境设置")
    else:
        print("[跳过] 保持原环境设置")
    
    # 交易参数
    print("\n3. 交易参数")
    
    # 初始资金
    try:
        current_balance = config.get('trading', 'initial_balance')
        balance_input = input(f"初始资金 [当前: ${current_balance:,.2f}，直接回车保持]: ").strip()
        if balance_input:
            initial_balance = float(balance_input)
            config.set('trading', 'initial_balance', initial_balance)
            print(f"[OK] 初始资金设置为: ${initial_balance:,.2f}")
        else:
            print(f"[跳过] 保持当前设置: ${current_balance:,.2f}")
    except ValueError:
        print("[错误] 输入无效，保持当前设置")
    
    # 风险比例
    try:
        current_risk = config.get_risk_per_trade() * 100
        risk_input = input(f"单笔风险比例% [当前: {current_risk:.1f}%，直接回车保持]: ").strip()
        if risk_input:
            risk_pct = float(risk_input) / 100
            config.set('trading', 'risk_per_trade', risk_pct)
            print(f"[OK] 风险比例设置为: {risk_pct*100:.1f}%")
        else:
            print(f"[跳过] 保持当前设置: {current_risk:.1f}%")
    except ValueError:
        print("[错误] 输入无效，保持当前设置")
    
    # 最大杠杆
    try:
        current_leverage = config.get('trading', 'max_leverage')
        leverage_input = input(f"最大杠杆倍数 [当前: {current_leverage}x，直接回车保持]: ").strip()
        if leverage_input:
            max_leverage = int(leverage_input)
            config.set('trading', 'max_leverage', max_leverage)
            print(f"[OK] 最大杠杆设置为: {max_leverage}x")
        else:
            print(f"[跳过] 保持当前设置: {current_leverage}x")
    except ValueError:
        print("[错误] 输入无效，保持当前设置")
    
    # 策略配置
    print("\n4. 策略配置")
    configure_strategies_wizard()
    
    print("\n[OK] 配置向导完成!")

def configure_strategies_wizard():
    """策略配置向导"""
    print("\n━━━ 策略配置 ━━━")
    
    # 尝试初始化多策略配置管理器
    try:
        multi_config = MultiStrategyConfigManager()
        if not multi_config.load_config():
            # 如果多策略配置不存在，创建基础配置
            print("🔧 正在初始化多策略配置...")
            multi_config._config_data = {
                "system": {"name": "Multi-Strategy Trading System", "version": "2.0.0"},
                "okx": {
                    "api_key": config.get('okx', 'api_key', ''),
                    "secret_key": config.get('okx', 'secret_key', ''),
                    "passphrase": config.get('okx', 'passphrase', ''),
                    "sandbox": config.is_sandbox()
                },
                "trading_engine": {"main_loop_interval": 10, "data_update_interval": 30},
                "strategy_manager": {"total_balance": config.get('trading', 'initial_balance', 1000.0), "reserved_balance": 0.1},
                "risk_manager": {"max_total_risk": 0.05, "max_daily_loss": 0.03},
                "strategies": {}
            }
            multi_config.save_config()
    except Exception as e:
        print(f"❌ 初始化策略配置失败: {e}")
        print("将跳过策略配置...")
        return
    
    # 显示当前策略状态
    current_strategies = multi_config.get_all_strategies_config()
    print(f"\n当前已配置 {len(current_strategies)} 个策略:")
    
    if current_strategies:
        for strategy_id, strategy_config in current_strategies.items():
            status = "🟢 启用" if strategy_config.active else "⚪ 禁用"
            allocation = strategy_config.allocation_ratio * 100
            symbols = strategy_config.config.get('supported_symbols', ['未设置'])
            print(f"  • {strategy_id} ({strategy_config.class_name}) - {status} - {allocation:.1f}% - {symbols}")
    else:
        print("  暂无配置的策略")
    
    # 显示可用策略类型
    print(f"\n可用的策略类型:")
    available_strategies = strategy_registry.get_available_strategies()
    strategy_info = strategy_registry.get_strategy_info()
    
    strategy_menu = {}
    for i, strategy_type in enumerate(available_strategies, 1):
        info = strategy_info.get(strategy_type, {})
        print(f"  {i}. {strategy_type}")
        print(f"     描述: {info.get('description', '无描述')}")
        print(f"     分类: {info.get('category', '其他')}")
        print(f"     风险: {info.get('risk_level', '未知')}")
        strategy_menu[str(i)] = strategy_type
    
    # 询问是否配置策略
    configure_choice = input(f"\n是否要配置交易策略? (y/N): ").strip().lower()
    if configure_choice != 'y':
        print("[跳过] 策略配置已跳过")
        return
    
    # 策略配置循环
    while True:
        print(f"\n策略管理选项:")
        print("1. 添加新策略")
        print("2. 启用/禁用现有策略") 
        print("3. 删除策略")
        print("4. 查看策略详情")
        print("0. 完成配置")
        
        manage_choice = input("请选择操作 (0-4): ").strip()
        
        if manage_choice == '0':
            break
        elif manage_choice == '1':
            add_strategy_simple(multi_config, strategy_menu)
        elif manage_choice == '2':
            toggle_strategy_simple(multi_config)
        elif manage_choice == '3':
            remove_strategy_simple(multi_config)
        elif manage_choice == '4':
            show_strategy_details(multi_config)
        else:
            print("❌ 无效选择")
    
    # 验证资金分配
    active_strategies = multi_config.get_active_strategies_config()
    total_allocation = sum(s.allocation_ratio for s in active_strategies.values())
    
    if total_allocation > 1.0:
        print(f"⚠️  警告: 活跃策略资金分配总和为 {total_allocation*100:.1f}%，超过100%")
        print("建议调整资金分配比例")
    elif total_allocation == 0:
        print("ℹ️  提示: 当前没有启用任何策略，系统将不会进行自动交易")
    else:
        print(f"✅ 资金分配正常: {total_allocation*100:.1f}%")

def add_strategy_simple(multi_config, strategy_menu):
    """简化的添加策略功能"""
    print(f"\n添加新策略:")
    
    # 选择策略类型
    choice = input(f"请选择策略类型 (1-{len(strategy_menu)}, 回车取消): ").strip()
    if not choice or choice not in strategy_menu:
        print("❌ 操作已取消")
        return
    
    strategy_type = strategy_menu[choice]
    print(f"已选择: {strategy_type}")
    
    # 自动生成策略ID
    strategy_id = f"{strategy_type.lower()}_{len(multi_config.get_all_strategies_config()) + 1}"
    
    # 确保ID唯一
    counter = 1
    base_id = strategy_id
    while multi_config.get_strategy_config(strategy_id):
        counter += 1
        strategy_id = f"{base_id}_{counter}"
    
    print(f"自动生成策略ID: {strategy_id}")
    
    # 获取默认配置
    default_config = strategy_registry.get_default_config(strategy_type)
    
    # 简化参数配置
    print(f"\n配置策略参数:")
    
    # 资金分配
    current_allocation = sum(s.allocation_ratio for s in multi_config.get_active_strategies_config().values())
    remaining = max(0, 1.0 - current_allocation)
    
    print(f"剩余可分配资金: {remaining*100:.1f}%")
    allocation_input = input(f"资金分配比例% (1-{remaining*100:.0f}, 默认 20): ").strip()
    
    try:
        if allocation_input:
            allocation_ratio = min(float(allocation_input) / 100, remaining)
        else:
            allocation_ratio = min(0.2, remaining)
    except ValueError:
        allocation_ratio = min(0.2, remaining)
    
    if allocation_ratio <= 0:
        print("❌ 没有足够的资金分配")
        return
    
    # 交易对配置
    symbols_input = input(f"支持的交易对 (默认: BTC-USDT-SWAP): ").strip()
    if symbols_input:
        symbols = [s.strip().upper() for s in symbols_input.split(',')]
        default_config['supported_symbols'] = symbols
    
    # 创建策略配置
    new_strategy = StrategyConfig(
        strategy_id=strategy_id,
        class_name=strategy_type,
        active=True,
        allocation_ratio=allocation_ratio,
        config=default_config
    )
    
    # 保存配置
    try:
        multi_config.add_strategy_config(new_strategy)
        multi_config.save_config()
        print(f"✅ 策略 '{strategy_id}' 添加成功！分配资金: {allocation_ratio*100:.1f}%")
    except Exception as e:
        print(f"❌ 保存失败: {e}")

def toggle_strategy_simple(multi_config):
    """简化的启用/禁用策略功能"""
    strategies = multi_config.get_all_strategies_config()
    if not strategies:
        print("❌ 暂无可管理的策略")
        return
    
    print(f"\n当前策略:")
    strategy_list = {}
    for i, (strategy_id, config) in enumerate(strategies.items(), 1):
        status = "🟢 启用" if config.active else "⚪ 禁用"
        print(f"  {i}. {strategy_id} - {status}")
        strategy_list[str(i)] = strategy_id
    
    choice = input(f"选择要切换的策略 (1-{len(strategy_list)}, 回车取消): ").strip()
    if not choice or choice not in strategy_list:
        print("❌ 操作已取消")
        return
    
    strategy_id = strategy_list[choice]
    strategy_config = strategies[strategy_id]
    new_status = not strategy_config.active
    
    try:
        multi_config.update_strategy_config(strategy_id, active=new_status)
        multi_config.save_config()
        status_text = "启用" if new_status else "禁用"
        print(f"✅ 策略 '{strategy_id}' 已{status_text}")
    except Exception as e:
        print(f"❌ 操作失败: {e}")

def remove_strategy_simple(multi_config):
    """简化的删除策略功能"""
    strategies = multi_config.get_all_strategies_config()
    if not strategies:
        print("❌ 暂无可删除的策略")
        return
    
    print(f"\n当前策略:")
    strategy_list = {}
    for i, (strategy_id, config) in enumerate(strategies.items(), 1):
        status = "🟢 启用" if config.active else "⚪ 禁用"
        allocation = config.allocation_ratio * 100
        print(f"  {i}. {strategy_id} - {status} - {allocation:.1f}%")
        strategy_list[str(i)] = strategy_id
    
    choice = input(f"选择要删除的策略 (1-{len(strategy_list)}, 回车取消): ").strip()
    if not choice or choice not in strategy_list:
        print("❌ 操作已取消")
        return
    
    strategy_id = strategy_list[choice]
    
    # 确认删除
    confirm = input(f"确认删除策略 '{strategy_id}'? (输入 'yes' 确认): ").strip()
    if confirm != 'yes':
        print("❌ 操作已取消")
        return
    
    try:
        multi_config.remove_strategy_config(strategy_id)
        multi_config.save_config()
        print(f"✅ 策略 '{strategy_id}' 已删除")
    except Exception as e:
        print(f"❌ 删除失败: {e}")

def show_strategy_details(multi_config):
    """显示策略详情"""
    strategies = multi_config.get_all_strategies_config()
    if not strategies:
        print("❌ 暂无策略")
        return
    
    print(f"\n━━━ 策略详细信息 ━━━")
    total_allocation = 0
    
    for strategy_id, config in strategies.items():
        status = "🟢 启用" if config.active else "⚪ 禁用"
        allocation = config.allocation_ratio * 100
        if config.active:
            total_allocation += allocation
            
        print(f"\n📈 {strategy_id}:")
        print(f"  类型: {config.class_name}")
        print(f"  状态: {status}")
        print(f"  资金分配: {allocation:.1f}%")
        print(f"  交易对: {config.config.get('supported_symbols', ['未设置'])}")
        print(f"  时间周期: {config.config.get('timeframes', ['未设置'])}")
        print(f"  风险比例: {config.config.get('risk_per_trade', 0)*100:.1f}%")
    
    print(f"\n💰 资金分配汇总:")
    print(f"  活跃策略总分配: {total_allocation:.1f}%")
    print(f"  剩余可分配: {100-total_allocation:.1f}%")

def test_api_connection():
    """测试API连接"""
    print("\n测试API连接...")
    
    if not config.validate_api_config():
        print("❌ API配置不完整")
        return
    
    try:
        from core.okx_client import OKXClient
        
        client = OKXClient(
            api_key=config.get('okx', 'api_key'),
            secret_key=config.get('okx', 'secret_key'),
            passphrase=config.get('okx', 'passphrase'),
            sandbox=config.is_sandbox()
        )
        
        # 首先测试API基础权限
        print("正在测试API权限...")
        permission_test = client.test_api_permissions()
        
        if not permission_test["success"]:
            print(f"❌ API权限测试失败: {permission_test['error']}")
            print("\n可能的解决方案:")
            print("1. 检查API Key是否有'读取'权限")
            print("2. 检查IP白名单设置")
            print("3. 确认API Key在正确的环境中创建（实盘/模拟）")
            print("4. 联系OKX客服确认账户状态")
            return
        
        # 测试手续费费率获取
        print("\n📊 获取交易手续费费率...")
        fee_test = client.get_trading_fee_rates(instType="SWAP")
        
        if fee_test["success"]:
            fee_data = fee_test['data']
            print(f"✅ 手续费费率获取成功")
            print(f"   用户等级: {fee_data['level']}")
            print(f"   挂单费率: {fee_data['maker_rate']*100:.4f}% (Maker)")
            print(f"   吃单费率: {fee_data['taker_rate']*100:.4f}% (Taker)")
            
            # 显示费率改进信息
            config_maker = config.get('fees', 'maker_fee', 0.0002)
            config_taker = config.get('fees', 'taker_fee', 0.0005)
            
            maker_diff = (config_maker - fee_data['maker_rate']) * 100
            taker_diff = (config_taker - fee_data['taker_rate']) * 100
            
            if abs(maker_diff) > 0.001 or abs(taker_diff) > 0.001:
                print(f"\n💡 费率对比 (配置 vs 实际):")
                print(f"   挂单: {config_maker*100:.4f}% vs {fee_data['maker_rate']*100:.4f}% (差异: {maker_diff:+.4f}%)")
                print(f"   吃单: {config_taker*100:.4f}% vs {fee_data['taker_rate']*100:.4f}% (差异: {taker_diff:+.4f}%)")
                print(f"   📈 系统现在使用API实时费率，更加精确！")
        else:
            print(f"⚠️  手续费费率获取失败，将使用配置文件费率: {fee_test.get('error')}")
        
        # 测试合约信息获取
        print("\n🔧 获取合约信息...")
        instrument_test = client.get_instrument_info("BTC-USDT-SWAP")
        
        if instrument_test["success"]:
            inst_data = instrument_test['data']
            print(f"✅ 合约信息获取成功")
            print(f"   产品ID: {inst_data['instId']}")
            print(f"   合约面值: {inst_data['ctVal']} {inst_data.get('ctValCcy', '')}")
            print(f"   数量精度: {inst_data.get('lotSz', 'N/A')} 张")
            print(f"   价格精度: {inst_data.get('tickSz', 'N/A')}")
            
            # 演示手续费计算对比
            if fee_test["success"]:
                print(f"\n💡 手续费计算演示 (BTC-USDT-SWAP, BTC价格: $100,000):")
                demo_price = 100000
                demo_position_value = 1000  # $1000仓位
                
                # 获取费率
                maker_rate = fee_test['data']['maker_rate']
                taker_rate = fee_test['data']['taker_rate']
                
                # 获取合约信息
                ct_val = float(inst_data['ctVal'])
                
                # 计算合约张数
                contract_size = demo_position_value / (ct_val * demo_price)
                contract_size = round(contract_size)
                actual_value = ct_val * contract_size * demo_price
                
                # 按OKX官方公式计算: 面值 × 张数 × 价格 × 费率
                maker_fee = ct_val * contract_size * demo_price * maker_rate
                taker_fee = ct_val * contract_size * demo_price * taker_rate
                
                print(f"   目标仓位: ${demo_position_value}")
                print(f"   合约面值: {ct_val} BTC")
                print(f"   合约张数: {int(contract_size)} 张") 
                print(f"   实际价值: ${actual_value:.2f}")
                print(f"   挂单手续费: ${maker_fee:.4f} ({maker_rate*100:.3f}%)")
                print(f"   吃单手续费: ${taker_fee:.4f} ({taker_rate*100:.3f}%)")
                print(f"   费率来源: {fee_test['data'].get('source', 'API')}")
                
                # 显示与文档示例的对比
                print(f"\n📋 参考OKX官方文档示例:")
                print(f"   公式: 面值 × 张数 × 价格 × 费率")
                print(f"   计算: {ct_val} × {contract_size} × {demo_price} × {taker_rate} = ${taker_fee:.4f}")
        else:
            print(f"⚠️  合约信息获取失败: {instrument_test.get('error')}")
        
        print("✅ API基础权限验证成功")
        
        # 测试衍生品权限
        print("正在测试衍生品交易权限...")
        derivatives_test = client.test_derivatives_permissions()
        
        if not derivatives_test["success"]:
            print(f"❌ 衍生品权限测试失败: {derivatives_test['error']}")
            print("\n🔥 关键问题: API Key缺少衍生品交易权限!")
            print("\n解决方案:")
            print("1. 登录OKX官网 -> API管理")
            print("2. 编辑您的API Key")
            print("3. 在权限设置中勾选 '衍生品交易' 或 '合约交易'")
            print("4. 保存并重新测试")
            print("\n⚠️  注意: 添加衍生品权限可能需要重新验证身份")
            return
            
        print("✅ 衍生品权限验证成功")
        
        # 测试获取余额
        print("正在获取账户余额...")
        balance = client.get_account_balance()
        
        if balance.get('code') == '0':
            print("[OK] API连接成功!")
            
            # 显示余额信息
            total_usdt = 0
            print("\n💰 账户余额信息:")
            if balance.get('data'):
                for account in balance['data']:
                    # 计算总权益
                    total_eq = float(account.get('totalEq', 0))
                    if total_eq > 0:
                        print(f"   总权益: ${total_eq:,.2f} USDT")
                        total_usdt = total_eq
                    
                    # 显示主要币种余额
                    for detail in account.get('details', []):
                        ccy = detail.get('ccy')
                        bal = float(detail.get('bal', 0))
                        if bal > 0.01:  # 只显示余额大于0.01的币种
                            print(f"   {ccy} 余额: {bal:,.6f}")
            
            # 确认实盘连接
            if total_usdt > 0:
                print(f"\n✅ 确认已连接实盘账户，当前总资金: ${total_usdt:,.2f} USDT")
            else:
                print("\n⚠️  未检测到资金余额，请确认账户状态")
        
        # 检测账户模式（学习自官方现货教程）
        print("\n📊 检测账户模式...")
        try:
            config_result = client.account_api.get_account_config()
            if config_result.get('code') == '0' and config_result.get('data'):
                acct_lv = config_result["data"][0]["acctLv"]
                mode_names = {
                    "1": "现货模式",
                    "2": "现货和合约模式", 
                    "3": "跨币种保证金模式",
                    "4": "组合保证金模式"
                }
                mode_name = mode_names.get(acct_lv, f"未知模式({acct_lv})")
                print(f"   当前账户模式: {mode_name}")
                
                # 衍生品交易建议
                if acct_lv in ["2", "3", "4"]:
                    print("   ✅ 该模式支持衍生品交易")
                else:
                    print("   ⚠️  当前为现货模式，需要切换账户模式才能进行合约交易")
                    print("   💡 建议：在OKX网页版切换到'现货和合约模式'或其他支持衍生品的模式")
            else:
                print("   ❌ 获取账户模式失败")
        except Exception as e:
            print(f"   ❌ 检测账户模式失败: {e}")
        
        # 测试获取行情
        print(f"\n正在获取{config.get_symbol()}行情...")
        try:
            ticker = client.get_ticker(config.get_symbol())
            
            if ticker.get('code') == '0' and ticker.get('data'):
                price_data = ticker['data'][0]
                print(f"[OK] 行情获取成功!")
                print(f"   最新价格: {price_data['last']}")
                # 安全获取24h涨跌数据，不同字段名的容错处理
                chg24h = price_data.get('chg24h') or price_data.get('changePercent24h') or 'N/A'
                print(f"   24h涨跌: {chg24h}")
            else:
                print(f"❌ 行情获取失败: {ticker.get('msg', '未知错误')}")
        except Exception as e:
            print(f"❌ 获取行情数据失败: {e}")
                
        else:
            print(f"❌ API连接失败: {balance.get('msg')}")
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")

def view_trade_history():
    """查看交易历史"""
    print("\n交易历史")
    print("="*50)
    
    data_dir = Path(__file__).parent / "data"
    trades_file = data_dir / "trades.json"
    
    if not trades_file.exists():
        print("暂无交易记录")
        return
    
    try:
        import json
        with open(trades_file, 'r', encoding='utf-8') as f:
            trades = json.load(f)
        
        if not trades:
            print("暂无交易记录")
            return
        
        print(f"共有 {len(trades)} 条交易记录:\n")
        
        for i, trade in enumerate(trades[-10:], 1):  # 显示最近10笔
            print(f"{i}. {trade['timestamp'][:19]}")
            print(f"   {trade['symbol']} {trade['action']} {trade['side']}")
            print(f"   数量: {trade['size']:.6f}")
            print(f"   价格: {trade.get('entry_price', 'N/A')}")
            print(f"   类型: {trade.get('signal_type', 'N/A')}")
            print()
            
    except Exception as e:
        print(f"读取交易历史失败: {e}")

def toggle_emergency_stop():
    """切换紧急停止开关"""
    current_status = config.is_emergency_stop()
    
    if current_status:
        print("\n当前状态: [警告] 紧急停止已激活")
        choice = input("是否关闭紧急停止? (y/N): ").strip().lower()
        if choice == 'y':
            config.set_emergency_stop(False)
            print("[OK] 紧急停止已关闭")
        else:
            print("保持当前状态")
    else:
        print("\n当前状态: [OK] 紧急停止未激活")
        choice = input("是否激活紧急停止? (y/N): ").strip().lower()
        if choice == 'y':
            config.set_emergency_stop(True)
            print("[警告] 紧急停止已激活")
        else:
            print("保持当前状态")

def show_documentation():
    """显示系统文档"""
    doc = """
    系统文档
    ========

    文件结构:
    ├── main.py                     # 主程序入口
    ├── core/                       # 核心模块
    │   ├── okx_client.py          # OKX API客户端
    │   ├── trading_engine.py      # 交易引擎
    │   ├── strategy_registry.py   # 策略注册表
    │   └── strategy_configurator.py # 策略配置器
    ├── strategies/                 # 交易策略
    │   ├── base_strategy.py       # 策略基类
    │   ├── ma_crossover.py        # 移动平均交叉策略
    │   ├── volatility_breakout.py # 波动率突破策略
    │   └── experimental/
    │       └── rsi_divergence_v2.py # RSI背离策略v2 (实验)
    ├── config/                     # 配置管理
    │   ├── config.py              # 单策略配置
    │   ├── trading_config.json    # 单策略配置文件
    │   ├── multi_config_manager.py # 多策略配置管理
    │   └── multi_strategy_config.json # 多策略配置文件
    ├── data/                       # 数据存储
    │   └── trades.json            # 交易记录
    └── logs/                       # 日志文件

    系统特性:
    - 支持多策略并行运行
    - 智能资金分配和风险管理
    - 交互式策略配置向导
    - 配置持久化保存

    使用流程:
    1. 首次使用前，运行"配置向导"设置API密钥和基础参数
    2. 在配置向导中设置交易策略
    3. 使用"测试API连接"验证配置正确性
    4. 使用"策略管理"功能添加/修改策略
    5. 强烈建议先在沙盒环境测试策略有效性
    6. 确认策略表现后，再考虑切换到实盘环境

    策略管理:
    - 配置向导包含策略配置步骤
    - 策略管理菜单可单独管理策略
    - 支持RSI背离和移动平均交叉策略
    - 可以动态启用/禁用策略
    - 自动资金分配和风险控制

    安全建议:
    - 始终使用小额资金测试
    - 设置合理的风控参数
    - 定期检查交易记录和账户状态
    - 遇到异常立即使用紧急停止功能
    - 策略配置会自动保存，支持断点续传

    风险提醒:
    - 自动化交易存在技术风险和市场风险
    - 任何策略都可能失效，需要持续监控
    - 请只使用您能承受损失的资金进行交易
    - 多策略运行时风险可能放大，请谨慎配置
    """
    
    print(doc)

def main():
    """主函数"""
    show_banner()
    
    while True:
        show_config_status()
        show_menu()
        
        choice = ""  # 初始化choice变量
        try:
            choice = input("\n请选择操作 (0-8): ").strip()
            
            if choice == '0':
                print("感谢使用！请谨慎交易，风险自负。")
                break
            elif choice == '1':
                if not config.validate_api_config():
                    print("[错误] API配置不完整，请先运行配置向导")
                    continue
                    
                print("\n[警告] 即将启动交易引擎")
                if not config.is_sandbox():
                    confirm = input("当前为实盘环境，确认启动? (yes/no): ").strip().lower()
                    if confirm != 'yes':
                        print("已取消启动")
                        continue
                
                try:
                    # 使用完整的多策略配置
                    multi_config = MultiStrategyConfigManager()
                    multi_config.load_config()
                    engine_config = multi_config._config_data  # 使用完整配置
                    
                    # 确保OKX配置是最新的
                    engine_config["okx"] = {
                        "api_key": config.get('okx', 'api_key'),
                        "secret_key": config.get('okx', 'secret_key'), 
                        "passphrase": config.get('okx', 'passphrase'),
                        "sandbox": config.is_sandbox()
                    }
                    
                    engine = MultiStrategyTradingEngine(engine_config)
                    import asyncio
                    asyncio.run(engine.start_trading())
                except Exception as e:
                    print(f"启动交易引擎失败: {e}")
                    
            elif choice == '2':
                continue  # 配置状态已在循环开始显示
            elif choice == '3':
                setup_wizard()
            elif choice == '4':
                configure_strategies_wizard()
            elif choice == '5':
                test_api_connection()
            elif choice == '6':
                view_trade_history()
            elif choice == '7':
                toggle_emergency_stop()
            elif choice == '8':
                show_documentation()
            else:
                print("无效选择，请输入0-8之间的数字。")
                
        except KeyboardInterrupt:
            print("\n\n操作已取消。")
            break
        except Exception as e:
            print(f"发生错误: {e}")
        
        if choice != '1':  # 启动引擎时不需要暂停
            input("\n按Enter继续...")

if __name__ == "__main__":
    main()