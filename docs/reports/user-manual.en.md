# ManiScope User Manual

## What ManiScope is

ManiScope is a visual analytics dashboard for assessing trade-based price-manipulation risk on cryptocurrency markets. The system targets the case of memecoins on decentralized exchanges, where low entry barriers, continuous trading, and limited regulation make it relatively easy for operators to influence market signals through multi-address coordination, short-term concentrated trading, or artificial trading activity. ManiScope loads pre-computed datasets such as DEX trade logs, token transfer logs, hourly balance snapshots, and per-user behavior sequences for one of two example tokens, ACT or PNUT, both issued on Solana. On top of those datasets it runs entity-clustering, link detection, and manipulation detection, then exposes the results through four coordinated, interactive views.

ManiScope is best understood as an investigator's tool rather than a real-time monitoring system. It answers questions of the form "who was manipulating this token over the past few weeks, how were the wallets connected, and how did their activity move the price" rather than "is something suspicious happening right now". The expected workflow is exploratory: pick a snapshot in time, configure detection rules, look for visual patterns across the four views, and drill down into individual holders when something catches your eye.

## Screen layout

The dashboard fills the entire browser window and is divided into three columns. The left column is a narrow Control Panel. The middle column is split vertically into the Token Distribution View at the top and the Behavior Detail View at the bottom. The right column is the Manipulation View, which contains a K-line chart sandwiched between two horizontal rows of detail cards.

```
+----------------------------------------------------------------------+
|  ManiScope                                              o ACT  o PNUT |
+--------------+----------------------------+--------------------------+
|              | Token Distribution View    | Manipulation View        |
|              | (top-holder ring +         | -- round-trip cards ---  |
|              |  related-user outer ring)  | |   K-line + bands    |  |
|  Control     |                            | -- same-direction cards  |
|  Panel       +----------------------------+                          |
|              | Behavior Detail View       |                          |
|              | (selected holder + entity  |                          |
|              |  + related holders)        |                          |
+--------------+----------------------------+--------------------------+
```

## The four views in detail

### 1. Control Panel (left column)

The Control Panel is the driver of the dashboard. It hosts four configuration groups, each with its own action button.

**Snapshot Configuration** is at the top. The Snapshot Time dropdown lets you pick any hourly timestamp from 2024-10-19 12:00 UTC onwards. Everything else in the dashboard is computed relative to this point in time, so changing it is the most consequential action you can take. Two thresholds shape the population of holders that ends up on screen: the **Top Holders Threshold** (default 0.3) is the cumulative balance fraction you want to capture among user-held supply, so 0.3 means "the smallest set of top holders whose combined holdings reach approximately 30 percent of the total token supply". A second threshold identifies **related holders**, namely any address that has direct transfers with at least one of the top holders and that itself holds at least a configurable minimum balance (the Related User Threshold, default 0.2). The Related User Threshold is anchored to the smallest top-holder balance rather than to a fixed amount, so the criterion remains meaningful across tokens with very different liquidity profiles. The Update Snapshot button refreshes the Token Distribution View at the chosen time.

**Entity Detection Configuration** sits below. Its orange Run Detection button triggers wallet-clustering. Rules can be specified from three aspects, mirroring the design of the rule tables in the paper: **network-based** rules that query the precomputed transfer-network statistics; **similarity-based** rules that compare per-user time series; and **manipulation-based** rules that group wallets if they participate in the same manipulation patterns. Network-based rules include Direct Transfer (reciprocal transfers between an address pair), Funding Relationship (whether two addresses share the same first funding source), and Same Sender / Same Recipient toggles. Similarity-based rules cover trading-action sequences, balance sequences, and earning sequences, each with its own similarity threshold.

**Link Detection Configuration** is the third group. Its action button (labeled Update Links in the running app) shares the same rule families as Entity Detection but with deliberately looser thresholds. The reason for the split is one of strictness: entity detection uses hard groupings (Union-Find on satisfied rules) and the strictest thresholds in order to minimize false positives, while link detection uses softer pairwise associations and more permissive thresholds in order to encourage discovery. The result is that entity detection produces wallet groups visualized as orange dashed clusters, while link detection produces grey edges between holders that are visualized as tentative connections in the Token Distribution View.

**Manipulation Detection Configuration** is the fourth group. Its Run Detection button runs the trade-pattern detector. Two complementary rules are available. The Round Trip rule looks for buy-then-sell sequences where the trader's net position returns to roughly zero with negligible profit, which is the canonical wash-trading signal. The Same Direction rule looks for stretches of consecutive same-side trades with no opposing trades mixed in, which is the canonical signature of coordinated accumulation or distribution. Both rules can be run at the **entity level** when the toggle is enabled, in which case trades from all wallets inside an entity are merged before detection runs and coordinated activity that would otherwise be invisible across separate wallets becomes detectable.

One detail that is not obvious from the UI: the page automatically runs all detection algorithms when it first loads, and when you change the snapshot time and click Update Snapshot. However, switching coins between ACT and PNUT clears the manipulation results, and you must click Run Detection again afterwards to repopulate them.

### 2. Token Distribution View (middle-top)

The Token Distribution View is an enhanced node-link diagram that depicts both the holding distribution among top holders and the relationships between them. It has a two-ring structure.

The **inner ring** contains the top holders selected by the Top Holders Threshold. Each top holder is represented as a node. Node size encodes the absolute token balance, so larger circles are larger holders. Node fill uses a blue color gradient where darker blue indicates a higher balance. Holder nodes are arranged using a force-directed layout with collision avoidance to prevent overlap, and linked nodes are positioned cohesively while still respecting the spatial constraint that keeps top holders inside the inner ring.

The **outer ring** contains the related holders, namely the filtered-out addresses that nevertheless have direct token transfers to top holders. Their node size is scaled consistently with the inner ring so that the relative magnitudes of related holders and top holders remain comparable at a glance. The aggregated holdings of all remaining holders, those that are neither top holders nor related to one, are conceptually represented as an Others aggregate at the outermost layer of the visualization, although its visibility depends on the threshold settings and on the structure of the snapshot.

The most important visual encodings overlay this layout.

- **Red stroke on a node**: the wallet appears as a participant in at least one detected manipulation event under the current rules. Suspicious nodes from manipulation behaviors are highlighted with this red stroke.
- **Blue stroke on a node**: the wallet has not been flagged by manipulation detection in the current run.
- **Orange dashed circle around a small group of inner-ring nodes**: a detected entity. Top holders that are identified as belonging to the same entity are spatially packed together inside this dashed circle.
- **Orange dashed link from a related holder to an entity**: the related holder is connected to the dashed entity circle by an orange dashed link, signalling that this related holder participates in the entity's transfer neighborhood without being clustered into the entity itself.
- **Grey link between two holders**: a relationship detected by Link Detection. Grey links are pairwise rather than entity-grouping, and they capture associations that are weaker than the entity rules but still worth flagging.

Interactions on this view are simple. **Hovering** any node reveals a tooltip with the wallet address, the token balance, and, for flagged wallets, the reasons for being marked suspicious. **Clicking** a node selects that holder, populates the Behavior Detail View below, and visually highlights the holder's entity if it has one. The Scale slider in the header bar zooms the entire view in or out.

The first thing to look at on this view is the ratio of red to blue strokes. A small minority red is normal for any active token. A majority red is a strong cue that manipulation activity is widespread among the top holders, and is the right place to begin a deeper investigation. The orange dashed clusters are the second thing to scan: each one is a wallet group that the entity detector is confident about, and they are the natural starting points for clicking through.

### 3. Behavior Detail View (middle-bottom)

The Behavior Detail View presents detailed behaviors of holders associated with a holder selected from the Token Distribution View. It is empty by default and populates only after you click a node above.

The **y-axis** lists, from the center outward, the selected holder and all holders that have entity or link relationships with it. The selected holder is placed at the center of the stack, with entity members and related holders around it. The **x-axis** is a timeline. For each holder, behaviors are illustrated across **three aspects**: actions, balance, and earnings.

**Actions** are encoded as colored circles along the timeline. Blue circles are buys, pink circles are sells, and grey circles are transfers. Each circle represents one transaction event for that holder.

**Balance** is visualized using a blue area chart for the holder's overall token balance over time. Blue and pink bars overlay the area chart at the moments when balance changes are caused by buy or sell actions, so you can see at a glance which actions moved the balance and in which direction.

**Earnings** are encoded using bars positioned beneath the action markers, where red bars represent realized losses and green bars represent realized gains. The bars summarize the realized profit and loss the holder has accumulated through their trading.

A **"Show Manipulation Boxes"** switch in the Control Panel (or in the panel header, depending on the layout) overlays **red bounding boxes** on top of the action sequences that have been identified as manipulation behaviors based on the user-defined detection rules. Toggle this on whenever you want to see exactly which time windows and which action sequences the detector flagged.

Users can zoom in and out to examine behavior details across specific time periods of interest.

The point of stacking many holder timelines together is visual coordination detection. If two wallets are operated by the same person, their dots will line up vertically because they share the same actions at the same times. If wallets are independent, their dots will be scattered randomly across rows. Coordinated peak days, when many wallets traded simultaneously, show up as obvious vertical bands of dots stretching across most rows. The most undervalued use of this view is for the related-holder rows: the entity detector clusters wallets only if their balances move in lockstep, so wallets controlled by one operator with different deposit and withdrawal schedules are missed. The related-holder rows recover those missing wallets via the transfer graph, and they often expose a much larger network than the entity boundaries alone suggest.

### 4. Manipulation View (right column)

The Manipulation View shows the relationship between price dynamics and detected manipulation behaviors over time. It is a vertical stack of several layered components built around a K-line chart.

The **K-line chart** in the middle visualizes price movements under a user-selected time granularity (the running app exposes 1H, 1D, 3D, and 1W). In each interval a candlestick encodes the open, high, low, and close prices, with color indicating whether the close is higher (green, bullish) or lower (red, bearish) than the open during that period.

**Above and below the K-line chart** there are two **grey bar charts** that show, per time interval, the count of detected manipulation patterns of each type. The top bars count round-trip manipulations and the bottom bars count same-direction manipulations. Together they let you see at a glance which intervals had concentrated manipulation activity.

Time intervals in which manipulation behaviors are detected are also highlighted with a **light blue background tint** on the K-line chart itself, so the price action and the manipulation flags share the same horizontal axis.

Beyond the bar counts, the view also presents detailed views in the form of **small cards above and below the chart**. Each card describes one specific trading pattern identified in a particular time interval. Round-Trip cards above the chart and Same-Direction cards below the chart use the same internal layout as the Behavior Detail View on a smaller scale: buy and sell actions are encoded as blue and pink circles, the y-axis lists the participants in that manipulation, and the x-axis shows the sequence of actions. The card header displays the hour bin, the time range, and the total USD volume of the event, plus a truncated wallet address.

Three layers of interaction tie the K-line and the cards together. First, you can **zoom** the K-line chart in and out to navigate to specific time intervals of interest. Second, you can **scroll the card rows independently** of the K-line via horizontal scroll bars. Third, every card stays **visually linked** to its corresponding time interval on the K-line via a **light blue connection band**, so even after you scroll the cards or zoom the K-line you can still trace any card back to the candle it belongs to.

### Coin selector

In the top-right corner of the page is a small pair of radio buttons labeled ACT and PNUT. Switching between them changes the data source for the entire dashboard. ACT shows around 51 active top holders at the default snapshot, with seven round-trip and seventy same-direction events. PNUT shows around 191 active top holders, a much busier graph. Note that switching coins clears the manipulation results, so you will need to click both Run Detection buttons again to repopulate them.

## Detection rule reference

The defaults baked into the running app are reproduced below for convenience. These match the rule tables in the paper.

### Network-based detection rules

| Rule | What it checks | Key parameters |
|---|---|---|
| Direct transfer | Reciprocal transfers between an address pair | min_tx_count (entity: 3, link: 1), min_tx_volume |
| Funding relation | Whether addresses share the same first funding source | Enabled for entity, disabled for link |
| Same sender / recipient | Whether multiple addresses share a common counterparty | Toggle only |

### Similarity-based detection rules

| Rule | Method | Key parameters |
|---|---|---|
| Trading action seq. | Contiguous subsequence matching on trade events | type (entity: action+amt+price; link: action only), max_time_diff (entity: 20 min; link: 120 min) |
| Balance seq. | Pearson correlation on resampled balance histories | similarity_threshold (entity: 0.6, link: 0.7) |
| Earning seq. | Pearson correlation on resampled PnL curves | similarity_threshold (entity: 0.8, link: 0.7) |

### Manipulation detection parameters

| Parameter | Round-trip | Same-direction |
|---|---|---|
| Purpose | Flag buy-sell subsequences where net position returns to roughly zero with negligible profit (wash-trading signal) | Flag stretches of consecutive same-direction trades that may indicate coordinated accumulation or distribution |
| max_time_diff | 120 min | 10 min |
| max_pos_diff | 100 tokens | not used |
| max_earning | 1000 USD | not used |
| min_seq_len | not used | 5 trades |
| max_diff_dir | not used | 0 (no opposing trades allowed) |
| entity_based | true | true |

A note on the relationship between entity detection and manipulation detection: when entity_based is enabled for either manipulation rule, trades from all wallets inside an entity are merged before the rule runs. This is the mechanism by which coordinated activity that would be invisible across separate wallets becomes detectable. In the running ACT example, three of the top holders are merged into a single entity, and entity-level round-trip detection then surfaces a wash-trading window that spans the merged wallets.

## Recommended workflow

The most productive way to use ManiScope follows a consistent ten-step rhythm.

1. Pick a snapshot time that is likely to be interesting. Snapshots near the end of a price move are usually the most informative because they let you see who held what at the climax of the rally or crash.
2. Set the Top Holders Threshold to capture the population you care about. The default of 0.3 is a good starting point.
3. Click Update Snapshot and wait a few seconds for the Token Distribution View to render.
4. Run the detection algorithms by clicking the orange Run Detection button under Entity Detection, then Update Links for link detection, then Run Detection under Manipulation Detection.
5. Visually scan the Token Distribution View and form a rough impression of the red-versus-blue ratio. Note where the orange dashed entity boundaries cluster, and which related holders are connected back to them by orange dashed links.
6. Click the largest red-stroked node. This is usually the heaviest manipulator, and it gives you the richest Behavior Detail View to start with.
7. In the Behavior Detail View, look at all three aspects (actions, balance, earnings) together, and toggle Show Manipulation Boxes so that the red bounding boxes are visible on top of the action dots.
8. Look for vertical alignment in the Behavior Detail View timeline. If multiple rows have dots clustered in the same time bands, those wallets traded in coordination.
9. Match those time windows against the K-line in the Manipulation View on the right. The light blue background tints on the K-line and the grey count bars above and below it tell you which intervals had heavy manipulation activity. Use the light blue connection bands to follow specific cards down to their candles, and ask whether the price responded to the coordinated bursts. Did it pump, dump, or stabilize?
10. Use the manipulation cards above and below the K-line as shortcuts to interesting moments. Each card is a pre-found event that you can verify against the chart.

## Things that are not obvious from the UI

Several quirks of ManiScope are worth knowing in advance.

The frontend automatically fetches manipulation results when the page first loads for the default snapshot. You can use those results immediately without clicking anything. However, switching coins clears the cached manipulation results, so a coin switch must always be followed by re-running the detection algorithms.

The entity detector under-clusters by default. It relies on hourly balance correlation as one of its strictest signals, which means wallets that are controlled by one operator but with different deposit and withdrawal schedules will not be grouped into an entity. The right way to compensate is to always click into a flagged member after running entity detection, then read the related-holder rows in the Behavior Detail View. Those rows are where the rest of the network typically becomes visible. Lowering the link detection thresholds can also pull more relationships into the grey-link layer of the Token Distribution View.

The Same-Direction detection includes single-wallet rapid bursts, not just multi-wallet coordinated dumps. A single wallet doing five identically-sized buys in 60 seconds will produce a Same-Direction card just like three different wallets dumping together in the same window. This means that bot-like algorithmic trading and genuine coordinated manipulation both end up in the bottom card row, and you should not assume that "70 same-direction cards" means "70 distinct coordinated groups".

The light blue connection bands on the Manipulation View are visually subtle. They are nevertheless the only visual element that links a card to a specific time region on the price chart, so it is worth training your eye to follow them.

Snapshot time matters more than it might seem. Choosing a snapshot at peak price gives you a different population of top holders than choosing one during the slow decline that follows, because some wallets exit the top-holder cohort between the two timestamps. If you want to see who entered and exited the network around a manipulation peak, try several snapshot times and compare the results.

The dashboard does not currently surface wallet labels. The underlying data has labels in `simplified_owner_labels.json` that distinguish exchange wallets, contract wallets, and human wallets, but those labels are not yet shown in the UI. Knowing whether a "top holder" is in fact a centralized exchange deposit address would change the interpretation of many flagged events, so this is a useful future enhancement to keep in mind.

## What is described in the paper but not yet in the running app

The paper describes an LLM-assisted layer on top of the visual analytics system, designed to reduce the manual effort of using the dashboard. The visual half is what is currently exposed in the running frontend; the LLM-assisted half is the planned roadmap. For reference, the paper outlines four LLM-driven features: (1) onboarding, where the LLM walks the user through the system, the views, and the visual encodings, then helps form insights from individual or multiple views; (2) automatic insight discovery, where the LLM explores the data and surfaces insights either based on user instructions or unprompted, reducing the amount of repetitive manual exploration; (3) insight annotation and customized auto-exploration, where the user annotates insights based on personal preference and the system uses those annotations to drive further automatic exploration; and (4) summary and report generation, where the LLM assembles the final insights into a structured report. None of these features is wired into the current frontend, so this manual covers only the visual analytics surface.
