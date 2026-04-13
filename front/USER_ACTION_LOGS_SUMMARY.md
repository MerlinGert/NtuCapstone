# CryptoVis User Action Logs Summary

This document categorizes and summarizes all the user actions logged by the CryptoVis system. Actions are grouped by their functional categories, detailing their source view, target view, and the specific information (`actionInfo`) they preserve.

## 1. System & Configuration Actions
These actions involve global system settings, data loading, and triggering backend detection algorithms.

| Action Type | Source View | Target View | Saved Information (`actionInfo`) | Description |
| :--- | :--- | :--- | :--- | :--- |
| `change_coin` | `Header Panel` | `All Views` | `{ coin: "ACT" \| "PNUT" }` | User toggled the primary token analyzed by the system. |
| `update_snapshot` | `Control Panel` | `All Views` | `{ config: { time, top_holder_threshold, related_user_threshold } }` | User changed the snapshot parameters and requested new snapshot data. |
| `run_entity_detection` | `Control Panel` | `All Views` | `{ config: { ...entity_detection_configuration } }` | User triggered the Entity Detection algorithm with specific parameters. |
| `update_link_detection` | `Control Panel` | `All Views` | `{ config: { ...link_detection_configuration } }` | User triggered the Link Detection algorithm with specific parameters. |
| `run_manipulation_detection`| `Control Panel` | `All Views` | `{ config: { ...manipulation_detection_configuration } }`| User triggered the Manipulation Detection algorithm with specific parameters. |

## 2. Interaction & Selection Actions
These actions involve clicking to select specific users or groups to view their detailed behaviors.

| Action Type | Source View | Target View | Saved Information (`actionInfo`) | Description |
| :--- | :--- | :--- | :--- | :--- |
| `select_user_from_network` | `Token Distribution` | `Behavior Details`| `{ targetUserId: "string" }` | User clicked a bubble in the force-directed graph to analyze a specific address. |
| `select_user_from_behavior_details`| `Behavior Details` | `Behavior Details`| `{ targetUserId: "string" }` | User clicked a truncated address label on the Y-axis of the behavior chart to isolate that user. |
| `click_manipulation_card` | `K-line Chart` | `Behavior Details`| `{ cardUsers: ["user1", "user2", ...] }` | User clicked a Manipulation Card (Round Trip / Same Direction) to view the behavior of the involved group. |
| `click_kline_align_cards` | `K-line Chart` | `K-line Chart` | `{ time: "ISOString", roundTripCount: number, sameDirectionCount: number }` | User clicked on a specific K-line time slice to horizontally scroll and align the relevant manipulation cards. |

## 3. View Adjustment Actions
These actions involve modifying how data is displayed within the charts (zooming, toggling elements, syncing).

| Action Type | Source View | Target View | Saved Information (`actionInfo`) | Description |
| :--- | :--- | :--- | :--- | :--- |
| `change_kline_granularity` | `K-line Chart` | `K-line Chart` | `{ granularity: "1min"\|"5min"\|"1D", label: "string" }` | User changed the time aggregation granularity for the candlestick chart. |
| `toggle_show_related_users` | `Behavior Details` | `Behavior Details`| `{ enabled: boolean }` | User toggled the switch to show/hide counterparties in the behavior sequence chart. |
| `toggle_show_manipulation_boxes`| `Behavior Details` | `Behavior Details`| `{ enabled: boolean }` | User toggled the switch to show/hide the red translucent manipulation warning boxes. |
| `sync_time_window` | `K-line Chart` OR `Behavior Details` | `Behavior Details` OR `K-line Chart` | `{ source: 'kline_chart' \| 'behavior_details' }` | User clicked the "Sync Time" button to align the X-axis domain between the K-line and Behavior charts. |

## 4. Continuous Navigation Actions (Merged)
These actions are highly frequent (e.g., scrolling, dragging, hovering). To prevent spamming the logs, the system automatically debounces and **merges** consecutive actions of the same type occurring within a short time window (2-3 seconds) into a single action record. 

When merged, the `actionInfo` becomes an **Array** of objects: `[{ time: "ISOString", data: { ... } }, ...]`, preserving the entire continuous trajectory.

| Action Type | Source View | Target View | Saved Information (`data` inside Array) | Description |
| :--- | :--- | :--- | :--- | :--- |
| `zoom_kline_chart` | `K-line Chart` | `K-line Chart` | `{ timeWindow: [startTime, endTime] }` | User panned or zoomed the candlestick chart. |
| `zoom_behavior_chart` | `Behavior Details` | `Behavior Details`| `{ timeWindow: [startTime, endTime] }` | User panned or zoomed the behavior sequence chart. |
| `scroll_manipulation_cards` | `K-line Chart` | `K-line Chart` | `{ type: "round_trip" \| "same_direction", visibleCards: ["time_label1", "time_label2"] }` | User horizontally scrolled the manipulation card container, bringing new cards into view. **Note:** Card scrolling triggered automatically by zooming the K-line chart is suppressed and not logged. |

## 5. Hover Exploration Actions (Merged)
Like navigation actions, hovers are merged into an array if they occur sequentially. The system employs a **3000ms (3 seconds)** debounce delay to filter out accidental, rapid mouse fly-overs. If a user is actively zooming/panning (`isZooming = true`) or scrolling cards (`isScrollingCards = true`), hover logging is completely suppressed to prevent misclicks.

If the user stops hovering before the 3 seconds are up, a `cancel_hover` action aborts the logging.

**Hover Merging Rule:** Once a hover is successfully logged, if the very next action is another hover of the **exact same type**, they will be merged into a single action array regardless of how much time passed between them. Time limits only apply to merging navigation actions (zoom/scroll).

| Action Type | Source View | Target View | Saved Information (`data` inside Array) | Description |
| :--- | :--- | :--- | :--- | :--- |
| `hover_token_distribution_user` | `Token Distribution` | `Token Distribution`| `{ targetUserId: "string", balance: number, isRelated: boolean, inGroup?: boolean }` | User hovered over a specific address bubble in the network graph. |
| `hover_kline` | `K-line Chart` | `K-line Chart` | `{ time: "ISOString", open: number, close: number, high: number, low: number }` | User hovered over a specific candlestick to view its OHLC data. |
| `hover_manipulation_card` | `K-line Chart` | `K-line Chart` | `{ type: "round_trip" \| "same_direction", time: "string", usersCount: number }` | User hovered over a manipulation summary card at the top or bottom of the K-line chart. |
| `hover_behavior_user_label` | `Behavior Details` | `Behavior Details`| `{ hoveredUserId: "string" }` | User hovered over the truncated user ID on the Y-axis to view the full address tooltip. |
| `hover_behavior_manipulation_box`| `Behavior Details` | `Behavior Details`| `{ method: "string", time: "string", usersCount: number }` | User hovered over a red translucent manipulation box in the behavior chart to see its details. |

---

### Global View State (`relatedViewWithViewState`)
Every single action recorded above (whether a single event or a merged continuous event) is accompanied by a snapshot of the system's overall state at the time the action was initiated. This is stored in the `relatedViewWithViewState` object:

```json
{
  "coin": "ACT" | "PNUT",
  "snapshotTime": "2024-11-09 23:00:00 UTC",
  "selectedUser": "address_string" | null,
  "selectedCardUsers": ["address1", "address2", ...],
  "klineTimeWindow": [startTime, endTime] | null,
  "behaviorTimeWindow": [startTime, endTime] | null,
  "hasEntityResults": boolean,
  "hasManipulationResults": boolean
}
```