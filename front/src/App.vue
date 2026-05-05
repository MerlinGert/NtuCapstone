<script>
import CryptoVis from './components/CryptoVis.vue'

const SESSION_ID_RE = /^[0-9a-f]{5}$/

export default {
  components: {
    CryptoVis,
  },
  data() {
    return {
      sessionId: null,
      sessionError: '',
    }
  },
  async created() {
    await this.initializeRouteSession()
  },
  methods: {
    async initializeRouteSession() {
      const path = window.location.pathname.replace(/\/+$/, '') || '/'
      if (path === '/') {
        try {
          const response = await fetch('/api/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
          })
          if (!response.ok) throw new Error(`HTTP ${response.status}`)
          const payload = await response.json()
          if (!SESSION_ID_RE.test(payload.sessionId)) {
            throw new Error('Backend returned an invalid session ID')
          }
          window.location.replace(`/${payload.sessionId}`)
        } catch (error) {
          this.sessionError = error && error.message ? error.message : String(error)
        }
        return
      }

      const candidate = path.slice(1)
      if (!SESSION_ID_RE.test(candidate)) {
        window.location.replace('/')
        return
      }
      this.sessionId = candidate
    },
  },
}
</script>

<template>
  <CryptoVis v-if="sessionId" :session-id="sessionId" />
  <div v-else class="session-bootstrap">
    <div v-if="sessionError" class="session-bootstrap-error">
      Failed to initialize session: {{ sessionError }}
    </div>
    <div v-else>Starting ManiScope session...</div>
  </div>
</template>

<style>
html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
}

.session-bootstrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4a5568;
  font-size: 14px;
}

.session-bootstrap-error {
  color: #c53030;
}
</style>
