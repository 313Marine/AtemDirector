function dashboardApp() {
  return {
    isConnected: false,
    atemIp: '192.168.1.100',
    switchMode: 'balanced_random',
    safeCamera: 1,
    lockDuration: 60,
    showModal: false,
    countdown: 0,
    state: {},
    sessionStats: {},
    recentEvents: [],
    ws: null,

    initWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/v1/ws`;
      
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('[Dashboard] WebSocket connected');
        this.isConnected = true;
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (e) {
          console.error('[Dashboard] Failed to parse message:', e);
        }
      };
      
      this.ws.onerror = () => {
        console.error('[Dashboard] WebSocket error');
        this.isConnected = false;
      };
      
      this.ws.onclose = () => {
        console.log('[Dashboard] WebSocket disconnected');
        this.isConnected = false;
        setTimeout(() => this.initWebSocket(), 3000);
      };
    },

    handleMessage(data) {
      if (data.type === 'state_update') {
        this.state = data.payload;
        this.updateCountdown();
      } else if (data.type === 'event') {
        this.recentEvents.unshift(data.payload);
        if (this.recentEvents.length > 50) {
          this.recentEvents.pop();
        }
      } else if (data.type === 'stats_update') {
        this.sessionStats = data.payload;
      }
    },

    updateCountdown() {
      if (this.state.engine_state?.countdown_seconds !== undefined) {
        this.countdown = Math.max(0, Math.ceil(this.state.engine_state.countdown_seconds));
      }
    },

    formatCountdown(seconds) {
      const mins = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    },

    formatDuration(seconds) {
      if (!seconds) return '0s';
      const mins = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      if (mins === 0) return `${secs}s`;
      return `${mins}m ${secs}s`;
    },

    formatTime(dateString) {
      const date = new Date(dateString);
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      return `${hours}:${minutes}:${seconds}`;
    },

    getInputSignal(input) {
      return this.state.input_signals?.[input]?.has_signal || false;
    },

    isInputEnabled(input) {
      return this.state.engine_state?.input_states?.[input]?.enabled !== false;
    },

    isInputLocked(input) {
      return this.state.engine_state?.input_states?.[input]?.locked === true;
    },

    isInCooldown(input) {
      return this.state.engine_state?.input_states?.[input]?.in_cooldown === true;
    },

    toggleInputEnabled(input) {
      const enabled = this.isInputEnabled(input);
      this.sendAPI('POST', `/api/v1/settings/input/enable`, {
        input_index: input,
        enabled: !enabled
      });
    },

    updateTransitionMode(event) {
      const mode = event.target.value;
      this.sendAPI('POST', `/api/v1/settings/transition/mode`, { mode });
    },

    updateMixDuration(event) {
      const duration_ms = parseInt(event.target.value, 10);
      this.sendAPI('POST', `/api/v1/settings/transition/duration`, { duration_ms });
    },

    updateSwitchMode(event) {
      const mode = event.target.value;
      this.switchMode = mode;
      this.sendAPI('POST', `/api/v1/settings/switch-mode`, { mode });
    },

    updateSafeCamera(event) {
      const value = event.target.value;
      const safeCamera = value ? parseInt(value, 10) : null;
      this.safeCamera = safeCamera;
      if (safeCamera) {
        this.sendAPI('POST', `/api/v1/settings/safe-camera`, { input_index: safeCamera });
      }
    },

    showLockModal() {
      this.showModal = true;
      this.$nextTick(() => {
        const input = document.querySelector('input[type="number"]');
        if (input) input.focus();
      });
    },

    sendControl(action, param) {
      let endpoint = `/api/v1/control/${action}`;
      let payload = {};

      if (action === 'extend' && param) {
        endpoint = `/api/v1/control/extend-current`;
        payload = { seconds: param };
      } else if (action === 'lock-current' && param) {
        endpoint = `/api/v1/control/lock-current`;
        payload = { seconds: param };
        this.showModal = false;
      }

      this.sendAPI('POST', endpoint, payload);
    },

    sendAPI(method, endpoint, data = {}) {
      const options = {
        method,
        headers: {
          'Content-Type': 'application/json'
        }
      };

      if (method !== 'GET' && Object.keys(data).length > 0) {
        options.body = JSON.stringify(data);
      }

      fetch(endpoint, options)
        .then(res => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then(data => {
          console.log('[Dashboard] API response:', data);
        })
        .catch(err => {
          console.error('[Dashboard] API error:', err);
        });
    }
  };
}
