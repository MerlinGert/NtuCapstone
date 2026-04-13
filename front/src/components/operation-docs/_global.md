# _global - Operation Log

## Overview

Global operations recorded automatically by `operationLogger.js` itself, not tied to any specific Vue component. These provide session context needed for operation replay and reproducibility.

## Logged Operations

### 1. session_start (instant, auto on page load)

- **Trigger:** Module initialization (page load / refresh)
- **Location:** `operationLogger.js` top-level
- **Record:**
  ```json
  {
    "action": "session_start",
    "component": "_global",
    "detail": {
      "width": 1920,
      "height": 1080,
      "userAgent": "Mozilla/5.0 ..."
    }
  }
  ```

### 2. viewport_resize (debounced, 500ms)

- **Trigger:** Browser window resize
- **Location:** `operationLogger.js` window resize listener
- **Note:** Only records the final size after user stops resizing for 500ms
- **Record:**
  ```json
  {
    "action": "viewport_resize",
    "component": "_global",
    "detail": {
      "width": 1440,
      "height": 900
    }
  }
  ```

## Summary Table

| Action | Type | Logging Method | Delay |
|--------|------|----------------|-------|
| session_start | instant (auto) | `logOp` | - |
| viewport_resize | debounced | `logOpDebounced` | 500ms |
