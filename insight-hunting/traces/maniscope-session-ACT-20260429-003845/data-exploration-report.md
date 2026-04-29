# ACT Data Exploration Report

Trace: `insight-hunting/traces/maniscope-session-ACT-20260429-003845`  
Basis: previous intention, insight, and recommendation analysis in [`analysis-report.md`](analysis-report.md) and [`trace-step-map.md`](trace-step-map.md)  
Data explored: local ACT files under `front/public/data/`

## 1. Scope And Method

This report explores ACT data beyond what the user directly inspected in the trace. The goal is to find additional low-level, mid-level, and high-level insights that follow from the earlier analysis.

Data used:

- `front/public/data/sorted_trades.csv`
- `front/public/data/sorted_transfers.csv`
- `front/public/data/transfer_network_stats.csv`
- `front/public/data/ACT_OHLC.json`
- `front/public/data/user_balance_1d.json`
- `front/public/data/user_earnings_1d.json`
- `front/public/data/simplified_owner_labels.json`
- `insight-hunting/traces/maniscope-session-ACT-20260429-003845/session.json`

Important caveats:

- These are data-derived insights, not necessarily insights the user saw during the interaction.
- `transfer_network_stats.csv` includes many contract and pool addresses. I treat contract-labeled common neighbors as market-structure evidence, not entity evidence.
- Direct entity claims still need raw transaction review. A transfer link is stronger than behavioral similarity, but it is not proof of common control by itself.
- The trace has a state gap around the 10-user selected group visible at action 10. That group is useful evidence, but the trace does not show the exact card click that selected it.

## 2. Cohorts Reconstructed From The Trace

The original report emphasized the 9-user card, the 11-user card, and the final 4-user prebuyer group. Data exploration adds a fourth important cohort: the 10-user selected state visible at action 10.

| Cohort | Source | Size | Key Role |
|---|---:|---:|---|
| A | Action 8 card users | 9 | Oct 24 to 25 same-direction card cohort |
| B | Action 10 selected-card state | 10 | Under-discussed bridge cohort between A and C |
| C | Action 12 card users | 11 | Oct 31 to Nov 1 suspicious card cohort |
| D | Action 18 selected-card state | 4 | Oct 21 prebuyer and later-seller group |
| E | Analysis-defined focus set | 5 | `7Sm`, `Eu4`, `DmJ`, `9Kj`, `62c` bridge accounts |

Important overlaps:

| Overlap | Shared Users | Interpretation |
|---|---:|---|
| A and B | `5YP...1xYv`, `DmJ...7uLH` | The action 10 state is not isolated from the Oct 24 to 25 card group. |
| A and C | `DmJ...7uLH` | Confirms `DmJ` as a repeated actor across two explicit card groups. |
| B and C | `4B3...eyV7`, `7Sm...c7qb`, `DmJ...7uLH`, `Eu4...hVzh`, `XiX...RSvN` | B is a stronger bridge into C than A is. |
| C and D | `62c...59Xe`, `9Kj...x5jE` | The final prebuyer group is directly tied to the Oct 31 to Nov 1 card group. |

### New Low-Level Insight 1

The action 10 selected-card state should be analyzed as its own cohort. It contains 10 users, all 10 traded during Oct 24 to 25, and 7 traded during the exact Oct 31 to Nov 1 card window.

Rationale: this group is visible in `relatedViewWithViewState.selectedCardUsers` even though the trace does not show the exact selection action. It overlaps both the earlier 9-user cohort and the later 11-user cohort, so ignoring it weakens the case reconstruction.

## 3. Window-Level Trading Results

Key windows:

| Window | Time Range |
|---|---|
| W0 | Oct 21, 2024, full UTC day |
| W1 | Oct 24, 2024 12:19:04 UTC to Oct 25, 2024 08:25:13 UTC |
| W1b | Oct 24, 2024 to Oct 26, 2024, full UTC days |
| W2 | Oct 31, 2024 17:50:41 UTC to Nov 1, 2024 03:35:47 UTC |
| W2b | Oct 31, 2024 to Nov 3, 2024, full UTC days |

| Cohort | Window | Active Users | Buy USD | Sell USD | Net Sell Minus Buy | Market Share |
|---|---:|---:|---:|---:|---:|---:|
| A Oct24 card9 | W1 exact | 2 of 9 | $185,386 | $0 | -$185,386 | 0.4% |
| A Oct24 card9 | W1b broad | 4 of 9 | $421,603 | $123,753 | -$297,850 | 0.5% |
| B Oct31 state10 | W1b broad | 10 of 10 | $645,862 | $404,835 | -$241,028 | 0.9% |
| B Oct31 state10 | W2 exact | 7 of 10 | $198,945 | $19,967 | -$178,977 | 1.9% |
| C Oct31 card11 | W0 Oct21 | 4 of 11 | $146,526 | $14,022 | -$132,504 | 0.5% |
| C Oct31 card11 | W2 exact | 8 of 11 | $135,421 | $106,317 | -$29,104 | 2.1% |
| C Oct31 card11 | W2b broad | 11 of 11 | $663,832 | $435,547 | -$228,285 | 1.8% |
| D prebuyer4 | W0 Oct21 | 4 of 4 | $164,376 | $0 | -$164,376 | 0.5% |
| D prebuyer4 | W2b broad | 3 of 4 | $65,064 | $236,734 | $171,670 | 0.5% |
| E bridge focus | W2b broad | 5 of 5 | $233,983 | $196,770 | -$37,213 | 0.7% |

### New Mid-Level Insight 1

The traced cohorts are not only wash-like. Several groups are strongly buy-heavy, which suggests inventory accumulation or price-support behavior.

Rationale:

- A is pure buy-side in the exact Oct 24 to 25 card window.
- B is buy-heavy in both Oct 24 to 25 and Oct 31 to Nov 1.
- C is mixed, but still net buy-heavy in the broad Oct 31 to Nov 2 window.
- D is the clearest role switch: buy-only on Oct 21, then net selling during Oct 31 to Nov 2.

This refines the earlier wash-trading interpretation. Some windows may be wash-like, but the stronger pattern is role differentiation: some accounts accumulate, some churn, and some later exit.

### New Mid-Level Insight 2

B is a likely bridge cohort that the earlier report underweighted.

Rationale:

- B shares `5YP...1xYv` and `DmJ...7uLH` with A.
- B shares five users with C.
- B has 10 of 10 users active during Oct 24 to 25 and 7 of 10 active in the exact Oct 31 to Nov 1 window.
- B's W2 exact activity is $198,945 buys versus $19,967 sells, which is more buy-heavy than C in the same exact window.

This suggests B may represent the transition between early same-direction buying and the later broad suspicious episode.

## 4. Market Timing And Concentration

Across all 25 reconstructed trace-union users, the daily market share is modest but rises during specific suspicious periods.

| Date | ACT Daily Return | Market Trade USD | Trace-Union Trade USD | Trace-Union Share | Active Trace Users |
|---|---:|---:|---:|---:|---:|
| Oct 21 | 63.1% | $35,408,939 | $287,099 | 0.8% | 8 |
| Oct 24 | -47.4% | $65,798,513 | $407,845 | 0.6% | 10 |
| Oct 25 | 6.8% | $48,337,646 | $870,843 | 1.8% | 14 |
| Oct 26 | -39.4% | $43,831,461 | $1,042,741 | 2.4% | 17 |
| Oct 27 | 85.8% | $17,865,661 | $535,969 | 3.0% | 9 |
| Oct 31 | -4.5% | $40,687,324 | $881,505 | 2.2% | 15 |
| Nov 1 | -17.7% | $13,355,367 | $464,896 | 3.5% | 10 |
| Nov 3 | 46.7% | $7,804,591 | $270,637 | 3.5% | 11 |

Top hourly bursts show stronger concentration than daily totals:

| Hour UTC | Trace-Union USD | Market Share | Buy USD | Sell USD | Active Trace Users |
|---|---:|---:|---:|---:|---:|
| Nov 1 03:00 | $73,797 | 14.3% | $25,167 | $48,630 | 2 |
| Oct 27 12:00 | $203,842 | 14.0% | $46,428 | $157,415 | 2 |
| Oct 31 10:00 | $41,827 | 11.3% | $41,827 | $0 | 2 |
| Oct 25 04:00 | $91,608 | 8.4% | $73,092 | $18,516 | 2 |
| Oct 26 04:00 | $281,749 | 6.0% | $281,749 | $0 | 3 |

### New High-Level Insight 1

The suspicious activity is more convincing at the micro-window level than at the daily market-share level.

Rationale: daily trace-union share is usually under 4%, so the group may not dominate the full market each day. But during specific hours, the trace-union share reaches 10% to 14% of all trade USD. This supports the user's focus on manipulation cards and Behavior Details rather than only daily K-line views. The suspected impact mechanism is likely narrow-time-window coordination, not broad daily volume dominance.

## 5. Role Signals Among Traced Users

The top traced users by full-period trade volume show distinct roles.

| User | Cohorts | Buy USD | Sell USD | Net Sell Minus Buy | Round-Trip Ratio | Final Balance | Last Earning |
|---|---|---:|---:|---:|---:|---:|---:|
| `DmJ...7uLH` | A, B, C, E | $541,883 | $172,183 | -$369,701 | 24.1% | 7,049,447 | -$176,462 |
| `ErA...T3ZU` | B | $326,641 | $325,968 | -$672 | 49.9% | 3,293,390 | -$672 |
| `XiX...RSvN` | B, C | $279,712 | $284,820 | $5,108 | 49.5% | 3,581,680 | $79,499 |
| `DNL...naji` | B | $454,482 | $4,634 | -$449,847 | 1.0% | 9,328,001 | $1,175 |
| `GCDE...LZXz` | C | $236,575 | $219,183 | -$17,392 | 48.1% | 2,327,155 | $27,266 |
| `9Kj...x5jE` | C, D, E | $172,193 | $121,793 | -$50,400 | 41.4% | 3,891,845 | $17,578 |
| `Eu4...hVzh` | B, C, E | $67,082 | $134,544 | $67,462 | 33.3% | 5,394,228 | $68,293 |
| `7Sm...c7qb` | B, C, E | $102,526 | $76,452 | -$26,074 | 42.7% | 544,432 | $29,077 |
| `62c...59Xe` | C, D, E | $102,815 | $62,791 | -$40,024 | 37.9% | 3,815,880 | $20,099 |

### New Mid-Level Insight 3

The trace-union users divide into at least four role types.

| Role | Example Users | Evidence |
|---|---|---|
| Cross-window bridge | `DmJ...7uLH` | Appears in A, B, C, and E; high buy volume and repeated cohort membership. |
| Funded or funding-linked accounts | `7Sm...c7qb`, `Eu4...hVzh` | Direct transfer from `7Sm` to `Eu4`; shared downstream neighbors. |
| Early accumulators and later sellers | `9Kj...x5jE`, `62c...59Xe` | Both appear in C, D, and E; bought on Oct 21 and sold during Oct 31 to Nov 2. |
| Inventory builders | `DNL...naji`, `DmJ...7uLH`, several A users | Large buy-side imbalance and substantial final balances. |

This role split gives a better explanation than treating all suspicious users as identical manipulators.

## 6. Transfer And Entity Expansion

Within the trace-union users, only one direct aggregated transfer edge appears:

| From | To | Count | Time | Amount |
|---|---|---:|---|---:|
| `7Sm...c7qb` | `Eu4...hVzh` | 1 | Oct 23, 2024 15:31 UTC | 5,558,866 ACT |

However, user-labeled external neighbors expand the `7Sm` and `Eu4` cluster:

| External User | Trace Users Connected | Transfer Count | Volume | First Seen | Last Seen | Why It Matters |
|---|---|---:|---:|---|---|---|
| `7EuM...FGf5` | `7Sm`, `Eu4` | 4 | 8,196,022 ACT | Oct 23 15:29 | Oct 27 18:13 | `7EuM` sent 6.19M ACT into `7Sm`, then `7Sm` funded `Eu4`. `Eu4` later sent 1.59M ACT back to `7EuM`. |
| `j1op...nngb` | `7Sm`, `Eu4` | 125 | 5,456,488 ACT | Oct 24 18:32 | Oct 27 03:15 | Large user-labeled neighbor that also traded heavily in Oct 24 to 25 and Oct 31 to Nov 1 windows. |
| `j1oe...nYbd` | `7Sm`, `Eu4` | 83 | 2,189,034 ACT | Oct 24 18:32 | Oct 27 03:15 | Similar to `j1op`, with strong Oct 24 to 27 transfer timing and later trading. |

Additional target details:

- `j1op...nngb` traded $437,836 in Oct 24 to 25 and $31,068 in the exact Oct 31 to Nov 1 window.
- `j1oe...nYbd` traded $404,750 in Oct 24 to 25 and $15,013 in the exact Oct 31 to Nov 1 window.
- `j1op...nngb` also matches the early-buy/later-sell pattern: $41,882 bought on Oct 21, $47,164 sold during Oct 31 to Nov 2, with 354,858 ACT remaining.

### New Mid-Level Insight 4

The `7Sm` and `Eu4` pair likely sits inside a larger transfer cluster involving `7EuM`, `j1op`, and `j1oe`.

Rationale: `7Sm -> Eu4` is the only direct edge inside the traced cohort, but `7EuM`, `j1op`, and `j1oe` are user-labeled external neighbors connected to both `7Sm` and `Eu4` with large ACT volumes. Two of them also trade in the same suspicious windows. This makes them higher-priority expansion candidates than random high-volume traders.

## 7. Candidate Expansion Outside The Trace

The data scan looked for accounts that bought on Oct 21, sold during Oct 31 to Nov 2, and retained a later balance. This matches the user's final campaign-level hypothesis.

| Candidate | In Trace | Oct 21 Buy | Oct 31 to Nov 2 Sell | Final Balance | Trace Transfer Degree |
|---|---:|---:|---:|---:|---:|
| `D4z...yWhL` | No | $486,851 | $462,707 | 324,882 ACT | 0 |
| `NHt...cash` | No | $84,649 | $278,927 | 0 ACT | 0 |
| `5iC...zz3c` | No | $122,388 | $82,021 | 0 ACT | 0 |
| `55N...jGdn` | No | $63,652 | $213,798 | 2,775 ACT | 0 |
| `4Gq...HmSa` | No | $54,392 | $202,494 | 0 ACT | 0 |
| `9Kj...x5jE` | Yes | $48,873 | $121,793 | 3,891,845 ACT | 0 |
| `62c...59Xe` | Yes | $42,692 | $62,791 | 3,815,880 ACT | 0 |
| `j1op...nngb` | No | $41,882 | $47,164 | 354,858 ACT | 2 |
| `XiX...RSvN` | Yes | $36,342 | $143,570 | 3,581,680 ACT | 0 |

The top outside candidate, `D4zVhwuUsFbcaty7wJhNEZ7VEwPHXQ5d2heXPxM5yWhL`, is extremely active. It repeatedly buys and sells nearly equal amounts every day:

| Date | Buy USD | Sell USD |
|---|---:|---:|
| Oct 21 | $486,851 | $492,334 |
| Oct 24 | $666,474 | $694,063 |
| Oct 25 | $361,700 | $365,870 |
| Oct 31 | $342,310 | $347,855 |

### New High-Level Insight 2

There may be a broader ecosystem of high-frequency round-trip accounts around the suspected campaign, but not all of them are trace-linked.

Rationale: `D4z`, `NHtd`, and `55NQ` match the early-buy/later-sell scan and show highly symmetric buy/sell behavior across many days. This looks more like high-frequency churn or market-making than the buy-heavy trace cohorts. Because these accounts do not yet have direct trace-transfer evidence, they should be treated as comparison or expansion candidates rather than folded into the same entity claim.

## 8. Counterparty Concentration

The traced cohorts repeatedly trade through the same dominant counterparty address `675k...1Mp8`.

| Cohort | Window | Top Counterparty | USD | Share |
|---|---|---|---:|---:|
| A | Oct 24 to 25 broad | `675k...1Mp8` | $386,373 | 70.8% |
| C | Oct 31 to Nov 1 exact | `675k...1Mp8` | $163,799 | 67.8% |
| C | Oct 31 to Nov 2 broad | `675k...1Mp8` | $799,576 | 72.7% |
| D | Oct 21 | `675k...1Mp8` | $149,844 | 91.2% |
| D | Oct 31 to Nov 2 broad | `675k...1Mp8` | $211,477 | 70.1% |

### New Low-Level Insight 2

Most traced cohort trading is routed through a single dominant counterparty address.

Rationale: this could simply be the main ACT pool, so it is not entity evidence. But it matters for wash-trading validation because the same pool can make same-entity buy/sell patterns appear as coordinated market activity. Any wash-trading check should pair entity evidence with pool-level order timing.

## 9. Integrated High-Level Interpretation

The deeper data supports a more nuanced campaign model:

1. **Pre-accumulation and early positioning**: D buys on Oct 21; C also has 4 of 11 users buying on Oct 21.
2. **Inventory-building cohorts**: A and B show strong buy-side behavior during Oct 24 to 25 and Oct 31 to Nov 1.
3. **Bridge and funding cluster**: `7Sm`, `Eu4`, `7EuM`, `j1op`, and `j1oe` form a higher-priority transfer-linked cluster.
4. **Later exit or partial realization**: D sells heavily during Oct 31 to Nov 2 while retaining balances.
5. **Background churn accounts**: accounts such as `D4z`, `NHtd`, and `55NQ` may represent broader volume-amplifying behavior, but they are not yet trace-linked.

### New High-Level Insight 3

The strongest case is not "one homogeneous manipulator group." The stronger model is a layered manipulation ecosystem with a trace-linked core, bridge accounts, inventory-building participants, early accumulators, and separate high-frequency churn accounts.

This is more defensible because it preserves the strongest direct evidence while preventing weaker behavioral similarities from contaminating the entity claim.

## 10. Recommendations

### Low-Level Recommendations

- Reopen action 10 and its screenshots or state context. Treat the 10-user selected state as a first-class cohort.
- Inspect `j1op...nngb`, `j1oe...nYbd`, and `7EuM...FGf5` in Behavior Details with related users enabled.
- Inspect the dominant counterparty `675k...1Mp8` as a pool or counterparty context, not as a suspicious holder by default.
- Review `D4z...yWhL`, `NHtd...cash`, and `55NQ...jGdn` as high-frequency comparison accounts.

### Mid-Level Recommendations

- Build an expanded transfer cluster around `7Sm`, `Eu4`, `7EuM`, `j1op`, and `j1oe`, then verify each edge with raw transaction records.
- Split suspicious users into role labels: accumulator, inventory builder, bridge account, funded account, later seller, and churn account.
- Run the early-buy/later-sell scanner across all ACT users, then compare candidate accounts against transfer connectivity to the traced union.
- Build hourly rather than daily trade-flow tables for Oct 24 to 27 and Oct 31 to Nov 3. The suspicious concentration is much clearer at hourly scale.
- Compare entity-based and non-entity manipulation detection after excluding contract and pool addresses from transfer-neighbor reasoning.

### High-Level Recommendations

- Reframe the investigation from a single-group collusion claim into a layered campaign hypothesis.
- Prioritize the transfer-linked core first: `7Sm`, `Eu4`, `7EuM`, `j1op`, and `j1oe`.
- Treat `D4z`, `NHtd`, and similar accounts as either control accounts or a second suspected strategy until direct linkage is found.
- Build a new evidence graph that includes original trace nodes plus new data-derived candidate nodes.
- Verify any external motive, such as an exchange listing, before using it as a conclusion.

## 11. Bottom Line

The deeper data exploration strengthens the original campaign hypothesis but changes its shape. The strongest evidence is now a layered pattern: early accumulation, buy-heavy inventory building, a transfer-linked `7Sm` and `Eu4` cluster with external user neighbors, and later partial exits. The weakest part remains motive and entity scope. The data supports expanding the investigation, especially around `7EuM`, `j1op`, and `j1oe`, but broader high-frequency accounts like `D4z` should remain candidates until direct linkage is established.
