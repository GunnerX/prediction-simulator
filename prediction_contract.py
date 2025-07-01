from web3 import Web3
import json
from typing import Optional, Dict, Any, List
from decimal import Decimal
from abi import PredictionAbiJson

class PredictionContract:
    """封装Prediction合约和ERC20合约的调用方法"""
    
    def __init__(self, web3: Web3, prediction_address: str, private_key: str, account_address: str):
        """
        初始化合约实例
        
        Args:
            web3: Web3实例
            prediction_address: Prediction合约地址
            private_key: 私钥
            account_address: 账户地址
        """
        self.web3 = web3
        self.prediction_address = prediction_address
        self.private_key = private_key
        self.account_address = account_address
        
        # ABI定义
        self.erc20_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [
                    {"name": "_owner", "type": "address"},
                    {"name": "_spender", "type": "address"}
                ],
                "name": "allowance",
                "outputs": [{"name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        self.prediction_abi = json.loads(PredictionAbiJson)
        
        # 创建合约实例
        self.prediction_contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(prediction_address),
            abi=self.prediction_abi
        )
    
    def _get_erc20_contract(self, token_address: str):
        """获取ERC20合约实例"""
        return self.web3.eth.contract(address=token_address, abi=self.erc20_abi)
    
    def _send_transaction(self, transaction_func, *args, gas_limit: Optional[int] = None, **kwargs) -> str:
        """
        发送交易的通用方法
        
        Args:
            transaction_func: 合约方法
            *args: 方法参数
            gas_limit: Gas限制
            **kwargs: 其他参数
            
        Returns:
            交易哈希
        """
        try:
            # 构建交易
            transaction = transaction_func(*args).build_transaction({
                'from': self.account_address,
                'nonce': self.web3.eth.get_transaction_count(self.account_address),
                'gasPrice': self.web3.eth.gas_price,
                'gas': gas_limit or 30000000,
                **kwargs
            })
            
            # 签名交易
            signed_txn = self.web3.eth.account.sign_transaction(transaction, private_key=self.private_key)
            
            # 发送交易
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"交易已发送，哈希: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            print(f"发送交易失败: {str(e)}")
            raise
    
    # ========== ERC20 合约方法 ==========
    
    def get_balance_of(self, token_address: str, account_address: Optional[str] = None) -> int:
        """
        获取ERC20代币余额
        
        Args:
            token_address: 代币合约地址
            account_address: 查询的账户地址，默认为当前账户
            
        Returns:
            代币余额
        """
        if account_address is None:
            account_address = self.account_address
            
        contract = self._get_erc20_contract(token_address)
        balance = contract.functions.balanceOf(account_address).call()
        print(f"账户 {account_address} 的代币余额: {balance}")
        return balance
    
    def approve_erc20(self, token_address: str, spender: str, amount: int, gas_limit: Optional[int] = None) -> str:
        """
        批准ERC20代币花费
        
        Args:
            token_address: 代币合约地址
            spender: 被授权地址
            amount: 授权金额
            gas_limit: Gas限制
            
        Returns:
            交易哈希
        """
        contract = self._get_erc20_contract(token_address)
        return self._send_transaction(
            contract.functions.approve, 
            spender, 
            amount,
            gas_limit=gas_limit
        )
    
    def get_allowance(self, token_address: str, owner: Optional[str] = None, spender: Optional[str] = None) -> int:
        """
        获取ERC20代币授权额度
        
        Args:
            token_address: 代币合约地址
            owner: 代币所有者，默认为当前账户
            spender: 被授权地址，默认为prediction合约
            
        Returns:
            授权额度
        """
        if owner is None:
            owner = self.account_address
        if spender is None:
            spender = self.prediction_address
            
        contract = self._get_erc20_contract(token_address)
        allowance = contract.functions.allowance(owner, spender).call()
        print(f"授权额度: {allowance}")
        return allowance
    
    # ========== Prediction 合约方法 ==========
    
    def add_liquidity(self, liquidity: int, to: Optional[str] = None, gas_limit: Optional[int] = None) -> str:
        """
        添加流动性
        
        Args:
            liquidity: 添加的流动性数量
            to: 接收LP代币的地址，默认为当前账户
            gas_limit: Gas限制
            
        Returns:
            交易哈希
        """
        if to is None:
            to = self.account_address
            
        return self._send_transaction(
            self.prediction_contract.functions.addLiquidity,
            liquidity,
            to,
            0,
            gas_limit=gas_limit
        )
    
    def remove_liquidity(self, liquidity: int, gas_limit: Optional[int] = None) -> str:
        """
        移除流动性
        
        Args:
            liquidity: 移除的流动性数量
            gas_limit: Gas限制
            
        Returns:
            交易哈希
        """
        return self._send_transaction(
            self.prediction_contract.functions.removeLiquidity,
            liquidity,
            0,
            gas_limit=gas_limit
        )
    
    def deposit(self, option_out: int, delta: int, min_receive: int, deadline: int = 2892290396, gas_limit: Optional[int] = None) -> str:
        """
        存款操作
        
        Args:
            option_out: 输出选项
            delta: 变化量
            min_receive: 最小接收数量
            deadline: 截止时间
            gas_limit: Gas限制
            
        Returns:
            交易哈希
        """
        return self._send_transaction(
            self.prediction_contract.functions.deposit,
            option_out,
            delta,
            min_receive,
            deadline,
            gas_limit=gas_limit
        )
    
    def withdraw(self, option_in: int, delta: int, min_receive: int, deadline: int = 2892290396, gas_limit: Optional[int] = None) -> str:
        """
        提款操作
        
        Args:
            option_in: 输入选项
            delta: 变化量
            min_receive: 最小接收数量
            deadline: 截止时间
            gas_limit: Gas限制
            
        Returns:
            交易哈希
        """
        return self._send_transaction(
            self.prediction_contract.functions.withdraw,
            option_in,
            delta,
            min_receive,
            deadline,
            gas_limit=gas_limit
        )
    
    def swap(self, option_out: int, option_in: int, delta: int, min_receive: int, deadline: int = 2892290396, gas_limit: Optional[int] = None) -> str:
        """
        交换操作
        
        Args:
            option_out: 输出选项
            option_in: 输入选项
            delta: 变化量
            min_receive: 最小接收数量
            deadline: 截止时间
            gas_limit: Gas限制
            
        Returns:
            交易哈希
        """
        return self._send_transaction(
            self.prediction_contract.functions.swap,
            option_out,
            option_in,
            delta,
            min_receive,
            deadline,
            gas_limit=gas_limit
        )
    
    # ========== 查询方法 ==========
    
    def get_base_token(self) -> str:
        """获取基础代币地址"""
        return self.prediction_contract.functions.baseToken().call()
    
    def get_options(self) -> List[str]:
        """获取所有选项地址"""
        return self.prediction_contract.functions.options().call()

    def get_owner(self) -> str:
        """获取合约所有者"""
        return self.prediction_contract.functions.owner().call()
    
    def get_option_by_index(self, index: int) -> str:
        """根据索引获取选项地址"""
        return self.prediction_contract.functions.options(index).call()
    
    def get_price(self, option: int) -> int:
        """获取选项价格"""
        return self.prediction_contract.functions.price(option).call()
    
    def get_reserves(self, index: int) -> int:
        """获取储备金"""
        return self.prediction_contract.functions.reserves(index).call()
    
    def get_amount_out(self, option_out: int, delta: int) -> int:
        """计算输出金额"""
        return self.prediction_contract.functions.getAmountOut(option_out, delta).call()
    
    def get_state(self) -> Dict[str, Any]:
        """获取合约状态"""
        m = self.prediction_contract.functions.state().call()
        return m
    
    def get_status(self) -> int:
        """获取合约状态"""
        return self.prediction_contract.functions.status().call()
    
    def get_description(self) -> str:
        """获取预测描述"""
        return self.prediction_contract.functions.description().call() 