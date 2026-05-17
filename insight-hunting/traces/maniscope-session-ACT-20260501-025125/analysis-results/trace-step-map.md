# Trace Step Map

Trace: `maniscope-session-ACT-20260501-025125`

## Compact Analytical Steps

| Step | Evidence | Intention mapping | Finding mapping | Interpretation |
| --- | --- | --- | --- | --- |
| S1 | A0-A2, Ann0-Ann3 | T1, AQ1, H1 | F1, F2, INS1 | User establishes holder centralization, suspicious styling, entity boundaries, and connected-component risk. |
| S2 | A3, Ann4-Ann5 | T2, AQ2, H2 | F3 | User checks whether the biggest visible holder is actually suspicious and records it as storage-like. |
| S3 | A4-A6, Ann6-Ann7 | T2, AQ2, H2 | F4 | User tests a flagged or nearby holder and records CqW as progressive accumulation rather than obvious manipulation. |
| S4 | A7-A11, Ann8-Ann10 | T2, AQ2, H2 | F5, INS2 | User explores DNL, DmJ, related users, and transfer-like behavior to identify functional accounts. |
| S5 | A12-A15, Ann12-Ann13 | T3, AQ3, H3 | F6, F7 | User moves from K-line card browsing to the A13 9-user Behavior Details cohort and marks price relevance. |
| S6 | A16-A20, Ann14-Ann15 | T3, AQ3, H3 | F8 | User examines the A16 9-user card and toggles time mode to inspect alternating buy/sell sequences. |
| S7 | A21-A23, Ann17-Ann19 | T3, AQ3, H3 | F9, INS3 | User inspects the A21 3-user card, then synthesizes the larger colluding-component insight and exports the trace. |
| S8 | Follow-up RI_RS1-RI_RS4 | Plan branches RS1-RS4 | F_AGENT_1 to H_AGENT_1 | Agent executes data and render validation, promotes the A21 adjacent hypothesis, and patches the graph. |

## Raw Action Map

| A# | Timestamp | Action type | Source | Target | Trace interpretation | Salience |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 2026-04-30T18:16:24.043Z | update_snapshot | control_panel | all_views | Update ACT snapshot with default thresholds | primary |
| 1 | 2026-04-30T18:16:28.076Z | toggle_show_links | token_distribution | token_distribution | Hide Token Distribution links | supporting |
| 2 | 2026-04-30T18:17:21.453Z | toggle_show_links | token_distribution | token_distribution | Show Token Distribution links | supporting |
| 3 | 2026-04-30T18:19:48.720Z | select_user_from_network | token_distribution | behavior_details | Select top holder 6Z6 in Token Distribution | primary |
| 4 | 2026-04-30T18:21:07.947Z | select_user_from_network | token_distribution | behavior_details | Select CqW in Token Distribution | primary |
| 5 | 2026-04-30T18:21:22.515Z | zoom_behavior_chart | behavior_details | behavior_details | Zoom CqW Behavior Details window | supporting |
| 6 | 2026-04-30T18:21:26.995Z | toggle_sequential_time | behavior_details | behavior_details | Toggle CqW Behavior Details to sequential time | supporting |
| 7 | 2026-04-30T18:22:33.088Z | select_user_from_network | token_distribution | behavior_details | Select DNL in Token Distribution | primary |
| 8 | 2026-04-30T18:22:39.570Z | toggle_show_related_users | behavior_details | behavior_details | Show related users for DNL | supporting |
| 9 | 2026-04-30T18:27:26.828Z | select_user_from_behavior_details | system | system | Select DmJ from Behavior Details | primary |
| 10 | 2026-04-30T18:27:28.204Z | toggle_show_related_users | behavior_details | behavior_details | Show related users for DmJ | supporting |
| 11 | 2026-04-30T18:27:26.484Z | hover_behavior_user_label | behavior_details | behavior_details | Hover DmJ Behavior Details label | low |
| 12 | 2026-04-30T18:42:39.970Z | scroll_manipulation_cards | kline_chart | kline_chart | Scroll same-direction manipulation cards | supporting |
| 13 | 2026-04-30T18:42:58.336Z | click_manipulation_card | kline_chart | behavior_details | Click 9-user same-direction card around A13 | primary |
| 14 | 2026-04-30T18:42:58.738Z | scroll_manipulation_cards | kline_chart | kline_chart | Scroll manipulation cards after A13 | supporting |
| 15 | 2026-04-30T18:43:20.145Z | toggle_sequential_time | behavior_details | behavior_details | Switch A13 cohort Behavior Details to absolute time | primary |
| 16 | 2026-04-30T18:44:25.011Z | click_manipulation_card | kline_chart | behavior_details | Click 9-user manipulation card around A16 | primary |
| 17 | 2026-04-30T18:44:25.410Z | scroll_manipulation_cards | kline_chart | kline_chart | Scroll manipulation cards after A16 | supporting |
| 18 | 2026-04-30T18:45:41.274Z | toggle_sequential_time | behavior_details | behavior_details | Switch A16 cohort Behavior Details to sequential time | primary |
| 19 | 2026-04-30T18:45:50.830Z | zoom_behavior_chart | behavior_details | behavior_details | Zoom A16 sequential Behavior Details to later events | primary |
| 20 | 2026-04-30T18:45:56.961Z | zoom_behavior_chart | behavior_details | behavior_details | Zoom A16 sequential Behavior Details to earlier events | primary |
| 21 | 2026-04-30T18:47:25.267Z | click_manipulation_card | kline_chart | behavior_details | Click 3-user round-trip card around A21 | primary |
| 22 | 2026-04-30T18:47:25.585Z | scroll_manipulation_cards | kline_chart | kline_chart | Scroll manipulation cards near A21 | supporting |
| 23 | 2026-04-30T18:51:00.051Z | export_session | system | system | Export ACT trace session | low |

## Annotation Map

| Ann | Timestamp | View | Insight | Text | Image |
| --- | --- | --- | --- | --- | --- |
| 0 | 2026-04-30T18:17:05.017Z | token_distribution | no | Approximately 51 users hold 30% of the token supply - highly centralized. Most are marked with red circles, indicating prior suspicious behavior. | ../images/annotation-0000-token_distribution.png |
| 1 | 2026-04-30T18:17:44.271Z | token_distribution | no | Several large, dark-colored nodes are grouped by three orange dashed circles, representing entities detected by the system's rules. These three entities collectively hold substanti | ../images/annotation-0001-token_distribution.png |
| 2 | 2026-04-30T18:18:30.110Z | token_distribution | no | Two of the three entities, along with several other holders, are connected within a single component (community). This token carries a high manipulation risk - a poor initial impre | ../images/annotation-0002-token_distribution.png |
| 3 | 2026-04-30T18:19:04.639Z | system | yes | A small number of whales control the vast majority of the circulating supply, while retail holders occupy only peripheral positions. |  |
| 4 | 2026-04-30T18:19:42.163Z | token_distribution | no | Top holder 6z6 holds 10M tokens but shows no manipulative behavior. | ../images/annotation-0004-token_distribution.png |
| 5 | 2026-04-30T18:20:09.593Z | behavior_details | no | A whale, but not a manipulator - tokens were acquired through transfers. | ../images/annotation-0005-behavior_details.png |
| 6 | 2026-04-30T18:21:03.711Z | token_distribution | no | Same-direction manipulation detected, but no entity affiliation. | ../images/annotation-0006-token_distribution.png |
| 7 | 2026-04-30T18:21:38.892Z | behavior_details | no | The holder progressively accumulates tokens; four purchases within a short window triggered a same-direction ramp detection. Upon closer review, this appears to be a normal holder | ../images/annotation-0007-behavior_details.png |
| 8 | 2026-04-30T18:22:26.669Z | token_distribution | no | Located within the flagged component. Frequently buys and transfers out tokens - appears to be a functional account serving an entity. | ../images/annotation-0008-token_distribution.png |
| 9 | 2026-04-30T18:22:54.330Z | behavior_details | no | Direct transfers to another seemingly normal account are observed - likely used to avoid detection. | ../images/annotation-0009-behavior_details.png |
| 10 | 2026-04-30T18:28:12.825Z | behavior_details | no | Another address bought a similar amount during the same period; investigating whether this affected the price - confirmed: it did. | ../images/annotation-0010-behavior_details.png |
| 12 | 2026-04-30T18:42:24.008Z | candlestick_chart | no | This clearly affected the price. | ../images/annotation-0012-candlestick_chart.png |
| 13 | 2026-04-30T18:44:17.574Z | behavior_details | no | Oct 26, within 32 minutes: 26.17M tokens traded in the same direction. After DMj's sell, 9 addresses buy frequently in the same direction. | ../images/annotation-0013-behavior_details.png |
| 14 | 2026-04-30T18:45:17.111Z | behavior_details | no | Same-direction trading alternates between buys and sells (round-trip pattern). | ../images/annotation-0014-behavior_details.png |
| 15 | 2026-04-30T18:46:28.244Z | behavior_details | no | (sketch only) | ../images/annotation-0015-behavior_details.png |
| 17 | 2026-04-30T18:48:48.675Z | behavior_details | no | Three addresses fall within the same connected component. | ../images/annotation-0017-behavior_details.png |
| 18 | 2026-04-30T18:49:42.463Z | system | yes | These addresses are also part of the same component - forming a large colluding group. |  |
| 19 | 2026-04-30T18:50:10.995Z | token_distribution | no | Most of these addresses belong to the identified component. | ../images/annotation-0019-token_distribution.png |

## Key Cross-References

- H1 is grounded in S1 and Token Distribution screenshots `../images/annotation-0000-token_distribution.png`, `../images/annotation-0001-token_distribution.png`, and `../images/annotation-0002-token_distribution.png`.
- H2 is grounded in S2-S4 and Behavior Details screenshots for 6Z6, CqW, DNL, and DmJ.
- H3 is grounded in S5-S7 and the clicked card screenshots `../images/action-0014-target-behavior_details-01.png`, `../images/action-0017-target-behavior_details-01.png`, and `../images/action-0022-target-behavior_details-01.png`.
- Follow-up evidence is grounded in `continued-investigation-assets/follow-up-data-summary.json` plus rendered PNGs under `continued-investigation-assets/`.
