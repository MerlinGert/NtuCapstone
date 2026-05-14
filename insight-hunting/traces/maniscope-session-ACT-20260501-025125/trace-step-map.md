# Trace Step Map

## Raw Action Map

| Action | Type | Source -> Target | Reasoning Role | Main Evidence |
|---:|---|---|---|---|
| 0 | `update_snapshot` | `control_panel` -> `all_views` | Update ACT snapshot at 2024-11-09 23:00 UTC and rerun detections | images/action-0001-target-kline_chart-01.png, images/action-0001-target-token_distribution-02.png |
| 1 | `toggle_show_links` | `token_distribution` -> `token_distribution` | Toggle Token Distribution links off | no exported screenshot |
| 2 | `toggle_show_links` | `token_distribution` -> `token_distribution` | Toggle Token Distribution links on | images/action-0003-source-token_distribution-01.png |
| 3 | `select_user_from_network` | `token_distribution` -> `behavior_details` | Select holder 6Z6 from Token Distribution | images/action-0004-source-token_distribution-01.png, images/action-0004-target-behavior_details-01.png |
| 4 | `select_user_from_network` | `token_distribution` -> `behavior_details` | Select holder CqW from Token Distribution | images/action-0005-source-token_distribution-01.png, images/action-0005-target-behavior_details-01.png |
| 5 | `zoom_behavior_chart` | `behavior_details` -> `behavior_details` | Zoom Behavior Details for CqW into the Oct. 26-27 window | no exported screenshot |
| 6 | `toggle_sequential_time` | `behavior_details` -> `behavior_details` | Toggle Sequential Time on for CqW behavior review | images/action-0007-source-behavior_details-01.png |
| 7 | `select_user_from_network` | `token_distribution` -> `behavior_details` | Select holder DNL from Token Distribution | images/action-0008-source-token_distribution-01.png, images/action-0008-target-behavior_details-01.png |
| 8 | `toggle_show_related_users` | `behavior_details` -> `behavior_details` | Show related users for DNL in Behavior Details | images/action-0009-source-behavior_details-01.png |
| 9 | `select_user_from_behavior_details` | `system` -> `system` | Select DmJ from Behavior Details | no exported screenshot |
| 10 | `toggle_show_related_users` | `behavior_details` -> `behavior_details` | Show related users for DmJ in Behavior Details | images/action-0011-source-behavior_details-01.png |
| 11 | `hover_behavior_user_label` | `behavior_details` -> `behavior_details` | Hover DmJ user label in Behavior Details | no exported screenshot |
| 12 | `scroll_manipulation_cards` | `kline_chart` -> `kline_chart` | Scroll same-direction manipulation cards to Oct. 25-27 | no exported screenshot |
| 13 | `click_manipulation_card` | `kline_chart` -> `behavior_details` | Click same-direction card with 9 card users | images/action-0014-source-kline_chart-01.png, images/action-0014-target-behavior_details-01.png |
| 14 | `scroll_manipulation_cards` | `kline_chart` -> `kline_chart` | Scroll same-direction cards after the 9-user card click | no exported screenshot |
| 15 | `toggle_sequential_time` | `behavior_details` -> `behavior_details` | Toggle Sequential Time off for the 9-user card users | images/action-0016-source-behavior_details-01.png |
| 16 | `click_manipulation_card` | `kline_chart` -> `behavior_details` | Click second same-direction card with 9 card users | images/action-0017-source-kline_chart-01.png, images/action-0017-target-behavior_details-01.png |
| 17 | `scroll_manipulation_cards` | `kline_chart` -> `kline_chart` | Scroll same-direction cards after the second 9-user card click | no exported screenshot |
| 18 | `toggle_sequential_time` | `behavior_details` -> `behavior_details` | Toggle Sequential Time on for second 9-user card users | images/action-0019-source-behavior_details-01.png |
| 19 | `zoom_behavior_chart` | `behavior_details` -> `behavior_details` | Zoom sequential Behavior Details for second 9-user card users | no exported screenshot |
| 20 | `zoom_behavior_chart` | `behavior_details` -> `behavior_details` | Zoom sequential Behavior Details again for second 9-user card users | no exported screenshot |
| 21 | `click_manipulation_card` | `kline_chart` -> `behavior_details` | Click same-direction card with 3 card users | images/action-0022-source-kline_chart-01.png, images/action-0022-target-behavior_details-01.png |
| 22 | `scroll_manipulation_cards` | `kline_chart` -> `kline_chart` | Scroll same-direction cards after the 3-user card click | no exported screenshot |
| 23 | `export_session` | `system` -> `system` | Export the session with snapshots included | no exported screenshot |


## Annotation Map

| Annotation | Source | Reasoning Output | Linked Graph Node |
|---:|---|---|---|
| 0 | `token_distribution` | Approximately 51 users hold 30% of the token supply, which is highly centralized. Most are marked with red circles, indicating prior suspicious behavior. | `F0` |
| 1 | `token_distribution` | Several large, dark-colored nodes are grouped by three orange dashed circles, representing entities detected by the system's rules. These three entities collectively hold substantial funds. Notably, each entity contains at least one account that appears normal alongside several suspicious ones, likely an intentional strategy to maintain a "clean-looking" account. | `F1` |
| 2 | `token_distribution` | Two of the three entities, along with several other holders, are connected within a single component (community). This token carries a high manipulation risk and creates a poor initial impression. | `F2` |
| 3 | `system` | A small number of whales control the vast majority of the circulating supply, while retail holders occupy only peripheral positions. | `IN3` |
| 4 | `token_distribution` | Top holder 6z6 holds 10M tokens but shows no manipulative behavior. | `F4` |
| 5 | `behavior_details` | A whale, but not a manipulator, because tokens were acquired through transfers. | `F5` |
| 6 | `token_distribution` | Same-direction manipulation detected, but no entity affiliation. | `F6` |
| 7 | `behavior_details` | The holder progressively accumulates tokens; four purchases within a short window triggered a same-direction ramp detection. Upon closer review, this appears to be a normal holder | `F7` |
| 8 | `token_distribution` | Located within the flagged component. Frequently buys and transfers out tokens, and appears to be a functional account serving an entity. | `F8` |
| 9 | `behavior_details` | Direct transfers to another seemingly normal account are observed, likely used to avoid detection. | `F9` |
| 10 | `behavior_details` | Another address bought a similar amount during the same period; the user investigated whether this affected the price and confirmed that it did. | `F10` |
| 11 | `candlestick_chart` | This clearly affected the price. | `F11` |
| 12 | `behavior_details` | Oct 26, within 32 minutes: 26.17M tokens traded in the same direction. After DMj's sell, 9 addresses buy frequently in the same direction. | `F12` |
| 13 | `behavior_details` | Same-direction trading alternates between buys and sells (round-trip pattern). | `F13` |
| 14 | `behavior_details` | visual annotation without text | `F14` |
| 15 | `behavior_details` | Three addresses fall within the same connected component. | `F15` |
| 16 | `system` | These addresses are also part of the same component, forming a large colluding group. | `IN16` |
| 17 | `token_distribution` | Most of these addresses belong to the identified component. | `F17` |


## Reasoning Threads

| Thread | User Path | Findings/Insights | Follow-up Branch |
|---|---|---|---|
| Supply and component risk | Actions 0-2; annotations 0-3 | `F0`, `F1`, `F2`, `IN3` support `H1` | `RS2` verifies entity/link/direct-transfer basis |
| Wallet role differentiation | Actions 3-11; annotations 4-10 | `F4` through `F10` support `H2` | `RS3` expands role differentiation with A16/A21 data |
| Oct. 26-27 same-direction coordination | Actions 12-23; annotations 12-19 | `F11` through `F17` and `IN16` support `H3` | `RS1`, `RS2`, `RS3` quantify, render, and refine the claim |

## Artifact Links

- Canonical graph: `reasoning-graph.json`
- User forest: `user-reasoning-forest.md`
- Recommendation plan graph: `recommendation-plan-graph.json`
- Recommendation plan forest: `recommendation-plan-forest.md`
- Follow-up report: `continued-investigation-report.md`
- Graph patch: `reasoning-graph-patch-001.json`
- Augmented forest: `augmented-reasoning-forest.md`
