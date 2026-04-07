# BSC Quest Bench - LLM Blockchain Transaction Benchmark

A comprehensive benchmark for evaluating LLM ability to generate accurate blockchain transaction code from natural language descriptions. Supports both single-round atomic operations and multi-round composite workflows.

> **🎯 Pure Natural Language Testing** — No code templates, no implementation hints, just natural language tasks. Tests true understanding, not pattern matching.

## Overview

BSC Quest Bench tests LLM competency in understanding blockchain concepts and generating correct transaction code. The system evaluates performance across:

- **Atomic Problems (62 problems)**: Single operations evaluated in one round
- **Composite Problems (45 problems)**: Multi-step workflows with planning and execution phases

### Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
cd bsc_quest_bench/skill_runner && bun install && cd ../..

# 2. Run all tests (atomic + composite)
python run_quest_bench.py --model gpt-4o

# 3. Run only atomic problems
python run_quest_bench.py --model gpt-4o --type atomic

# 4. Run only composite problems
python run_quest_bench.py --model gpt-4o --type composite

# 5. Run with naive mode (easier, with implementation hints)
python run_quest_bench.py --model gpt-4o --naive-mode
```

## Key Features

### Core Features
- **Dual Evaluation Mode**: Single-round atomic + Multi-round composite
- **Pure Natural Language Input**: No code templates, only task descriptions
- **Three-Part Prompt**: Role + Environment + Natural Language Task
- **Difficulty Control**: Toggle between normal and naive mode via `--naive-mode`
- **Real-World Simulation**: Tests understanding like real user interactions

### Problem Coverage

| Type | Count | Description |
|------|-------|-------------|
| **Atomic** | 62 | Single blockchain operations |
| **Composite** | 45 | Multi-step workflows |
| **Total** | 107 | Comprehensive coverage |

### Technical Features
- **Specialized Validators**: 62+ validators for precise scoring
- **Efficiency-Based Scoring**: Composite problems penalize extra steps
- **Environment Isolation**: Complete state reset using Anvil snapshots
- **Local Anvil Fork**: BSC mainnet fork with pre-deployed test contracts
- **Fast Execution**: ~0.002s per test reset using snapshots

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BSC Quest Bench Flow                     │
└─────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │  Load Problem   │
                    │   Definition    │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────▼────────┐         ┌─────────▼─────────┐
     │  ATOMIC MODE    │         │  COMPOSITE MODE   │
     │  (Single-Round) │         │  (Multi-Round)    │
     └────────┬────────┘         └─────────┬─────────┘
              │                            │
     ┌────────▼────────┐         ┌─────────▼─────────┐
     │ Generate Prompt │         │  PLANNING PHASE   │
     │ (Role+Env+Task) │         │ (Parse subtasks)  │
     └────────┬────────┘         └─────────┬─────────┘
              │                            │
     ┌────────▼────────┐         ┌─────────▼─────────┐
     │  LLM Generates  │         │ EXECUTION PHASE   │
     │  TypeScript     │         │ (Multiple rounds) │
     └────────┬────────┘         └─────────┬─────────┘
              │                            │
     ┌────────▼────────┐         ┌─────────▼─────────┐
     │ Execute on      │         │ Execute each      │
     │ Anvil Fork      │         │ subtask on Anvil  │
     └────────┬────────┘         └─────────┬─────────┘
              │                            │
              └──────────────┬─────────────┘
                             │
                    ┌────────▼────────┐
                    │   Validation    │
                    │   & Scoring     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Reset via      │
                    │  Snapshot       │
                    └─────────────────┘
```

## Problem Types

### Atomic Problems (62 total)

Single blockchain operations evaluated in one round.

#### 1. Native Token Transfers (7 problems)
| Problem ID | Description |
|------------|-------------|
| `bnb_transfer_basic` | Basic BNB transfer |
| `bnb_transfer_percentage` | Transfer percentage of balance |
| `bnb_transfer_with_message` | Transfer with data field |
| `bnb_transfer_to_contract` | Transfer to contract address |
| `bnb_transfer_max_amount` | Transfer maximum available |
| `wbnb_deposit` | Wrap BNB to WBNB |
| `wbnb_withdraw` | Unwrap WBNB to BNB |

#### 2. ERC20 Operations (12 problems)
| Problem ID | Description |
|------------|-------------|
| `erc20_transfer_fixed` | Fixed amount transfer |
| `erc20_transfer_percentage` | Percentage transfer |
| `erc20_transfer_max_amount` | Maximum amount transfer |
| `erc20_approve` | Approve spender |
| `erc20_increase_allowance` | Increase allowance |
| `erc20_decrease_allowance` | Decrease allowance |
| `erc20_revoke_approval` | Revoke approval |
| `erc20_burn` | Burn tokens |
| `erc20_permit` | ERC2612 signature approval |
| `erc20_transferfrom_basic` | TransferFrom operation |
| `erc20_transfer_with_callback_1363` | ERC1363 callback transfer |
| `erc20_approve_and_call_1363` | ERC1363 approve and call |

#### 3. NFT Operations (6 problems)
| Problem ID | Description |
|------------|-------------|
| `erc721_transfer` | ERC721 transfer |
| `erc721_safe_transfer` | ERC721 safe transfer |
| `erc721_approve` | ERC721 approve |
| `erc721_set_approval_for_all` | ERC721 global approval |
| `erc1155_transfer_single` | ERC1155 single token transfer |
| `erc1155_safe_transfer_with_data` | ERC1155 transfer with data |

#### 4. Contract Interactions (3 problems)
| Problem ID | Description |
|------------|-------------|
| `contract_call_simple` | Simple contract call |
| `contract_call_with_value` | Call with BNB value |
| `contract_call_with_params` | Call with parameters |

#### 5. DeFi Operations (17 problems)

**PancakeSwap Swaps (5 problems)**
- `swap_exact_bnb_for_tokens` - Swap BNB → Token
- `swap_exact_tokens_for_bnb` - Swap Token → BNB
- `swap_exact_tokens_for_tokens` - Swap Token → Token
- `swap_tokens_for_exact_tokens` - Exact output swap
- `swap_multihop_routing` - Multi-hop routing

**PancakeSwap Liquidity (4 problems)**
- `add_liquidity_bnb_token` - Add BNB+Token liquidity
- `add_liquidity_tokens` - Add Token+Token liquidity
- `remove_liquidity_bnb_token` - Remove BNB+Token liquidity
- `remove_liquidity_tokens` - Remove Token+Token liquidity

**Staking/Farming (5 problems)**
- `stake_single_token` - Stake single token
- `stake_lp_tokens` - Stake LP tokens
- `unstake_lp_tokens` - Unstake LP tokens
- `harvest_rewards` - Harvest farming rewards
- `emergency_withdraw` - Emergency withdrawal

**DeFi Queries (3 problems)**
- `query_pair_reserves` - Query pool reserves
- `query_swap_output_amount` - Calculate swap output
- `query_swap_input_amount` - Calculate swap input

#### 6. Query Operations (14 problems)

**Balance & Allowance Queries**
- `query_bnb_balance` - Query BNB balance
- `query_erc20_balance` - Query ERC20 balance
- `query_erc20_allowance` - Query ERC20 allowance

**NFT Queries**
- `query_nft_owner` - Query NFT owner
- `query_nft_balance` - Query NFT balance
- `query_nft_token_uri` - Query NFT metadata URI
- `query_nft_approval_status` - Query NFT approval

**Staking Queries**
- `query_staked_amount` - Query staked amount
- `query_pending_rewards` - Query pending rewards

**Token Info Queries**
- `query_token_metadata` - Query token name/symbol/decimals
- `query_token_total_supply` - Query total supply

**Blockchain Queries**
- `query_current_block_number` - Get current block
- `query_gas_price` - Get gas price
- `query_transaction_count_nonce` - Get nonce

#### 7. Advanced Features (3 problems)
| Problem ID | Description |
|------------|-------------|
| `contract_delegate_call` | Delegate call pattern |
| `contract_payable_fallback` | Payable fallback/receive |
| `erc20_flashloan` | Flash loan execution |

---

### Composite Problems (45 total)

Multi-step workflows with planning and execution phases.

#### Evaluation Flow
```
1. PLANNING PHASE (Not scored)
   └── LLM creates execution plan with subtasks

2. EXECUTION PHASE (Scored)
   └── LLM executes each subtask
   └── Each round counts toward step count

3. VALIDATION
   └── Check final state against requirements
   └── Apply efficiency penalty if steps > optimal
```

#### Scoring Formula
```
Final Score = Base Score × min(1.0, optimal_steps / actual_steps)
```

| Steps Used | Penalty |
|------------|---------|
| ≤ optimal | 100% (no penalty) |
| 2× optimal | 50% |
| 3× optimal | 33% |

#### Composite Problem Categories

**Approval + Operation Workflows (8 problems)**
| Problem ID | Optimal Steps | Description |
|------------|---------------|-------------|
| `composite_approve_add_liquidity` | 3 | Approve tokens then add liquidity |
| `composite_approve_remove_liquidity` | 3 | Approve LP then remove liquidity |
| `composite_approve_stake_tokens` | 3 | Approve then stake tokens |
| `composite_approve_swap_tokens` | 3 | Approve then swap tokens |
| `composite_approve_swap_to_bnb` | 3 | Approve then swap to BNB |
| `composite_approve_swap_query_result` | 3 | Approve, swap, query result |
| `composite_approve_transferfrom` | 3 | Approve then transferFrom |
| `composite_batch_approve_2_tokens` | 3 | Approve 2 tokens for router |

**Batch Transfer Operations (6 problems)**
| Problem ID | Optimal Steps | Description |
|------------|---------------|-------------|
| `composite_batch_transfer_2_bnb` | 3 | Transfer BNB to 2 recipients |
| `composite_batch_transfer_3_bnb` | 3 | Transfer BNB to 3 recipients |
| `composite_batch_transfer_2_tokens` | 3 | Transfer tokens to 2 recipients |
| `composite_batch_transfer_3_tokens` | 3 | Transfer tokens to 3 recipients |
| `composite_batch_mixed_transfers` | 3 | Mixed BNB and token transfers |
| `composite_split_and_transfer` | 3 | Split amount and transfer |

**Query + Verify Workflows (10 problems)**
| Problem ID | Optimal Steps | Description |
|------------|---------------|-------------|
| `composite_batch_query_2_balances` | 3 | Query 2 token balances |
| `composite_batch_query_portfolio` | 3 | Query portfolio balances |
| `composite_query_allowance_approve_verify` | 2 | Query, approve, verify |
| `composite_query_balance_wrap_verify` | 3 | Query, wrap BNB, verify |
| `composite_query_bnb_transfer_verify` | 2 | Query, transfer, verify |
| `composite_query_erc20_transfer_verify` | 3 | Query, transfer ERC20, verify |
| `composite_query_nft_transfer_verify` | 2 | Query, transfer NFT, verify |
| `composite_query_reserves_before_after_swap` | 3 | Query reserves, swap, query again |
| `composite_query_staked_stake_verify` | 2 | Query staked, stake, verify |
| `composite_query_swap_verify_output` | 3 | Query, swap, verify output |

**DeFi Workflows (12 problems)**
| Problem ID | Optimal Steps | Description |
|------------|---------------|-------------|
| `composite_add_liquidity_stake_lp` | 3 | Add liquidity then stake LP |
| `composite_remove_liquidity_unwrap` | 3 | Remove liquidity, unwrap WBNB |
| `composite_full_liquidity_cycle` | 5 | Add, stake, harvest, unstake, remove |
| `composite_liquidity_provision_with_stake` | 6 | Full LP provision workflow |
| `composite_triple_pool_liquidity` | 6 | Interact with 3 pools |
| `composite_multi_token_swap` | 3 | Multi-token swap chain |
| `composite_multi_approve_multi_swap` | 5 | Multiple approvals and swaps |
| `composite_swap_approve_stake` | 3 | Swap, approve, stake |
| `composite_swap_unwrap_bnb` | 3 | Swap to WBNB, unwrap |
| `composite_wrap_swap_wbnb` | 3 | Wrap BNB, swap WBNB |
| `composite_wrap_add_liquidity` | 3 | Wrap BNB, add liquidity |
| `composite_wrap_unwrap_cycle` | 3 | Wrap and unwrap cycle |

**Staking Workflows (6 problems)**
| Problem ID | Optimal Steps | Description |
|------------|---------------|-------------|
| `composite_complete_swap_stake_workflow` | 6 | Swap, add LP, stake |
| `composite_emergency_exit_workflow` | 5 | Emergency unstake and exit |
| `composite_harvest_reinvest_workflow` | 5 | Harvest rewards and reinvest |
| `composite_unstake_harvest_query` | 3 | Unstake, harvest, query |
| `composite_query_rewards_harvest_verify` | 3 | Query rewards, harvest, verify |
| `composite_portfolio_rebalance` | 5 | Rebalance portfolio |

**NFT Operations (2 problems)**
| Problem ID | Optimal Steps | Description |
|------------|---------------|-------------|
| `composite_nft_transfer_with_payment` | 3 | Transfer NFT with BNB payment |
| `composite_nft_bundle_sale` | 5 | Bundle multiple NFT operations |

**Optimized Workflows (1 problem)**
| Problem ID | Optimal Steps | Description |
|------------|---------------|-------------|
| `composite_optimized_swap_with_query` | 5 | Query-optimized swap |

---

## Installation

### Prerequisites

- **Python**: 3.10+
- **Node.js**: 18+ or **Bun**: 1.0+ (recommended)
- **Foundry/Anvil**: Latest version
- **OS**: Ubuntu 22.04+, macOS 12+, or Windows 11 with WSL2

### Step 1: Install Foundry/Anvil

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
anvil --version
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Install TypeScript Runtime & Dependencies

```bash
# Install Bun (recommended)
curl -fsSL https://bun.sh/install | bash

# Install TypeScript dependencies
cd bsc_quest_bench/skill_runner
bun install
cd ../..
```

## Usage

### Run All Tests

```bash
# Run all problems (atomic + composite)
python run_quest_bench.py --model gpt-4o

# Run with naive mode (easier)
python run_quest_bench.py --model gpt-4o --naive-mode
```

### Run by Problem Type

```bash
# Atomic problems only
python run_quest_bench.py --model gpt-4o --type atomic

# Composite problems only
python run_quest_bench.py --model gpt-4o --type composite
```

### Run Specific Problems

```bash
# Test specific problems
python run_quest_bench.py \
  --model gpt-4o \
  --questions bnb_transfer_basic composite_approve_swap_tokens
```

### Run Random Sample

```bash
# Test 10 random problems (proportionally sampled)
python run_quest_bench.py --model gpt-4o --max-questions 10
```

### Resume or Rerun Failed Tests

```bash
# Resume from question index 25 (0-based)
python run_quest_bench.py --model gpt-4o --start-index 25

# Rerun specific failed tests by index
python run_quest_bench.py --model gpt-4o --type composite --rerun-indices "5,6,13,15,20"
```

### Use Custom API Endpoint

```bash
# OpenRouter
python run_quest_bench.py \
  --model anthropic/claude-sonnet-4 \
  --base-url https://openrouter.ai/api/v1 \
  --api-key your-key

# Azure OpenAI
python run_quest_bench.py \
  --model gpt-4 \
  --base-url https://your-resource.openai.azure.com/ \
  --api-key your-key

# Alibaba Cloud DashScope
python run_quest_bench.py \
  --model qwen-turbo \
  --base-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --api-key your-key
```

### Command Line Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--model` | string | ✅ | LLM model name (e.g., gpt-4o, claude-3-sonnet) |
| `--type` | string | ❌ | Problem type: `atomic`, `composite`, or `all` (default: all) |
| `--questions` | list | ❌ | Specific question IDs to test (space-separated) |
| `--max-questions` | int | ❌ | Maximum number of random questions to test |
| `--start-index` | int | ❌ | Start from question index (0-based, for resuming) |
| `--rerun-indices` | string | ❌ | Comma-separated indices to rerun (e.g., "5,6,13,15") |
| `--run-index` | int | ❌ | Run index for multiple experiments (default: 0) |
| `--output-dir` | string | ❌ | Results output directory (default: `results/`) |
| `--api-key` | string | ❌ | API key for LLM provider |
| `--base-url` | string | ❌ | Custom API base URL |
| `--fork-url` | string | ❌ | BSC RPC URL to fork (default: BSC Mainnet) |
| `--naive-mode` | flag | ❌ | Include detailed implementation guidance |
| `--nl-difficulty` | string | ❌ | NL template difficulty: `random`, `precise`, `moderate`, or `vague` (default: random) |
| `--library` | string | ❌ | JavaScript library: `ethers` or `viem` (default: ethers) |

## Scoring System

### Atomic Problems

Each atomic problem is scored on a 100-point scale:

```
Check 1: Transaction Success    (30 points)
Check 2: Recipient Address      (20 points)
Check 3: Transfer Amount        (20 points)
Check 4: Balance Change         (20 points)
Check 5: Gas Usage              (10 points)
─────────────────────────────────────────────
Total:                          100 points
```

### Composite Problems

Composite problems use efficiency-based scoring:

```
Final Score = Base Score × Efficiency Factor

Efficiency Factor = min(1.0, optimal_steps / actual_steps)
```

**Example:**
- Optimal steps: 3
- Actual steps: 4
- Efficiency: 3/4 = 75%
- If base score is 100, final score = 75

**Passing Threshold:** Score ≥ 60

## Results

### Output Files

```
results/quest_bench_{model}_{index}_{timestamp}.json    # Results JSON
log/{model}_{type}_{timestamp}_full.log                  # Full console log
log/{model}_{type}_{timestamp}_fail.log                  # Failed tests only
```

### Example Result Summary

```
================================================================================
📊 FINAL RESULTS
================================================================================
Model: gpt-4o
Total Questions: 107
  - Atomic: 62 (✅ 58 / ❌ 4)
  - Composite: 45 (✅ 40 / ❌ 5)

✅ Successful: 98
❌ Failed: 10

💯 Total Score: 9250.5
📊 Average Score: 85.7
📈 Success Rate: 90.7%
================================================================================
```

## Project Structure

```
.
├── run_quest_bench.py              # Main benchmark runner
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── bsc_quest_bench/
    ├── quest_controller.py         # LLM interaction controller
    ├── quest_env.py                # Anvil environment manager
    ├── quest_executor.py           # Transaction executor
    ├── parameter_generator.py      # Random parameter generation
    ├── system_config.json          # System configuration
    ├── validators/                 # Specialized validators (62+ files)
    │   ├── __init__.py
    │   ├── composite_validator.py  # Multi-turn composite validator
    │   ├── bnb_transfer_validator.py
    │   └── ...
    ├── question_bank/              # Problem definitions
    │   ├── basic_transactions/     # 40 atomic problems
    │   ├── defi_operations/        # 19 atomic problems
    │   ├── advanced_features/      # 3 atomic problems
    │   └── composite_problems/     # 45 composite problems
    ├── skill_runner/               # TypeScript executor
    │   ├── runBscSkill.ts
    │   └── package.json
    └── contracts/                  # Test contracts
        ├── SimpleStaking.sol
        ├── SimpleLPStaking.sol
        └── ...
```

## Environment & Test Contracts

### Execution Environment

The benchmark runs on a **local Anvil fork** of BSC mainnet:

- ✅ All BSC mainnet contracts accessible (PancakeSwap, USDT, CAKE, etc.)
- ✅ Pre-funded test account with BNB and tokens
- ✅ Pre-deployed test contracts for specialized testing
- ✅ Fast snapshot-based state reset (~0.002s)

### Available Test Contracts

| Key | Contract | Purpose |
|-----|----------|---------|
| `erc1363_token` | ERC1363Token | Token with callback support |
| `erc1155_token` | ERC1155Multi | Multi-token NFT |
| `simple_staking` | SimpleStaking | Single-token staking |
| `simple_lp_staking` | SimpleLPStaking | LP token staking |
| `simple_reward_pool` | SimpleRewardPool | Reward distribution |
| `simple_counter` | SimpleCounter | Counter for testing |
| `donation_box` | DonationBox | Donation receiver |
| `message_board` | MessageBoard | Message storage |
| `fallback_receiver` | FallbackReceiver | Fallback function test |

## Prompt Design

### Three-Part Structure

```
┌─────────────────────────────────────────────────────────┐
│ Part 1: Role Prompt (Universal)                        │
├─────────────────────────────────────────────────────────┤
│ "You are an expert blockchain developer..."            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Part 2: Environment Description (Universal)             │
├─────────────────────────────────────────────────────────┤
│ - TypeScript + ethers.js v6                            │
│ - Local Anvil fork of BSC mainnet                       │
│ - Pre-deployed test contracts                           │
│ - Technical specifications                              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Part 3: Natural Language Task (Problem-Specific)        │
├─────────────────────────────────────────────────────────┤
│ "Stake 7.4 CAKE in the single token farming pool"      │
└─────────────────────────────────────────────────────────┘
```

### Difficulty Modes

| Mode | Flag | Description |
|------|------|-------------|
| **Normal** | (default) | Pure natural language, tests true understanding |
| **Naive** | `--naive-mode` | Includes implementation guidance |

## Troubleshooting

### RPC Rate Limit Errors

The default RPC is `https://bsc-dataseed.binance.org` (free public endpoint). If you see `HTTP error 429` or "rate limit reached", consider using a paid RPC provider:

```bash
# Use paid RPC provider (QuickNode, Alchemy, Ankr, etc.)
python run_quest_bench.py --model gpt-4o --fork-url https://your-paid-rpc-endpoint.com

# Alternative free BSC endpoints (may also have rate limits)
python run_quest_bench.py --model gpt-4o --fork-url https://bsc-dataseed1.binance.org
python run_quest_bench.py --model gpt-4o --fork-url https://bsc-dataseed2.binance.org
```

**Recommended paid RPC providers:**
- [QuickNode](https://www.quicknode.com/) - Fast and reliable
- [Alchemy](https://www.alchemy.com/) - Developer friendly
- [Ankr](https://www.ankr.com/) - Affordable pricing
- [NodeReal](https://nodereal.io/) - BSC optimized

### Anvil Connection Issues

```bash
# Bypass proxy for localhost
NO_PROXY="localhost,127.0.0.1" python run_quest_bench.py --model gpt-4o
```

### Resume After Failure

```bash
# Resume from where you left off
python run_quest_bench.py --model gpt-4o --start-index 25

# Or rerun specific failed tests
python run_quest_bench.py --model gpt-4o --type composite --rerun-indices "5,6,13"
```

## Performance

| Operation | Time |
|-----------|------|
| Initial Setup | ~27 seconds |
| Per-Test Reset | ~0.002 seconds |
| 62 Atomic Tests | ~5-10 minutes |
| 45 Composite Tests | ~30-60 minutes |
| Full Benchmark (107) | ~45-90 minutes |

## Recent Updates

### Feature 2: Tightened Validation Thresholds (2026-03-13)

Based on reviewer feedback, we tightened validator tolerance thresholds to improve evaluation precision:

- **Transfer validators**: Tightened from 1-2% to **0.1%**
- **Approval validators**: Tightened from 1% to **0** (exact match)
- **Swap validators**: Unchanged (AMM characteristics require tolerance)

See: [doc/FEATURE_UPDATES.md](doc/FEATURE_UPDATES.md)

### Feature 3: NL Difficulty Control (2026-03-13)

Implemented NL difficulty-based template selection mechanism to control benchmark natural language difficulty:

```bash
# Run tests with different difficulty levels
python run_quest_bench.py --model MODEL --nl-difficulty precise  # Clear, easy
python run_quest_bench.py --model MODEL --nl-difficulty moderate # Balanced
python run_quest_bench.py --model MODEL --nl-difficulty vague    # Ambiguous, hard
python run_quest_bench.py --model MODEL --nl-difficulty random   # Random (default)
```

- **Precise**: Clear technical terms, explicit parameters
- **Moderate**: Some colloquial expressions, but key parameters included
- **Vague**: Colloquial, incomplete or ambiguous information

See: [doc/FEATURE_UPDATES.md](doc/FEATURE_UPDATES.md)

### Viem Library Support (2026-03-13)

Added viem library support to reduce dependency bias:

```bash
# Use ethers.js (default)
python run_quest_bench.py --model MODEL --library ethers

# Use viem
python run_quest_bench.py --model MODEL --library viem
```

**Supported libraries**:
- ✅ **ethers.js v6** - Current mainstream, high representation in LLM training data
- ✅ **viem v2** - Future trend, modern design, excellent performance

See: [doc/VIEM_SUPPORT.md](doc/VIEM_SUPPORT.md)

## Documentation

Complete documentation in `doc/` directory:

- [FEATURE_UPDATES.md](doc/FEATURE_UPDATES.md) - Latest feature updates
- [VIEM_SUPPORT.md](doc/VIEM_SUPPORT.md) - Viem library support details
- [BSC_BENCH_ARCHITECTURE.md](doc/BSC_BENCH_ARCHITECTURE.md) - System architecture
- [QUEST_BENCH_USAGE.md](doc/QUEST_BENCH_USAGE.md) - Usage guide
- [VALIDATOR_STANDARD_v2.md](doc/VALIDATOR_STANDARD_v2.md) - Validator standard
- [JSON_FORMAT_STANDARD_v2.md](doc/JSON_FORMAT_STANDARD_v2.md) - JSON format standard

## License

MIT License

## Acknowledgments

Built with:
- [Foundry/Anvil](https://github.com/foundry-rs/foundry) - Local EVM simulation
- [ethers.js](https://docs.ethers.org/) - Ethereum library
- [viem](https://viem.sh/) - Modern Ethereum library
- [web3.py](https://web3py.readthedocs.io/) - Python Web3 interface
- [Bun](https://bun.sh/) - Fast TypeScript runtime

## Contributing

We welcome contributions! Please:
1. Follow the prompt design philosophy
2. Maintain backward compatibility
3. Add tests for new features
4. Update documentation

## If you are interested in our work, please cite



## Citation

If you use EVM-quest-bench in your research, please cite:

```bibtex
@article{yang2026evm,
  title={EVM-QuestBench: An Execution-Grounded Benchmark for Natural-Language Transaction Code Generation},
  author={Yang, Pei and Chen, Wanyi and Wang, Ke and Ai, Lynn and Yang, Eric and Shi, Tianyu},
  journal={arXiv preprint arXiv:2601.06565},
  year={2026}
}

```




