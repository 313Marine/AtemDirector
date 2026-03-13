# ATEM Director Dashboard

Professional operator dashboard for controlling ATEM video switchers with real-time status, input monitoring, and automated switching control.

## Overview

The dashboard is a **dark control-room interface** designed for high visibility and operator efficiency. It uses:

- **Alpine.js** for state management and interactivity
- **WebSocket** for real-time updates (no polling)
- **Vanilla CSS** for dark theme styling
- **Semantic HTML** for accessibility

## Architecture

### Frontend Stack
- **HTML Template** (`templates/dashboard.html`) - Semantic structure, Alpine.js data binding
- **CSS Styling** (`static/style.css`) - Dark theme, control-room aesthetic
- **JavaScript** (`static/dashboard.js`) - Alpine.js component with WebSocket integration

### Backend Integration
- **Dashboard Route** (`api/dashboard.py`) - Serves HTML template
- **WebSocket Endpoint** (`api/websocket.py`) - Real-time state updates
- **Control Endpoints** (`api/control.py`) - Handle operator commands
- **Settings Endpoints** (`api/settings.py`) - Configuration updates

## Features

### 1. Status Bar
- ATEM connection state (connected/disconnected)
- Device IP address
- Current program input
- Current preview input
- Transition mode (CUT/MIX)
- Switch mode

### 2. Countdown Panel
- Large countdown timer (MM:SS format)
- Current active camera
- Next planned action (if available)
- Engine state badge (RUNNING/PAUSED/LOCKED/HOLD)
- Lock/hold status indicators

### 3. Input Grid (1-8)
Each input card displays:
- Input number (CAM 1-8)
- Signal presence (green: signal OK, red: no signal)
- Enabled/Disabled status
- Program marker (PGM) if program input
- Preview marker (PVW) if preview input
- Safe camera marker if configured
- Enable/Disable button

### 4. Controls Panel
- **START** - Begin auto switching
- **STOP** - Stop auto switching
- **SKIP** - Skip current camera, switch immediately
- **SKIP NEXT** - Re-randomize next interval
- **+30s** - Extend hold time by 30 seconds
- **+1m** - Extend hold time by 1 minute
- **HOLD** - Hold current camera indefinitely
- **LOCK** - Lock for configurable duration
- **RELEASE** - Release lock
- **PANIC CUT** - Immediate cut (red emergency button)
- **RECONNECT** - Reconnect to ATEM device

### 5. Settings Panel
- **Transition Mode** - CUT or MIX
- **Mix Duration** - 1-5000ms
- **Switch Mode** - Algorithm selection (Balanced Random, Pure Random, Weighted, Round Robin)
- **Safe Camera** - Fallback camera selection

### 6. Statistics Panel
- Session switch count
- Session duration
- Average hold time per camera

### 7. Event Log Panel
- Timestamped event log (last 10 events visible)
- Event type (SWITCH, OVERRIDE, MANUAL, ERROR)
- From/To cameras
- Reason/description
- Color-coded by event type

## Real-Time Updates via WebSocket

### Message Types

**State Update**
```json
{
  "type": "state_update",
  "payload": {
    "atem_status": {...},
    "switcher_state": {...},
    "engine_state": {...},
    "input_signals": {...},
    "program_input": 1,
    "preview_input": 2,
    "transition_mode": "cut"
  }
}
```

**Event**
```json
{
  "type": "event",
  "payload": {
    "id": 123,
    "event_type": "switch",
    "from_input": 1,
    "to_input": 2,
    "reason": "Auto switch",
    "created_at": "2024-01-15T10:30:45Z"
  }
}
```

**Statistics Update**
```json
{
  "type": "stats_update",
  "payload": {
    "total_switches": 42,
    "total_duration_seconds": 3600,
    "average_hold_seconds": 30.5
  }
}
```

## Styling Reference

### Dark Theme Colors
- **Background**: `#0a0e27` - Deep blue-black
- **Panel Background**: `#151a2d` - Slightly lighter
- **Primary Accent**: `#00ff00` - Bright lime green (high visibility)
- **Secondary Accent**: `#00aaff` - Cyan for preview
- **Warning**: `#ffaa00` - Orange for safe/warnings
- **Danger**: `#ff4444` - Red for errors/panic

### State Indicators
- **Program Input**: Green glow with bright border
- **Preview Input**: Cyan/blue border
- **Safe Camera**: Orange triple-width border
- **Signal OK**: Green badge with border
- **No Signal**: Red badge with border
- **Locked**: Red status badge
- **Held**: Yellow status badge
- **Cooldown**: Reduced opacity (0.6)

## Keyboard Shortcuts (Future)

Can be added to Alpine.js for operator efficiency:
- `Space` - Start/Stop toggle
- `S` - Skip current
- `H` - Hold current
- `P` - Panic cut
- `1-8` - Switch to camera
- `Esc` - Close modals

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Requires WebSocket support
- Requires ES6 JavaScript support

## Performance

- **State Updates**: 100-500ms (via WebSocket)
- **Countdown**: Updated live every 100ms locally
- **Event Log**: Capped at 50 events
- **No Polling**: All updates via WebSocket (single connection)
- **Minimal Redraws**: Alpine.js only updates changed DOM elements

## Responsive Design

- **Desktop** (1920x1080): Full 3-column layout
- **Widescreen** (2560x1440): Same layout, larger panels
- **Tablet/Mobile**: Stacked layout (future enhancement)

## CSS Architecture

### File Structure
```
static/
├── style.css         # All styling (one file for simplicity)
├── dashboard.js      # Alpine.js component
└── (Alpine.js via CDN)
```

### Styling Approach
- **CSS Grid** for panel layout
- **Flexbox** for internal component layouts
- **CSS Variables** for theme colors (could be added)
- **Media Queries** for responsive design
- **No CSS Framework** - Pure CSS for control room simplicity

## Future Enhancements

1. **Keyboard Shortcuts** - Operator hotkeys
2. **Dark/Light Theme Toggle** - User preference
3. **Camera Presets** - Save/load preset configs
4. **Advanced Stats** - Per-camera usage over time
5. **Audio Monitoring** - Audio signal indicators
6. **Mobile Responsive** - Stacked layout for mobile
7. **Internationalization** - Multiple language support
8. **Custom Layouts** - Operator-configurable dashboard
9. **Recording Controls** - Start/stop recording overlay
10. **Streaming Status** - Live stream indicators

## Troubleshooting

### WebSocket Connection Failed
- Check browser console for errors
- Verify API server is running
- Check firewall allows WebSocket traffic
- Verify CORS configuration

### Dashboard Not Loading
- Ensure `templates/` and `static/` directories exist
- Verify FastAPI serves static files correctly
- Check browser cache, clear if needed
- Verify template path in `dashboard.py`

### Real-Time Updates Not Showing
- Open browser DevTools > Network > WS tab
- Verify WebSocket connection is open
- Check message format in console
- Verify orchestrator is publishing updates
