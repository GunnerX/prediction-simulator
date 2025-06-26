#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERC20合约封装类
"""

from web3 import Web3
from typing import Optional

class ERC20Contract:
    """封装ERC20合约的调用方法"""
    
    def __init__(self, web3: Web3, token_address: str, private_key: str, account_address: str):
        """
        初始化ERC20合约实例
        
        Args:
            web3: Web3实例
            token_address: ERC20代币合约地址
            private_key: 私钥
            account_address: 账户地址
        """
        self.web3 = web3
        self.token_address = token_address
        self.private_key = private_key
        self.account_address = account_address
        
        # ERC20 ABI定义
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
            },
            {
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        # 创建合约实例
        self.contract = self.web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=self.erc20_abi)
    
    def _get_contract(self):
        """获取ERC20合约实例"""
        return self.contract
    
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
                'gas': gas_limit or 10000000,
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
    
    def get_balance_of(self, account_address: Optional[str] = None) -> int:
        """
        获取ERC20代币余额
        
        Args:
            account_address: 查询的账户地址，默认为当前账户
            
        Returns:
            代币余额
        """
        if account_address is None:
            account_address = self.account_address
            
        contract = self._get_contract()
        balance = contract.functions.balanceOf(Web3.to_checksum_address(account_address)).call()
        print(f"账户 {account_address} 的代币余额: {balance}")
        return balance
    
    def approve(self, spender: str, amount: int, gas_limit: Optional[int] = None) -> str:
        """
        批准ERC20代币花费
        
        Args:
            spender: 被授权地址
            amount: 授权金额
            gas_limit: Gas限制
            
        Returns:
            交易哈希
        """
        contract = self._get_contract()
        return self._send_transaction(
            contract.functions.approve, 
            Web3.to_checksum_address(spender), 
            amount,
            gas_limit=gas_limit
        )
    
    # ========== 额外的辅助方法 ==========
    
    def get_allowance(self, owner: Optional[str] = None, spender: str = None) -> int:
        """
        获取ERC20代币授权额度
        
        Args:
            owner: 代币所有者，默认为当前账户
            spender: 被授权地址
            
        Returns:
            授权额度
        """
        if owner is None:
            owner = self.account_address
            
        contract = self._get_contract()
        allowance = contract.functions.allowance(owner, spender).call()
        print(f"授权额度: {allowance}")
        return allowance
    
    def get_decimals(self) -> int:
        """
        获取代币小数位数
        
        Returns:
            小数位数
        """
        contract = self._get_contract()
        decimals = contract.functions.decimals().call()
        return decimals
    
    def get_symbol(self) -> str:
        """
        获取代币符号
        
        Returns:
            代币符号
        """
        contract = self._get_contract()
        symbol = contract.functions.symbol().call()
        return symbol
    
    def get_name(self) -> str:
        """
        获取代币名称
        
        Returns:
            代币名称
        """
        contract = self._get_contract()
        name = contract.functions.name().call()
        return name
    
    def get_total_supply(self) -> int:
        """
        获取代币总供应量
        
        Returns:
            总供应量
        """
        contract = self._get_contract()
        total_supply = contract.functions.totalSupply().call()
        return total_supply
    
    def get_token_info(self) -> dict:
        """
        获取代币完整信息
        
        Returns:
            代币信息字典
        """
        try:
            contract = self._get_contract()
            
            info = {
                "address": self.token_address,
                "name": contract.functions.name().call(),
                "symbol": contract.functions.symbol().call(),
                "decimals": contract.functions.decimals().call(),
                "total_supply": contract.functions.totalSupply().call(),
                "balance": contract.functions.balanceOf(self.account_address).call()
            }
            
            print(f"代币信息: {info}")
            return info
            
        except Exception as e:
            print(f"获取代币信息失败: {str(e)}")
            return {"error": str(e)} 