# ManiScope ACT Session Interaction Analysis Report

Trace: `insight-hunting/traces/maniscope-session-ACT-20260429-003845`  
Coin: ACT  
Snapshot: `2024-11-09 23:00:00 UTC`  
Exported at: `2026-04-28T16:38:45.715Z`

## 1. Scope And Method

This report analyzes the user interaction trace in this folder, including:

- [`session.json`](session.json), which contains 19 logged actions, 11 annotations, action view states, and image references.
- The screenshots under [`images/`](images/), especially annotation images because they capture the user's explicit evidence markings.
- The current ManiScope user manual and frontend source under `front/`, used to interpret view semantics, action logging, and visual encodings.
- Local ACT data files under `front/public/data/`, used for limited validation of selected wallet groups, trade timing, direct transfers, and residual balances.

The analysis separates three evidence types:

- **Observed interaction evidence**: actions, timestamps, selected users, clicked card users, screenshots, and annotation text from `session.json`.
- **System-semantics evidence**: what each view and control means according to the manual and source code.
- **Data validation evidence**: checks against ACT trade, transfer, OHLC, and balance files.

Important caveats:

- Some interaction state changes are visible in later action view states without a matching explicit click action. For example, action 18 contains a selected four-wallet group, but the trace does not include the card-click action that selected it.
- The trace supports the trading-pattern hypothesis strongly, but it does not itself prove an exchange listing event or the user's inferred motive. That motive should be externally verified.
- All market and behavior timestamps in this report are UTC.

## 2. ManiScope Context Used For Interpretation

ManiScope combines three investigation surfaces:

- **Token Distribution**: holder graph, suspicious red-stroked nodes, entity boundaries, and relationship links.
- **K-line And Manipulation Cards**: OHLC price chart plus round-trip cards above the chart and same-direction cards below the chart.
- **Behavior Details**: per-wallet timelines. Blue points represent buys, pink points represent sells, grey arrows/points represent transfers, red boxes mark detected manipulation windows, and light blue areas represent balance.

The frontend logs actions with source view, target view, action type, selected users, current time windows, and optional screenshots. This is why the report can reconstruct both direct user operations and broader analytical goals.

## 3. Chronological Reconstruction

| Stage | Evidence | What The User Did | Initial Interpretation |
|---|---|---|---|
| 1 | Action 0, [`action-0001-target-token_distribution-02.png`](images/action-0001-target-token_distribution-02.png), [`action-0001-target-kline_chart-01.png`](images/action-0001-target-kline_chart-01.png) | Loaded ACT at `2024-11-09 23:00:00 UTC` with default thresholds. | The user started from the current end-of-window snapshot and available detection results. |
| 2 | Annotation 0, [`annotation-0000-token_distribution.png`](images/annotation-0000-token_distribution.png) | Marked a dense suspicious holder component in Token Distribution. | The first analytical focus was relationship structure among suspicious holders. |
| 3 | Actions 1 to 3, [`action-0002-target-behavior_details-01.png`](images/action-0002-target-behavior_details-01.png), [`action-0004-target-behavior_details-01.png`](images/action-0004-target-behavior_details-01.png) | Selected and reselected wallet `7SmhQ9r2TLLgS5cmWoFSVGZZw7sEySmZXzwBVscrc7qb`. | The user treated this wallet as a lead account and moved from graph structure to account behavior. |
| 4 | Action 4, annotations 1 to 3, [`annotation-0001-candlestick_chart.png`](images/annotation-0001-candlestick_chart.png), [`annotation-0002-candlestick_chart.png`](images/annotation-0002-candlestick_chart.png), [`annotation-0003-candlestick_chart.png`](images/annotation-0003-candlestick_chart.png) | Changed K-line granularity to `1d`, annotated price-decline and post-uptrend manipulation windows. | The user shifted to price and manipulation timing. |
| 5 | Action 8, [`action-0009-source-kline_chart-01.png`](images/action-0009-source-kline_chart-01.png), [`action-0009-target-behavior_details-01.png`](images/action-0009-target-behavior_details-01.png), annotation 4 | Clicked a manipulation card with 9 users and inspected their behavior. | The user tested whether a manipulation-card cohort entered and traded in a coordinated time window. |
| 6 | Actions 10 to 14, annotations 5 to 7, [`annotation-0005-behavior_details.png`](images/annotation-0005-behavior_details.png), [`annotation-0006-candlestick_chart.png`](images/annotation-0006-candlestick_chart.png), [`annotation-0007-behavior_details.png`](images/annotation-0007-behavior_details.png) | Used Sequential Time and returned to absolute time while comparing later card cohorts. | The user was comparing event order and real-time alignment across suspicious wallets. |
| 7 | Actions 15 to 17, annotations 8 and 9, [`annotation-0008-behavior_details.png`](images/annotation-0008-behavior_details.png), [`annotation-0009-behavior_details.png`](images/annotation-0009-behavior_details.png) | Selected `7Sm...`, enabled related users, and annotated direct transfer and behavioral similarity. | The user was connecting behavior similarity to entity or funding evidence. |
| 8 | Action 18, annotation 10, [`annotation-0010-behavior_details.png`](images/annotation-0010-behavior_details.png) | Inspected a four-wallet group with early Oct 21 purchases and later sales. | The user generalized the case into an accumulation, manipulation, and profit-taking narrative. |

## 4. User Intentions

### 4.1 Low-Level Intentions

Low-level intentions are directly visible in single actions or annotations:

- Load ACT and update the snapshot at `2024-11-09 23:00:00 UTC`.
- Inspect the suspicious holder component in Token Distribution.
- Select `7Sm...c7qb` from the holder graph and open its Behavior Details.
- Change K-line granularity to `1d`.
- Scroll same-direction manipulation cards across dates from Oct 19 through early Nov.
- Click manipulation cards around Oct 24 to 25 and Oct 31 to Nov 1.
- Toggle Sequential Time to compare event order.
- Toggle Show Related Users for `7Sm...c7qb`.

These do not require much inference because they are logged directly in `session.json`.

### 4.2 Mid-Level Intentions

#### Intention A: Identify whether suspicious holders are structurally connected.

Evidence:

- Annotation 0 says: "A large portion of these suspicious holders belong to the same connected component in the holder relationship graph; seven of them form three distinct entity groups."
- The annotated Token Distribution screenshot marks a dense red-stroked cluster, orange entity outlines, and relationship lines.
- The user selected `7Sm...c7qb`, hovered it as a related holder, then later enabled Show Related Users.

Rationale:

The user did not simply inspect a single large holder. They moved from the graph-level cluster to a selected account and later back to related users. This sequence indicates a mid-level goal: determine whether suspicious addresses are isolated traders or part of a connected structure. The entity groups and relationship component were being used as evidence of coordination.

#### Intention B: Relate manipulation activity to price regimes.

Evidence:

- The user changed K-line granularity to `1d`.
- Annotation 1 marks manipulation activity during price-declining periods and says holders may have been trying to support price.
- Annotation 2 marks the Oct 20 to Oct 23 upward trend and notes a subsequent surge in manipulation.
- Annotation 3 compares round-trip and same-direction activity across multiple days.

Rationale:

Changing to daily granularity makes single trade details less important and makes multi-day price phases easier to see. The annotations mark broad regions on the K-line rather than individual trades. This supports the conclusion that the user wanted to understand how suspicious activity aligned with price increases, drawdowns, and later stabilization attempts.

#### Intention C: Test whether manipulation-card cohorts behave like coordinated groups.

Evidence:

- Action 8 clicked a card with 9 users:
  - `BgBm...dDon`
  - `EnMA...LBZ3`
  - `5RA2...VEz`
  - `5YPy...xYv`
  - `22JY...eBm`
  - `35No...uPQ`
  - `DmJR...7uLH`
  - `CqWV...xuhV`
  - `5WF1...mZEw`
- Action 12 clicked a card with 11 users:
  - `Eu4D...Vzh`
  - `9KjD...5jE`
  - `XiXR...sVn`
  - `49Fd...WGm`
  - `DmJR...7uLH`
  - `7iVQ...SzE`
  - `4B3Q...yV7`
  - `62cM...9Xe`
  - `GCDE...ZXz`
  - `HEHu...mpb`
  - `7Smh...c7qb`
- Annotation 4 says most suspicious holders newly entered and bought in a coordinated time window.
- Annotation 7 says a new group appears, distinct from the Oct 24 to 25 group except that `DmJ...` is consistently present.

Rationale:

Manipulation cards aggregate users by detected behavior windows. The user clicked card cohorts, inspected their Behavior Details, and used Sequential Time. That combination is useful for answering "did these users act together in time and sequence?" It is not just exploration of one card, because later screenshots and annotations compare different card groups across separate days.

#### Intention D: Determine whether separate manipulation episodes are linked by bridge accounts or entity evidence.

Evidence:

- `DmJR...7uLH` appears in both the Oct 24 to 25 card group and the Oct 31 to Nov 1 card group.
- Annotation 7 explicitly notes that `DMj` is consistently present across otherwise distinct groups.
- Annotation 8 says `Eu4...Vzh` and `7Sm...c7qb` are the same entity because `7Sm...c7qb` funds `Eu4...Vzh`.
- Local transfer data confirms a direct transfer of `5,558,866.23` ACT from `7Sm...c7qb` to `Eu4...Vzh` at `2024-10-23 15:31:44 UTC`.

Rationale:

The user moved from temporal similarity to relationship evidence. This matters because wash trading or collusion claims are stronger when addresses are linked by funding, direct transfer, common counterparties, or repeated co-occurrence. The session behavior suggests the user was trying to move from "these wallets act similarly" to "these wallets may be controlled together."

### 4.3 High-Level Intention

#### High-level intention: Build a coherent manipulation campaign hypothesis for ACT.

Evidence:

- The session starts with suspicious holder clustering, then moves through price timing, card cohorts, account behavior, direct transfer evidence, repeated actors, and finally early accumulation.
- Annotation 10 states the user's final high-level takeaway: selected holders likely belong to the same manipulative group, and their goal appears to be inflating price ahead of an exchange listing to realize profits.
- The final inspected group contains early buyers around Oct 21, and local data shows those four wallets bought about `$164,376` on Oct 21 and sold about `$236,734` during Oct 31 to Nov 2.

Rationale:

A high-level intention must explain why the user stitched together graph structure, K-line timing, card cohorts, behavior timelines, direct transfers, and early accumulation. The most consistent explanation is that the user wanted to construct a case-level narrative: accumulation, price support or inflation, coordinated manipulation windows, and profit-taking. The "exchange listing" motive appears in the user's annotation, but it is not independently verified by this trace.

## 5. Insights

### 5.1 Low-Level Insights

- A dense portion of red-stroked suspicious holders is connected in Token Distribution.
- `7Sm...c7qb` is a related suspicious holder and became an early focus.
- Manipulation-card activity appears across multiple windows, especially Oct 24 to 25 and Oct 31 to Nov 1.
- Behavior Details shows repeated clusters of blue buy points and pink sell points across selected user rows.
- `7Sm...c7qb` has a direct transfer relationship with `Eu4...Vzh`.

### 5.2 Mid-Level Insights

#### Insight A: The suspicious holders are not merely individually suspicious; many are connected by graph/entity structure.

Evidence:

- Annotation 0 and its screenshot mark a large connected component in Token Distribution.
- The visual marks multiple orange dashed entity groups inside or adjacent to the suspicious red-stroked nodes.

Rationale:

If suspicious holders were randomly distributed, the main evidence would be isolated red nodes. Instead, the user's first annotation highlights a connected component and entity groups. This supports the insight that the suspicious population has relationship structure worth investigating as a coordinated actor set.

#### Insight B: The Oct 24 to 25 window contains coordinated new-entry behavior, but the wash-trading interpretation still depends on entity linkage.

Evidence:

- Annotation 4 says most suspicious holders newly entered on this day and bought within the same time window.
- The Oct 24 to 25 clicked card group contains 9 users.
- Local data for that card group shows 35 buys worth about `$185,386` during the card window `2024-10-24 12:19:04` to `2024-10-25 08:25:13`, involving 2 of those 9 users in direct trades during that exact card span.
- Annotation 3 says same-direction activity includes both buys and sells and could resemble wash trading if these addresses belong to the same entity.

Rationale:

The data supports coordinated buy-side activity in the inspected card cohort. The wash-trading claim is plausible but requires proving that the buy-side and sell-side addresses are linked strongly enough to be treated as the same actor or colluding actors. That is why entity and transfer evidence matter for the next step.

#### Insight C: The Oct 31 to Nov 1 window shows a broader synchronized activity episode.

Evidence:

- Annotation 6 says nearly all suspicious holders exhibit manipulative activity simultaneously.
- Action 12 clicked a card with 11 users.
- In the card window `2024-10-31 17:50:41` to `2024-11-01 03:35:47`, local data shows those 11 users executed 53 buys worth about `$135,421` and 15 sells worth about `$106,317`.
- In the broader Nov 1 behavior-box window, local data shows the same group executed 173 buys worth about `$602,781` and 52 sells worth about `$435,547`.

Rationale:

This looks stronger than a single same-direction card because both the screenshot evidence and local data show many accounts active in a narrow interval. The buy and sell totals suggest this is not just passive holding behavior. It is an organized trading episode that deserves deeper entity and counterparty analysis.

#### Insight D: There are repeated actors across otherwise distinct manipulation windows.

Evidence:

- `DmJR...7uLH` appears in both the Oct 24 to 25 and Oct 31 to Nov 1 clicked card groups.
- `9KjD...5jE` and `62cM...9Xe` appear in both the final four-wallet prebuyer group and the Oct 31 to Nov 1 card group.
- Annotation 7 explicitly identifies `DMj` as consistently present.

Rationale:

Repeated actors are important because they connect separate episodes into a campaign-like pattern. `DmJR...7uLH` is especially important because it bridges the two main clicked card cohorts. `9KjD...5jE` and `62cM...9Xe` link the early accumulation group to the later Oct 31 to Nov 1 episode.

#### Insight E: `7Sm...c7qb` and `Eu4...Vzh` have strong direct-transfer evidence.

Evidence:

- Annotation 8 states that `7Sm...c7qb` funds `Eu4...Vzh`.
- Local transfer data confirms a direct transfer:
  - Time: `2024-10-23 15:31:44 UTC`
  - From: `7SmhQ9r2TLLgS5cmWoFSVGZZw7sEySmZXzwBVscrc7qb`
  - To: `Eu4DNnkPbV9kMj81FwaZMHPqAHsBAVrwbtjGfKdRhVzh`
  - Amount: `5,558,866.23` ACT

Rationale:

This is stronger than behavior similarity alone. A large direct transfer before later activity creates a concrete funding or control link. It supports treating `7Sm...c7qb` and `Eu4...Vzh` as part of the same investigative cluster, even if further evidence is needed to establish common control.

### 5.3 High-Level Insights

#### Insight A: The trace supports a multi-stage manipulation hypothesis.

Evidence:

- Oct 21 prebuyer group bought about `$164,376` on Oct 21.
- ACT's daily close increased from about `0.0256` on Oct 21 to about `0.0544` on Oct 23, then dropped sharply on Oct 24.
- The user annotated manipulation after the Oct 20 to 23 price rise.
- Oct 24 to 25 and Oct 31 to Nov 1 show concentrated suspicious card activity.
- The final prebuyer group sold about `$236,734` during Oct 31 to Nov 2, while local balance data still shows nonzero later holdings for several accounts.

Rationale:

The sequence fits a campaign narrative better than a single isolated event: accumulation, price rise, suspicious activity during or after price stress, later synchronized activity, and partial exit or profit-taking. The trace does not prove intent, but it provides a coherent pattern that justifies deeper investigation.

#### Insight B: Wallets appear to play different roles in the suspected campaign.

Evidence:

- The final four-wallet group appears to be an early accumulation and later exit group.
- The Oct 24 to 25 group appears more like a new-entry or coordinated buy group.
- The Oct 31 to Nov 1 group includes both repeated accounts and accounts with later buy/sell activity.
- `DmJR...7uLH` bridges the two main card windows.
- `7Sm...c7qb` funds `Eu4...Vzh`.

Rationale:

Not all suspicious accounts need to perform the same action. A manipulation campaign can involve accumulators, funders, price-support buyers, sell-side profit takers, and bridge accounts. The trace supports this role-based reading more than a simple "all accounts behave identically" reading.

#### Insight C: The exchange-listing motive is plausible in the user's hypothesis but remains unverified.

Evidence:

- Annotation 10 explicitly says the likely goal was inflating price ahead of an exchange listing to realize profits.
- The trace itself does not contain news, listing calendars, exchange data, or external event evidence.

Rationale:

The trace supports "coordinated activity around price movement." It does not independently establish "ahead of an exchange listing." That motive should be treated as a hypothesis until verified with external sources and event dates.

## 6. Recommendations

### 6.1 Low-Level Recommendations

- Reopen and compare annotations 0, 3, 4, 7, 8, 9, and 10.
- Inspect the card windows around `10/24-10/25` and `10/31-11/01`.
- Use Behavior Details with Sequential Time on and off for the same card cohorts.
- Keep Show Related Users enabled for `7Sm...c7qb` while inspecting `Eu4...Vzh` and nearby entity members.
- Export or tabulate the raw trade rows for the exact accounts in the three candidate groups.

### 6.2 Mid-Level Recommendations

#### Recommendation A: Run entity and link checks specifically around bridge accounts.

Priority accounts:

- `DmJR...7uLH`
- `7Smh...c7qb`
- `Eu4D...Vzh`
- `9KjD...5jE`
- `62cM...9Xe`

Rationale:

The current findings depend heavily on whether separate visible cohorts are actually connected. `DmJR...7uLH` bridges the two major card groups. `7Sm...c7qb` directly funds `Eu4...Vzh`. `9KjD...5jE` and `62cM...9Xe` connect early accumulation to the later Oct 31 to Nov 1 activity. Entity and link detection should be tuned to validate these bridge relationships.

#### Recommendation B: Compare entity-based and non-entity manipulation detection results.

Rationale:

Several insights depend on whether buy-side and sell-side wallets are linked. If manipulation only appears under entity-based detection, then entity quality becomes central evidence. If manipulation appears without entity grouping, the trading behavior itself is stronger. Comparing both modes will separate algorithmic grouping effects from raw behavior signals.

#### Recommendation C: Build a per-window trade-flow table.

Suggested windows:

- Oct 21 accumulation.
- Oct 24 to Oct 25 card window.
- Oct 31 to Nov 1 card window.
- Oct 31 to Nov 2 broader exit window.

Suggested columns:

- Wallet
- Group membership
- First trade
- Buy count and buy USD
- Sell count and sell USD
- Net token balance change
- Ending balance
- Direct-transfer counterparties

Rationale:

The screenshots show qualitative coordination. A table converts that into evidence that can be compared across users and windows. It will also reveal whether a wallet's apparent role is accumulation, wash-like turnover, price support, or exit.

#### Recommendation D: Test the wash-trading hypothesis with counterparty and liquidity-pool evidence.

Rationale:

Same-direction activity plus opposite buy/sell behavior is not enough to prove wash trading. The next step should check whether the same wallets, linked wallets, or common counterparties repeatedly appear on both sides of the trades. This is especially important for Oct 24 to 25, where the user explicitly framed wash trading as conditional on entity linkage.

### 6.3 High-Level Recommendations

#### Recommendation A: Treat this as a suspected coordinated ACT manipulation campaign and build a case timeline.

Proposed timeline:

| Date Range | Hypothesized Role | Evidence To Include |
|---|---|---|
| Oct 21 | Accumulation | Four-wallet group buys about `$164k`; ACT price begins rising. |
| Oct 20 to Oct 23 | Price rise | K-line annotations show upward trend. |
| Oct 24 to Oct 25 | Coordinated manipulation or price support | Manipulation cards, new-entry behavior, coordinated buys. |
| Oct 31 to Nov 1 | Larger synchronized manipulation window | 11-wallet card group, simultaneous behavior, large buy and sell totals. |
| Nov 1 onward | Profit-taking and residual holdings | Prebuyer group sells about `$237k` during Oct 31 to Nov 2 and retains balances afterward. |

Rationale:

A case timeline makes the high-level hypothesis falsifiable. Each stage can be checked with wallet-level evidence and external market events. It also prevents the investigation from over-weighting a single screenshot or annotation.

#### Recommendation B: Prioritize bridge accounts before peripheral accounts.

Recommended priority:

1. `DmJR...7uLH`
2. `7Smh...c7qb`
3. `Eu4D...Vzh`
4. `9KjD...5jE`
5. `62cM...9Xe`

Rationale:

Bridge accounts are more informative than one-window participants because they can connect otherwise separate events. If these bridges are confirmed through transfer, funding, or behavioral evidence, the campaign-level hypothesis becomes much stronger.

#### Recommendation C: Externally verify the exchange-listing hypothesis before using it as a conclusion.

Rationale:

The trace supports coordinated trading and possible price inflation. It does not include exchange listing evidence. To move from "coordinated trading around price moves" to "inflation ahead of listing," the investigation needs independent listing dates, announcement times, social or exchange references, and ideally a comparison of trading behavior before and after those announcements.

#### Recommendation D: Create a control comparison.

Possible controls:

- ACT holders with similar balances but no manipulation-card participation.
- ACT manipulation-card users that do not share transfer or entity links.
- PNUT sessions using the same detection settings.

Rationale:

The current evidence is suggestive because the suspicious users cluster in time and relationship space. A control comparison helps quantify whether the observed timing and relationships are unusual or simply common among active traders in this dataset.

## 7. Key Evidence Tables

### 7.1 Candidate User Groups

| Group | Source | Users |
|---|---|---|
| Initial selected user | Actions 1 to 3 | `7Smh...c7qb` |
| Oct 24 to 25 card group | Action 8 | `BgBm...dDon`, `EnMA...LBZ3`, `5RA2...VEz`, `5YPy...xYv`, `22JY...eBm`, `35No...uPQ`, `DmJR...7uLH`, `CqWV...xuhV`, `5WF1...mZEw` |
| Oct 31 to Nov 1 card group | Action 12 | `Eu4D...Vzh`, `9KjD...5jE`, `XiXR...sVn`, `49Fd...WGm`, `DmJR...7uLH`, `7iVQ...SzE`, `4B3Q...yV7`, `62cM...9Xe`, `GCDE...ZXz`, `HEHu...mpb`, `7Smh...c7qb` |
| Oct 21 prebuyer group | Action 18 view state, annotation 10 | `9KjD...5jE`, `D22g...JWv`, `F39g...KEa`, `62cM...9Xe` |

### 7.2 Repeated Or Linking Accounts

| Account | Evidence | Interpretation |
|---|---|---|
| `DmJR...7uLH` | Appears in both Oct 24 to 25 and Oct 31 to Nov 1 clicked card groups. | Candidate bridge across manipulation episodes. |
| `7Smh...c7qb` | Selected early, appears in Oct 31 to Nov 1 card group, funds `Eu4D...Vzh`. | Lead account and possible funder. |
| `Eu4D...Vzh` | Receives `5,558,866.23` ACT from `7Smh...c7qb`. | Directly funded account, likely part of same investigative cluster. |
| `9KjD...5jE` | Appears in Oct 31 to Nov 1 group and Oct 21 prebuyer group. | Links early accumulation to later activity. |
| `62cM...9Xe` | Appears in Oct 31 to Nov 1 group and Oct 21 prebuyer group. | Links early accumulation to later activity. |

### 7.3 Validated Trade Summaries

| Window | Group | Buy USD | Sell USD | Interpretation |
|---|---:|---:|---:|---|
| Oct 21 | Four prebuyers | `$164,376` | `$0` | Early accumulation pattern. |
| Oct 24 to Oct 25 card window | 9-wallet card group | `$185,386` | `$0` | Supports coordinated buy-side entry for the clicked cohort. |
| Oct 31 to Nov 1 card window | 11-wallet card group | `$135,421` | `$106,317` | Supports concentrated multi-wallet activity with both buys and sells. |
| Oct 31 to Nov 2 broader window | 11-wallet card group | `$602,781` | `$435,547` | Supports a larger synchronized trading episode. |
| Oct 31 to Nov 2 broader window | Four prebuyers | `$34,682` | `$236,734` | Supports later exit or profit-taking by early buyers. |

## 8. Bottom Line

The user appears to have performed a coherent forensic workflow rather than casual dashboard exploration. The session starts with a suspicious holder component, moves to price and manipulation timing, drills into card-user behavior, checks entity and direct-transfer evidence, and ends with a campaign-level hypothesis.

The strongest supported conclusion is that ACT contains a connected suspicious wallet cluster with repeated coordinated activity around Oct 24 to 25 and Oct 31 to Nov 1. The strongest inferred campaign narrative is early accumulation around Oct 21, coordinated price support or inflation, later synchronized trading, and partial profit-taking. The weakest part of the current case is the exchange-listing motive, which should be verified externally before being used as a final conclusion.
