<template>
  <div class="imported-analysis-page">
    <div class="imported-analysis-header">
      <div>
        <div class="imported-analysis-title">Imported LLM Analysis</div>
        <div class="imported-analysis-subtitle">
          Load a previously exported LLM analysis JSON and browse it with the same card view.
        </div>
      </div>
      <div class="imported-analysis-actions">
        <button class="imported-analysis-btn" type="button" @click="$refs.fileInput.click()">
          Import JSON
        </button>
        <input
          ref="fileInput"
          type="file"
          accept=".json,application/json"
          style="display: none"
          @change="onFileChosen"
        />
      </div>
    </div>

    <div v-if="importError" class="imported-analysis-error">
      {{ importError }}
    </div>

    <div v-if="analysisPayload" class="imported-analysis-summary">
      <span class="imported-analysis-chip">
        {{ analysisPayload.sessionId ? `Session ${analysisPayload.sessionId}` : 'Imported session' }}
      </span>
      <span v-if="analysisPayload.exportedAt" class="imported-analysis-chip">
        Exported {{ formatDate(analysisPayload.exportedAt) }}
      </span>
      <span v-if="analysisPayload.artifactSummary" class="imported-analysis-chip imported-analysis-chip-wide">
        {{ analysisPayload.artifactSummary }}
      </span>
    </div>

    <div class="imported-analysis-body">
      <div v-if="!analysisPayload" class="imported-analysis-empty">
        Choose an exported `LLM analysis JSON` file to restore the analysis view here.
      </div>
      <NotesPanel
        v-else
        class="imported-analysis-panel"
        :analysis-only="true"
        :analysis-payload="analysisPayload"
        initial-tab="llm_analysis"
      />
    </div>
  </div>
</template>

<script>
import NotesPanel from './NotesPanel.vue'

export default {
  name: 'ImportedAnalysisWorkspace',
  components: {
    NotesPanel,
  },
  data() {
    return {
      analysisPayload: null,
      importError: '',
    }
  },
  methods: {
    async onFileChosen(event) {
      const [file] = Array.from(event?.target?.files || [])
      event.target.value = ''
      if (!file) return
      try {
        const text = await file.text()
        const parsed = JSON.parse(text)
        this.validateImportedPayload(parsed)
        this.analysisPayload = parsed
        this.importError = ''
      } catch (error) {
        this.analysisPayload = null
        this.importError = error && error.message ? error.message : 'Failed to import analysis JSON.'
      }
    },
    validateImportedPayload(payload) {
      if (!payload || typeof payload !== 'object') {
        throw new Error('Invalid analysis file: not a JSON object.')
      }
      if (!Array.isArray(payload.displayForest)) {
        throw new Error('Invalid analysis file: missing `displayForest` array.')
      }
      if (!payload.reasoningGraph && !payload.augmentedReasoningGraph) {
        throw new Error('Invalid analysis file: missing reasoning graph content.')
      }
    },
    formatDate(value) {
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return value
      return date.toLocaleString()
    },
  },
}
</script>

<style scoped>
.imported-analysis-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 20px;
  box-sizing: border-box;
  background: #f8fafc;
  color: #1f2937;
}

.imported-analysis-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.imported-analysis-title {
  font-size: 22px;
  font-weight: 800;
  color: #111827;
}

.imported-analysis-subtitle {
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.imported-analysis-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.imported-analysis-btn {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  padding: 8px 12px;
}

.imported-analysis-btn:hover {
  border-color: #94a3b8;
  background: #ffffff;
}

.imported-analysis-error {
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid #fecaca;
  border-radius: 10px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 13px;
}

.imported-analysis-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.imported-analysis-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 1px solid #d8e0ec;
  background: #ffffff;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
  line-height: 18px;
  padding: 2px 9px;
}

.imported-analysis-chip-wide {
  max-width: 100%;
  overflow-wrap: anywhere;
}

.imported-analysis-body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
}

.imported-analysis-empty {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed #cbd5e1;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  color: #64748b;
  font-size: 14px;
  text-align: center;
  padding: 24px;
}

.imported-analysis-panel {
  width: 100%;
  min-height: 0;
}
</style>
