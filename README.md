# NtuCapstone — ManiScope

ACT Token 链上行为分析与操纵检测可视化系统。

---

## 目录

- [技术栈](#技术栈)
- [快速启动](#快速启动)
- [系统架构](#系统架构)
- [数据文件](#数据文件)
- [实现状态总览](#实现状态总览)
  - [后端 API 状态](#后端-api-状态)
  - [前端组件状态](#前端组件状态)
  - [检测规则状态](#检测规则状态)
  - [数据管道状态](#数据管道状态)
- [已实现功能详述](#已实现功能详述)
  - [Snapshot 快照服务](#snapshot-快照服务)
  - [transfer-network 检测规则](#transfer-network-检测规则)
- [未实现功能详述](#未实现功能详述)
  - [Entity Detection 规则（待实现）](#entity-detection-规则待实现)
  - [Wash Trade 洗盘检测规则](#wash-trade-洗盘检测规则)
  - [Pump & Dump 拉高出货检测规则](#pump--dump-拉高出货检测规则)

---

## 技术栈

| 层 | 技术 |
|---|---|
| Frontend | Vue 3 + Vite + D3.js + naive-ui |
| Backend | FastAPI + Uvicorn + Python |
| 图算法 | NetworkX |
| 数据处理 | pandas |

---

## 快速启动

```bash
# 1. 启动后端 (port 8000)
cd front/server
pip install fastapi uvicorn pandas pydantic networkx
python main.py

# 2. 启动前端 (port 3000+)
cd front
npm install
npm run dev
```

---

## 系统架构

```
前端 (Vite + Vue3, port 3000+)
  └── /api/*  →  Vite 代理  →  http://localhost:8000
后端 (FastAPI, port 8000)
  ├── /api/entity/*    entity_detection.py
  ├── /api/snapshot/*  snapshot_service.py
  └── /api/analyze     main.py (mock endpoint)
数据
  ├── public/transfer_network_stats.csv               转账对统计 (36MB)
  ├── public/ACT_OHLC.json                            OHLC 价格 (4种粒度)
  └── public/processed/transfers/
        ├── hourly_balance_snapshots.json             每小时余额快照 (516条)
        ├── top_holders_summary.json                  Top Holder 余额历史
        └── owner_labels.json                         地址标签
```

---

## 数据文件

| 文件 | 是否存在 | 大小 | 用途 |
|------|----------|------|------|
| `public/transfer_network_stats.csv` | ✅ | 36 MB | 转账对统计（from/to/count/first/last） |
| `public/ACT_OHLC.json` | ✅ | — | OHLC 价格（1H/1D/3D/1W） |
| `public/processed/transfers/hourly_balance_snapshots.json` | ✅ | — | 每小时余额快照，516条 |
| `public/processed/transfers/top_holders_summary.json` | ✅ | — | Top Holder 余额历史 |
| `public/processed/transfers/owner_labels.json` | ✅ | — | 地址标签（交易所/合约/用户） |
| `user_behavior_sequences.json` | ❌ | — | 用户行为序列（需运行 process_user_behavior.py） |
| 原始逐笔转账 CSV | ❌ | — | 每笔转账记录（含金额/时间），多条规则前置依赖 |

---

## 实现状态总览

### 后端 API 状态

| 方法 | 路径 | 状态 | 说明 |
|------|------|------|------|
| `GET` | `/` | ✅ 已实现 | 健康检查 |
| `GET` | `/api/snapshot/times` | ✅ 已实现 | 返回全部 516 个快照时间戳 |
| `POST` | `/api/snapshot/process` | ✅ 已实现 | 按时间+阈值处理快照，返回 Top Holder 分组 |
| `POST` | `/api/entity/detect` | ⚠️ 部分实现 | 只有 `transfer-network` 规则运行，其余 rule_type 返回 mock 数据 |
| `POST` | `/api/entity/links` | ✅ 已实现 | 返回地址间连线（边权 ≥ threshold） |
| `GET` | `/api/entity/rules/templates` | ⚠️ 部分实现 | 返回静态规则模板结构，无对应执行逻辑 |
| `POST` | `/api/analyze` | ❌ Mock | 固定返回 score=0.85，无实际分析 |

### 前端组件状态

| 组件 | 状态 | 说明 |
|------|------|------|
| `CryptoVis.vue` | ✅ 已实现 | 主布局（3列），事件总线 |
| `ControlPanel.vue` — Snapshot 区域 | ✅ 已实现 | 时间选择 + 阈值 + Update View |
| `ControlPanel.vue` — Network Based 检测 | ✅ 已实现 | threshold + 时间范围输入，可触发检测 |
| `ControlPanel.vue` — Behavior Similarity 检测 | ❌ 未实现 | 显示 "Configuration not yet available." |
| `ControlPanel.vue` — Manipulation Detection | ❌ 未实现 | 点击只弹 alert，无实际功能 |
| `TokenDistribution.vue` | ✅ 已实现 | 气泡图 + 实体组橙色虚线圈 + 连线 |
| `HolderView.vue` | ✅ 已实现 | 单 Holder 余额历史折线图 |
| `CandlestickChart.vue` | ✅ 已实现 | K 线图（使用 ACT_OHLC.json） |
| `SmartContract.vue` | ⚠️ 待确认 | 智能合约相关面板 |
| `FunctionView.vue` | ⚠️ 待确认 | 功能视图 |

### 检测规则状态

| # | 规则 ID | 分类 | 状态 | 数据依赖 |
|---|---------|------|------|----------|
| 1 | `transfer-network` | Entity / 转账网络 | ✅ **已实现** | `transfer_network_stats.csv` ✅ |
| 2 | `funded`（首笔资金溯源） | Entity / 转账网络 | ❌ 未实现 | 原始 CSV ❌ |
| 3 | `high-frequency`（高频交易） | Entity / 转账网络 | ❌ 未实现 | 原始 CSV ❌ |
| 4 | `high-volume`（大额共振） | Entity / 转账网络 | ❌ 未实现 | 原始 CSV ❌ |
| 5 | `shared-in`（共享首笔来源） | Entity / 转账网络 | ❌ 未实现 | 原始 CSV ❌ |
| 6 | `shared-out`（共享末笔出口） | Entity / 转账网络 | ❌ 未实现 | 原始 CSV ❌ |
| 7 | `multi-hop`（快进快出） | Entity / 转账网络 | ❌ 未实现 | 原始 CSV ❌ |
| 8 | Similar Trading Sequence | Entity / 行为相似 | ❌ 未实现 | `user_behavior_sequences.json` ❌ |
| 9 | Similar Balance Sequence | Entity / 行为相似 | ❌ 未实现 | `hourly_balance_snapshots.json` ✅ |
| 10 | Similar Earning Sequence | Entity / 行为相似 | ❌ 未实现 | `user_behavior_sequences.json` ❌ |
| 11 | Wash Roundtrip（买卖净头寸≈0） | Manipulation | ❌ 未实现 | 原始交易 CSV ❌ |
| 12 | Wash Loop Group（闭环转账） | Manipulation | ❌ 未实现 | `transfer_network_stats.csv` ⚠️ |
| 13 | Coordinated Price Move | Manipulation | ❌ 未实现 | 原始 CSV + OHLC ❌ |

> **汇总：13 条规则，1 条已实现（#1 transfer-network），12 条待实现。**

### 数据管道状态

| 脚本 | 状态 | 说明 |
|------|------|------|
| `generate_balance_snapshots.py` | ✅ 已运行 | 已生成 `balance_snapshots.csv` |
| `generate_hourly_snapshots.py` | ✅ 已运行 | 已生成 `hourly_balance_snapshots.json`（516条） |
| `precompute_transfer_stats.py` | ✅ 已运行 | 已生成 `transfer_network_stats.csv`（36MB） |
| `process_user_behavior.py` | ❌ 未接入后端 | 脚本存在但输出 `user_behavior_sequences.json` 未连接后端，为 Rule 8/10 前置条件 |
| `summarize_holders.py` | ✅ 已运行 | 已生成 `top_holders_summary.json` |
| `extract_account_labels.py` | ✅ 已运行 | 已生成 `owner_labels.json` |

---

## 已实现功能详述

### Snapshot 快照服务

**后端文件：** `front/server/snapshot_service.py`

#### GET /api/snapshot/times

返回所有快照时间戳列表（共 516 条，每小时一个，从 2024-10-19 12:00 到 2024-11-10）。

```json
{ "times": ["2024-10-19 12:00:00", "2024-10-19 13:00:00", ...] }
```

#### POST /api/snapshot/process

按指定时间和 threshold 处理快照，返回 Top Holder 分组。算法：对余额排序，cumsum 累计直到超过 threshold 百分比的地址为 Top 组，其余归 "Others"。

**请求体：**

```json
{ "time": "2024-11-09 21:00:00", "threshold": 0.5 }
```

**响应（简化）：**

```json
{
  "time": "2024-11-09 21:00:00",
  "holders": [
    { "address": "addr1", "balance": 1200000, "percentage": 0.045 },
    { "address": "Others", "balance": 8000000, "percentage": 0.30 }
  ]
}
```

---

### transfer-network 检测规则

**后端文件：** `front/server/entity_detection.py`
**触发方式：** `POST /api/entity/detect`，rules 中 `rule_type = "transfer-network"`

#### 算法流程

1. 读取 `transfer_network_stats.csv`（列：`from_owner, to_owner, transaction_count, first_transaction, last_transaction`）
2. 按 `time_range` 近似过滤（`last_transaction >= start` 且 `first_transaction <= end`）
3. 按 `target_users` 过滤（两端均需在目标列表内）
4. 构建**无向图**，边权 = 交易次数（双向合并求和）
5. 删除边权 ≤ threshold 的边
6. 找连通分量，每个含 ≥ 2 节点的分量输出为一个实体组
7. `confidence = 0.8 + 0.02 × min(10, 总交易次数)`

#### 请求示例

```json
POST /api/entity/detect
{
  "target_users": ["addr1", "addr2", "addr3"],
  "time_range": { "start": "2024-10-19 12:00:00", "end": "2024-11-10 00:00:00" },
  "rules": [
    { "rule_type": "transfer-network", "parameters": { "threshold": 5 }, "enabled": true }
  ]
}
```

#### 响应示例

```json
{
  "status": "success",
  "processed_count": 968,
  "detected_entities": [
    {
      "entity_id": "entity_group_0_1234567890",
      "confidence": 0.92,
      "reason": "Network detection (stats): 3 addresses connected via 12 transactions (threshold > 5)",
      "details": { "members": ["addrA", "addrB", "addrC"], "total_transactions": 12, "member_count": 3 }
    }
  ],
  "metadata": { "execution_time_seconds": 6.3, "rules_applied": 1 }
}
```

#### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `threshold` | int | 5 | 最小交易次数；低于此值的边被删除 |

#### 已知局限

- 无向图，不区分转账方向
- 时间过滤为近似值（基于聚合 first/last），无法精确到每笔交易
- 每次调用全量扫描 36MB CSV，无缓存，约需 6s
- 对 `transfer-network` 以外的 `rule_type` 使用 `hash(uid) % 2000` mock 数据，无实际意义

#### /api/entity/links

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `threshold` | int | 1 | 最小交易次数；低于此值的连线不返回 |

实测：threshold=1 → 175,136 条连线；threshold=10 → 15,367 条。

---

## 未实现功能详述

> 以下所有规则均为 ❌ 未实现，仅为参数与算法设计规范，供开发参考。

### Entity Detection 规则（待实现）

#### Rule E-2：`funded` — 首笔资金溯源

**目标：** 检测 B 的第一笔收款来自 A，判断 A 是 B 的启动资金方，发现批量孵化钱包。

**数据依赖：** 原始转账 CSV（需按时间排序提取每地址首笔收款）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `min_shared_count` | int | 3 | 同一 funder 资助的最少地址数 |
| `first_tx_window_hours` | float | 168 | 首笔收款时间允许最大分散范围（小时） |
| `amount_tolerance_pct` | float | 0.2 | 初始资金金额相似度容差 |
| `ignore_exchange_addresses` | bool | true | 是否过滤已知交易所地址 |

---

#### Rule E-3：`high-frequency` — 高频交易

**目标：** 检测短时间密集交易地址，识别机器人 / 做市脚本。

**数据依赖：** 原始转账 CSV

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `window_seconds` | int | 60 | 滑动时间窗口大小（秒） |
| `max_tx_in_window` | int | 10 | 窗口内最大允许交易次数 |
| `min_trigger_count` | int | 3 | 至少触发几次窗口超限才判定高频 |
| `count_direction` | string | `"both"` | `"send"` / `"receive"` / `"both"` |

---

#### Rule E-4：`high-volume` — 大额共振

**目标：** 检测相同时窗内多地址同步大额转账，识别协同操作。

**数据依赖：** 原始转账 CSV（含金额字段）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `min_amount` | float | — | 单笔最小金额阈值 |
| `time_window_hours` | float | 1 | 协同时间窗口 |
| `min_group_size` | int | 3 | 最少同步地址数 |

---

#### Rule E-5：`shared-in` — 共享首笔来源

**目标：** 多个地址的首笔收款均来自同一上游地址 X，识别批量分发控制节点。

**数据依赖：** 原始转账 CSV

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `min_shared_count` | int | 3 | 共享同一来源的地址最少数量 |
| `first_tx_window_hours` | float | 168 | 首笔收款时间允许分散范围 |
| `ignore_exchange_addresses` | bool | true | 是否过滤交易所地址 |

---

#### Rule E-6：`shared-out` — 共享末笔出口

**目标：** 多个地址的最后一笔转出均流向同一目标 Y，识别统一出口 / 资金归集。

**数据依赖：** 原始转账 CSV

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `min_shared_count` | int | 3 | 共享同一出口的地址最少数量 |
| `last_tx_window_hours` | float | 168 | 最后转出时间允许分散范围 |
| `ignore_exchange_addresses` | bool | true | 是否过滤交易所地址 |

---

#### Rule E-7：`multi-hop` — 快进快出（过桥地址）

**目标：** 检测资金停留时间极短的中转地址，识别混淆路径 / 洗钱跳板。

**数据依赖：** 原始转账 CSV（计算 holding time = 收款 → 转出时间差）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_holding_minutes` | int | 60 | 收款后转出最长允许时间 |
| `min_pass_through_ratio` | float | 0.8 | 转出金额 / 收入金额，高于此值视为"穿透" |
| `min_occurrences` | int | 3 | 至少触发几次才算异常 |
| `ignore_exchange_addresses` | bool | true | 是否过滤交易所地址 |

---

#### Rule E-8：Similar Trading Sequence — 相似交易序列

**目标：** 检测多个地址在同时间段内执行高度相似的买卖动作序列，识别协同操纵账户。

**数据依赖：** `user_behavior_sequences.json`（含 `type: buy/sell`, `price_usd`, `amount`, `block_time`）

**算法：** DTW（Dynamic Time Warping）或序列对齐

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `require_same_direction` | bool | true | 是否要求买卖方向一致 |
| `compare_mode` | string | `"action+amount"` | `"action"` / `"action+amount"` / `"action+price"` |
| `min_sequence_length` | int | 3 | 连续相似动作最短长度 |
| `time_window_hours` | float | 6 | 序列需在此窗口内发生 |
| `amount_tolerance_pct` | float | 0.15 | 金额相似度容差 |
| `price_tolerance_pct` | float | 0.05 | 价格相似度容差 |
| `min_similarity_score` | float | 0.75 | 序列整体相似度阈值（0~1） |

---

#### Rule E-9：Similar Balance Sequence — 相似余额曲线

**目标：** 检测多个地址的余额变化曲线高度同步，识别同一控制人 / 强关联账户。

**数据依赖：** `hourly_balance_snapshots.json`（516 个小时快照，**数据已就绪 ✅，可优先实现**）

**算法：** 按时间对齐各地址余额序列 → Pearson 相关系数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sampling_granularity_hours` | int | 1 | 时间采样粒度（小时） |
| `min_pearson_correlation` | float | 0.85 | Pearson 相关系数阈值，超过则认为相似 |
| `min_active_periods` | int | 10 | 地址至少有几个活跃采样点才参与计算 |
| `max_neighbors_per_node` | int | 5 | 每个地址最多保留几个最相似邻居 |
| `min_group_size` | int | 2 | 相似组最小成员数 |

---

#### Rule E-10：Similar Earning Sequence — 相似收益曲线

**目标：** 检测多个地址的 PnL 曲线高度同步，识别同策略账户 / 收益协同操纵群体。

**数据依赖：** `user_behavior_sequences.json`（buy/sell price_usd × amount）+ `ACT_OHLC.json`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `earning_type` | string | `"realized"` | `"realized"` 已实现 / `"unrealized"` 估值 / `"both"` |
| `sampling_granularity_hours` | int | 1 | 时间采样粒度（小时） |
| `min_pearson_correlation` | float | 0.80 | Pearson 相关系数阈值 |
| `min_active_periods` | int | 5 | 最少活跃采样点 |
| `max_neighbors_per_node` | int | 5 | 每个地址最多保留几个最相似邻居 |

---

### Wash Trade 洗盘检测规则

#### Rule W-1：Loop Transfer Pattern — 闭环转账

**目标：** 检测 A → B → C → A 型闭环，识别循环转账 / Wash Trading。

**数据依赖：** 原始转账 CSV（`from_owner`, `to_owner`, `amount_display`, `block_time`）

**算法：** 有向图 + `nx.simple_cycles()`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `min_cycle_length` | int | 2 | 环的最小节点数（A→B→A 算2） |
| `max_cycle_length` | int | 6 | 环的最大节点数，超过视为噪声 |
| `time_window_hours` | float | 24 | 环中所有交易须在此时间窗口内完成 |
| `require_time_order` | bool | true | 是否要求按时间顺序形成闭环 |
| `amount_similarity_pct` | float | 0.2 | 环内各交易金额相似度阈值 |
| `min_net_balance_ratio` | float | 0.1 | 节点净头寸 / 总交易量，低于此值视为中性 |

**置信度公式（建议）：**

$$confidence = 0.5 + 0.1 \times (6 - cycle\_length) + 0.2 \times (1 - amount\_variance) + 0.2 \times time\_score$$

---

#### Rule W-2：Star Transfer Pattern — 星形转账

**目标：** 检测资金归集（多→一）或资金分发（一→多），识别中转地址 / 批量控制地址。

**数据依赖：** 有向转账图，聚合每节点的 in-degree / out-degree

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `direction` | string | `"both"` | `"in"` 归集 / `"out"` 分发 / `"both"` |
| `min_degree` | int | 5 | 中心节点最小连接数 |
| `time_window_hours` | float | 48 | 所有转账发生的时间窗口 |
| `amount_similarity_pct` | float | 0.3 | 各条边金额相似度阈值 |
| `balance_ratio_threshold` | float | 0.15 | 进出金额之差 / 总金额，低于此值视为平衡 |
| `min_tx_per_spoke` | int | 1 | 每条辐射边最少交易次数 |

---

#### Rule W-3：Smurfing — 快进快出（中转跳板）

**目标：** 检测资金停留时间极短的"过桥地址"，识别混淆路径 / 洗钱跳板。

**数据依赖：** 原始转账 CSV（计算每地址收到 → 转出时间差）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_holding_minutes` | int | 60 | 收到资金后转出的最长允许时间 |
| `min_pass_through_ratio` | float | 0.8 | 转出金额 / 收入金额，高于此值视为"穿透" |
| `min_occurrences` | int | 3 | 至少触发几次才算异常 |
| `ignore_exchange_addresses` | bool | true | 是否排除已知交易所地址 |

---

#### Rule W-4：High-Frequency Transaction — 高频交易

**目标：** 检测短时间内密集交易的地址，识别机器人 / 做市脚本。

**数据依赖：** 原始转账 CSV

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `window_seconds` | int | 60 | 滑动时间窗口大小（秒） |
| `max_tx_in_window` | int | 10 | 窗口内最大允许交易次数 |
| `min_trigger_count` | int | 3 | 至少触发几次窗口超限才判定为高频 |
| `count_direction` | string | `"both"` | `"send"` / `"receive"` / `"both"` |

---

### Pump & Dump 拉高出货检测规则

#### Rule P-1：Similar Trading Sequence — 相似交易序列

> 同 Rule E-8，参数见上方。

---

#### Rule P-2：Similar Balance Sequence — 相似余额曲线

> 同 Rule E-9，参数见上方。

---

#### Rule P-3：Similar Earning Sequence — 相似收益曲线

> 同 Rule E-10，参数见上方。

---

#### Rule P-4：Coordinated Price Move — 协同价格操纵

**目标：** 检测多个地址协同在价格上涨前买入、高位后抛出，识别拉高出货行为。

**数据依赖：** 原始交易 CSV（含 buy/sell 及时刻） + `ACT_OHLC.json`（价格时序）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `price_surge_pct` | float | 0.20 | 价格上涨幅度阈值（20% 视为明显拉升） |
| `pre_surge_window_hours` | float | 6 | 拉升前多少小时内的买入算"提前布局" |
| `post_surge_window_hours` | float | 12 | 拉升后多少小时内的卖出算"高位出货" |
| `min_buy_amount` | float | — | 最小布局金额 |
| `min_sell_ratio` | float | 0.5 | 出货量 / 持有量，高于此值视为清仓 |
| `min_coordinated_addresses` | int | 3 | 最少协同地址数 |
| `time_tolerance_minutes` | int | 30 | 多地址动作时间对齐容差 |
