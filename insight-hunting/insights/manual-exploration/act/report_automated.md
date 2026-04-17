# ACT — Automated Exploration Report

**Token:** ACT (Solana memecoin)
**Snapshot:** 2024-11-09 23:00:00 UTC
**Detection settings:** Default (Top Holder Threshold 0.3, Related User Threshold 0.2, Entity Detection via balance similarity, Link Detection via trading action + manipulation-based)
**Method:** Data collected via ManiScope backend API + browser screenshot automation

---

## At a glance

| Metric | Value |
|---|---|
| Top holders (excl. Others) | 21 wallets |
| Flagged (manipulation-involved) holders | 8 / 21 (38%) |
| Clean holders | 13 / 21 (62%) |
| Related users | 84 wallets |
| Detected entities | 7 (sizes: 4, 2, 2, 3, 2, 2, 2 → 17 wallets) |
| Round-trip events (1h) | 14 |
| Same-direction events (1h) | 225 |
| Unique manipulation participants | 69 wallets |
| Total top-holder balance | 287.41M ACT (30.3% of tracked supply) |
| Others balance | 660.91M ACT |
| Largest entity by balance | E1: 56.26M (4 members) |
| Most active round-trip wallet | GT7VSVNp… (5 events, 23 trades max) |
| Most active same-direction wallet | 7QxQ7d5z… (22 events) |

The K-line spans **2024-10-19 → 2024-11-09**. Manipulation events are heavily concentrated in the **first two weeks post-launch** (10/19–11/02), with activity tapering off sharply afterward.

![ManiScope overview — Token Distribution + K-line (1h granularity)](screenshots_automated/01_overview.png)

---

## Finding 1 — The biggest holders are mostly clean; flagged wallets are mid-sized

Cross-referencing the 21 top holders with manipulation detection results reveals a clear pattern: **the top 4 holders by balance are all clean**.

| Rank | Address | Balance | Status | Entity |
|---|---|---|---|---|
| 1 | A77HErqt… | 47.78M | CLEAN | E7 |
| 2 | 5Q544fKr… | 40.15M | CLEAN | E1 |
| 3 | u6PJ8DtQ… | 30.53M | CLEAN | E2 |
| 4 | 51B3ZUzg… | 19.00M | CLEAN | — |
| 5 | ASTyfSim… | 13.36M | CLEAN | — |
| **6** | **25t5RCFq…** | **12.83M** | **FLAGGED** | **E3** |
| 7 | 5PAhQiYd… | 10.68M | CLEAN | — |
| 8 | 6Z6RJJGr… | 10.64M | CLEAN | — |
| **9** | **CqWVLXaj…** | **10.23M** | **FLAGGED** | — |
| 10 | 7tPwvKZ5… | 10.09M | CLEAN | E1 |
| **11** | **DNLFULTWp…** | **9.33M** | **FLAGGED** | — |
| 12 | BmFdpraQ… | 8.88M | CLEAN | E5 |
| 13 | BY4StcU9… | 8.09M | CLEAN | E6 |
| 14 | GAh4TSR1… | 8.00M | CLEAN | — |
| 15 | GvZknRDv… | 7.83M | CLEAN | — |
| **16** | **ABGmmHMR…** | **7.64M** | **FLAGGED** | — |
| **17** | **DmJRzwcm…** | **7.05M** | **FLAGGED** | **E4** |
| 18 | GrTu9D6n… | 6.80M | CLEAN | — |
| **19** | **5RA23pdR…** | **6.66M** | **FLAGGED** | — |
| **20** | **9zR6kRdR…** | **6.23M** | **FLAGGED** | — |
| **21** | **D22gQL14…** | **5.62M** | **FLAGGED** | — |

**Takeaway:** The top 5 wallets by balance (accounting for 151.7M ACT, 53% of top-holder supply) are entirely clean. The 8 flagged wallets are concentrated in ranks 6–21, with balances ranging from 5.62M to 12.83M. This means the biggest ACT holders are passive accumulators (likely exchanges, market makers, or early buyers) rather than active manipulators. The manipulation network operates through **mid-tier wallets**.

![Clicking the 2nd largest holder (5Q544f, Entity E1 member, clean) — node info panel](screenshots_automated/03_node_selected.png)

---

## Finding 2 — Seven entity clusters detected, two with near-perfect correlation

The balance-sequence similarity detector identified **7 distinct entity clusters**. The most notable are:

### Entity E4 — 3 members, correlation ≈ 1.00 (perfect synchronization)

| Member | Balance | Type | Manipulation |
|---|---|---|---|
| DmJRzwcm… | 7.05M | Top Holder | 10 SD + 1 RT |
| BgBmwgMG… | 4.38M | Related | 1 SD |
| 6mx8oLCa… | 1.49M | Related | — |

The two internal relations both have **correlation scores of 1.00** (0.9999999…), meaning these three wallets have virtually identical hourly balance profiles. This is the strongest possible signal that a single operator controls them. Combined balance: **12.92M ACT**.

DmJRzwcm… alone is involved in **10 same-direction events and 1 round-trip**, making Entity E4 the most manipulation-active entity cluster.

### Entity E1 — 4 members, the largest by total balance

| Member | Balance | Type | Correlation |
|---|---|---|---|
| 5Q544fKr… | 40.15M | Top Holder | 0.66 (with 7tP) |
| 7tPwvKZ5… | 10.09M | Top Holder | 0.76 (with 8YA) |
| HEHuAEtn… | 4.79M | Related | 0.64 (with 7tP) |
| 8YA3S4JA… | 1.22M | Related | — |

Despite being the largest entity cluster by balance (**56.26M ACT**), none of its top-holder members are directly flagged for manipulation. The related members HEHuAEtn and 8YA3S4JA are flagged, suggesting that while the main wallets accumulate passively, the peripheral wallets engage in trading activity.

### Entity E2 — Near-perfect correlation (0.997)

| Member | Balance | Type |
|---|---|---|
| u6PJ8DtQ… | 30.53M | Top Holder |
| 4xaVwgkt… | 1.16M | Related |

These two wallets move in near-perfect lockstep (correlation 0.997). The main wallet holds 30.53M ACT (3rd largest overall) but is completely clean from a manipulation standpoint. This entity likely represents a single investor using a satellite wallet structure.

---

## Finding 3 — GT7VSVNp… is the most active round-trip trader

Wallet `GT7VSVNpqiutRVKhmgw3sJMRJCHyb8yg2W1ta12E4HPp` appears in **5 of the 14 round-trip events** and **12 same-direction events**, making it the single most manipulation-active address in the dataset. Notably, this wallet is **not a top holder** — it operates through the related-user tier.

Its most intense episode:
- **2024-11-04 23:40:54 → 2024-11-05 00:20:56**: 23 trades in 40 minutes
- **2024-11-03 05:26:20 → 2024-11-03 06:57:28**: 13 trades in ~90 minutes

The round-trip pattern (rapid buy-sell cycles with near-zero net position change) is consistent with **volume-printing bot behavior** — deliberately inflating order book volume to attract organic traders.

![Round-trip card selected — Behavior Detail showing buy/sell cycles and earning bars](screenshots_automated/04_roundtrip_selected.png)

Other notable round-trip wallets:

| Wallet | RT events | Highest trade count |
|---|---|---|
| GT7VSVNp… | 5 | 23 trades (11/04) |
| XiXRAfbX… | 1 | 11 trades (10/31, 5 min window) |
| ErAJGcJT… | 1 | 10 trades (10/19) |
| FDotWh7o… | 1 | 6 trades (10/24) |

---

## Finding 4 — Same-direction trading is pervasive: 225 events across 69 wallets

The same-direction detector found **225 events** (all single-participant at 1h granularity), involving **69 unique wallets**. The top offenders:

| Wallet | SD events | Primary direction | Sample |
|---|---|---|---|
| 7QxQ7d5z… | 22 | mixed | Sells 32 trades in 26 min (10/31) |
| 896TAYRn… | 14 | sell-heavy | 26 sell trades in 42 min (10/21) |
| GT7VSVNp… | 12 | buy-heavy | Buy bursts across 10/21–11/04 |
| 7jNj82Kr… | 12 | mixed | Active 10/19–10/31 |
| 25t5RCFq… | 11 | mixed | Entity E3 member, 12.83M balance |
| DmJRzwcm… | 10 | mixed | Entity E4 member, 7.05M balance |
| DNLFULTWp… | 10 | buy-heavy | 33 buys in 15 min (11/03) |

**Key observation:** Several same-direction-heavy wallets (25t5RCFq, DmJRzwcm, DNLFULTWp) are also top holders, meaning they are both accumulating large positions **and** engaging in rapid-fire trading. This is consistent with an accumulation strategy that uses rapid same-direction bursts to build position while minimizing price impact.

---

## Finding 5 — Manipulation activity timeline: early-window concentration

Analyzing the temporal distribution of manipulation events:

**Round-trip events by date:**
- Oct 19–25: 4 events (earliest market activity)
- Oct 27–31: 4 events (mid-period)
- Nov 1–5: 6 events (late surge, GT7V wallet)

**Same-direction events peak wallets by period:**
- FqYtts1V: 37 trades on 10/23 (buy burst, 34 min)
- 2koNeb1o: 29 trades on 10/28 (buy burst, 21 min)
- 7QxQ7d5z: 32 trades on 10/31 (sell burst, 26 min)
- DNLFULTWp: 33 trades on 11/03 (buy burst, 15 min)

The manipulation volume is concentrated in the **Oct 19 – Nov 5 window**, with the token transitioning to a lower-activity phase afterward. The late-period GT7V activity (5 round-trips in 2 days) represents a last burst of wash trading before the manipulation operators likely exited.

![K-line at 1h granularity with round-trip (top) and same-direction (bottom) manipulation cards](screenshots_automated/02_kline_1h.png)

![K-line at 1d granularity — daily aggregation of manipulation events](screenshots_automated/02_kline_1d.png)

---

## Finding 6 — Entity E3: a flagged top holder with a silent partner

Entity E3 consists of:

| Member | Balance | Events |
|---|---|---|
| 25t5RCFq… | 12.83M | 11 SD (flagged) |
| FWDKVa9A… | 1.85M | Flagged (related) |

With correlation 0.64 (the lowest among detected entities), these two wallets are loosely synchronized. The main wallet 25t5RCFq is the **6th largest holder** and one of the most manipulation-active top holders (11 same-direction events). Its partner FWDKVa9A holds a small satellite position.

This entity is notable because unlike E1/E2/E7 (large-balance, clean entities), E3 is a **mid-tier entity that is actively involved in manipulation**. It represents a different operator profile: one that maintains moderate holdings while aggressively trading.
![Entity E4 (DmJ) selected — Token Distribution + Behavior Detail with manipulation timeline](screenshots_automated/05_entity_e4_dmj.png)
---

## Summary of entity landscape

| Entity | Members | Total Balance | Max Correlation | Manipulation Profile |
|---|---|---|---|---|
| E1 | 4 | 56.26M | 0.76 | Clean top holders + flagged periphery |
| E2 | 2 | 31.69M | 1.00 | Entirely clean, passive pair |
| E3 | 2 | 14.68M | 0.64 | Active manipulator, mid-tier |
| **E4** | **3** | **12.92M** | **1.00** | **Most active, perfect sync** |
| E5 | 2 | 12.90M | 0.84 | Mixed (1 clean TH + 1 flagged RU) |
| E6 | 2 | 9.70M | 0.90 | Clean pair |
| E7 | 2 | 48.98M | 0.71 | Clean pair (largest single holder) |

---

## Workflow recommendation for ACT investigation

1. **Start with Entity E4** (DmJ cluster) — it has perfect balance correlation and the highest manipulation activity. This is the clearest sybil cluster.
2. **Investigate GT7VSVNp…** independently — though not a top holder, this wallet's 5 round-trips and 12 same-direction events make it the most active single manipulator.
3. **Examine the top same-direction wallets** (7QxQ, 896T, 7jNj) — their high event counts and concentrated burst patterns suggest bot-driven accumulation/distribution.
4. **Cross-reference Entity E1's related members** (HEHuAEtn, 8YA3S4JA) — they are flagged while the main wallets are clean, suggesting the entity may have a hidden manipulation layer.
5. **Use the K-line 1h view** for granular manipulation card browsing — the 1d view aggregates too aggressively and loses many same-direction events.

---

## Methodology

- **Data source:** ManiScope backend API (`/api/snapshot/process`, `/api/detection/run`, `/api/manipulation_service/detect`)
- **Entity detection:** Balance sequence similarity with 1h granularity, threshold 0.6
- **Link detection:** Trading action sequence (action_only type, max_time_diff 120s) + manipulation-based (max_time_diff 120s)
- **Manipulation detection:** Round-trip (max_time_diff 120s, max_earning $1000) + Same-direction (max_time_diff 10s, min_seq_length 5)
- **Screenshots:** Captured via Playwright automation of the ManiScope frontend at localhost:3000
- **All quantitative claims** derived from API response data; no raw CSV files were read directly
