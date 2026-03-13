ATEM Director - Comprehensive Hardening Strategy

This document outlines all hardening changes made to improve operational safety and failure handling.

## Key Hardening Areas

### 1. ATEM Connection Failures
- **ATEM unavailable at startup**: Boot in DEGRADED mode with safe defaults, don't block startup
- **Wrong IP/Port**: Validation at startup with clear errors logged, fallback to degraded mode
- **Connection timeouts**: Exponential backoff (2s → 30s cap), max 5 attempts before giving up
- **Disconnect during countdown**: Stop engine, move to ERROR state with graceful error handling

### 2. Signal Handling
- **Signal loss during countdown**: Check before each switch, fall back to safe camera if unavailable
- **Signal restoration**: Monitor and automatically resume operation
- **Zero eligible inputs**: Hold current, retry every 5s, warn operator repeatedly
- **One eligible input**: Auto-switch without randomization, log as forced

### 3. Configuration & State
- **Empty timing pool**: Load defaults (30s-150s intervals), warn operator
- **Invalid settings input**: Validate all inputs, reject with HTTPException
- **Safe camera unavailable**: Auto-select input 1 as fallback
- **Corrupted stored config**: Load safe defaults, log error, allow operator to fix

### 4. Operation Resilience
- **Manual operator switching**: Detect and track, don't interfere
- **Transition command failure**: Log, retry once, fallback to safe mode
- **Duplicate command execution**: Idempotent operations, state guards prevent re-execution
- **Timer race conditions**: Lock-protected countdown, check before transition

### 5. Connection Recovery
- **Reconnect during countdown**: Detect change, pause engine, resume when stable
- **WebSocket reconnects**: Send full state on reconnect, don't drop events
- **Stale dashboard state**: Always send timestamp, client detects stale data

### 6. Visibility & Audit
- **Comprehensive logging**: Every significant action logged with context
- **Event audit trail**: Full history of switches, errors, manual operations
- **Runtime state clarity**: Clear error messages, operational status in dashboard
- **Warnings for edge cases**: Alert operator when entering risky states

## Implementation Details by Component

See modified files for specific changes.
