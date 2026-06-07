<script>
import CryptoVis from './components/CryptoVis.vue'
import ImportedAnalysisWorkspace from './components/ImportedAnalysisWorkspace.vue'
import ImportedStudyWorkspace from './components/ImportedStudyWorkspace.vue'

const SESSION_ID_RE = /^[0-9a-f]{5}$/
const WORKSPACE_ROLES = new Set(['human', 'agent'])
const IMPORTED_ANALYSIS_ROUTE = '/analysis-import'
const IMPORTED_STUDY_ROUTE = '/study-import'

export default {
  components: {
    CryptoVis,
    ImportedAnalysisWorkspace,
    ImportedStudyWorkspace,
  },
  data() {
    return {
      routeMode: 'session',
      sessionId: null,
      sessionMode: 'specialized',
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
      if (path === IMPORTED_STUDY_ROUTE) {
        this.routeMode = 'imported_study'
        this.sessionId = null
        return
      }
      if (path === '/base') {
        try {
          const response = await fetch('/api/base/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
          })
          if (!response.ok) throw new Error(`HTTP ${response.status}`)
          const payload = await response.json()
          if (!SESSION_ID_RE.test(payload.sessionId)) {
            throw new Error('Backend returned an invalid session ID')
          }
          window.location.replace(`/base/${payload.sessionId}`)
        } catch (error) {
          this.sessionError = error && error.message ? error.message : String(error)
        }
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
      if (parts[0] === 'base') {
        const candidate = parts[1]
        if (!SESSION_ID_RE.test(candidate) || parts.length > 3) {
          window.location.replace('/base')
          return
        }
        if (parts[2] === 'agent') {
          window.location.replace(`/base/${candidate}`)
          return
        }
        if (parts.length === 3) {
          window.location.replace(`/base/${candidate}`)
          return
        }
        this.sessionId = candidate
        this.sessionMode = 'baseline'
        this.workspaceRole = 'human'
        return
      }

      const candidate = parts[0]
      const role = parts[1] || 'human'
      if (!SESSION_ID_RE.test(candidate) || !WORKSPACE_ROLES.has(role) || parts.length > 2) {
        window.location.replace('/')
        return
      }
      this.sessionId = candidate
      this.sessionMode = 'specialized'
      this.workspaceRole = role
    },
  },
}
</script>

<template>
  <ImportedAnalysisWorkspace v-if="routeMode === 'imported_analysis'" />
  <ImportedStudyWorkspace v-else-if="routeMode === 'imported_study'" />
  <CryptoVis
    v-else-if="sessionId"
    :session-id="sessionId"
    :session-mode="sessionMode"
    :workspace-role="workspaceRole"
  />
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
