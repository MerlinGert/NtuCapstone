# CandlestickChart - Operation Log

## Component Overview

CandlestickChart displays an OHLC K-line chart with manipulation overlay cards (Round Trip on top, Same Direction on bottom). Users interact through time granularity switching, zoom, crosshair hover, and card scrolling.

## Logged Operations

### 1. granularity_change (instant)

- **Trigger:** Click a granularity button (1H, 1D, 3D, 1W)
- **Location:** `onGranularityChange()` method
- **Record:**
  ```json
  {
    "action": "granularity_change",
    "component": "CandlestickChart",
    "detail": {
      "granularity": "1H"
    }
  }
  ```

### 2. zoom (debounced, 500ms)

- **Trigger:** Mouse wheel or pinch zoom on K-line chart
- **Location:** D3 zoom `.on('zoom')` handler
- **Note:** Only records the final zoom state after user stops zooming for 500ms
- **Record:**
  ```json
  {
    "action": "zoom",
    "component": "CandlestickChart",
    "detail": {
      "scale": 2.5,
      "x": -120.3
    }
  }
  ```

### 3. crosshair_hover (delayed, >1s)

- **Trigger:** Mouse hovers over a candle for more than 1 second
- **Location:** `hoverRect.on('mousemove')` handler, cancelled on `mouseleave`
- **Note:** If user moves away within 1s, no log is recorded
- **Record:**
  ```json
  {
    "action": "crosshair_hover",
    "component": "CandlestickChart",
    "detail": {
      "time": "2024-11-09T10:00:00.000Z",
      "open": 0.0045,
      "close": 0.0048
    }
  }
  ```

### 4. card_scroll (debounced, 500ms)

- **Trigger:** Horizontal scroll on top (Round Trip) or bottom (Same Direction) manipulation card containers
- **Location:** `onCardScroll()` method
- **Note:** Only records final scroll position after user stops scrolling for 500ms
- **Record:**
  ```json
  {
    "action": "card_scroll",
    "component": "CandlestickChart",
    "detail": {
      "position": "top",
      "scrollLeft": 240
    }
  }
  ```

## Summary Table

| Action | Type | Logging Method | Delay |
|--------|------|----------------|-------|
| granularity_change | instant | `logOp` | - |
| zoom | debounced | `logOpDebounced` | 500ms |
| crosshair_hover | delayed | `logOpDelayed` + `cancelDelayed` | 1000ms |
| card_scroll | debounced | `logOpDebounced` | 500ms |
