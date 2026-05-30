<script>
import CryptoVis from './components/CryptoVis.vue'
import ImportedAnalysisWorkspace from './components/ImportedAnalysisWorkspace.vue'

const SESSION_ID_RE = /^[0-9a-f]{5}$/
const WORKSPACE_ROLES = new Set(['human', 'agent'])
const IMPORTED_ANALYSIS_ROUTE = '/analysis-import'

export default {
  components: {
    CryptoVis,
    ImportedAnalysisWorkspace,
  },
  data() {
    return {
      routeMode: 'session',
      sessionId: null,
      workspaceRole: 'human',
      sessionError: '',
    }
  },
  async created() {
    await this.initializeRouteSession()
  },
  methods: {
    async initializeRouteSession() {
      const path = window.location.pathname.replace(/\/+$/, '') || '/'
      if (path === IMPORTED_ANALYSIS_ROUTE) {
        this.routeMode = 'imported_analysis'
        this.sessionId = null
        return
      }
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
          window.location.replace(`/${payload.sessionId}/human`)
        } catch (error) {
          this.sessionError = error && error.message ? error.message : String(error)
        }
        return
      }

      const parts = path.slice(1).split('/')
      const candidate = parts[0]
      const role = parts[1] || 'human'
      if (!SESSION_ID_RE.test(candidate) || !WORKSPACE_ROLES.has(role) || parts.length > 2) {
        window.location.replace('/')
        return
      }
      this.sessionId = candidate
      this.workspaceRole = role
    },
  },
}
</script>

<template>
  <ImportedAnalysisWorkspace v-if="routeMode === 'imported_analysis'" />
  <CryptoVis v-else-if="sessionId" :session-id="sessionId" :workspace-role="workspaceRole" />
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
