# ManiScope User Manual

## What ManiScope is

ManiScope is a four-panel dashboard for analyzing token price-manipulation activity on Solana memecoins. It loads pre-computed datasets such as OHLC, balances, transfers, and behavior sequences for one of two tokens, ACT or PNUT. On top of those datasets it runs entity-clustering and manipulation-detection algorithms, then exposes the results through linked, interactive visualizations.

ManiScope is best understood as an investigator's tool rather than a real-time monitoring tool. It answers questions of the form "who was manipulating this token over the past few weeks, and how did they do it" rather than "is something suspicious happening right now". The expected workflow is exploratory: pick a snapshot in time, run the detectors, look for visual patterns, and drill down into individual wallets when something catches your eye.

## Screen layout

The dashboard fills the entire browser window and is divided into three columns. The left column is a narrow control panel. The middle column is split vertically into a token-holder network at the top and a behavior timeline at the bottom. The right column is a candlestick chart sandwiched between two horizontal rows of manipulation cards.

```
+----------------------------------------------------------------------+
|  ManiScope                                              o ACT  o PNUT |
+--------------+----------------------------+--------------------------+
|              | TokenDistribution          | CandlestickChart         |
|              | (token-holder bubble       | -- round-trip cards ---  |
|              |  network)                  | |   K-line + bands    |  |
|  Control     |                            | -- same-direction cards  |
|  Panel       +----------------------------+                          |
|              | BehaviorDetails            |                          |
|              | (selected user's           |                          |
|              |  multi-wallet timeline)    |                          |
+--------------+----------------------------+--------------------------+
```

## The four panels in detail

### 1. ControlPanel (left column)

The ControlPanel is the driver of the dashboard. It is divided into three sections, each with its own action button.

**Snapshot Configuration** is at the top. The Snapshot Time dropdown lets you pick any hourly timestamp from 2024-10-19 12:00 UTC onwards. Everything else in the dashboard is computed relative to this point in time, so changing it is the most consequential action you can take. Two thresholds shape the population of wallets that ends up on screen: the Top Holders Threshold (default 0.3) is the cumulative balance fraction you want to capture among user-held supply, so 0.3 means "the smallest set of top holders whose combined balance exceeds 30 percent of all user balances", and the Related User Threshold (default 0.2) is a secondary cutoff for which 2nd-degree wallets, connected via transfers but below the main threshold, count as related users. The Update Snapshot button refreshes the network graph at the chosen time.

**Entity Detection** sits below. Its orange Run Detection button triggers wallet-clustering. Two families of rules can be enabled: Network Based rules use the transfer graph and have toggles for Direct Transfer, Funding Relationship, Same Sender, and Same Recipient, plus minimum transaction count and volume thresholds; Similarity Based rules use behavior similarity, including balance correlation, earnings correlation, and trade-sequence correlation between wallets. The Similarity Based rules are typically the most powerful, since perfect balance correlation between independent-looking wallets is a strong indicator of common ownership.

**Manipulation Detection** is the third section. Its Run Detection button runs the trade-pattern detector. The Round Trip rule looks for single-wallet wash trading, with parameters for the maximum time between buy and sell, the maximum allowable position difference, and the maximum realized earning. The Same Direction rule, which appears further down the panel, looks for coordinated multi-buy or multi-sell bursts.

One detail that is not obvious from the UI: the page automatically runs both detection algorithms when it first loads, and when you change the snapshot time and click Update Snapshot. However, switching coins between ACT and PNUT clears the manipulation results, and you must click Run Detection again afterwards to repopulate them.

### 2. TokenDistribution (middle-top, the bubble graph)

TokenDistribution renders a force-directed network graph of the top holders at the selected snapshot time. Its header bar shows the snapshot time, a Scale zoom slider, and a count of how many active users are present.

Reading the graph visually relies on a small set of consistent encodings. The bubble size represents the balance held by the wallet at the snapshot time, so larger circles are larger holders. The bubble fill is a blue colormap, with darker blue for higher balance. The bubble border is the most important channel: a blue border means the wallet is currently clean, and a red border means the wallet appears as a participant in at least one detected manipulation event. Around small clusters of bubbles you may also see an orange dashed circle. Each dashed circle is one detected entity, and the wallets enclosed by it have been clustered together by the entity detector. Tiny pale circles at the periphery of the main cluster, connected back to it by thin gray lines, are related users, meaning 2nd-degree wallets that are not top holders themselves but transfer tokens to or from the top holders.

Interactions on this panel are simple. Clicking a bubble selects that wallet, populates the BehaviorDetails panel below, and visually highlights its entity if it has one. Dragging the Scale slider in the header zooms the entire graph in or out.

The first thing to look at on this panel is the ratio of red to blue borders. A small minority red is normal for any active token. A majority red is a strong cue that manipulation activity is widespread among the top holders, and is the right place to begin a deeper investigation.

### 3. BehaviorDetails (middle-bottom, the multi-row timeline)

BehaviorDetails populates only after you click a node in the bubble graph. Once activated it shows a stacked timeline of every wallet that is in scope for the selected user. That includes the user themselves, every other member of the user's entity, and every related user that has a transfer connection to the entity.

Each row of the panel is one wallet, labeled with a 3-character prefix and a role tag of "Selected User", "Entity Member", or "Related User". The horizontal axis is time, with date ticks of the form Mon 21, Wed 23, and so on. The dots scattered along each row are individual trade actions for that wallet, color-coded by action type so that buys, sells, and transfers can be told apart at a glance. A "Show Manipulation Boxes" checkbox at the top of the panel overlays colored rectangles on the time windows where the system detected a manipulation event for that wallet.

The point of stacking many wallet timelines together is visual coordination detection. If two wallets are operated by the same person, their dots will line up vertically because they share the same actions at the same times. If wallets are independent, their dots will be scattered randomly across rows. Coordinated peak days, when many wallets traded simultaneously, show up as obvious vertical bands of dots stretching across most rows.

The most undervalued feature of BehaviorDetails is the "Related User" rows. The entity detector clusters wallets only if their balances move in lockstep, so wallets controlled by one operator with different deposit and withdrawal schedules are missed. The related-user rows recover those missing wallets via the transfer graph, and they often expose a much larger network than the entity boundaries alone suggest.

### 4. CandlestickChart (right column, K-line plus manipulation cards)

CandlestickChart is a vertical stack of three sections. At the top is a horizontal row of small Round-Trip cards, in the middle is the main K-line, and at the bottom is a second horizontal row of Same-Direction cards. The two card rows scroll horizontally if there are more events than fit.

Each Round-Trip card represents one detected wash-trading event by a single wallet. The card shows the hour bin that the event falls into (such as 10/26 02:00), the exact time range and total USD volume of the round-trip, a truncated wallet address, and a miniature timeline that displays the buy and sell sequence as colored dots. Same-Direction cards have the same shape but represent coordinated multi-buy or multi-sell bursts rather than round trips. In the default ACT snapshot the round trips number around seven and the same-direction events number around seventy.

The main K-line is a standard candlestick chart of OHLC data for the selected coin. Green candles are bullish (close above open) and red candles are bearish. The granularity buttons in the top right corner switch the bin size between 1H, 1D, 3D, and 1W.

A subtle but useful overlay connects the two card rows to the K-line. Each card is linked to its time region on the price chart by a soft blue band that runs from the card down (or up) into the K-line area. By scanning vertically you can see exactly which candle a manipulation card belongs to, which is the most efficient way to correlate a flagged event with the price action that resulted from it.

### Coin selector

In the top-right corner of the page is a small pair of radio buttons labeled ACT and PNUT. Switching between them changes the data source for the entire dashboard. ACT shows around 51 active top holders at the default snapshot, with seven round-trip and seventy same-direction events. PNUT shows around 191 active top holders, a much busier graph. Note that switching coins clears the manipulation results, so you will need to click both Run Detection buttons again to repopulate them.

## Recommended workflow

The most productive way to use ManiScope follows a consistent ten-step rhythm.

1. Pick a snapshot time that is likely to be interesting. Snapshots near the end of a price move are usually the most informative because they let you see who held what at the climax of the rally or crash.
2. Set the Top Holders Threshold to capture the population you care about. The default of 0.3 is a good starting point.
3. Click Update Snapshot and wait a few seconds for the network graph to render.
4. Run both detection algorithms by clicking the orange Run Detection button under Entity Detection and then the one under Manipulation Detection.
5. Visually scan the TokenDistribution graph and form a rough impression of the red-versus-blue ratio. Note where the orange dashed entity boundaries cluster.
6. Click the largest red-bordered bubble. This is usually the heaviest manipulator, and it gives you the richest BehaviorDetails view to start with.
7. Toggle the "Show Manipulation Boxes" checkbox in BehaviorDetails so that the manipulation windows are visible on top of the action dots.
8. Look for vertical alignment in the BehaviorDetails timeline. If multiple rows have dots clustered in the same time bands, those wallets traded in coordination.
9. Match those time windows against the K-line on the right. Use the soft blue bands that connect the cards to specific candles, and ask whether the price responded to the coordinated bursts. Did it pump, dump, or stabilize?
10. Use the manipulation cards above and below the K-line as shortcuts to interesting moments. Each card is a pre-found event that you can verify against the chart.

## Things that are not obvious from the UI

Several quirks of ManiScope are worth knowing in advance.

The frontend automatically fetches manipulation results when the page first loads for the default snapshot. You can use those results immediately without clicking anything. However, switching coins clears the cached manipulation results, so a coin switch must always be followed by re-running both detection algorithms.

The entity detector under-clusters by default. It relies on hourly balance correlation, which means wallets that are controlled by one operator but with different deposit and withdrawal schedules will not be grouped. The right way to compensate is to always click into a flagged member after running entity detection, then read the Related User rows in BehaviorDetails. Those rows are where the rest of the network typically becomes visible.

The Same-Direction detection includes single-wallet rapid bursts, not just multi-wallet coordinated dumps. A single wallet doing five identically-sized buys in 60 seconds will produce a Same-Direction card just like three different wallets dumping together in the same window. This means that bot-like algorithmic trading and genuine coordinated manipulation both end up in the bottom card row, and you should not assume that "70 same-direction cards" means "70 distinct coordinated groups".

The K-line manipulation bands are visually subtle, drawn in a light blue tint. They are nevertheless the only visual element that links a card to a specific time region on the price chart, so it is worth training your eye to follow them.

Snapshot time matters more than it might seem. Choosing a snapshot at peak price gives you a different population of top holders than choosing one during the slow decline that follows, because some wallets exit the top-holder cohort between the two timestamps. If you want to see who entered and exited the network around a manipulation peak, try several snapshot times and compare the results.

Finally, the dashboard does not currently surface wallet labels. The underlying data has labels in `simplified_owner_labels.json` that distinguish exchange wallets, contract wallets, and human wallets, but those labels are not yet shown in the UI. Knowing whether a "top holder" is in fact a centralized exchange deposit address would change the interpretation of many flagged events, so this is a useful future enhancement to keep in mind.
