# ManiScope ACT User Trace Analysis

## Scope and method

This report analyzes `maniscope-session-ACT-20260501-025125`, a ManiScope export for ACT. The session was exported at `2026-04-30T18:51:25.070Z` with snapshot images included. The active market snapshot in the trace is `2024-11-09 23:00:00 UTC`.

The trace contains 24 logged actions, 18 annotation records, and 36 PNG images. I reconstructed the analysis from `session.json`, annotation text, interaction screenshots, the current ManiScope user manual, selected frontend source semantics, and supporting local ACT data. Local data validation is explicitly separated from what the user directly saw in the UI.

## Source files used

Trace and documentation:

- `session.json`
- `images/*.png`
- `docs/reports/user-manual.en.md`
- `skills/user-trace-analysis.md`

Frontend semantics:

- `front/src/components/CryptoVis.vue`
- `front/src/components/TokenDistribution.vue`
- `front/src/components/CandlestickChart.vue`
- `front/src/components/BehaviorDetails.vue`
- `front/src/components/UserActionTimeline.vue`
- `front/src/components/AnnotationTimeline.vue`
- `front/src/components/UserActionTree.vue`
- `front/src/utils/sessionIO.js`

Supporting ACT data:

- `front/public/data/sorted_trades.csv`
- `front/public/data/sorted_transfers.csv`
- `front/public/data/user_relations.json`

## Caveats and assumptions

- Hover and zoom or scroll snapshot categories were disabled in the exported config, so several important navigations have JSON state but no screenshot.
- Some action timestamps are not strictly sorted by array order. For example, action 11 has timestamp `2026-04-30T18:27:26.484Z`, but appears after actions 9 and 10. I treat the action array as the logged sequence and note timestamp anomalies where relevant.
- Manipulation card clicks store `cardUsers`, but not full card metadata. Exact card time windows are inferred from nearby screenshots and card labels. Local CSV calculations therefore support, rather than replace, the visual trace.
- External market motives, such as listings, announcements, or news, were not checked. Any motive claim should remain unverified.
- Annotation screenshots are treated as the strongest evidence for what the user intended to preserve. Interaction screenshots are used for context and before or after state.

## System and view semantics

Token Distribution encodes top holders and related users as a graph. Larger nodes mean larger balances. Red-stroked nodes are involved in detected manipulation results under the active rules. Blue-stroked nodes are not flagged. Orange dashed boundaries are detected entity groups. Grey links appear when link detection is shown.

The K-line view places round-trip manipulation cards above the candlestick chart and same-direction manipulation cards below it. Clicking a card loads the participating wallets into Behavior Details as Card Users.

Behavior Details shows per-wallet rows with trade and transfer events, balance history, earnings, related users, and manipulation boxes. Sequential Time changes the x-axis from absolute dates to event order, which is useful for comparing patterns but weakens direct alignment with the K-line chart.

## Chronological reconstruction

| Step | Logged actions and annotations | What happened | Why it matters |
|---|---|---|---|
| 1 | Actions 0-2, annotations 0-3, screenshots [annotation-0000](images/annotation-0000-token_distribution.png), [annotation-0001](images/annotation-0001-token_distribution.png), [annotation-0002](images/annotation-0002-token_distribution.png) | The user updated the ACT snapshot, toggled links off and back on, then annotated a concentrated Token Distribution graph. They recorded that roughly 51 users held 30% of supply, many were red-stroked, and several large nodes sat inside three entity boundaries. | This established the high-level starting hypothesis: ACT looked supply-concentrated and structurally suspicious before any individual wallet investigation. |
| 2 | Action 3, annotations 4-5, screenshots [annotation-0004](images/annotation-0004-token_distribution.png), [annotation-0005](images/annotation-0005-behavior_details.png) | The user selected `6Z6RJJGrmVyndcPyTFhmLYHkHttiYtTccKpXFV9r2237` and concluded that this top holder held about 10M tokens but did not show manipulative behavior. The Behavior Details annotation says the tokens were acquired through transfers. | This is the first role distinction: a whale can be important to supply concentration without being a manipulator. |
| 3 | Actions 4-6, annotations 6-7, screenshots [annotation-0006](images/annotation-0006-token_distribution.png), [annotation-0007](images/annotation-0007-behavior_details.png) | The user selected `CqWVLXaj8r6vud5SfFr81SzmFoqXa5daLi1WbpQZxuhV`, zoomed Behavior Details to `2024-10-26T18:37:54.743Z` through `2024-10-27T14:27:23.240Z`, and enabled Sequential Time. They annotated a same-direction detector hit, but judged the wallet as a normal progressive accumulator. | This weakened a naive detector-only reading. The user was checking whether suspicious labels represented actual manipulation or benign accumulation. |
| 4 | Actions 7-11, annotations 8-10, screenshots [annotation-0008](images/annotation-0008-token_distribution.png), [annotation-0009](images/annotation-0009-behavior_details.png), [annotation-0010](images/annotation-0010-behavior_details.png) | The user selected `DNLFULTWBTkpfwpXZeMA7ckMbQntHuLqxZq6RH6xnaji`, enabled related users, then moved through a related label to `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH`. They annotated DNL as a likely functional account and DmJ as an account whose similar-period buying affected price. | This moved the analysis from static graph suspicion to role and timing: one account seemed operational, and another became a repeated behavior anchor. |
| 5 | Action 12, annotation 12, screenshot [annotation-0012](images/annotation-0012-candlestick_chart.png) | The user scrolled same-direction K-line cards around `2024-10-25` to `2024-11-01`, then annotated the K-line around the `2024-10-24` to `2024-10-27` price region as clearly price affecting. | This linked wallet behavior to price movement, although the trace alone does not quantify causality. |
| 6 | Actions 13-15, annotation 13, screenshots [action-0014-source](images/action-0014-source-kline_chart-01.png), [annotation-0013](images/annotation-0013-behavior_details.png) | The user clicked a same-direction manipulation card with 9 card users, then turned Sequential Time off. The annotation states that on `2024-10-26`, within about 32 minutes, 26.17M tokens traded in the same direction, and that after DmJ's sell, 9 addresses bought frequently in the same direction. | This is the first explicit cohort-level coordination finding. |
| 7 | Actions 16-20, annotations 14-15, screenshots [action-0017-source](images/action-0017-source-kline_chart-01.png), [annotation-0014](images/annotation-0014-behavior_details.png), [annotation-0015](images/annotation-0015-behavior_details.png) | The user clicked another 9-user card, toggled Sequential Time on, and zoomed the sequential chart. The main annotation says same-direction trading alternates between buys and sells, forming a round-trip-like pattern. | The user was testing whether same-direction bursts were part of a broader cycle rather than isolated buys. |
| 8 | Actions 21-23, annotations 17-19, screenshots [action-0022-source](images/action-0022-source-kline_chart-01.png), [annotation-0017](images/annotation-0017-behavior_details.png), [annotation-0019](images/annotation-0019-token_distribution.png) | The user clicked a 3-user card containing `7SmhQ9r2TLLgS5cmWoFSVGZZw7sEySmZXzwBVscrc7qb`, `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH`, and `GCDEuA5Q6KugDcN5wxnorwkeSrMYiPJse24pDfFbLZXz`. They then created a high-level insight that these addresses were part of the same component, forming a large colluding group, and exported the session. | This is the final synthesis: repeated card cohorts and graph/component evidence were combined into a collusion hypothesis. |

## Intention Space analysis

### Tasks

| ID | Task | Evidence | Rationale |
|---|---|---|---|
| T1 | Configure and inspect ACT snapshot with links. | Actions 0-2; annotations 0-3. | The first actions update the snapshot and inspect link visibility before any wallet selection. |
| T2 | Check whether the top whale `6Z6...2237` is manipulative. | Action 3; annotations 4-5. | The user explicitly wrote that this top holder was not manipulative and checked Behavior Details. |
| T3 | Evaluate whether `CqW...xuhV` is a true manipulator or normal accumulator. | Actions 4-6; annotations 6-7. | The user compares a detector hit against behavior timing and concludes it appears normal. |
| T4 | Inspect functional or related accounts around `DNL...naji` and `DmJ...7uLH`. | Actions 7-11; annotations 8-10. | The user enables related users and follows a Behavior Details label, which is consistent with relationship tracing. |
| T5 | Relate manipulation cards to K-line price movement. | Action 12; annotation 12. | The annotation is explicitly about price impact after card scrolling. |
| T6 | Inspect card-user cohorts in Behavior Details. | Actions 13-21; annotations 13-17. | The user repeatedly clicks cards, toggles Sequential Time, zooms, and annotates cohort behavior. |
| T7 | Synthesize trace findings into a colluding-group claim. | Annotations 18-19; action 23. | The final high-level insight references many prior annotations, then the user exports the session. |

### Analytic Questions

| ID | Analytic Question | Evidence | Rationale and confidence |
|---|---|---|---|
| AQ1 | Is ACT's supply and holder graph suspicious enough to justify investigation? | Annotations 0-3, Token Distribution screenshots. | Direct user-authored evidence. The user observed concentration, red-stroked nodes, entity boundaries, and a connected component. Confidence: high for trace-supported suspicion, not for proven manipulation. |
| AQ2 | Which flagged wallets are likely benign, functional, or manipulative? | Annotations 4-10; wallet selections for `6Z6...`, `CqW...`, `DNL...`, `DmJ...`. | The user differentiates a passive whale, a normal accumulator, a functional account, and a price-impact account. Confidence: medium, because some roles need local data or model validation. |
| AQ3 | Did the same-direction and round-trip card windows align with price movement? | Annotation 12; K-line screenshot; card-click actions 13, 16, and 21. | The user explicitly connected behavior to price, and the K-line screenshot marks the high-volatility `2024-10-24` to `2024-10-27` region. Confidence: medium, because causality is visually inferred. |
| AQ4 | Are the clicked cohorts part of a larger connected collusive component? | Annotations 17-19; repeated card users; Token Distribution component screenshot. | The final insight makes this claim, and repeated users bridge multiple card cohorts. Confidence: medium-high as a trace-supported hypothesis, pending graph computation. |

### Hypotheses

| ID | Hypothesis | Evidence | Rationale and caveat |
|---|---|---|---|
| H1 | ACT manipulation is likely organized around a connected component rather than isolated wallets. | Annotations 2, 18, 19; repeated users across card clicks. | The user starts with component-level graph evidence and ends with a colluding-group insight. Caveat: the exact component membership should be recomputed from link or entity data. |
| H2 | Some normal-looking accounts serve operational roles, such as storage, transfer, or detection-avoidance accounts. | Annotations 1, 8, 9; DNL transfer validation. | The trace repeatedly notes normal-looking accounts inside suspicious groups. Caveat: intent to avoid detection is unverified and should remain a hypothesis. |
| H3 | The `2024-10-25` to `2024-10-27` behavior includes coordinated same-direction and round-trip-like activity that affected price. | Annotations 10, 12, 13, 14; card screenshots and local trade summaries. | The trace links behavior windows, K-line movement, and repeated card-user cohorts. Caveat: price impact needs a volume-share and counterfactual test. |

## Finding Space analysis

### User-authored Findings

| ID | Finding | Evidence |
|---|---|---|
| F1 | Approximately 51 users held 30% of the token supply, and most were marked suspicious. | Annotation 0; [annotation-0000](images/annotation-0000-token_distribution.png). |
| F2 | Three large detected entities collectively held substantial funds and contained a mix of suspicious and apparently normal accounts. | Annotation 1; [annotation-0001](images/annotation-0001-token_distribution.png). |
| F3 | Two entities plus several holders were connected in a single component, creating a poor initial risk impression. | Annotation 2; [annotation-0002](images/annotation-0002-token_distribution.png). |
| F4 | `6Z6RJJGrmVyndcPyTFhmLYHkHttiYtTccKpXFV9r2237` was a top holder with about 10M tokens but no visible manipulative behavior. | Annotations 4-5; [annotation-0004](images/annotation-0004-token_distribution.png), [annotation-0005](images/annotation-0005-behavior_details.png). |
| F5 | `CqWVLXaj8r6vud5SfFr81SzmFoqXa5daLi1WbpQZxuhV` triggered same-direction detection but appeared to be a normal progressive accumulator. | Annotations 6-7; [annotation-0007](images/annotation-0007-behavior_details.png). |
| F6 | `DNLFULTWBTkpfwpXZeMA7ckMbQntHuLqxZq6RH6xnaji` appeared to be a functional account, and direct transfers to another normal-looking account were observed. | Annotations 8-9; [annotation-0009](images/annotation-0009-behavior_details.png). |
| F7 | Another address bought a similar amount during the same period and appeared to affect price. | Annotation 10; [annotation-0010](images/annotation-0010-behavior_details.png). |
| F8 | The K-line region around `2024-10-24` to `2024-10-27` was interpreted as price-affected by manipulation activity. | Annotation 12; [annotation-0012](images/annotation-0012-candlestick_chart.png). |
| F9 | A `2024-10-26` same-direction cohort showed frequent buying after DmJ's sell. | Annotation 13; [annotation-0013](images/annotation-0013-behavior_details.png). |
| F10 | A later selected 3-address card was interpreted as part of the same component, supporting a large colluding-group claim. | Annotations 17-19; [annotation-0017](images/annotation-0017-behavior_details.png), [annotation-0019](images/annotation-0019-token_distribution.png). |

### Analyst-inferred Findings with local validation

| ID | Finding | Supporting evidence | What would weaken it |
|---|---|---|---|
| MF1 | The user was building a role-based case, not just collecting suspicious flags. | The sequence distinguishes `6Z6...` as a passive whale, `CqW...` as likely normal, `DNL...` as functional, and `DmJ...` as price-relevant. | If local data showed these roles were inconsistent across the full period. |
| MF2 | Repeated card users act as bridges across suspected manipulation windows. | `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH` appears in all three clicked card cohorts. `5YPynSvVjWB6EQeFNg3WiKoGsm7J9doxpBY3sVMy1xYv` appears in the first and second cohorts. `7SmhQ9r2TLLgS5cmWoFSVGZZw7sEySmZXzwBVscrc7qb` appears in the second and third cohorts. | If card clicks came from unrelated card types and the overlap is coincidental. |
| MF3 | Local trades support a strong same-direction burst for the first 9-user cohort, although not every listed card user traded inside the inferred exact window. | For action 13 users, during inferred card window `2024-10-26 07:10:41 UTC` to `2024-10-27 07:42:24 UTC`, local trades show 67 buys, 0 sells, 11.62M ACT bought, and about $319.47K buy USD across 4 active users. | The inferred card window may be incomplete because card metadata was not exported. |
| MF4 | The second 9-user cohort has round-trip-like aggregate behavior over `2024-10-25` to `2024-10-27`. | Local trades for action 16 users over that visual window show 192 buys and 63 sells, with 29.22M ACT bought and 24.77M ACT sold, about $699.20K buy USD and $510.35K sell USD. | This aggregate could still mix independent strategies without wallet-level synchronization. |
| MF5 | The 3-user card has a plausible round-trip signature for the active traders. | For action 21 users during inferred `2024-10-25 17:24:32 UTC` to `2024-10-26 02:52:01 UTC`, local trades show 16 buys and 20 sells, 6.05M ACT bought and 9.44M ACT sold, with buy and sell USD of about $133.63K and $137.57K. | One of the three users had no trades in that exact CSV window, so the exported card or data window may include additional context. |

### Important local-data checks

| Wallet or group | Trace role | Local validation |
|---|---|---|
| `6Z6RJJGrmVyndcPyTFhmLYHkHttiYtTccKpXFV9r2237` | Passive whale, not manipulator | No trades were found in `sorted_trades.csv`. `sorted_transfers.csv` shows a 10,636,142.000784 ACT incoming transfer from `4V9nKsuJHbaD1fNn7sn1y4M3L2j541DZb89sjNnZzkQ6` at `2024-10-24 11:07:59 UTC`, supporting the transfer-acquired interpretation. |
| `CqWVLXaj8r6vud5SfFr81SzmFoqXa5daLi1WbpQZxuhV` | Detector hit but likely normal accumulator | Full-period trades show 27 buys, 2 sells, 10.73M ACT bought, and 0.50M ACT sold. This supports accumulation, although it does not prove benign intent. |
| `DNLFULTWBTkpfwpXZeMA7ckMbQntHuLqxZq6RH6xnaji` | Functional account | Full-period trades show 165 buys and 3 sells. Transfers show 17.31M ACT incoming and 7.98M ACT outgoing. The largest outgoing sink is `GvZknRDvFn1XXhBycPxw1kAL2dVDa2pAB5fJdRmmDZHD`, receiving 7.83M ACT on `2024-10-31`. |
| `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH` | Repeated price-relevant bridge account | Full-period trades show 103 buys, 22 sells, 17.60M ACT bought, and 10.55M ACT sold. It appears in all three clicked card cohorts. |
| Action 13 card users | Same-direction cohort | 9 exported card users; local inferred-window trades show pure buying among active users. |
| Action 16 card users | Alternating same-direction and sell pattern | 9 exported card users; local `2024-10-25` to `2024-10-27` trades show both substantial buys and sells. |
| Action 21 card users | Small component or round-trip card | 3 exported card users; local inferred-window trades show near-balanced USD buy and sell totals among active users. |

## High-level Insights

| ID | Insight | Evidence and rationale | Confidence |
|---|---|---|---|
| I1 | ACT presented a high-risk investigation surface because concentration, suspicious node strokes, entity boundaries, and links all appeared early in the trace. | The first three annotations build this directly from Token Distribution. This is an insight about risk triage, not proof of manipulation. | High for trace interpretation. |
| I2 | Detector output needed analyst adjudication. Some flagged wallets looked benign or passive, while others looked operational or bridge-like. | `6Z6...` and `CqW...` were used as counterexamples to blanket suspicion. `DNL...` and `DmJ...` became role-specific suspects. | Medium-high. |
| I3 | The strongest trace-supported hypothesis is a connected collusive component active around `2024-10-25` to `2024-10-27`, with DmJ as a repeated bridge across same-direction and round-trip-like windows. | The final high-level insight, card-user overlaps, K-line annotation, and local trade summaries all point in this direction. | Medium. The component and price impact need explicit statistical validation. |

## Top-down investigation recommendations

The recommendations are organized into three investigator-facing classes. The first continues the user's case. The second asks what else is similar enough to deserve exploration. The third captures hindsight opportunities that the user did not pursue, even though the trace and local ACT data suggest they may matter.

### Class A: Continue the user's path

#### S1: Validate the core collusion case

Target hypothesis: H1 and H3.

Why this matters: The trace's strongest path is not just "some wallets look suspicious". It is a case theory: DmJ bridges multiple card cohorts, the `2024-10-25` to `2024-10-27` windows align with price movement, and many selected addresses appear to sit in the same component.

Target outcome: A case packet with one role timeline, one manipulation-window table, and one reproducible component map.

| Analytic Activity | Type | Interactions |
|---|---|---|
| AA1: Reconstruct role and window evidence | Visual Analysis | Reopen annotations 4-17, card screenshots, and Token Distribution screenshots; transcribe which visual cue supports each wallet role and time window. |
| AA2: Quantify clicked cohorts and bridge wallets | Statistical Analysis | Calculate trade counts, buy/sell tokens, USD flow, net position, transfers, balances, and earnings for every selected and clicked wallet. |
| AA3: Recompute component and price-impact evidence | Statistical Analysis | Build a relationship graph from `user_relations.json` and `sorted_transfers.csv`, then join clicked cohorts to market-wide `sorted_trades.csv` and `ACT_OHLC.json`. |

| Interaction ID | Interaction Type | Evidence Route | Expected Output |
|---|---|---|---|
| S1-I1 | Visualization Action | visualization -> finding | A visual role table linked to [annotation-0005](images/annotation-0005-behavior_details.png), [annotation-0007](images/annotation-0007-behavior_details.png), [annotation-0009](images/annotation-0009-behavior_details.png), [annotation-0013](images/annotation-0013-behavior_details.png), and [annotation-0017](images/annotation-0017-behavior_details.png). |
| S1-I2 | Data Action | data -> finding | A per-wallet metric table for all selected and clicked users, including DmJ's recurrence across all three clicked cohorts. |
| S1-I3 | Data Action | data -> finding | Window-level market-share and OHLC movement metrics for the `2024-10-25` to `2024-10-27` windows. |
| S1-I4 | Model Action | model -> visualization -> finding | Rerun entity and link detection with stricter and looser thresholds, then inspect whether DmJ, DNL, and the clicked card users remain in the same core component. |
| S1-I5 | Synthesis Action | findings -> insight | A confidence-labeled case theory that separates direct trace evidence, local data validation, and weak assumptions. |

### Class B: Similar new explorations

#### S2: Search for sibling manipulation windows

Target analytic question: AQ3.

Why this matters: The user focused on `2024-10-25` to `2024-10-27`, but the K-line screenshots show additional card windows nearby, and local data shows intense high-frequency activity after the user's focus window.

Target outcome: A ranked list of candidate sibling windows with card labels, active wallets, cohort volume, and whether they reuse known bridge wallets.

Local leads to start with:

- The visible `2024-10-30` to `2024-10-31` same-direction area includes DNL in the card row; local data shows DNL made 35 buys, 0 sells, bought 2.43M ACT, and spent about $99.32K between `2024-10-30 18:37:50 UTC` and `2024-10-30 20:04:50 UTC`.
- The same visible region also includes `5WF1V6TBDHxrZvPhh6doyE5ZEb8BaFFgqg7wR81zmZEw`, which was already in the user's first clicked card and had 16 trades over `2024-10-30` to `2024-10-31`.
- Local high-frequency post-window traders not in the trace include `HjiNTb9SJzVi9fc3ekr5PUMd3fCkFwEwAde52vDQD3hs` with 422 trades and about $756.66K volume on `2024-10-31`, and `6jvYtr9G5WQnKs3cFsFtKmEfkbEnUXFhBKsmZad26QPV` with 1306 trades and about $714.54K volume on `2024-11-01`.

| Analytic Activity | Type | Interactions |
|---|---|---|
| AA4: Mine visible but unclicked K-line cards | Visual Analysis | Reopen K-line screenshots and list all visible cards that the user did not click, especially `2024-10-28`, `2024-10-30` to `2024-10-31`, and `2024-10-31` to `2024-11-01`. |
| AA5: Rank sibling windows from local data | Statistical Analysis | Group trades by day and wallet; rank windows by trade count, USD volume, buy/sell balance, and overlap with known trace wallets. |

| Interaction ID | Interaction Type | Evidence Route | Expected Output |
|---|---|---|---|
| S2-I1 | Visualization Action | visualization -> finding | A card inventory from [action-0014-source](images/action-0014-source-kline_chart-01.png), [action-0017-source](images/action-0017-source-kline_chart-01.png), and [action-0022-source](images/action-0022-source-kline_chart-01.png). |
| S2-I2 | Data Action | data -> finding | A ranked table of unclicked windows, including DNL's `2024-10-30` buying burst and high-volume post-window traders. |
| S2-I3 | Synthesis Action | findings -> insight | A decision on which sibling windows deserve full Behavior Details investigation. |

#### S3: Search for similar wallet roles outside the user's selected group

Target analytic question: AQ2.

Why this matters: The user found role types, not just wallet addresses. Similar passive whales, functional accounts, storage sinks, bridge wallets, and round-trip actors may exist outside the specific component they followed.

Target outcome: A candidate roster of uninvestigated wallets grouped by role similarity.

Local leads to start with:

- Round-trip-like high-frequency candidates include `63qFfzr6aUjWiwFDc8T3UkKGM4iZLGxCcyE2exnS9aic` on `2024-10-28` with 712 buys and 698 sells, and `D4zVhwuUsFbcaty7wJhNEZ7VEwPHXQ5d2heXPxM5yWhL` on `2024-10-31` with 81 buys and 81 sells.
- Large one-sided sell or exit candidates include `3DrUWhsaxJcGkf5XkrQNCQfCDmJnVxHitz31UvNkqPUL`, which sold 34.20M ACT across 3 trades on `2024-10-31`, and `G9VG1W6Nzcj5n62Z1VWyq2uSbJr4BvFHDHWEyW2GnpTu`, which sold 4.84M ACT across 19 trades on `2024-11-03`.

| Analytic Activity | Type | Interactions |
|---|---|---|
| AA6: Build role-similarity features | Statistical Analysis | Compute wallet features for all ACT traders: trade count, buy/sell symmetry, net tokens, net USD, transfer-in/out volume, first/last action, and final balance. |
| AA7: Inspect top role matches visually | Visual Analysis | Load the highest-ranked uninvestigated wallets in ManiScope and inspect Token Distribution, Behavior Details, related users, and manipulation boxes. |

| Interaction ID | Interaction Type | Evidence Route | Expected Output |
|---|---|---|---|
| S3-I1 | Data Action | data -> finding | A role-similarity table with candidate passive whales, functional accounts, bridge wallets, round-trip actors, and exit sellers. |
| S3-I2 | Visualization Action | data -> visualization -> finding | Behavior Details screenshots for the top candidates from each role class. |
| S3-I3 | Synthesis Action | findings -> insight | A short list of wallets that warrant deeper case-building and wallets likely explained by benign or bot-like behavior. |

### Class C: Hindsight opportunities

#### S4: Follow the DNL storage sink that the user did not pursue

Target hypothesis: H2.

Why this matters: The user saw DNL as functional, but did not follow its biggest downstream sink. Local transfer data shows DNL sent 7.83M ACT to `GvZknRDvFn1XXhBycPxw1kAL2dVDa2pAB5fJdRmmDZHD` in three transfers within about ten minutes on `2024-10-31`; that sink has no trades in `sorted_trades.csv` and no outgoing transfers in `sorted_transfers.csv`.

Target outcome: A downstream custody and storage analysis for DNL and related functional accounts.

| Analytic Activity | Type | Interactions |
|---|---|---|
| AA8: Trace DNL downstream custody | Statistical Analysis | Query all DNL outgoing transfers, recipient labels, recipient balances, and recipient later actions. |
| AA9: Inspect sink visibility in ManiScope | Visual Analysis | Load `GvZkn...DZHD` if available in the snapshot and inspect whether it appears as a top holder, related user, component member, or visually peripheral address. |

| Interaction ID | Interaction Type | Evidence Route | Expected Output |
|---|---|---|---|
| S4-I1 | Data Action | data -> finding | A transfer chain table from DNL to `GvZkn...DZHD` and any downstream wallets. |
| S4-I2 | Visualization Action | data -> visualization -> finding | Token Distribution and Behavior Details evidence for the sink wallet if present in the visible ManiScope state. |
| S4-I3 | Synthesis Action | findings -> insight | A custody-role conclusion: storage sink, operational relay, or unrelated recipient. |

#### S5: Test whether the campaign had a post-support exit phase

Target hypothesis: H3.

Why this matters: The user focused on price support and same-direction buying. A manipulation case is stronger if it also identifies later exits, profit-taking, or inventory movement after the support window.

Target outcome: A post-window exit analysis from `2024-10-28` through `2024-11-03`.

| Analytic Activity | Type | Interactions |
|---|---|---|
| AA10: Compute post-window exits | Statistical Analysis | Rank wallets by large sells, net outflow, realized earnings, and transfers after `2024-10-27`. |
| AA11: Compare exits to original component | Statistical Analysis | Intersect exit sellers and sink recipients with the clicked card users, entity groups, and link components. |
| AA12: Inspect top exits visually | Visual Analysis | Load top exit candidates in Behavior Details and compare their timing against K-line price movement. |

| Interaction ID | Interaction Type | Evidence Route | Expected Output |
|---|---|---|---|
| S5-I1 | Data Action | data -> finding | A ranked exit table including candidates such as `3DrU...qPUL` and `G9VG...npTu`. |
| S5-I2 | Data Action | data -> finding | A component-overlap table showing whether exit sellers connect back to DmJ, DNL, or clicked card cohorts. |
| S5-I3 | Visualization Action | data -> visualization -> finding | Behavior Details and K-line evidence for the top post-window exits. |
| S5-I4 | Synthesis Action | findings -> insight | A conclusion on whether the observed campaign has an accumulation, support, and exit structure. |

## Evidence tables

### Clicked card users

| Action | Approximate trace focus | Card users | Repeated bridge users |
|---|---|---|---|
| 13 | Same-direction card around `2024-10-26` to `2024-10-27` | `5RA23pdRqxPHjGZT9kUCdywx5QgQ3NFo5NXiNSsCCVEz`; `CqWVLXaj8r6vud5SfFr81SzmFoqXa5daLi1WbpQZxuhV`; `5WF1V6TBDHxrZvPhh6doyE5ZEb8BaFFgqg7wR81zmZEw`; `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH`; `35NoW8F4Q3Gcqf3Wf4RMmoAgS7FHchCjv3R2F241zuPQ`; `22JYebQtQSLchTXiRJVCx7hpPamN1YzLJKHET52S6eBm`; `EnMAi9raXU8KMBP3YLKAsLL1EnucWrggtBAxZAsmLBZ3`; `BgBmwgMG1cRQxHKkgYd42Gz8rpXtSNcnqgazWGPfdDon`; `5YPynSvVjWB6EQeFNg3WiKoGsm7J9doxpBY3sVMy1xYv` | `DmJR...7uLH`, `5YP...1xYv` |
| 16 | Second 9-user card with alternating buy and sell behavior | `7SmhQ9r2TLLgS5cmWoFSVGZZw7sEySmZXzwBVscrc7qb`; `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH`; `2brzD1rU8m71zf23bfgtw3vn9pqZG2CDxYU3nQ5pPizN`; `XiXRAfbXGgNsZw2hwPdqBsU461kXFfYgTMV8sgjRSvN`; `85TMiRBoDjZiFjHUwrrBkqZDh4o3SHMPtgbDXM7N7Qff`; `DNLFULTWBTkpfwpXZeMA7ckMbQntHuLqxZq6RH6xnaji`; `5YPynSvVjWB6EQeFNg3WiKoGsm7J9doxpBY3sVMy1xYv`; `ErAJGcJTEUqa11ag1MxLWZjqoqzgTtZKJk9cQiN9T3ZU`; `Eu4DNnkPbV9kMj81FwaZMHPqAHsBAVrwbtjGfKdRhVzh` | `DmJR...7uLH`, `5YP...1xYv`, `7Sm...c7qb` |
| 21 | Three-user card linked to same component | `7SmhQ9r2TLLgS5cmWoFSVGZZw7sEySmZXzwBVscrc7qb`; `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH`; `GCDEuA5Q6KugDcN5wxnorwkeSrMYiPJse24pDfFbLZXz` | `DmJR...7uLH`, `7Sm...c7qb` |

### Key screenshots

| Screenshot | Use in analysis |
|---|---|
| [annotation-0000-token_distribution.png](images/annotation-0000-token_distribution.png) | Supply concentration and many suspicious nodes. |
| [annotation-0002-token_distribution.png](images/annotation-0002-token_distribution.png) | Component-level risk around two entities and other holders. |
| [annotation-0005-behavior_details.png](images/annotation-0005-behavior_details.png) | Passive whale behavior for `6Z6...2237`. |
| [annotation-0009-behavior_details.png](images/annotation-0009-behavior_details.png) | DNL related-user and transfer evidence. |
| [annotation-0010-behavior_details.png](images/annotation-0010-behavior_details.png) | DmJ and related wallets during a price-relevant period. |
| [annotation-0012-candlestick_chart.png](images/annotation-0012-candlestick_chart.png) | K-line price region marked as affected. |
| [annotation-0013-behavior_details.png](images/annotation-0013-behavior_details.png) | Same-direction 9-user cohort. |
| [annotation-0014-behavior_details.png](images/annotation-0014-behavior_details.png) | Alternating buy and sell pattern across the second 9-user cohort. |
| [annotation-0017-behavior_details.png](images/annotation-0017-behavior_details.png) | Three-user card with component claim. |
| [annotation-0019-token_distribution.png](images/annotation-0019-token_distribution.png) | Final graph-level support for large component membership. |

## Bottom line

The strongest trace-supported conclusion is that the user was building a collusion case for ACT around a concentrated, linked holder component and repeated manipulation-card cohorts active around `2024-10-25` to `2024-10-27`. The strongest local validation is that DmJ recurs across all clicked cohorts, the first 9-user inferred card window contains pure buying among active users, and DNL has large outgoing transfers to a normal-labeled wallet.

The weakest unresolved claim is price causality and motive. The trace shows visual K-line alignment and user-authored price-impact annotations, but a defensible conclusion still needs market-wide volume share, OHLC movement, and falsification against benign accumulation or independent trading.
