# Prediction合约封装库

这是一个用于与Prediction预测市场合约交互的Python封装库，提供了简单易用的接口来执行各种操作。

## 功能特性

### ERC20合约操作
- `get_balance_of()` - 获取代币余额
- `approve_erc20()` - 授权代币花费
- `get_allowance()` - 查询授权额度

### Prediction合约操作
- `add_liquidity()` - 添加流动性
- `remove_liquidity()` - 移除流动性
- `deposit()` - 存款操作
- `withdraw()` - 提款操作
- `swap()` - 代币交换

### 查询功能
- `get_base_token()` - 获取基础代币地址
- `get_options()` - 获取所有选项
- `get_price()` - 获取选项价格
- `get_reserves()` - 获取储备金
- `get_state()` - 获取合约状态

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 1. 初始化合约实例

```python
from web3 import Web3
from prediction_contract import PredictionContract

# 配置连接
web3 = Web3(Web3.HTTPProvider("YOUR_RPC_URL"))
prediction = PredictionContract(
    web3=web3,
    prediction_address="0x...",  # 合约地址
    private_key="0x...",         # 私钥
    account_address="0x..."      # 账户地址
)
```

### 2. ERC20操作示例

```python
# 获取代币余额
balance = prediction.get_balance_of("0x...")
print(f"余额: {balance}")

# 授权代币
tx_hash = prediction.approve_erc20(
    token_address="0x...",
    spender="0x...",
    amount=1000000000000000000  # 1 token (18 decimals)
)
```

### 3. 流动性操作

```python
# 添加流动性
tx_hash = prediction.add_liquidity(
    liquidity=1000,
    gas_limit=400000
)

# 移除流动性
tx_hash = prediction.remove_liquidity(
    liquidity=500,
    gas_limit=300000
)
```

### 4. 存款和提款

```python
import time

# 存款
deadline = int(time.time()) + 3600  # 1小时后过期
tx_hash = prediction.deposit(
    option_out=0,
    delta=100,
    min_receive=90,
    deadline=deadline
)

# 提款
tx_hash = prediction.withdraw(
    option_in=0,
    delta=50,
    min_receive=45,
    deadline=deadline
)
```

### 5. 使用辅助工具

```python
from utils import to_wei, from_wei, get_deadline, calculate_slippage

# 单位转换
amount_in_wei = to_wei(1.5, 18)  # 1.5 tokens to wei
amount_in_tokens = from_wei(1500000000000000000, 18)  # wei to tokens

# 生成截止时间
deadline = get_deadline(2)  # 2小时后

# 计算滑点保护
min_receive = calculate_slippage(1000, 0.5)  # 0.5%滑点
```

## 注意事项

1. **私钥安全**: 绝不要在代码中硬编码私钥，建议使用环境变量
2. **Gas费用**: 每个操作都可以自定义gas_limit，建议根据网络情况调整
3. **授权检查**: 在执行需要代币转移的操作前，确保有足够的授权额度
4. **滑点保护**: 在deposit/withdraw操作中合理设置min_receive参数
5. **截止时间**: deadline参数必须是未来的时间戳

## 错误处理

```python
try:
    tx_hash = prediction.deposit(...)
    print(f"交易成功: {tx_hash}")
except Exception as e:
    print(f"交易失败: {str(e)}")
```

## 完整示例

参考 `example_usage.py` 文件查看完整的使用示例。

## 支持的网络

- 以太坊主网
- 测试网络 (Goerli, Sepolia等)
- 兼容EVM的其他链

## 许可证

MIT License 