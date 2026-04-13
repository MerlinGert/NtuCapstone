# TokenDistribution - Operation Log

## Component Overview

TokenDistribution is a D3 force-directed graph visualization showing token holder distribution. Users interact with nodes (single holders and entity group members) through click, drag, hover, and scale controls.

## Logged Operations

### 1. node_select (instant)

- **Trigger:** Click on an independent node (single holder)
- **Location:** D3 `.on("click")` handler on `.single` elements
- **Record:**
  ```json
  {
    "action": "node_select",
    "component": "TokenDistribution",
    "detail": {
      "nodeId": "0x1234...",
      "nodeType": "single | related"
    }
  }
  ```

### 2. group_member_select (instant)

- **Trigger:** Click on a node inside an entity group
- **Location:** D3 `.on("click")` handler on `.member` elements
- **Record:**
  ```json
  {
    "action": "group_member_select",
    "component": "TokenDistribution",
    "detail": {
      "nodeId": "0x1234...",
      "groupId": "entity_0"
    }
  }
  ```

### 3. node_drag (instant, on drag end, filtered)

- **Trigger:** User drags a node and releases
- **Location:** D3 drag `.on("end")` handler
- **Filter:** Only logged when drag distance > 5px (euclidean). Shorter drags are treated as click misfires and ignored.
- **Record:**
  ```json
  {
    "action": "node_drag",
    "component": "TokenDistribution",
    "detail": {
      "nodeId": "0x1234...",
      "from": { "x": 100, "y": 200 },
      "to": { "x": 300, "y": 150 }
    }
  }
  ```

### 4. open_snapshot (instant)

- **Trigger:** Click the "Snapshot" button in the header
- **Location:** `openSnapshot()` method
- **Record:**
  ```json
  {
    "action": "open_snapshot",
    "component": "TokenDistribution",
    "detail": {}
  }
  ```

### 5. scale_change (debounced, 500ms)

- **Trigger:** Drag the scale range slider
- **Location:** `onScaleChange()` method, logged via `logOpDebounced`
- **Note:** Only records the final value after user stops adjusting for 500ms
- **Record:**
  ```json
  {
    "action": "scale_change",
    "component": "TokenDistribution",
    "detail": {
      "scaleFactor": 0.6
    }
  }
  ```

### 6. node_hover (delayed, >1s)

- **Trigger:** Mouse hovers over an independent node for more than 1 second
- **Location:** D3 `.on("mouseover")` on `.single` elements, cancelled on `.on("mouseout")`
- **Note:** If user moves away within 1s, no log is recorded
- **Record:**
  ```json
  {
    "action": "node_hover",
    "component": "TokenDistribution",
    "detail": {
      "nodeId": "0x1234..."
    }
  }
  ```

### 7. member_hover (delayed, >1s)

- **Trigger:** Mouse hovers over a group member node for more than 1 second
- **Location:** D3 `.on("mouseover")` on `.member` elements, cancelled on `.on("mouseout")`
- **Note:** If user moves away within 1s, no log is recorded
- **Record:**
  ```json
  {
    "action": "member_hover",
    "component": "TokenDistribution",
    "detail": {
      "nodeId": "0x1234..."
    }
  }
  ```

## Summary Table

| Action | Type | Logging Method | Delay |
|--------|------|----------------|-------|
| node_select | instant | `logOp` | - |
| group_member_select | instant | `logOp` | - |
| node_drag | instant (on end) | `logOp` | - |
| open_snapshot | instant | `logOp` | - |
| scale_change | debounced | `logOpDebounced` | 500ms |
| node_hover | delayed | `logOpDelayed` + `cancelDelayed` | 1000ms |
| member_hover | delayed | `logOpDelayed` + `cancelDelayed` | 1000ms |
