# Continued Investigation Report

## Scope

This follow-up executed every branch in `recommendation-plan-forest.md` after reconstructing the original user reasoning graph. Evidence came from local ACT data, the ManiScope render API, exported trace screenshots, and render API summaries saved under `continued-investigation-assets/`.

## Branch Status

| Branch | Status | Evidence Produced |
|---|---|---|
| `RS1` Quantify and render Oct. 26-27 clicked-card evidence | Executed | `followup-data-summary.json`, `followup-kline-oct26-oct27-1h.png`, `followup-behavior-a13-card-users.png` |
| `RS2` Verify entity, link-component, and direct-transfer evidence | Executed | `followup-render-data-summary.json`, `followup-token-distribution-links.png`, raw transfer check in `followup-data-summary.json` |
| `RS3` Test role differentiation in A16 and A21 card users | Executed | A16/A21 trade summaries in `followup-data-summary.json`, `followup-behavior-a16-card-users.png`, `followup-behavior-a21-card-users.png` |

No branch was blocked.

## Results

### RS1: Oct. 26-27 clicked-card evidence

A13 contains 9 card users in the trace. Within the user-selected Behavior Details window, 5 of those 9 users were active in raw trade data. They made 49 trades: 35 buys and 14 sells. The active users bought 9.95M ACT for $261.28K and sold 8.30M ACT for $193.63K.

The 1-minute OHLC data for the A13 window opened at 0.0300868 and closed at 0.0231492, a -23.1% close-to-open change. The same window reached a high 45.0% above the first-minute open and a low 49.8% below it. This supports the user's price-impact concern, although it also shows strong volatility in both directions.

The follow-up K-line render shows finer-grained same-direction cards in the focused Oct. 26-27 window, including card totals of 15.85M, 9.83M, and 2.51M tokens. The A13 Behavior Details render gives visual support for the row-level timing pattern, but exact counts come from raw CSV data.

### RS2: Component and relation basis

The current render API snapshot reports 49 processed top users covering 217.87M ACT, or 30.29% of user-held balance. User-held balance is 719.37M ACT, or 75.86% of the total supply. The render API returns three balance-sequence entity groups.

For the selected and clicked follow-up users, the link-derived component connects 16 of 17 users. `CqWVLX...` remains isolated. This refines the original colluding-group insight: most selected users are connected in the model-derived link graph, but not all.

Raw transfer evidence is much narrower. Among selected and clicked follow-up users, the raw transfer CSV contains one direct internal transfer: `7SmhQ9... -> Eu4DNn...`, 5.56M ACT, on Oct. 23. Therefore, the large-component claim should be described as model-link/timing evidence, not direct-transfer proof.

### RS3: Role differentiation

A16 has 377 trades by all 9 users in its broad Behavior Details window. It contains 37.93M ACT bought for $1.03M and 34.47M ACT sold for $791.03K. DmJ is the highest-frequency actor with 95 trades. DNL is a buy-heavy functional candidate. Several users show mixed buy/sell roles rather than simple same-direction accumulation.

A21 has 150 trades by 3 users. DmJ is high-frequency and net-buying in token amount, GCDE has equal token buy and sell amounts across the window, and 7Sm is net-selling in token amount. The rendered Behavior Details views support the role-differentiated interpretation.

The RS3 Hypothesis Expansion branch is therefore promoted into adjacent hypothesis `H_AGENT_1`: the larger ACT coordination group contains differentiated roles, including high-frequency buyers, net sellers, round-trip-like actors, and transfer-linked functional accounts.

## Patch Summary

`reasoning-graph-patch-001.json` adds follow-up agent interactions, findings, and one synthesized insight. The patch qualifies `IN16` and supports `H3` with exact trade totals, rendered evidence, link-component checks, and role-differentiation evidence.

`reasoning-graph-patch-002.json` promotes the executed Hypothesis Expansion branch into adjacent hypothesis root `H_AGENT_1`, supported directly by the A16/A21 statistical role finding and the A16/A21 rendered Behavior Details finding.

## Bottom Line

The follow-up supports a core coordinated-manipulation interpretation for the ACT trace, especially around the Oct. 26-27 same-direction activity. The strongest evidence is model-link/timing evidence plus exact trade/price-window data. The unresolved limitation is direct collusion proof: raw transfers among the selected users are sparse, so the report should not overstate the component as a direct-transfer cluster.
