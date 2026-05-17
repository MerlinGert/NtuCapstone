# Continued Investigation Report

Trace: `maniscope-session-ACT-20260501-025125`

## Scope

This report records execution of every Recommendation Plan Forest branch in `recommendation-plan-graph.json`. The execution used local ACT data, backend-served behavior sequences, and rendered ManiScope views. All kept rendered images are saved under `continued-investigation-assets/`.

## Actions Taken

- `RI_RS1`: calculated buy/sell counts, USD volume, wallet overlap, snapshot balances, and direct transfers for A13, A16, and A21 using `front/public/data/sorted_trades.csv`, `front/public/data/sorted_transfers.csv`, `front/public/data/user_behavior_sequences.json`, and `front/public/data/hourly_balance_snapshots.json`.
- `RI_RS2`: calculated OHLC movement and clicked-cohort market-share percentages using `front/public/data/ACT_OHLC.json` and `front/public/data/sorted_trades.csv`.
- `RI_RS3`: compared selected wallet profiles for 6Z6, CqW, DNL, DmJ, 7Sm, and GCDE.
- `RI_RS4`: rendered Token Distribution, K-line, and Behavior Details evidence through the local ManiScope render API and resolved the proposed A21 adjacent hypothesis.

## Evidence Assets

- `continued-investigation-assets/follow-up-data-summary.json`
- `continued-investigation-assets/token-distribution-final-snapshot.png`
- `continued-investigation-assets/kline-oct25-oct28-window.png`
- `continued-investigation-assets/behavior-a13-card-window.png`
- `continued-investigation-assets/behavior-a16-card-window.png`
- `continued-investigation-assets/behavior-a21-card-window.png`

## Branch Results

### RS1: Classify Card Roles

Status: executed.

| Card | Users | Window used for local validation | Trades | Buys / sells | Clicked USD | Market share | Net tokens | Users with trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A13 | 9 | 2024-10-25T08:38:45Z to 2024-10-26T08:38:24Z | 115 | 99 / 16 | $846,294.23 | 1.52% | 20.17M | 8 |
| A16 | 9 | 2024-10-26T07:10:41Z to 2024-10-27T07:42:24Z | 35 | 19 / 16 | $256,955.53 | 0.84% | -2.03M | 4 |
| A21 | 3 | 2024-10-25T17:24:32Z to 2024-10-26T02:52:01Z | 36 | 16 / 20 | $271,203.00 | 1.24% | -3.39M | 2 |

Key evidence:

- A13 is net-buying in the screenshot-derived card window: 99 buys, 16 sells, $846,294.23, and 20.17M net tokens.
- A16 is mixed and role-specialized: 19 buys, 16 sells, $256,955.53, and -2.03M net tokens. Eu4 and ErA act as sellers in the exact window, while 85T and XiX are buyers.
- A21 is compact and round-trip-like: DmJ and GCDE trade in the exact A21 window, with $271,203.00 across 36 trades.
- Repeated wallets connect the card sequence: A13/A16 share 5YP...xYv and DmJ...uLH; A16/A21 share 7Sm...7qb and DmJ...uLH; A13/A21 share DmJ...uLH.

### RS2: Quantify Price Windows

Status: executed.

| Window | 1H rows covered | Open | Close | High | Low | Open-to-close |
| --- | --- | --- | --- | --- | --- | --- |
| A13 | 2024-10-25T09:00:00Z to 2024-10-26T08:00:00Z | 0.016268 | 0.023241 | 0.043826 | 0.014645 | 42.86% |
| A16 | 2024-10-26T08:00:00Z to 2024-10-27T07:00:00Z | 0.028001 | 0.024391 | 0.043633 | 0.015091 | -12.89% |
| A21 | 2024-10-25T18:00:00Z to 2024-10-26T02:00:00Z | 0.039521 | 0.021756 | 0.039800 | 0.020490 | -44.95% |
| Oct 25-27 | 2024-10-25T00:00:00Z to 2024-10-27T23:00:00Z | 0.028541 | 0.035021 | 0.043826 | 0.011287 | 22.71% |

Finding: the price relevance claim is supported, but direct causality remains tentative. A13 has the strongest positive movement and intrawindow high. A16 and A21 are volatile but negative open-to-close in their exact card windows.

### RS3: Contrast Role Profiles

Status: executed.

| Wallet address | All trades | Buys / sells | All USD | Net tokens | Events | Snapshot balance | First trade |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6Z6RJJGrmVyndcPyTFhmLYHkHttiYtTccKpXFV9r2237 | 0 | 0 / 0 | $0.00 | 0.00M | 3 | 10.64M | none |
| CqWVLXaj8r6vud5SfFr81SzmFoqXa5daLi1WbpQZxuhV | 29 | 27 / 2 | $279,596.52 | 10.23M | 25 | 10.23M | 2024-10-25T18:38:26Z |
| DNLFULTWBTkpfwpXZeMA7ckMbQntHuLqxZq6RH6xnaji | 168 | 165 / 3 | $459,115.69 | 17.16M | 165 | 9.33M | 2024-10-25T04:23:53Z |
| DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH | 125 | 103 / 22 | $714,065.70 | 7.05M | 124 | 7.05M | 2024-10-24T03:53:43Z |
| 7SmhQ9r2TLLgS5cmWoFSVGZZw7sEySmZXzwBVscrc7qb | 41 | 27 / 14 | $178,977.58 | 2.66M | 61 | 0.54M | 2024-10-19T17:49:58Z |
| GCDEuA5Q6KugDcN5wxnorwkeSrMYiPJse24pDfFbLZXz | 121 | 60 / 61 | $455,757.79 | 2.19M | 85 | 2.33M | 2024-10-20T02:28:27Z |

Finding: the raw data supports role separation. 6Z6 is storage-like, CqW is an accumulator, DNL and DmJ are active high-trade wallets, and GCDE/7Sm fit the A21 adjacent pattern differently.

Direct transfer evidence found one internal clicked-wallet edge: `7Sm...7qb` -> `Eu4...Vzh`, amount 5.56M, first seen `2024-10-23T15:31:44Z`. This supports broad component linkage for A16 but does not prove direct transfer linkage inside A21.

### RS4: Promote Or Reject A21

Status: executed and promoted with qualification.

Resolution: promoted. The proposed adjacent hypothesis is supported as a behavior-linked nested round-trip mechanism, not as a direct-transfer component.

Support:

- A21 has exact-window trading by DmJ and GCDE, with near-balanced buy/sell structure in GCDE and net-selling from DmJ.
- A21 overlaps A16 through `7Sm...7qb` and `DmJ...uLH`.
- The rendered A21 Behavior Details view preserves the compact 3-user pattern in the exact card window.

Qualification:

- No direct internal transfer was found among the three A21 users in the exact A21 card window.
- Therefore the promoted hypothesis is about a behavior-linked nested mechanism, while the direct-transfer version is unsupported.

## Reasoning Graph Patch Summary

`reasoning-graph-patch-001.json` adds agent follow-up Interaction, Finding, Insight, and Hypothesis nodes. It also adds `H_AGENT_1` as a new root through `add_root`, so the augmented forest contains a separate A21 adjacent-hypothesis tree.

## Blockers

None. The local backend and frontend started successfully. The local frontend package did not include a standalone Playwright dependency, but the available browser automation tool executed the render API and saved PNG evidence.

## Bottom Line

The follow-up strengthens H3 and refines it: the suspicious ACT case is best explained as a broader colluding component with role specialization and a nested A21 round-trip-like subpattern. The price windows are materially relevant, but the evidence should not be worded as proof of single-window causality.
