import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import random
import time
from datetime import datetime
from web3 import Web3
from prediction_contract import PredictionContract
from erc20_contract import ERC20Contract

# 配置Streamlit页面
st.set_page_config(
    page_title="预测合约操作器",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 添加自定义CSS隐藏侧栏收起按钮
st.markdown("""
<style>
    /* 隐藏侧栏收起按钮 */
    .css-1d391kg {
        display: none;
    }
    
    /* 隐藏侧栏顶部的收起按钮 */
    [data-testid="collapsedControl"] {
        display: none;
    }
    
    /* 确保侧栏始终显示 */
    .css-1d391kg, .css-1lcbmhc, .css-1lcbmhc .css-1d391kg {
        display: none;
    }
    
    /* 隐藏侧栏的折叠控制器 */
    .st-emotion-cache-1cypcdb {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# 链上合约操作类
class ChainContractOperator:
    def __init__(self, rpc_url, prediction_address, base_token_address, 
                 account_address, account_private_key, 
                 lp_provider_address, lp_provider_private_key):
        # 从参数接收配置
        self.RPC_URL = rpc_url
        self.PREDICTION_CONTRACT_ADDRESS = prediction_address
        self.BASE_TOKEN_ADDRESS = base_token_address
        self.ACCOUNT_ADDRESS = account_address
        self.ACCOUNT_PRIVATE_KEY = account_private_key
        self.LP_PROVIDER_ADDRESS = lp_provider_address
        self.LP_PROVIDER_PRIVATE_KEY = lp_provider_private_key

        self.operation_history = []
        self.init_contracts()
    
    def init_contracts(self):
        """初始化合约连接"""
        try:
            # 初始化Web3连接
            self.web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
            
            if not self.web3.is_connected():
                st.error("❌ Web3连接失败！")
                return False
            
            # 创建合约实例
            self.prediction_for_trade = PredictionContract(
                web3=self.web3,
                prediction_address=self.PREDICTION_CONTRACT_ADDRESS,
                private_key=self.ACCOUNT_PRIVATE_KEY,
                account_address=self.ACCOUNT_ADDRESS
            )

            self.prediction_for_lp_send = PredictionContract(
                web3=self.web3,
                prediction_address=self.PREDICTION_CONTRACT_ADDRESS,
                private_key=self.LP_PROVIDER_PRIVATE_KEY,
                account_address=self.LP_PROVIDER_ADDRESS
            )
            
            self.base_token = ERC20Contract(
                web3=self.web3,
                token_address=self.BASE_TOKEN_ADDRESS,
                private_key=self.ACCOUNT_PRIVATE_KEY,
                account_address=self.ACCOUNT_ADDRESS
            )

            self.base_token_for_lp = ERC20Contract(
                web3=self.web3,
                token_address=self.BASE_TOKEN_ADDRESS,
                private_key=self.LP_PROVIDER_PRIVATE_KEY,
                account_address=self.LP_PROVIDER_ADDRESS
            )

            self.prediction_lp = ERC20Contract(
                web3=self.web3,
                token_address=self.PREDICTION_CONTRACT_ADDRESS,
                private_key=self.LP_PROVIDER_PRIVATE_KEY,
                account_address=self.LP_PROVIDER_ADDRESS
            )

            options = self.prediction_for_trade.get_options()

            self.owner = self.prediction_for_trade.get_owner()

            self.o1 = ERC20Contract(
                web3=self.web3,
                token_address=options[0],
                private_key=self.ACCOUNT_PRIVATE_KEY,
                account_address=self.ACCOUNT_ADDRESS
            )

            self.o2 = ERC20Contract(
                web3=self.web3,
                token_address=options[1],
                private_key=self.ACCOUNT_PRIVATE_KEY,
                account_address=self.ACCOUNT_ADDRESS
            )



            
            st.success("✅ 合约连接成功！")

            account_allowance = self.base_token.get_allowance(self.ACCOUNT_ADDRESS, self.PREDICTION_CONTRACT_ADDRESS)

            lp_allowance = self.base_token_for_lp.get_allowance(self.LP_PROVIDER_ADDRESS, self.PREDICTION_CONTRACT_ADDRESS)

            if account_allowance < 100000000000000000000000000000000000000:
                st.success("开始approve交易账户")

                tx_hash = self.base_token.approve(self.PREDICTION_CONTRACT_ADDRESS, 1000000000000000000000000000000000000000)

                tx_success, receipt = self.wait_for_transaction(tx_hash)
                if tx_success:
                    st.code(f"approve for trade hash: {tx_hash}")
                    
                    st.success("✅ approve for trade success")
                
                else:
                    st.error("❌ approve for trade failed")
                    return False
            
            if lp_allowance < 100000000000000000000000000000000000000:
                st.success("开始approveLP提供者账户")

                tx_hash = self.base_token_for_lp.approve(self.PREDICTION_CONTRACT_ADDRESS, 1000000000000000000000000000000000000000)

                tx_success, receipt = self.wait_for_transaction(tx_hash)
                if tx_success:
                    st.code(f"approve for lp hash: {tx_hash}")
                    
                    st.success("✅ approve for lp success")
                    
                else:
                    st.error("❌ approve for lp failed")
                    return False

            st.success("✅ 合约初始化成功！")

            return True
            
        except Exception as e:
            st.error(f"❌ 合约初始化失败: {str(e)}")
            return False
    
    def get_current_balances(self):
        """获取当前链上余额 - 协程并发版本"""
        import asyncio
        import time
        
        def run_concurrent_queries():
            """使用协程并发查询所有余额"""
            async def query_all():
                loop = asyncio.get_event_loop()
                
                # 创建所有查询任务
                tasks = [
                    loop.run_in_executor(None, self.base_token.get_balance_of, self.PREDICTION_CONTRACT_ADDRESS),
                    loop.run_in_executor(None, self.base_token.get_balance_of, self.ACCOUNT_ADDRESS),
                    loop.run_in_executor(None, self.base_token_for_lp.get_balance_of, self.LP_PROVIDER_ADDRESS),
                    loop.run_in_executor(None, self.base_token.get_balance_of, self.owner),
                    loop.run_in_executor(None, self.o1.get_balance_of, self.ACCOUNT_ADDRESS),
                    loop.run_in_executor(None, self.o2.get_balance_of, self.ACCOUNT_ADDRESS),
                    loop.run_in_executor(None, self.prediction_for_trade.get_price, 0),
                    loop.run_in_executor(None, self.prediction_for_trade.get_price, 1),
                    loop.run_in_executor(None, self.prediction_lp.get_balance_of, self.LP_PROVIDER_ADDRESS)
                ]
                
                # 并发执行所有查询
                return await asyncio.gather(*tasks, return_exceptions=True)
            
            # 尝试运行协程
            try:
                return asyncio.run(query_all())
            except RuntimeError:
                # 如果在已有事件循环中，使用nest_asyncio
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                    return asyncio.run(query_all())
                except ImportError:
                    return None
        
        try:
            start_time = time.time()
            
            # 尝试协程并发查询
            results = run_concurrent_queries()
            
            if results is None:
                # 协程失败，回退到同步方式
                st.warning("⚠️ 协程环境不支持，使用同步查询")
                return self._get_balances_sync()
            
            end_time = time.time()
            
            # 处理结果
            (pool_balance, user_balance, lp_provider_balance, owner_balance, 
             user_o1_balance, user_o2_balance, o1_price_raw, 
             o2_price_raw, lp_balance) = results
            
            # 检查是否有异常
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    st.warning(f"⚠️ 查询第{i+1}项失败: {str(result)}")
                    results[i] = 0  # 设置默认值
            
            st.info(f"⚡ 并发查询完成，耗时: {end_time - start_time:.2f}秒")
            
            return {
                'pool_balance': int(pool_balance) / 1e6,
                'user_balance': int(user_balance) / 1e6,
                'lp_provider_balance': int(lp_provider_balance) / 1e6,
                'owner_balance': int(owner_balance) / 1e6,
                'user_o1_balance': int(user_o1_balance) / 1e6,
                'user_o2_balance': int(user_o2_balance) / 1e6,
                'user_lp_balance': int(lp_balance) / 1e6,
                'o1_price': int(o1_price_raw) / 1e6,
                'o2_price': int(o2_price_raw) / 1e6
            }
        except Exception as e:
            st.error(f"❌ 协程查询失败，回退到同步方式: {str(e)}")
            return self._get_balances_sync()
    
    def _get_balances_sync(self):
        """同步方式获取余额 - 作为备用方案"""
        try:
            # 获取池子余额
            pool_balance = self.base_token.get_balance_of(self.PREDICTION_CONTRACT_ADDRESS)
            # 获取用户余额
            user_balance = self.base_token.get_balance_of(self.ACCOUNT_ADDRESS)
            # 获取LP提供者余额
            lp_provider_balance = self.base_token_for_lp.get_balance_of(self.LP_PROVIDER_ADDRESS)
            # 获取owner余额
            owner_balance = self.base_token.get_balance_of(self.owner)
            # 获取用户的o1、o2代币余额
            user_o1_balance = self.o1.get_balance_of(self.ACCOUNT_ADDRESS)
            user_o2_balance = self.o2.get_balance_of(self.ACCOUNT_ADDRESS)
            # 获取价格
            o1_price_raw = self.prediction_for_trade.get_price(0)
            o2_price_raw = self.prediction_for_trade.get_price(1)
            # 获取lp代币余额
            lp_balance = self.prediction_lp.get_balance_of(self.LP_PROVIDER_ADDRESS)
            
            return {
                'pool_balance': int(pool_balance) / 1e6,
                'user_balance': int(user_balance) / 1e6,
                'lp_provider_balance': int(lp_provider_balance) / 1e6,
                'owner_balance': int(owner_balance) / 1e6,
                'user_o1_balance': int(user_o1_balance) / 1e6,
                'user_o2_balance': int(user_o2_balance) / 1e6,
                'user_lp_balance': int(lp_balance) / 1e6,
                'o1_price': int(o1_price_raw) / 1e6,
                'o2_price': int(o2_price_raw) / 1e6
            }
        except Exception as e:
            st.error(f"❌ 同步查询也失败: {str(e)}")
            return None
    
    def calculate_prices(self, balances):
        """从余额中提取价格信息"""
        if not balances:
            return {'o1_price': 0, 'o2_price': 0}
        
        return {
            'o1_price': balances['o1_price'],
            'o2_price': balances['o2_price']
        }
    
    def get_available_operations(self, balances):
        """根据当前余额确定可执行的操作"""
        available_ops = []
        
        # Deposit: 需要用户有BaseToken余额
        if balances['user_balance'] > 1:  # 至少1 USDC才能deposit
            available_ops.append('deposit_o1')  # deposit到option 0
            available_ops.append('deposit_o2')  # deposit到option 1
        
        # Add Liquidity: 需要LP提供者有BaseToken余额  
        if balances['lp_provider_balance'] > 1:
            available_ops.append('add_liquidity')
        
        # Remove Liquidity: 需要用户有LP代币
        if balances['user_lp_balance'] > 0.1:  # 至少0.1个LP代币
            available_ops.append('remove_liquidity')
        
        # Withdraw o1: 需要用户有o1代币
        if balances['user_o1_balance'] > 0.1:  # 至少0.1个o1代币
            available_ops.append('withdraw_o1')
            
        # Withdraw o2: 需要用户有o2代币
        if balances['user_o2_balance'] > 0.1:  # 至少0.1个o2代币
            available_ops.append('withdraw_o2')
        
        return available_ops
    
    def deposit_o1(self, amount_usdc):
        """向option 0 (O1) 存入BaseToken"""
        try:
            amount_wei = int(amount_usdc * 1e6)
            # deposit(option_out, delta, min_receive)
            tx_hash = self.prediction_for_trade.deposit(0, amount_wei, 0)  # option_out = 0 (O1)
            return tx_hash, True
        except Exception as e:
            st.error(f"❌ Deposit O1失败: {str(e)}")
            return None, False
    
    def deposit_o2(self, amount_usdc):
        """向option 1 (O2) 存入BaseToken"""
        try:
            amount_wei = int(amount_usdc * 1e6)
            # deposit(option_out, delta, min_receive)  
            tx_hash = self.prediction_for_trade.deposit(1, amount_wei, 0)  # option_out = 1 (O2)
            return tx_hash, True
        except Exception as e:
            st.error(f"❌ Deposit O2失败: {str(e)}")
            return None, False

    def withdraw_o1(self, amount_usdc):
        """从option 0 (O1) 提取到BaseToken"""
        try:
            amount_wei = int(amount_usdc * 1e6)
            # withdraw(option_in, delta, min_receive)
            tx_hash = self.prediction_for_trade.withdraw(0, amount_wei, 0)  # option_in = 0 (O1)
            return tx_hash, True
        except Exception as e:
            st.error(f"❌ Withdraw O1失败: {str(e)}")
            return None, False
    
    def withdraw_o2(self, amount_usdc):
        """从option 1 (O2) 提取到BaseToken"""
        try:
            amount_wei = int(amount_usdc * 1e6)
            # withdraw(option_in, delta, min_receive)
            tx_hash = self.prediction_for_trade.withdraw(1, amount_wei, 0)  # option_in = 1 (O2)
            return tx_hash, True
        except Exception as e:
            st.error(f"❌ Withdraw O2失败: {str(e)}")
            return None, False

    def add_liquidity(self, amount_usdc):
        """添加流动性"""
        try:
            amount_wei = int(amount_usdc * 1e6)
            tx_hash = self.prediction_for_lp_send.add_liquidity(amount_wei, self.LP_PROVIDER_ADDRESS)
            return tx_hash, True
        except Exception as e:
            st.error(f"❌ Add Liquidity失败: {str(e)}")
            return None, False
    
    def remove_liquidity(self, amount_usdc):
        """移除流动性"""
        try:
            amount_wei = int(amount_usdc * 1e6)
            tx_hash = self.prediction_for_lp_send.remove_liquidity(amount_wei)
            return tx_hash, True
        except Exception as e:
            st.error(f"❌ Remove Liquidity失败: {str(e)}")
            return None, False
    
    def get_smart_operation_amount(self, operation, balances):
        """根据操作类型和当前余额智能确定操作金额"""
        if operation in ['deposit_o1', 'deposit_o2']:
            # Deposit: 用户余额的5%-20%
            max_amount = balances['user_balance'] * 0.2
            min_amount = min(1.0, balances['user_balance'] * 0.05)
            return random.uniform(min_amount, max_amount)
            
        elif operation == 'add_liquidity':
            # Add Liquidity: LP提供者余额的5%-15%
            max_amount = balances['lp_provider_balance'] * 0.15
            min_amount = min(1.0, balances['lp_provider_balance'] * 0.05)
            return random.uniform(min_amount, max_amount)
            
        elif operation == 'remove_liquidity':
            # Remove Liquidity: 基于LP代币余额，最多移除一半
            max_removable = max(0, balances['user_lp_balance'] - 0.1)  # 保留0.1个LP代币
            max_amount = min(max_removable * 0.5, max_removable)  # 最多移除一半
            min_amount = min(0.1, max_amount)
            return random.uniform(min_amount, max_amount) if max_amount > min_amount else min_amount
            
        elif operation == 'withdraw_o1':
            # Withdraw O1: 最多卖一半，但至少保留0.1个代币
            max_sellable = max(0, balances['user_o1_balance'] - 0.1)
            max_amount = min(max_sellable * 0.5, max_sellable)  # 最多卖一半
            min_amount = min(0.1, max_amount)
            return random.uniform(min_amount, max_amount) if max_amount > min_amount else min_amount
            
        elif operation == 'withdraw_o2':
            # Withdraw O2: 最多卖一半，但至少保留0.1个代币
            max_sellable = max(0, balances['user_o2_balance'] - 0.1) 
            max_amount = min(max_sellable * 0.5, max_sellable)  # 最多卖一半
            min_amount = min(0.1, max_amount)
            return random.uniform(min_amount, max_amount) if max_amount > min_amount else min_amount
            
        else:
            return random.uniform(1.0, 10.0)  # 默认值
    
    def wait_for_transaction(self, tx_hash, timeout=120):
        """等待交易确认并返回结果"""
        try:
            st.info(f"⏳ 等待交易确认... ({tx_hash[:10]}...)")
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            
            if receipt.status == 1:
                st.success(f"✅ 交易成功确认！Gas使用: {receipt.gasUsed:,}")
                return True, receipt
            else:
                st.error(f"❌ 交易失败！状态: {receipt.status}")
                return False, receipt
                
        except Exception as e:
            st.error(f"❌ 等待交易确认失败: {str(e)}")
            return False, None
    
    def get_last_state(self):
        """获取上一个状态的余额和价格数据"""
        if len(self.operation_history) > 0:
            last_record = self.operation_history[-1]
            return {
                'pool_balance': last_record['pool_balance'],
                'user_balance': last_record['user_balance'],
                'lp_provider_balance': last_record['lp_provider_balance'],
                'owner_balance': last_record['owner_balance'],
                'user_o1_balance': last_record['user_o1_balance'],
                'user_o2_balance': last_record['user_o2_balance'],
                'user_lp_balance': last_record['user_lp_balance']
            }, {
                'o1_price': last_record['o1_price'],
                'o2_price': last_record['o2_price']
            }
        return None, None

    def record_operation(self, operation_type, amount, tx_hash, success, balances, prices):
        """记录操作历史"""
        self.operation_history.append({
            'timestamp': datetime.now(),
            'operation': operation_type,
            'amount': amount,
            'tx_hash': tx_hash,
            'success': success,
            'pool_balance': balances['pool_balance'] if balances else 0,
            'user_balance': balances['user_balance'] if balances else 0,
            'lp_provider_balance': balances['lp_provider_balance'] if balances else 0,
            'owner_balance': balances['owner_balance'] if balances else 0,
            'user_o1_balance': balances['user_o1_balance'] if balances else 0,  # 保留用于内部逻辑
            'user_o2_balance': balances['user_o2_balance'] if balances else 0,  # 保留用于内部逻辑
            'user_lp_balance': balances['user_lp_balance'] if balances else 0,  # LP代币余额
            'o1_price': prices['o1_price'] if prices else 0,
            'o2_price': prices['o2_price'] if prices else 0
        })

# Streamlit 应用
st.title("🔗 预测市场合约模拟测试")
st.markdown("**建议自己去tenderly创建自己的测试链环境 然后配置自己用的交互的钱包地址并领水和points**")


# 配置区域
st.header("🔧 合约配置")
with st.expander("📝 配置参数", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌐 网络配置")
        rpc_url = st.text_input(
            "tenderly的测试的RPC节点地址", 
            help="tenderly的测试的RPC节点地址"
        )
        
        prediction_address = st.text_input(
            "预测合约地址", 
            help="Prediction合约的地址"
        )
        
        base_token_address = st.text_input(
            "基础代币地址", 
            help="Point代币的合约地址"
        )
    
    with col2:
        st.subheader("👤 账户配置")
        account_address = st.text_input(
            "交易账户地址(用于执行Deposit/Withdraw操作的账户地址)", 
            help="用于Deposit/Withdraw操作的账户地址"
        )
        
        account_private_key = st.text_input(
            "交易账户私钥(不要加0x前缀)", 
            type="password",
            help="交易账户的私钥"
        )
        
        lp_provider_address = st.text_input(
            "LP提供者地址(用于执行Add/Remove Liquidity操作的账户地址)", 
            help="用于 Add/Remove Liquidity操作的账户地址"
        )
        
        lp_provider_private_key = st.text_input(
            "LP提供者私钥(不要加0x前缀)", 
            type="password",
            help="LP提供者的私钥"
        )

# 检查配置完整性
config_complete = all([rpc_url, prediction_address, base_token_address, 
                      account_address, account_private_key, 
                      lp_provider_address, lp_provider_private_key])

# 初始化按钮
col1, col2 = st.columns(2)
with col1:
    if config_complete:
        init_button = st.button("🚀 初始化合约连接", type="primary", use_container_width=True)
    else:
        st.button("🚀 初始化合约连接", type="primary", disabled=True, use_container_width=True)
        st.error("❌ 请填写所有配置参数！")

with col2:
    if 'operator' in st.session_state:
        if st.button("🔄 重新初始化", type="secondary", use_container_width=True):
            # 清除现有的操作器和余额缓存
            del st.session_state.operator
            if 'current_balances' in st.session_state:
                del st.session_state.current_balances
            st.rerun()

# 初始化合约操作器
if config_complete and 'operator' not in st.session_state and 'init_button' in locals() and init_button:
    with st.spinner("正在初始化合约连接..."):
        try:
            st.session_state.operator = ChainContractOperator(
                rpc_url=rpc_url,
                prediction_address=prediction_address,
                base_token_address=base_token_address,
                account_address=account_address,
                account_private_key=account_private_key,
                lp_provider_address=lp_provider_address,
                lp_provider_private_key=lp_provider_private_key
            )
            
            # 尝试初始化合约连接
            if st.session_state.operator.init_contracts():
                st.success("✅ 合约初始化成功！")
            else:
                st.error("❌ 合约初始化失败！")
                del st.session_state.operator
                st.stop()
                
        except Exception as e:
            st.error(f"❌ 初始化错误: {str(e)}")
            if 'operator' in st.session_state:
                del st.session_state.operator
            st.stop()

# 检查是否已初始化
if 'operator' not in st.session_state:
    st.info("💡 请配置参数并点击'初始化合约连接'开始使用")
    st.stop()

operator = st.session_state.operator

# 初始化时自动获取余额
if 'current_balances' not in st.session_state:
    with st.spinner("获取初始链上余额..."):
        balances = operator.get_current_balances()
        if balances:
            st.session_state.current_balances = balances
            # 记录初始状态作为第一个数据点
            prices = operator.calculate_prices(balances)
            operator.record_operation("初始化", 0, None, True, balances, prices)
            
            # 检查两个账户的point余额是否足够
            min_required_balance = 10.0  # 设置最小需要的余额阈值
            
            if balances['user_balance'] < min_required_balance:
                st.warning(f"⚠️ 交易账户point余额不足！当前余额: {balances['user_balance']} 先去tenderly领水领点point ")
            
            if balances['lp_provider_balance'] < min_required_balance:
                st.warning(f"⚠️ LP提供者账户point余额不足！当前余额: {balances['lp_provider_balance ']} 先去tenderly领水领点point ")
            
            if balances['user_balance'] >= min_required_balance and balances['lp_provider_balance'] >= min_required_balance:
                st.success("✅ 两个账户point余额充足，可以开始操作！")

# 侧边栏配置
st.sidebar.header("⚙️ 操作参数")

# 显示当前余额
if st.sidebar.button("🔄 刷新余额"):
    with st.spinner("获取链上余额..."):
        balances = operator.get_current_balances()
        if balances:
            st.session_state.current_balances = balances

if 'current_balances' in st.session_state:
    balances = st.session_state.current_balances
    prices = operator.calculate_prices(balances)
    
    st.sidebar.success(f"🏦 池子余额: {balances['pool_balance']} USDC")
    st.sidebar.info(f"💰 交易账户余额: {balances['user_balance']} USDC")
    
    st.sidebar.info(f"🎯 交易账户O1代币余额: {balances['user_o1_balance']} O1")
    st.sidebar.info(f"🎯 交易账户O2代币余额: {balances['user_o2_balance']} O2")

    
    st.sidebar.success(f"🏪 LP提供者账户余额: {balances['lp_provider_balance']} USDC")
    st.sidebar.success(f"🔗 LP提供者账户LP余额: {balances['user_lp_balance']}")

    st.sidebar.info(f"👑 Owner余额: {balances['owner_balance']} USDC")
    st.sidebar.metric("💰 O1价格", f"{prices['o1_price']} USDC")
    st.sidebar.metric("💰 O2价格", f"{prices['o2_price']} USDC")
    
    # 显示可用操作
    available_ops = operator.get_available_operations(balances)
    if available_ops:
        st.sidebar.success(f"✅ 可用操作: {', '.join(available_ops)}")
    else:
        st.sidebar.warning("⚠️ 当前没有可用操作")

# 操作参数
num_operations = st.sidebar.slider("操作次数", min_value=1, max_value=50, value=10)

# 操作权重设置
st.sidebar.subheader("操作权重")
deposit_o1_weight = st.sidebar.slider("Deposit O1 权重", 0, 100, 30)
deposit_o2_weight = st.sidebar.slider("Deposit O2 权重", 0, 100, 30)
withdraw_o1_weight = st.sidebar.slider("Withdraw O1 权重", 0, 100, 25)
withdraw_o2_weight = st.sidebar.slider("Withdraw O2 权重", 0, 100, 25)
add_liquidity_weight = st.sidebar.slider("Add Liquidity 权重", 0, 100, 20)
remove_liquidity_weight = st.sidebar.slider("Remove Liquidity 权重", 0, 100, 10)

# 手动操作区域
st.subheader("🎮 手动操作")
col1, col2 = st.columns(2)

with col1:
    manual_amount = st.number_input("操作金额 (USDC)", value=10.0, min_value=0.0, format="%f")
    
with col2:
    manual_operation = st.selectbox("操作类型", ["deposit_o1", "deposit_o2", "withdraw_o1", "withdraw_o2", "add_liquidity", "remove_liquidity"])

if st.button("🚀 执行单次操作", type="primary"):
    with st.spinner(f"正在执行 {manual_operation}..."):
        # 获取操作前余额
        balances_before = operator.get_current_balances()
        
        # 初始化变量
        tx_hash, success = None, False
        
        # 检查操作是否可用
        available_ops = operator.get_available_operations(balances_before)
        if manual_operation not in available_ops:
            st.error(f"❌ 操作 {manual_operation} 当前不可用！请检查余额。")
            # 记录失败的操作 - 使用上一个状态的数据
            last_balances, last_prices = operator.get_last_state()
            if last_balances and last_prices:
                operator.record_operation(manual_operation, manual_amount, None, False, last_balances, last_prices)
            else:
                prices_before = operator.calculate_prices(balances_before)
                operator.record_operation(manual_operation, manual_amount, None, False, balances_before, prices_before)
        else:
            # 执行操作
            if manual_operation == 'deposit_o1':
                tx_hash, success = operator.deposit_o1(manual_amount)
            elif manual_operation == 'deposit_o2':
                tx_hash, success = operator.deposit_o2(manual_amount)
            elif manual_operation == 'withdraw_o1':
                # 检查是否超过可卖数量
                max_sellable = max(0, balances_before['user_o1_balance'] - 0.1) * 0.5
                if manual_amount > max_sellable:
                    st.error(f"❌ 超出最大可卖数量 {max_sellable}")
                    success = False
                    # 记录失败的操作 - 使用上一个状态的数据
                    last_balances, last_prices = operator.get_last_state()
                    if last_balances and last_prices:
                        operator.record_operation(manual_operation, manual_amount, None, False, last_balances, last_prices)
                    else:
                        prices_before = operator.calculate_prices(balances_before)
                        operator.record_operation(manual_operation, manual_amount, None, False, balances_before, prices_before)
                else:
                    tx_hash, success = operator.withdraw_o1(manual_amount)
            elif manual_operation == 'withdraw_o2':
                # 检查是否超过可卖数量
                max_sellable = max(0, balances_before['user_o2_balance'] - 0.1) * 0.5
                if manual_amount > max_sellable:
                    st.error(f"❌ 超出最大可卖数量 {max_sellable}")
                    success = False
                    # 记录失败的操作 - 使用上一个状态的数据
                    last_balances, last_prices = operator.get_last_state()
                    if last_balances and last_prices:
                        operator.record_operation(manual_operation, manual_amount, None, False, last_balances, last_prices)
                    else:
                        prices_before = operator.calculate_prices(balances_before)
                        operator.record_operation(manual_operation, manual_amount, None, False, balances_before, prices_before)
                else:
                    tx_hash, success = operator.withdraw_o2(manual_amount)
            elif manual_operation == 'add_liquidity':
                tx_hash, success = operator.add_liquidity(manual_amount)
            elif manual_operation == 'remove_liquidity':
                tx_hash, success = operator.remove_liquidity(manual_amount)
        
        # 等待交易确认
        if success and tx_hash:
            tx_success, receipt = operator.wait_for_transaction(tx_hash)
            
            if tx_success:
                st.code(f"交易哈希: {tx_hash}")
                
                # 获取操作后余额
                balances_after = operator.get_current_balances()
                
                # 记录操作
                prices = operator.calculate_prices(balances_after)
                operator.record_operation(manual_operation, manual_amount, tx_hash, True, balances_after, prices)
                
                # 更新余额显示
                if balances_after:
                    st.session_state.current_balances = balances_after
            else:
                # 交易失败 - 使用上一个状态的数据
                last_balances, last_prices = operator.get_last_state()
                if last_balances and last_prices:
                    operator.record_operation(manual_operation, manual_amount, tx_hash, False, last_balances, last_prices)
                else:
                    # 如果没有上一个状态，使用当前状态
                    prices_before = operator.calculate_prices(balances_before)
                    operator.record_operation(manual_operation, manual_amount, tx_hash, False, balances_before, prices_before)

# 批量操作
st.subheader("🔄 批量自动操作")

if st.button("🚀 开始智能批量操作", type="secondary"):
    if sum([deposit_o1_weight, deposit_o2_weight, withdraw_o1_weight, withdraw_o2_weight, add_liquidity_weight, remove_liquidity_weight]) == 0:
        st.error("❌ 请至少设置一个操作权重大于0")
    else:
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 执行批量操作
        for i in range(num_operations):
            # 获取当前余额
            current_balances = operator.get_current_balances()
            if not current_balances:
                st.error("❌ 无法获取余额，停止操作")
                break
            
            # 获取可用操作
            available_ops = operator.get_available_operations(current_balances)
            
            if not available_ops:
                st.warning(f"⚠️ 第{i+1}次操作：没有可用操作，跳过")
                continue
            
            # 根据权重和可用操作选择操作
            operation_weights = {
                'deposit_o1': deposit_o1_weight,
                'deposit_o2': deposit_o2_weight,
                'withdraw_o1': withdraw_o1_weight,
                'withdraw_o2': withdraw_o2_weight,
                'add_liquidity': add_liquidity_weight,
                'remove_liquidity': remove_liquidity_weight
            }
            
            # 只保留可用操作的权重
            filtered_weights = {op: weight for op, weight in operation_weights.items() 
                               if op in available_ops and weight > 0}
            
            if not filtered_weights:
                st.warning(f"⚠️ 第{i+1}次操作：没有设置权重的可用操作，跳过")
                continue
            
            # 选择操作
            operations = list(filtered_weights.keys())
            weights = list(filtered_weights.values())
            operation = random.choices(operations, weights=weights)[0]
            
            # 智能确定操作金额
            amount = operator.get_smart_operation_amount(operation, current_balances)
            
            status_text.text(f'执行中: {operation} {amount} USDC ({i+1}/{num_operations})')
            
            # 执行操作
            tx_hash, success = None, False
            try:
                if operation == 'deposit_o1':
                    tx_hash, success = operator.deposit_o1(amount)
                elif operation == 'deposit_o2':
                    tx_hash, success = operator.deposit_o2(amount)
                elif operation == 'withdraw_o1':
                    tx_hash, success = operator.withdraw_o1(amount)
                elif operation == 'withdraw_o2':
                    tx_hash, success = operator.withdraw_o2(amount)
                elif operation == 'add_liquidity':
                    tx_hash, success = operator.add_liquidity(amount)
                elif operation == 'remove_liquidity':
                    tx_hash, success = operator.remove_liquidity(amount)
                
                # 等待交易确认
                if success and tx_hash:
                    # 批量操作使用较短的超时时间
                    tx_success, receipt = operator.wait_for_transaction(tx_hash, timeout=60)
                    
                    if tx_success:
                        # 获取操作后余额
                        balances_after = operator.get_current_balances()
                        
                        # 记录操作
                        prices = operator.calculate_prices(balances_after)
                        operator.record_operation(operation, amount, tx_hash, True, balances_after, prices)
                    else:
                        # 交易失败 - 使用上一个状态的数据
                        last_balances, last_prices = operator.get_last_state()
                        if last_balances and last_prices:
                            operator.record_operation(operation, amount, tx_hash, False, last_balances, last_prices)
                        else:
                            prices_current = operator.calculate_prices(current_balances)
                            operator.record_operation(operation, amount, tx_hash, False, current_balances, prices_current)
                else:
                    # 记录失败的操作 - 使用上一个状态的数据
                    last_balances, last_prices = operator.get_last_state()
                    if last_balances and last_prices:
                        operator.record_operation(operation, amount, None, False, last_balances, last_prices)
                    else:
                        prices_current = operator.calculate_prices(current_balances)
                        operator.record_operation(operation, amount, None, False, current_balances, prices_current)
                    
            except Exception as e:
                st.error(f"操作 {i+1} 失败: {str(e)}")
                # 记录失败的操作 - 使用上一个状态的数据
                last_balances, last_prices = operator.get_last_state()
                if last_balances and last_prices:
                    operator.record_operation(operation, amount, None, False, last_balances, last_prices)
                else:
                    prices_current = operator.calculate_prices(current_balances)
                    operator.record_operation(operation, amount, None, False, current_balances, prices_current)
            
            # 更新进度
            progress_bar.progress((i + 1) / num_operations)
        
        status_text.text("✅ 智能批量操作完成！")

# 显示操作历史和图表  
if len(operator.operation_history) > 0:
    st.subheader("📈 操作历史和余额变化")
    
    # 转换为DataFrame
    df = pd.DataFrame(operator.operation_history)
    df['operation_id'] = range(len(df))
    
    # 创建多子图
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('池子余额变化', '账户余额变化', 'O1/O2价格变化', 'LP余额变化'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # 第一个子图：池子余额变化
    fig.add_trace(go.Scatter(
        x=df['operation_id'],
        y=df['pool_balance'],
        mode='lines+markers',
        name='池子余额 (USDC)',
        line=dict(color='blue', width=2),
        marker=dict(size=4)
    ), row=1, col=1)
    
    # 第二个子图：账户余额变化
    fig.add_trace(go.Scatter(
        x=df['operation_id'],
        y=df['user_balance'],
        mode='lines+markers',
        name='交易账户余额 (USDC)',
        line=dict(color='red', width=2),
        marker=dict(size=4)
    ), row=1, col=2)
    
    fig.add_trace(go.Scatter(
        x=df['operation_id'],
        y=df['lp_provider_balance'],
        mode='lines+markers',
        name='LP提供者账户余额 (USDC)',
        line=dict(color='green', width=2),
        marker=dict(size=4)
    ), row=1, col=2)
    
    fig.add_trace(go.Scatter(
        x=df['operation_id'],
        y=df['owner_balance'],
        mode='lines+markers',
        name='Owner余额 (USDC)',
        line=dict(color='purple', width=2),
        marker=dict(size=4)
    ), row=1, col=2)
    
    # 第三个子图：O1/O2价格变化
    fig.add_trace(go.Scatter(
        x=df['operation_id'],
        y=df['o1_price'],
        mode='lines+markers',
        name='O1价格 (USDC)',
        line=dict(color='teal', width=2),
        marker=dict(size=4)
    ), row=2, col=1)
    
    fig.add_trace(go.Scatter(
        x=df['operation_id'],
        y=df['o2_price'],
        mode='lines+markers',
        name='O2价格 (USDC)',
        line=dict(color='darkorange', width=2),
        marker=dict(size=4)
    ), row=2, col=1)
    
    # 第四个子图：LP余额变化
    fig.add_trace(go.Scatter(
        x=df['operation_id'],
        y=df['user_lp_balance'],
        mode='lines+markers',
        name='LP提供者账户LP余额',
        line=dict(color='darkviolet', width=2),
        marker=dict(size=4)
    ), row=2, col=2)
    
    # 更新布局
    fig.update_layout(
        title="📈 链上合约完整监控面板",
        height=800,
        showlegend=True,
        hovermode='x unified'
    )
    
    # 显示图表
    st.plotly_chart(fig, use_container_width=True)
    
    # 显示操作分布统计
    st.subheader("📊 操作分布统计")
    operation_counts = df['operation'].value_counts()
    
    # 过滤掉"初始化"操作来统计真实操作
    real_operations = df[df['operation'] != '初始化']
    
    if len(real_operations) > 0:
        real_operation_counts = real_operations['operation'].value_counts()
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**操作次数统计:**")
            for op, count in real_operation_counts.items():
                percentage = (count / len(real_operations)) * 100
                st.write(f"- {op}: {count}次 ({percentage:.1f}%)")
            
            # 显示总操作数
            st.write(f"**总操作数:** {len(real_operations)}次")
        
        with col2:
            # 创建操作分布饼图
            fig_pie = go.Figure(data=[go.Pie(
                labels=real_operation_counts.index,
                values=real_operation_counts.values,
                hole=0.3
            )])
            fig_pie.update_layout(
                title="操作分布",
                height=300
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("💡 尚未执行任何交易操作，当前仅显示初始状态数据。请执行一些操作后查看分布统计。")
    
    # 显示统计信息
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if len(df) > 0:
            st.metric(
                "池子余额", 
                f"{df['pool_balance'].iloc[-1]}"
            )
    
    with col2:
        if len(df) > 0:
            st.metric(
                "交易账户", 
                f"{df['user_balance'].iloc[-1]}"
            )
    
    with col3:
        if len(df) > 0:
            st.metric(
                "LP提供者", 
                f"{df['lp_provider_balance'].iloc[-1]}"
            )
    
    with col4:
        if len(df) > 0:
            st.metric(
                "Owner余额", 
                f"{df['owner_balance'].iloc[-1]}"
            )
    
    with col5:
        # 计算成功率时排除初始化操作
        real_operations = df[df['operation'] != '初始化']
        if len(real_operations) > 0:
            success_rate = (real_operations['success'].sum() / len(real_operations)) * 100
            st.metric("操作成功率", f"{success_rate:.1f}%")
        else:
            st.metric("操作成功率", "暂无数据")
    
    # 详细操作历史
    with st.expander("📝 查看详细操作历史"):
        display_df = df[['operation_id', 'operation', 'amount', 'success', 'tx_hash', 
                        'pool_balance', 'user_balance', 'lp_provider_balance', 'owner_balance',
                        'o1_price', 'o2_price', 'user_lp_balance']].copy()
        display_df['tx_hash'] = display_df['tx_hash'].apply(lambda x: f"{x[:10]}..." if x else "失败")
        # 不进行任何四舍五入，保持原始精度
        st.dataframe(display_df, use_container_width=True)

# 说明信息
with st.expander("ℹ️ 使用说明"):
    st.markdown("""
    ### ⚠️ 重要提醒：
    - 这是真实的链上操作，会产生 Gas 费用
    - 操作在 Arbitrum Sepolia 测试网上执行
    - 使用 `web3.eth.wait_for_transaction_receipt()` 轮询交易状态
    - 每次操作都会等待链上确认（超时120秒）
    
    ### 操作说明：
    - **Deposit O1**: 用户向合约存入 BaseToken 换取 O1 代币 (option_out=0)
    - **Deposit O2**: 用户向合约存入 BaseToken 换取 O2 代币 (option_out=1)  
    - **Withdraw O1**: 用户卖出 O1 代币换取 BaseToken (option_in=0)
    - **Withdraw O2**: 用户卖出 O2 代币换取 BaseToken (option_in=1)
    - **Add Liquidity**: 用户向合约添加流动性获得LP代币
    - **Remove Liquidity**: 用户移除流动性，销毁LP代币换取BaseToken
    
    ### 智能操作逻辑：
    - 使用合约的 `get_price()` 函数获取实时的 O1/O2 价格
    - 系统根据当前BaseToken余额自动判断可执行的操作
    - Withdraw 操作使用固定金额范围，由合约检查是否有足够的代币余额
    - 操作金额根据用户BaseToken余额比例智能调整
    
    ### 合约参数说明：
    - **Option 0 (O1)**: 第一个预测选项代币，索引为 0
    - **Option 1 (O2)**: 第二个预测选项代币，索引为 1
    - **BaseToken**: 基础代币 (USDC)，用于购买选项代币和添加流动性
    - **Owner**: 合约所有者地址，追踪其BaseToken余额变化
    
    ### 账户分离设计：
    - **交易账户**: 执行 Deposit/Withdraw 操作，买卖 O1/O2 代币
    - **LP提供者账户**: 执行 Add/Remove Liquidity 操作，管理流动性
    - 两个账户使用不同地址，实现操作类型的完全分离
    
    ### 图表说明：
    **第一个图 - 池子余额变化:**
    - 🔵 **蓝色线**：合约中的 BaseToken 余额
    
    **第二个图 - 账户余额变化:**
    - 🔴 **红色线**：交易账户的 BaseToken 余额  
    - 🟢 **绿色线**：LP提供者账户的 BaseToken 余额
    - 🟣 **紫色线**：Owner钱包的 BaseToken 余额
    
    **第三个图 - 价格变化:**
    - 🟦 **青色线**：O1 代币实时价格
    - 🟠 **橙色线**：O2 代币实时价格
    
    **第四个图 - LP余额变化:**
    - 🟪 **紫罗兰线**：LP提供者账户的 LP 代币余额
    
    - 显示每次真实交易后的链上状态和实时价格变化
    """) 