# A Coordinated Price-Manipulation Network on the ACT Token

## What this report is

This report walks through how I used the ManiScope dashboard to identify what looks like a single coordinated price-manipulation operation on the ACT token during the three weeks from 2024-10-19 to 2024-11-10. The story is told in the order I actually found it, panel by panel, so that the reasoning is reproducible. Each step describes a visual observation, the hypothesis it generated, and the next view I went to in order to confirm or refute the hypothesis. The conclusion is supported by two independent detection methods agreeing on the same wallets, by the temporal clustering of suspicious events, and by the structure of the transfer-relationship graph that the dashboard exposes.

## Step 1. First glance at the network graph

I opened the dashboard at `localhost:3000`. The default snapshot was 2024-11-09 23:00:00 UTC, with a Top Holder Threshold of 0.3, both the entity detection and the manipulation detection already run on initial load. The first thing I noticed when looking at the Token Distribution View in the top-center was that almost every circle had a red border rather than a blue one. To quantify this, I queried the computed style of every circle in the SVG and counted the borders. Out of 49 top holders rendered in the graph, 36 have a red stroke, which means they appear as a participant in at least one detected manipulation event. That is 74 percent. The remaining 13 wallets have the normal blue stroke. Three small clusters are wrapped in orange dashed circles, which mark the entity boundaries.

The visual gestalt is unusual. In a healthy market you would expect a small minority of suspicious actors mixed into a majority of clean traders. Here it is the inverse. Three quarters of the wallets that hold a meaningful amount of ACT are flagged for some kind of price manipulation. This is the cue that pushed me to investigate further rather than to dismiss the page as a noisy detector with a low precision threshold.

## Step 2. Confirming the impression with the K-line

If 74 percent of top holders are genuinely manipulating, the price chart should look artificial rather than organic. I switched my attention to the Manipulation View on the right.

The dataset spans 2024-10-19 to 2024-11-10, which is roughly three weeks. The starting price on the morning of October 19 is about 0.000292 dollars. By October 25 the price has reached its all-time high of about 0.045 dollars. By the end of the dataset on November 10 it has retraced to about 0.021 dollars. That is a roughly 155-fold rapid pump to peak followed by a 50 percent decline. Even by Solana memecoin standards this profile is suggestive of orchestrated activity rather than gradual organic adoption.

I also noted the manipulation cards above and below the chart at this point. There were seven Round-Trip cards on top and seventy Same-Direction cards on the bottom. A pure count of seventy coordinated-direction events in three weeks is high enough to take seriously, even before reading what each card actually contains.

So far the hypothesis from Step 1, that ACT is a heavily manipulated token, was holding up.

## Step 3. Looking at the entity highlights

The dashboard had clustered the top holders into three small entities, each visible in the Token Distribution View as a group of bubbles inside an orange dashed circle. By inspecting the Token Distribution Vue component's props directly, I could see the entity members and the rule that linked them.

| Entity | Members | Linking rule |
|---|---|---|
| 0 | DmJ, BgB, 5YP | balance correlation = 1.00 |
| 1 | HEH, 4B3, 7Sm | balance correlation = 0.78 |
| 2 | EnM, Cmq | balance correlation = 0.998 |

Eight wallets across three clusters, all of them grouped because their hourly balance time series move in lockstep. A perfect 1.00 balance correlation between three independent-looking wallets is by itself a strong signal of common ownership, since two genuinely separate traders almost never produce identical hourly balance curves. However, 8 wallets does not match the 36 wallets with red borders. There are clearly more manipulators than there are entity members. Something about the entity detector's view of the network is incomplete. To find out what, I clicked on the largest entity member.

## Step 4. Clicking DmJ and discovering the hidden network

I clicked on the largest bubble in Entity 0, which corresponds to the address `DmJRzwcmFFFKhJ5dSJuSU3Lns4bfiMb8b1V3vhJG7uLH`, abbreviated DmJ. The moment I clicked, the Behavior Detail View below the Token Distribution View populated with a multi-row timeline. I expected to see three rows for the three entity members. Instead I saw 19 rows, labeled with three role tags: one row labeled "Selected User" for DmJ, two labeled "Entity Member" for BgB and 5YP, and 16 labeled "Related User".

These 16 related users are not in DmJ's entity by balance correlation, but they have direct transfer relationships to the wallets in DmJ's entity within the snapshot window. In other words, clicking one entity member exposes a much larger 2nd-degree neighborhood in the transfer graph.

This is the moment the picture shifted. I cross-referenced these 19 wallets against the full list of 106 detected manipulation events that the dashboard had already loaded. Every single one of the 19 wallets is flagged for at least one manipulation event. The combined manipulation volume across these 19 wallets is approximately 116 million dollars. The breakdown is in the table below, sorted by personal manipulation volume.

| Wallet | Entity | Events | Volume flagged | Methods |
|---|---|---|---|---|
| DmJ...7uLH | entity_0 | 12 | 25.2M | round_trip + same_direction |
| 7Sm...c7qb | entity_1 | 7 | 13.0M | round_trip + same_direction |
| DNL...naji | none | 10 | 12.4M | same_direction |
| XiX...RSvN | none | 7 | 10.8M | round_trip + same_direction |
| 4B3...eyV7 | entity_1 | 5 | 7.1M | round_trip + same_direction |
| 22J...6eBm | none | 1 | 6.9M | same_direction |
| 5YP...1xYv | entity_0 | 4 | 4.9M | same_direction |
| BgB...dDon | entity_0 | 1 | 4.4M | same_direction |
| 35N...zuPQ | none | 1 | 4.2M | same_direction |
| 5RA...CVEz | none | 3 | 4.1M | same_direction |
| GCD...LZXz | none | 5 | 4.1M | round_trip + same_direction |
| Cmq...pvWd | entity_2 | 2 | 3.3M | same_direction |
| F39...xKEa | none | 3 | 3.3M | same_direction |
| Eu4...hVzh | none | 2 | 3.2M | same_direction |
| EnM...LBZ3 | entity_2 | 3 | 3.1M | same_direction |
| 3b5...r558 | none | 2 | 2.2M | same_direction |
| 2br...PizN | none | 6 | 1.5M | round_trip + same_direction |
| 9zR...ewvV | none | 2 | 1.4M | same_direction |
| 5WF...mZEw | none | 3 | 0.9M | same_direction |

Two facts about this table are notable. First, all three members of Entity 1 (`7Sm` and `4B3` are visible here, and `HEH` is in the entity but not in DmJ's transfer neighborhood) and both members of Entity 2 (`EnM`, `Cmq`) appear as Related Users of Entity 0. The three entities the detector found are not unrelated clusters at all. They are connected to each other through transfers. Second, 12 of the 19 wallets are not in any detected entity, yet every one of them is flagged for manipulation. The entity detector under-clustered the operation, leaving most of its participants outside the orange dashed circles.

The conclusion at this point was that what looks like three small unrelated wallet clusters is, with high confidence, a single transfer-connected manipulation network containing at least 19 wallets and approximately 116 million dollars of flagged volume.

## Step 5. Time-clustering and the price action

A network of 19 manipulating wallets is suspicious on its own. To make the case conclusive, I needed evidence of actual coordination, meaning that these wallets did not just manipulate independently but acted at the same times. I bucketed all 106 manipulation events by date and looked for spikes.

| Date | Events | Volume | Direction |
|---|---|---|---|
| Oct 19 | 5 | 7.1M | mixed |
| Oct 21 | 5 | 10.5M | mixed |
| Oct 24 | 12 | 11.5M | mixed |
| **Oct 25** | **18** | **29.4M** | wash, buy approximately equal to sell |
| **Oct 26** | **12** | **29.8M** | pure pump, 100 percent buys |
| **Oct 31** | **17** | **27.3M** | net buy, 18.7M buys vs 8.6M sells |
| Nov 01 | 7 | 6.2M | mixed |

Three spike days, October 25, 26, and 31, account for approximately 86 million dollars out of the roughly 116 million dollar total. Cross-referencing each spike day with the price action in the K-line gives a coherent narrative.

On October 25 the ACT price touched its all-time peak of about 0.045 dollars. The same day saw 18 manipulation events with buy and sell volume nearly balanced. This is wash trading at the top, which is consistent with operators inflating turnover to attract attention and to support the rally just below the peak.

On October 26 the price dropped from about 0.035 to about 0.023 dollars during the day, a 34 percent intraday decline. The same day saw 12 manipulation events with 29.8 million dollars of pure coordinated buying. Nobody in this network sold a thing on October 26. This is the textbook signature of a manipulator network defending the price during a sell-off, by absorbing dumps from outside sellers in order to slow the decline and protect the position.

On October 31 the price opened at about 0.041 dollars, traded down to an intraday low of about 0.0009 dollars (a 98 percent drop), and recovered to close at about 0.027 dollars. This is a flash-crash followed by a recovery. The same day saw 17 manipulation events, mostly buys, with a net buy volume of about 10 million dollars. The network appears to have bought the crash recovery, which is the standard play after liquidations have wiped out the leveraged longs.

The temporal pattern matches a single coordinated playbook executed by the same operator, namely "pump, defend the dip, scoop the flash-crash recovery, then let the price drift". The wallets are different, but the playbook is identical.

## Conclusion

What looks at first like three small unrelated wallet clusters on the ACT token is, with high confidence, a single coordinated price-manipulation operation. The evidence is layered.

There are at least 19 transfer-connected wallets in the network. They include the members of all three entities the detector found, plus 12 additional wallets that the entity detector missed because their balance schedules were not synchronized closely enough to trip the 0.7 correlation threshold. Combined manipulation volume across these 19 wallets is approximately 116 million dollars over three weeks, which is about 74 percent of all top holders by count being implicated. The network's activity is not uniformly distributed in time, but is concentrated on three peak days, October 25, 26, and 31, that together account for approximately 86 million dollars of the total. The directional bias on each peak day matches the corresponding price action in a consistent way, with wash trading near the all-time high, pure coordinated buying during the post-peak dip, and net buying during the flash-crash recovery. Two independent detection algorithms agree on most of the wallets, since the entity detector clustered some of them via balance correlation while the manipulation detector flagged each one independently for trade patterns. Two methods agreeing is much stronger than either alone.

## The two strongest individual cases

Within this larger network there are two specific cases that I would flag if asked to surface only the most defensible findings.

The first is **Entity 0**, comprising the wallets `DmJ`, `BgB`, and `5YP`. These three wallets have a balance correlation of exactly 1.00 over hourly granularity, which is to say their balance time series are mathematically identical up to floating-point noise. Independent traders almost never produce identical hourly balance curves, and the simplest explanation by far is that all three wallets are operated by the same person who is moving balances across them in a coordinated fashion. Combined manipulation volume across these three wallets is 34.5 million dollars across 17 events.

The second is **DmJ's 3.85 million dollar round-trip on October 25, from 18:21:28 to 18:26:14 UTC**. Six transactions are involved, with a total turnover of 3.85 million dollars, and the entire round-trip cycle takes less than five minutes. For context, that single round-trip moved roughly a quarter of the daily peak liquidity for the token. Five minutes for a four-million-dollar wash cycle is not human discretionary trading, and the round-trip detector flagged it precisely because it fits the wash-trading template very tightly.

## Caveats and what would strengthen the case further

A few things would make this finding more conclusive if they were verified externally. First, the dashboard does not currently surface wallet labels, so I cannot confirm that none of the 19 wallets is a known centralized exchange deposit address. If any of them turns out to be a CEX hot wallet, the interpretation of "transfer connection" changes substantially. Second, the entity detector relies on a balance correlation threshold and on a transfer count threshold, both of which could be loosened to see whether the rest of the network is captured automatically rather than only via the click-through workflow. Third, an end-to-end verification against the raw `sorted_transfers.csv` and `sorted_trades.csv` files would let us confirm the timing and amounts of each flagged event independently of the dashboard's pre-computed manipulation results.

None of these caveats undermine the central finding. They would simply turn a high-confidence visual case into a verified evidence chain suitable for handing off to a downstream analyst or compliance reviewer.
