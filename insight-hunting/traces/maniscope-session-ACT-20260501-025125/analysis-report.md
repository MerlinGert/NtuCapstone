# ManiScope Trace Analysis Report

## Scope And Method

This report analyzes the exported ManiScope ACT session in `insight-hunting/traces/maniscope-session-ACT-20260501-025125`.

The analysis uses the trace as primary evidence and local ACT data as supporting validation. User-authored annotations are treated as the strongest evidence of what the user believed. Local trade, transfer, balance, and OHLC files are used to test whether those beliefs are supported by the underlying data.

All trace timestamps are UTC. K-line card labels in screenshots appear to be rendered in the browser's displayed chart time. Where local data was checked against card windows, I call out possible chart-time versus raw-data-time ambiguity.

## Source Files Used

| Source | Use |
|---|---|
| `docs/reports/user-manual.en.md` | View semantics for Token Distribution, K-line cards, Behavior Details, annotations, and Action Tree. |
| `skills/user-trace-analysis.md` | Required workflow and deliverable structure. |
| `session.json` | Action sequence, selected users, card users, view states, annotations, screenshots, and export metadata. |
| `images/*.png` | Visual evidence from action snapshots and user annotations. |
| `front/public/data/hourly_balance_snapshots.json` | Holder concentration and final snapshot ranks at `2024-11-09 23:00:00 UTC`. |
| `front/public/data/sorted_trades.csv` | Per-wallet trades, cohort window summaries, and buy/sell role evidence. |
| `front/public/data/sorted_transfers.csv` and `transfer_network_stats.csv` | Direct transfer evidence and shared transfer-neighbor expansion. |
| `front/public/data/ACT_OHLC.json` | Price movement around user-marked windows. |

## Caveats And Assumptions

- The session has 24 logged actions, 18 annotation records, and 36 exported images. It was exported at `2026-04-30T18:51:25.070Z`.
- Hover and zoom or scroll auto-capture were disabled in config, but several zoom and scroll actions still appear in the action log. Missing screenshots for those categories are expected.
- Some screenshots show K-line card labels with times that may not map one-to-one to raw trade timestamps. I use exact labels when readable, but treat local data checks as validation rather than a reconstruction of the detector's internal event subset.
- The trace supports a collusion hypothesis, but it does not prove motive. Any exchange-listing or external catalyst explanation remains unverified.
- The UI's entity and link component can include similarity and manipulation links, not only direct transfers. Direct-transfer validation is therefore partial evidence for graph connectivity, not a replacement for the UI link detector.

## System Semantics Needed For This Trace

- In Token Distribution, red-stroked nodes are users involved in current manipulation results, blue-stroked nodes are not flagged, orange dashed boundaries show detected entity groups, and grey links show softer link-detection relationships.
- In K-line, cards above the chart are Round Trip events and cards below the chart are Same Direction events. Clicking a card loads its participating wallets into Behavior Details.
- In Behavior Details, blue circles are buy actions, pink circles are sell actions, grey arrows are transfers, light blue areas show balances, and red boxes mark detected manipulation sequences. Sequential Time changes the x-axis from calendar time to event order.
- Annotation records capture what the user considered important enough to preserve. High-level insight records in the Action Tree can combine earlier annotation nodes.

## Chronological Reconstruction

| Step | Actions And Annotations | What Happened | Why It Matters |
|---|---|---|---|
| S1 | Actions 0-2, annotations 0-3, screenshots `images/annotation-0000-token_distribution.png`, `images/annotation-0001-token_distribution.png`, `images/annotation-0002-token_distribution.png` | The user loaded ACT at snapshot `2024-11-09 23:00:00 UTC`, toggled links off and back on, then annotated top-holder concentration, three entity regions, and a connected component. | This establishes the user's first high-level concern: supply is centralized and suspicious users are structurally connected. |
| S2 | Action 3, annotations 4-5, screenshots `images/annotation-0004-token_distribution.png`, `images/annotation-0005-behavior_details.png` | The user selected `6Z6RJJ...r2237`, the largest holder, and concluded it was a whale but not a manipulator because the balance came from transfers. | This shows the user was not treating every large holder as malicious. They were trying to distinguish passive storage from active manipulation. |
| S3 | Actions 4-6, annotations 6-7, screenshots `images/action-0005-target-behavior_details-01.png`, `images/action-0007-source-behavior_details-01.png` | The user selected `CqWVLX...xuhV`, zoomed into `2024-10-26T18:37:54.743Z` to `2024-10-27T14:27:23.240Z`, enabled Sequential Time, and judged the same-direction alert as likely normal accumulation. | This is a false-positive check. It also shows the user using Behavior Details rather than relying only on red node styling. |
| S4 | Actions 7-11, annotations 8-10, screenshots `images/action-0009-source-behavior_details-01.png`, `images/annotation-0009-behavior_details.png`, `images/annotation-0010-behavior_details.png` | The user selected `DNLFULT...naji`, showed related users, then selected `DmJRzw...7uLH` from Behavior Details. They noted frequent DNL buying, transfers to a seemingly normal account, and another address buying similar amounts in the same period. | This is the first concrete role hypothesis: DNL looks like a functional account, and DmJ appears as a related actor whose activity may affect price. |
| S5 | Action 12, annotation 12, screenshot `images/annotation-0012-candlestick_chart.png` | The user scrolled the Same Direction cards and annotated the K-line price region, stating that the activity clearly affected price. | This connects behavior-level evidence to market-level price movement. |
| S6 | Actions 13-15, annotation 13, screenshots `images/action-0014-source-kline_chart-01.png`, `images/action-0014-target-behavior_details-01.png`, `images/annotation-0013-behavior_details.png` | The user clicked a 9-wallet manipulation card with users `5RA...`, `CqW...`, `5WF...`, `DmJ...`, `35N...`, `22J...`, `EnM...`, `BgB...`, and `5YP...`. They annotated an Oct 26 cluster: after DmJ sold, nine addresses bought frequently in the same direction. | This is the strongest same-direction coordination evidence in the trace. It shows a multi-wallet sequence rather than a single wallet anomaly. |
| S7 | Actions 16-20, annotations 14-15, screenshots `images/action-0017-target-behavior_details-01.png`, `images/annotation-0014-behavior_details.png`, `images/annotation-0015-behavior_details.png` | The user clicked another 9-wallet card: `7Sm...`, `DmJ...`, `2br...`, `XiX...`, `85T...`, `DNL...`, `5YP...`, `ErA...`, `Eu4...`. They toggled Sequential Time and zoomed to compare ordering, then annotated alternating same-direction buy and sell clusters as round-trip-like. | This broadens the investigation from pure accumulation into role alternation and possible wash or round-trip behavior. |
| S8 | Actions 21-23, annotations 17-19, screenshots `images/action-0022-source-kline_chart-01.png`, `images/action-0022-target-behavior_details-01.png`, `images/annotation-0017-behavior_details.png`, `images/annotation-0019-token_distribution.png` | The user clicked a 3-wallet card with `7Sm...`, `DmJ...`, and `GCDE...`, annotated that these addresses fall in the same connected component, then created a high-level insight that many selected addresses form a large colluding group. | This is the user's final synthesis: multiple card cohorts and graph evidence should be understood as one larger component, not isolated events. |

## Reconstructed Cohorts

| Cohort | Trace Source | Users |
|---|---|---|
| A: Oct 26 9-user same-direction card | Action 13, annotation 13 | `5RA23pdRqxPHjGZT9kUCdywx5QgQ3NFo5NXiNSsCCVEz`, `CqWVLXaj8r6vud5SfFr81SzmFoqXa5daLi1WbpQZxuhV`, `5WF1V6TBDHxrZvPhh6doyE5ZEb8BaFFgqg7wR81zmZEw`, `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH`, `35NoW8F4Q3Gcqf3Wf4RMmoAgS7FHchCjv3R2F241zuPQ`, `22JYebQtQSLchTXiRJVCx7hpPamN1YzLJKHET52S6eBm`, `EnMAi9raXU8KMBP3YLKAsLL1EnucWrggtBAxZAsmLBZ3`, `BgBmwgMG1cRQxHKkgYd42Gz8rpXtSNcnqgazWGPfdDon`, `5YPynSvVjWB6EQeFNg3WiKoGsm7J9doxpBY3sVMy1xYv` |
| B: Oct 31 9-user alternating card | Action 16, annotations 14-15 | `7SmhQ9r2TLLgS5cmWoFSVGZZw7sEySmZXzwBVscrc7qb`, `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH`, `2brzD1rU8m71zf23bfgtw3vn9pqZG2CDxYU3nQ5pPizN`, `XiXRAfbXGgNsZw2hwPdqBsU461kXFfYgTMV8sgjRSvN`, `85TMiRBoDjZiFjHUwrrBkqZDh4o3SHMPtgbDXM7N7Qff`, `DNLFULTWBTkpfwpXZeMA7ckMbQntHuLqxZq6RH6xnaji`, `5YPynSvVjWB6EQeFNg3WiKoGsm7J9doxpBY3sVMy1xYv`, `ErAJGcJTEUqa11ag1MxLWZjqoqzgTtZKJk9cQiN9T3ZU`, `Eu4DNnkPbV9kMj81FwaZMHPqAHsBAVrwbtjGfKdRhVzh` |
| C: Oct 25 3-user connected-component card | Action 21, annotations 17-19 | `7SmhQ9r2TLLgS5cmWoFSVGZZw7sEySmZXzwBVscrc7qb`, `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH`, `GCDEuA5Q6KugDcN5wxnorwkeSrMYiPJse24pDfFbLZXz` |

Important overlaps:

| Overlap | Users | Interpretation |
|---|---|---|
| A and B | `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH`, `5YPynSvVjWB6EQeFNg3WiKoGsm7J9doxpBY3sVMy1xYv` | These two link the Oct 26 same-direction group to the later alternating group. |
| A and C | `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH` | DmJ bridges the earlier 3-wallet card and the larger Oct 26 cohort. |
| B and C | `7SmhQ9r2TLLgS5cmWoFSVGZZw7sEySmZXzwBVscrc7qb`, `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH` | 7Sm and DmJ link the 3-wallet card to the later 9-wallet card. |

## User Intentions By Level

### Low-Level Intentions

| ID | Intention | Evidence | Rationale |
|---|---|---|---|
| I-L1 | Load ACT at the late snapshot and expose links in Token Distribution. | Actions 0-2. | The first sequence sets snapshot `2024-11-09 23:00:00 UTC` and toggles Show Links back on before annotations. |
| I-L2 | Inspect whether `6Z6...r2237` is a manipulator or only a passive whale. | Action 3, annotations 4-5. | The user selected the largest holder and then annotated that it has no manipulative behavior and acquired tokens through transfers. |
| I-L3 | Inspect `CqW...xuhV` in Behavior Details and compare absolute versus sequential time. | Actions 4-6, annotations 6-7. | The user zoomed a behavior window and enabled Sequential Time after selecting CqW. |
| I-L4 | Inspect `DNL...naji` with related users visible. | Actions 7-8, annotations 8-9. | The user turned on Show Related Users after selecting DNL and annotated direct transfers. |
| I-L5 | Inspect K-line manipulation cards and load card cohorts into Behavior Details. | Actions 12-22. | The user scrolled same-direction cards and clicked three manipulation cards. |

### Mid-Level Intentions

| ID | Intention | Evidence | Rationale | Confidence |
|---|---|---|---|---|
| I-M1 | Assess whether ACT has high manipulation risk from holder concentration plus structural links. | Annotations 0-3, Token Distribution screenshots. | The user did not only count whales. They marked red suspicious nodes, orange entity groups, and connected components, which implies a combined concentration and linkage assessment. | Direct evidence |
| I-M2 | Separate suspicious-looking but benign holders from accounts that function inside a manipulative group. | S2, S3, S4. | The user explicitly cleared 6Z, tentatively cleared CqW, then described DNL as a functional account serving an entity. This contrast shows a classification intent. | Strong inference |
| I-M3 | Test whether Behavior Details anomalies map to K-line price effects. | Annotation 10 and annotation 12. | The user first wrote that similar buying affected price, then annotated the K-line with "clearly affected the price." This ties wallet-level activity to market movement. | Direct evidence |
| I-M4 | Compare multiple detected manipulation cohorts for common wallets and repeated behavior patterns. | Actions 13, 16, 21 and annotations 13-19. | The user moved from one 9-wallet card to another 9-wallet card and then to a 3-wallet card, using Behavior Details and Token Distribution to compare them. | Strong inference |

### High-Level Intentions

| ID | Intention | Evidence | Rationale | Confidence |
|---|---|---|---|---|
| I-H1 | Build a case that ACT manipulation is organized by a larger connected group rather than isolated suspicious wallets. | High-level insight annotation 18, annotations 0-2, 8-10, 13-19. | The final insight selected 12 prior annotations and states that the addresses form a large colluding group. The selected evidence spans graph structure, transfers, price effects, and card cohorts. | Direct evidence |
| I-H2 | Identify roles inside the suspected group: passive whale, functional buyer, clean-looking sink, repeated bridge, and card cohort participants. | 6Z, CqW, DNL, GvZ, DmJ, card cohorts A, B, and C. | The user repeatedly asks whether a holder is normal, functional, or connected. The local data reinforces this role-oriented framing. | Strong inference |

## Insights By Level

### Low-Level Insights

| ID | Insight | Evidence | Validation |
|---|---|---|---|
| G-L1 | ACT's late snapshot is highly centralized. | Annotation 0 and high-level insight annotation 3. | At `2024-11-09 23:00:00 UTC`, 49 positive-balance wallets held 30.29 percent of user-held ACT. The UI annotation estimated approximately 51 users, which is close to the local data result. |
| G-L2 | `6Z6...r2237` is a top whale but shows no trades in local trade data. | Annotations 4-5. | Local data ranks it first at 10,636,142 ACT. It has 0 buys and 0 sells in `sorted_trades.csv`, and was funded by `4V9n...zkQ6` in two transfers on `2024-10-24 11:07:39 UTC` and `2024-10-24 11:07:59 UTC`. |
| G-L3 | `DNL...naji` transferred a large balance to `GvZ...ZHD`, which itself shows no trades. | Annotation 9 and screenshot `images/action-0009-source-behavior_details-01.png`. | Local transfer data shows DNL sent 800,000 ACT, 6,500,000 ACT, and 528,572.256551 ACT to `GvZknRDvFn1XXhBycPxw1kAL2dVDa2pAB5fJdRmmDZHD` on `2024-10-31 01:43:33 UTC` to `01:53:38 UTC`. GvZ ranks fifth at 7,828,572 ACT and has 0 trades. |
| G-L4 | `DmJ...7uLH` appears in every clicked card cohort. | Actions 13, 16, and 21. | Local data shows DmJ ranked seventh at 7,049,447 ACT, with $541,883 buys and $172,183 sells across 103 buy records and 22 sell records. |

### Mid-Level Insights

| ID | Insight | Evidence And Rationale | Validation And Caveats |
|---|---|---|---|
| G-M1 | The initial graph evidence supports a structural manipulation-risk hypothesis, not just a whale-count concern. | Annotations 0-2 mark red nodes, three entity regions, and a connected component. The user links concentration, detected entities, and links before selecting any specific wallet. | Local data confirms concentration. The exact UI component membership comes from ManiScope's entity and link detector and cannot be fully reproduced from direct transfers alone. |
| G-M2 | DNL likely acts as a functional account that accumulates and then moves inventory to a clean-looking sink. | The user annotated DNL as frequent buyer and transfer-out account, then marked direct transfers to a seemingly normal account. | DNL bought $454,482 of ACT and sold only $4,634. It transferred 7,828,572 ACT to GvZ, which has no trades and remains a top holder. This strongly supports the functional-account and storage-account role split. |
| G-M3 | CqW is plausibly a false positive in the viewed same-direction window, but it should not be fully cleared. | The user saw progressive accumulation and wrote that the same-direction ramp may be normal. | CqW is rank 2 with 10,229,457 ACT, $268,897 buys, and only $10,700 sells. However, transfer stats show it shares major transfer neighbors with DNL and DmJ, including `5Q544f...ge4j1`, `BQ72n...GQDV`, `7tPwv...QVzK`, and `7NoYC...g9e9`. The local data weakens a full "normal holder" conclusion. |
| G-M4 | The Oct 26 9-wallet card is best read as coordinated accumulation around an event window. | Annotation 13 states that after DmJ sold, nine addresses bought frequently in the same direction. The behavior screenshot marks a dense Oct 26 cluster across several cohort rows. | Using the chart-label window shifted by 8 hours, all 9 A-cohort users were active, with 126 buys, 0 sells, about 30.37M ACT bought, and about $805k buy notional. In the unshifted label window, 4 A users bought 11.62M ACT with no sells. Timezone ambiguity affects the exact count, but not the buy-heavy direction. |
| G-M5 | The later 9-wallet card is not a simple buy-only pattern; it looks like role alternation or round-trip-like coordination. | Annotation 14 says same-direction trading alternates between buys and sells. Annotation 15 shows the same card in Sequential Time with separated clusters. | In the broad `2024-10-31` to `2024-11-01` window, 8 of 9 B users were active, with $485,513 buys and $174,971 sells. Around the apparent shifted card label window, XiX bought and sold within minutes, while 7Sm and Eu4 bought and ErA sold shortly after. This supports mixed roles rather than one-direction accumulation. |
| G-M6 | Price impact is plausible but should be tied to specific windows. | Annotation 12 states that the marked activity clearly affected price. | In minute OHLC, the readable `2024-10-25 17:24:32` to `2024-10-26 02:52:01` window rose about 100 percent from first open to last close. The broader marked period around Oct 24 to Oct 27 contains both a large decline and recovery. The evidence supports material price movement, but direction depends on which card window is tested. |

### High-Level Insights

| ID | Insight | Evidence And Rationale | Validation And Caveats |
|---|---|---|---|
| G-H1 | The strongest supported narrative is a layered manipulation ecosystem with different wallet roles. | The trace begins with entity and component structure, then classifies 6Z, CqW, DNL, DmJ, and card cohorts. The final high-level insight combines 12 earlier annotations into a large colluding-group claim. | Local data supports roles: 6Z and GvZ are passive high-balance storage wallets with no trades; DNL is a heavy buyer and transfer-out wallet; DmJ bridges all clicked card cohorts; 5YP and 7Sm bridge subsets of cohorts; several top holders are repeated card users. |
| G-H2 | The suspected component is larger than the wallets clicked in the trace. | The UI shows connected components and the user explicitly says most selected addresses belong to the identified component. | Transfer-neighbor expansion found common hubs. `5Q544f...ge4j1` connects 15 of the 19 trace-union users with 292 transactions and 86.65M ACT volume. Other shared neighbors include `BQ72n...GQDV`, `7tPwv...QVzK`, `7NoYC...g9e9`, `CapuX...LVps`, and `GuYRk...22J`. These are strong expansion targets, but they require role validation before being labeled colluders. |
| G-H3 | "Clean-looking account" behavior is strongly supported for DNL to GvZ, but only hypothesized for the broader entity set. | Annotation 1 speculates that normal-looking accounts inside entities may be intentional. Annotation 9 provides a concrete DNL transfer case. | DNL to GvZ is strong direct evidence. Applying the same explanation to every blue or normal-looking node inside entity boundaries needs more transfer and behavior checks. |

## Evidence Tables

### Snapshot And Wallet Roles

| Wallet | Snapshot Rank | Snapshot Balance | Trace Role | Local Trade Summary |
|---|---:|---:|---|---|
| `6Z6RJJGrmVyndcPyTFhmLYHkHttiYtTccKpXFV9r2237` | 1 | 10,636,142 ACT | Passive whale candidate | 0 buys, 0 sells; funded by transfers. |
| `CqWVLXaj8r6vud5SfFr81SzmFoqXa5daLi1WbpQZxuhV` | 2 | 10,229,457 ACT | Accumulator, possible false positive but not fully cleared | 27 buys, 2 sells; $268,897 buy, $10,700 sell. |
| `DNLFULTWBTkpfwpXZeMA7ckMbQntHuLqxZq6RH6xnaji` | 3 | 9,328,001 ACT | Functional buyer and transfer-out wallet | 165 buys, 3 sells; $454,482 buy, $4,634 sell. |
| `GvZknRDvFn1XXhBycPxw1kAL2dVDa2pAB5fJdRmmDZHD` | 5 | 7,828,572 ACT | Clean-looking sink candidate | 0 buys, 0 sells; received 7,828,572 ACT from DNL. |
| `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH` | 7 | 7,049,447 ACT | Repeated bridge and active trader | 103 buys, 22 sells; $541,883 buy, $172,183 sell. |

### Cohort Window Summaries

| Window | Cohort | Local Summary | Interpretation |
|---|---|---|---|
| `2024-10-25 23:10:41 UTC` to `2024-10-26 23:42:24 UTC`, chart-label window shifted by 8 hours | A: Oct 26 9-user card | 9 active users, 126 buys, 0 sells, 30.37M ACT bought, about $805k buy notional | Strong buy-side coordination evidence. |
| `2024-10-26 07:10:41 UTC` to `2024-10-27 07:42:24 UTC`, unshifted readable label | A: Oct 26 9-user card | 4 active A users, 67 buys, 0 sells, 11.62M ACT bought, about $319k buy notional | Still buy-heavy, but fewer active wallets due chart-time ambiguity. |
| `2024-10-31` to `2024-11-01` | B: Oct 31 9-user card | 8 active users, $485,513 buys, $174,971 sells, 16.43M ACT bought, 5.51M ACT sold | Mixed buy and sell roles; consistent with alternating or round-trip-like behavior. |
| `2024-10-25` to `2024-10-27` | C: 3-user card | 3 active users, $341,146 buys, $246,572 sells, 14.38M ACT bought, 13.63M ACT sold | Strong active-trading group; not a passive holding cluster. |

### Transfer Evidence

| Evidence | Details | Interpretation |
|---|---|---|
| DNL to GvZ | DNL sent 800,000 ACT, 6,500,000 ACT, and 528,572.256551 ACT to GvZ on `2024-10-31 01:43:33 UTC` to `01:53:38 UTC`. | Strong evidence of a functional buyer moving inventory to a clean-looking storage wallet. |
| 7Sm to Eu4 | `7SmhQ9...c7qb` sent 5,558,866.23 ACT to `Eu4DNn...hVzh` on `2024-10-23 15:31:44 UTC`. | Direct link between two B-cohort wallets. |
| Shared hub `5Q544f...ge4j1` | Connected to 15 of 19 trace-union users, 292 transactions, 86.65M ACT volume. | Strong candidate for expanding the component beyond clicked wallets. |
| Shared hubs `BQ72n...GQDV`, `7tPwv...QVzK`, `7NoYC...g9e9`, `CapuX...LVps` | Each connects 7 or more trace-union users. | These are follow-up entities or infrastructure nodes to classify. |

## Action Recommendations: Top-Down Plan

The recommendations should be read from high-level goals to atomic actions. Each goal explains why the work matters, then breaks the investigation into mid-level workstreams. Atomic actions are grouped into two action types:

- **Visual actions**: actions that require inspecting ManiScope GUI components or screenshots. If the GUI displays a statistic, checking that displayed statistic is still a visual action.
- **Statistical actions**: actions that calculate statistics not shown in the GUI and therefore require scripts or data queries.

### R-H1: Build A Role-Based Collusion Case Timeline

**Why this matters.** The strongest supported interpretation is a layered manipulation ecosystem, not a flat list of suspicious wallets. The case needs to explain what different wallets did, when they did it, and how the roles connect across graph structure, transfers, behavior details, and price movement.

**Target outcome.** A timeline from `2024-10-24` through `2024-11-03` that labels wallets as passive whale, clean-looking sink, functional buyer, bridge actor, accumulation cohort member, round-trip-like actor, or unresolved candidate.

#### Workstream R-H1.M1: Confirm Core Wallet Roles

| Action Type | Atomic Actions | Expected Evidence |
|---|---|---|
| Visual | Open Behavior Details for `6Z6RJJGrmVyndcPyTFhmLYHkHttiYtTccKpXFV9r2237`; check whether the chart shows only transfer-derived balance and no manipulation boxes. | Confirms whether 6Z should stay in the passive-whale role. |
| Visual | Open Behavior Details for `GvZknRDvFn1XXhBycPxw1kAL2dVDa2pAB5fJdRmmDZHD`; inspect whether the balance appears after DNL's transfer and whether the GUI shows trades, manipulation boxes, or related users. | Confirms or weakens the clean-looking sink role. |
| Visual | Open Behavior Details for `DNLFULTWBTkpfwpXZeMA7ckMbQntHuLqxZq6RH6xnaji`; enable Show Related Users; inspect buy clusters, transfer arrows, and related labels. | Confirms the functional-buyer and transfer-out role visually. |
| Visual | Open Behavior Details for `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH`; inspect repeated buy/sell clusters and manipulation boxes across Oct 25, Oct 26, Oct 31, and Nov 1. | Confirms DmJ as a bridge actor across several suspicious windows. |
| Statistical | Calculate per-wallet buy count, sell count, buy USD, sell USD, token inflow, token outflow, first action time, last action time, and final snapshot balance for 6Z, GvZ, DNL, DmJ, CqW, 5YP, 7Sm, XiX, Eu4, and GCDE. | Produces a role table that does not rely only on screenshot interpretation. |
| Statistical | Calculate net inventory change and realized buy/sell notional for each core wallet during `2024-10-24` to `2024-11-03`. | Distinguishes accumulation, distribution, storage, and round-trip-like behavior. |

#### Workstream R-H1.M2: Verify The DNL To GvZ Entity Hypothesis

| Action Type | Atomic Actions | Expected Evidence |
|---|---|---|
| Visual | In Token Distribution, locate DNL and GvZ if both are visible; check whether they sit in the same entity boundary or connected component. | Tests whether the GUI already surfaces the suspected relationship. |
| Visual | In Control Panel, run entity detection with Network Based and Direct Transfer enabled; inspect whether DNL and GvZ are grouped. | Tests whether the existing GUI entity rules support the candidate entity. |
| Visual | In Behavior Details for DNL with Show Related Users enabled, check whether the transfer recipient shown by the GUI corresponds to GvZ. | Aligns the visual transfer arrow with the candidate sink wallet. |
| Statistical | Query `sorted_transfers.csv` for all DNL to GvZ transfers and calculate total amount, transaction count, first timestamp, and last timestamp. | Confirms the direct transfer totals: 7.83M ACT over three transfers. |
| Statistical | Calculate GvZ's complete trade count and transfer history before and after `2024-10-31 01:43:33 UTC`. | Confirms whether GvZ is truly passive storage or later becomes active. |

### R-H2: Validate Manipulation Windows And Price Impact

**Why this matters.** The user explicitly concluded that the suspicious behavior affected price. That claim is important, but it needs exact window validation because screenshots and raw data may use different time displays.

**Target outcome.** A window-by-window evidence table for the A, B, and C card cohorts, with active users, buy/sell direction, notional volume, token amount, price return, and confidence level.

#### Workstream R-H2.M1: Resolve Card Window Ambiguity

| Action Type | Atomic Actions | Expected Evidence |
|---|---|---|
| Visual | Reopen K-line screenshots `images/action-0014-source-kline_chart-01.png`, `images/action-0017-source-kline_chart-01.png`, and `images/action-0022-source-kline_chart-01.png`; transcribe each clicked card's type, date label, exact time label, amount label, and listed users. | Establishes the GUI-observed card metadata. |
| Visual | In ManiScope, click the same cards again if the session can be recreated; check whether the selected card highlight, Behavior Details users, and K-line connection bands match the screenshots. | Confirms that the screenshot-derived windows are not misread. |
| Statistical | For each card, compute cohort trades under both interpretations: raw UTC card label and chart-label time shifted by the local display offset. | Quantifies the time-display ambiguity instead of hiding it. |
| Statistical | For each interpreted window, calculate active-wallet count, buy count, sell count, buy USD, sell USD, ACT bought, ACT sold, median inter-trade interval, and largest single-wallet contribution. | Converts card interpretation into auditable window statistics. |

#### Workstream R-H2.M2: Test Price Impact

| Action Type | Atomic Actions | Expected Evidence |
|---|---|---|
| Visual | Inspect the K-line region marked in `images/annotation-0012-candlestick_chart.png`; compare the user-marked rectangle with the visible candlestick direction and manipulation-card bands. | Checks the user's visual price-impact claim in the GUI. |
| Visual | Use K-line granularity controls to inspect the same windows at `1h`, `1d`, and, if practical, finer granularities; record whether the displayed trend changes materially. | Determines whether price impact is visible only at one granularity or persists across views. |
| Statistical | Calculate OHLC return, high-low range, volume, and before/after return for each card window and for a matched baseline window of similar length. | Tests whether the marked activity coincides with abnormal price movement. |
| Statistical | Calculate the traced cohort's share of market trade volume during each window. | Tests whether the cohort was large enough to plausibly move price. |

#### Workstream R-H2.M3: Compare Detector Explanations

| Action Type | Atomic Actions | Expected Evidence |
|---|---|---|
| Visual | Toggle entity-based manipulation detection in the GUI and rerun manipulation detection; check whether the A, B, and C cards still appear. | Identifies whether the cards depend on entity merging. |
| Visual | Use Behavior Details with and without Sequential Time for the A and B cohorts; compare whether coordination is clearer in absolute time or event order. | Clarifies whether the evidence is simultaneous market action or sequence-pattern similarity. |
| Statistical | Recompute same-direction and round-trip-like summaries for each wallet individually and for the grouped cohorts. | Separates individually suspicious wallets from wallets that only become suspicious as a group. |

### R-H3: Expand The Suspected Component Without Overgeneralizing

**Why this matters.** The trace suggests a larger connected component, but expanding too aggressively will create false positives. Expansion should start from high-confidence bridge evidence and then classify each candidate by role.

**Target outcome.** An expanded component map with confidence labels: confirmed direct-transfer relation, shared hub relation, GUI component relation, behavior-similarity relation, or unresolved relation.

#### Workstream R-H3.M1: Recheck CqW Before Clearing It

| Action Type | Atomic Actions | Expected Evidence |
|---|---|---|
| Visual | Open CqW in Behavior Details with Show Related Users enabled; inspect related-wallet labels, transfer arrows, manipulation boxes, and balance trend. | Determines whether the GUI supports the broader linkage caveat. |
| Visual | In Token Distribution with Show Links enabled, check whether CqW lies inside the same connected component as DNL, DmJ, or the clicked card users. | Tests whether CqW's visual position contradicts the "normal holder" interpretation. |
| Statistical | Calculate CqW's shared transfer neighbors with DNL and DmJ, including transaction count, total volume, first timestamp, and last timestamp. | Tests whether CqW is only behaviorally benign in one window or structurally linked to the group. |
| Statistical | Compare CqW's buy timing with A-cohort and B-cohort activity using overlap counts and nearest-neighbor time gaps. | Checks whether CqW's accumulation is independent or coordinated. |

#### Workstream R-H3.M2: Classify Shared Transfer Hubs

| Action Type | Atomic Actions | Expected Evidence |
|---|---|---|
| Visual | If visible in Token Distribution or related-user lists, inspect `5Q544f...ge4j1`, `BQ72n...GQDV`, `7tPwv...QVzK`, `7NoYC...g9e9`, and `CapuX...LVps`; record whether the GUI shows them as entity members, related users, or peripheral nodes. | Checks whether shared hubs are visible in the investigator-facing graph. |
| Visual | Use snapshots and Behavior Details screenshots to verify whether the hubs connect to multiple clicked wallets in the GUI, not only in raw transfers. | Separates GUI-supported evidence from analyst-only expansion. |
| Statistical | Build a transfer graph induced by the 19 trace-union users plus their shared neighbors; calculate component membership, degree, weighted degree, total volume, and first/last activity. | Produces a reproducible expanded component candidate list. |
| Statistical | For each shared hub, calculate whether it traded, only transferred, or interacted with known pool or contract addresses. | Prevents labeling exchange, pool, or infrastructure artifacts as colluding wallets. |

#### Workstream R-H3.M3: Prepare External Motive Checks Only After On-Chain Evidence Is Stable

| Action Type | Atomic Actions | Expected Evidence |
|---|---|---|
| Visual | Review final GUI annotations and the Action Tree high-level insight to ensure the on-chain story is internally consistent before adding off-chain claims. | Prevents external events from driving the interpretation prematurely. |
| Statistical | After the on-chain timeline is fixed, calculate whether suspicious activity clusters around externally known events, using event timestamps as comparison anchors. | Tests motive hypotheses without weakening the trace-grounded case. |

### Prioritized Next Actions

| Priority | Action Type | Atomic Action | Reason |
|---:|---|---|---|
| 1 | Visual | Inspect GvZ in Behavior Details and compare it with DNL's related-user view. | This is the fastest way to confirm the clean-sink hypothesis visually. |
| 2 | Statistical | Generate a role table for core wallets with buy/sell totals, transfer totals, and final balances. | This turns the main narrative into auditable evidence. |
| 3 | Statistical | Recompute A, B, and C card windows under both raw UTC and chart-time interpretations. | This resolves the most important caveat in the current report. |
| 4 | Visual | Reopen K-line and Behavior Details evidence for A and B cohorts at multiple granularities and with Sequential Time toggled. | This confirms whether coordination is visually robust. |
| 5 | Statistical | Build the expanded transfer graph around shared hubs and classify each hub. | This expands the case while controlling false positives. |

## Bottom Line

The user's main goal was to decide whether ACT's late-snapshot holder graph and manipulation-card events indicate a coordinated manipulation group. The strongest trace-supported finding is not merely that many top holders are red. It is that several high-balance wallets, card cohorts, and transfer-linked accounts appear to play different roles inside a larger component.

The best-supported concrete evidence is DNL's 7.83M ACT transfer to GvZ, DmJ's presence across all clicked cohorts, and the Oct 26 A cohort's buy-heavy pattern. The weakest part of the current case is the broad claim that all normal-looking accounts inside the entity groups are intentional clean accounts. That is strongly supported for DNL to GvZ, but broader generalization needs more transfer and behavior checks.
