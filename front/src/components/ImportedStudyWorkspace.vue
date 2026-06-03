<template>
  <div class="imported-study-page">
    <div class="imported-study-header">
      <div>
        <div class="imported-study-title">Imported Study Package</div>
        <div class="imported-study-subtitle">
          Load an exported study ZIP to restore the workspace and browse all recorded contents.
        </div>
      </div>
      <div class="imported-study-actions">
        <button class="imported-study-btn" type="button" @click="$refs.fileInput.click()">
          Import ZIP
        </button>
        <input
          ref="fileInput"
          type="file"
          accept=".zip,application/zip,.json,application/json"
          style="display: none"
          @change="onFileChosen"
        />
      </div>
    </div>

    <div v-if="importError" class="imported-study-error">
      {{ importError }}
    </div>

    <div v-if="importedPayload" class="imported-study-summary">
      <span class="imported-study-chip">
        {{ importedMeta.sessionId ? `Session ${importedMeta.sessionId}` : 'Imported archive' }}
      </span>
      <span v-if="importedMeta.sessionMode" class="imported-study-chip">
        {{ importedMeta.sessionMode === 'baseline' ? 'Baseline' : 'Specialized' }}
      </span>
      <span v-if="importedMeta.coin" class="imported-study-chip">
        {{ importedMeta.coin }}
      </span>
      <span v-if="importedMeta.exportedAt" class="imported-study-chip">
        Exported {{ formatDate(importedMeta.exportedAt) }}
      </span>
      <span class="imported-study-chip">
        {{ importedPayload.userActionSequence.length }} actions
      </span>
      <span class="imported-study-chip">
        {{ importedPayload.annotationRecords.length }} annotations
      </span>
      <span class="imported-study-chip">
        {{ importedPayload.chatbotLogs.length }} chat turns
      </span>
      <span class="imported-study-chip">
        {{ importedPayload.llmAnalysisTrace?.length || 0 }} LLM analysis events
      </span>
      <span v-if="importedMeta.imageCount" class="imported-study-chip">
        {{ importedMeta.imageCount }} images
      </span>
    </div>

    <div v-if="importedPayload" class="imported-study-tabs">
      <button
        class="imported-study-tab"
        :class="{ active: activeTab === 'workspace' }"
        type="button"
        @click="activeTab = 'workspace'"
      >
        Workspace View
      </button>
      <button
        class="imported-study-tab"
        :class="{ active: activeTab === 'contents' }"
        type="button"
        @click="activeTab = 'contents'"
      >
        Archive Contents
      </button>
      <button
        class="imported-study-tab"
        :class="{ active: activeTab === 'trace_timeline' }"
        type="button"
        @click="activeTab = 'trace_timeline'"
      >
        Trace Timeline
      </button>
    </div>

    <div class="imported-study-body">
      <div v-if="!importedPayload" class="imported-study-empty">
        Choose a previously exported study package ZIP to inspect the restored workspace, metadata,
        screenshots, milestones, and chat logs here.
      </div>

      <div v-else-if="activeTab === 'workspace'" class="imported-study-workspace">
        <CryptoVis
          :key="viewerKey"
          :session-mode="effectiveSessionMode"
          workspace-role="human"
          :imported-payload="importedPayload"
          :imported-meta="importedMeta"
        />
      </div>

      <div v-else-if="activeTab === 'trace_timeline'" class="imported-study-contents">
        <section class="imported-study-section">
          <h3>Trace Timeline</h3>
          <TraceTimelineViewer
            :actions="importedPayload.userActionSequence"
            :chatbot-logs="importedPayload.chatbotLogs"
            :llm-analysis-trace="importedPayload.llmAnalysisTrace"
          />
        </section>
      </div>

      <div v-else class="imported-study-contents">
        <section class="imported-study-section">
          <h3>Export Info</h3>
          <div class="imported-study-grid">
            <div class="imported-study-card">
              <div class="imported-study-label">Format</div>
              <div>{{ importedMeta.exportFormat || 'session-json' }}</div>
            </div>
            <div class="imported-study-card">
              <div class="imported-study-label">Version</div>
              <div>{{ importedMeta.exportVersion || '-' }}</div>
            </div>
            <div class="imported-study-card">
              <div class="imported-study-label">Snapshots</div>
              <div>{{ importedMeta.includesSnapshots ? 'Included' : 'Not included' }}</div>
            </div>
            <div class="imported-study-card">
              <div class="imported-study-label">Image Directory</div>
              <div>{{ importedMeta.imageDirectory || '-' }}</div>
            </div>
          </div>
        </section>

        <section class="imported-study-section">
          <h3>Study Info</h3>
          <div class="imported-study-grid">
            <div class="imported-study-card">
              <div class="imported-study-label">Participant ID</div>
              <div>{{ importedPayload.studyInfo?.participantId || '-' }}</div>
            </div>
            <div class="imported-study-card">
              <div class="imported-study-label">Session Order</div>
              <div>{{ importedPayload.studyInfo?.sessionOrder || '-' }}</div>
            </div>
            <div class="imported-study-card">
              <div class="imported-study-label">Condition</div>
              <div>{{ importedPayload.studyInfo?.condition || '-' }}</div>
            </div>
            <div class="imported-study-card">
              <div class="imported-study-label">Dataset</div>
              <div>{{ importedPayload.studyInfo?.dataset || importedMeta.coin || '-' }}</div>
            </div>
          </div>
          <div class="imported-study-notes">
            {{ importedPayload.studyInfo?.studyNotes || 'No study notes.' }}
          </div>
        </section>

        <section class="imported-study-section">
          <h3>Current View Screenshots</h3>
          <div v-if="screenshotEntries.length" class="imported-study-screenshots">
            <div
              v-for="entry in screenshotEntries"
              :key="entry.name"
              class="imported-study-screenshot-card"
            >
              <div class="imported-study-label">{{ formatViewName(entry.name) }}</div>
              <img :src="entry.url" :alt="entry.name" class="imported-study-screenshot" />
            </div>
          </div>
          <div v-else class="imported-study-empty-inline">No current-view screenshots in this archive.</div>
        </section>

        <section class="imported-study-section">
          <h3>Analysis Milestones</h3>
          <div v-if="importedPayload.analysisMilestones.length" class="imported-study-list">
            <div
              v-for="(milestone, index) in importedPayload.analysisMilestones"
              :key="milestone.name || index"
              class="imported-study-list-item"
            >
              <div class="imported-study-list-title">
                {{ milestone.name || `Milestone ${index + 1}` }}
              </div>
              <div class="imported-study-list-meta">
                {{ formatDate(milestone.timestamp) }}
              </div>
              <pre v-if="milestone.details" class="imported-study-json">{{ toPrettyJson(milestone.details) }}</pre>
            </div>
          </div>
          <div v-else class="imported-study-empty-inline">No analysis milestones recorded.</div>
        </section>

        <section class="imported-study-section">
          <h3>Chat Logs</h3>
          <div v-if="importedPayload.chatbotLogs.length" class="imported-study-list">
            <div
              v-for="(entry, index) in importedPayload.chatbotLogs"
              :key="entry.id || index"
              class="imported-study-list-item"
            >
              <div class="imported-study-list-title">
                Turn {{ index + 1 }} · {{ entry.triggerType || 'manual' }}
              </div>
              <div class="imported-study-list-meta">
                {{ formatDate(entry.timestamp) }}
              </div>
              <div class="imported-study-text-block">
                <strong>Prompt</strong>
                <div>{{ entry.prompt || '-' }}</div>
              </div>
              <div class="imported-study-text-block">
                <strong>Response</strong>
                <div>{{ entry.response?.text || '-' }}</div>
              </div>
              <div v-if="entry.promptAttachments?.length" class="imported-study-media-row">
                <img
                  v-for="(attachment, attachmentIndex) in entry.promptAttachments"
                  :key="attachment.id || attachmentIndex"
                  :src="attachment.dataUrl"
                  :alt="attachment.name || `attachment-${attachmentIndex + 1}`"
                  class="imported-study-media"
                />
              </div>
              <div v-if="chatArtifactImages(entry).length" class="imported-study-media-row">
                <img
                  v-for="(artifact, artifactIndex) in chatArtifactImages(entry)"
                  :key="artifact.id || artifactIndex"
                  :src="artifact.dataUrl || artifact.url"
                  :alt="artifact.title || `artifact-${artifactIndex + 1}`"
                  class="imported-study-media"
                />
              </div>
            </div>
          </div>
          <div v-else class="imported-study-empty-inline">No chat logs recorded.</div>
        </section>

        <section class="imported-study-section">
          <h3>Derived Tables</h3>
          <div v-if="derivedTableEntries.length" class="imported-study-grid">
            <div
              v-for="entry in derivedTableEntries"
              :key="entry.key"
              class="imported-study-card imported-study-card-wide"
            >
              <div class="imported-study-label">
                {{ entry.key }} · {{ entry.count }} rows
              </div>
              <pre class="imported-study-json">{{ toPrettyJson(entry.preview) }}</pre>
            </div>
          </div>
          <div v-else class="imported-study-empty-inline">No derived tables found.</div>
        </section>
      </div>
    </div>
  </div>
</template>

<script>
import CryptoVis from './CryptoVis.vue'
import TraceTimelineViewer from './TraceTimelineViewer.vue'
import { parseImportFile } from '../utils/sessionIO'

export default {
  name: 'ImportedStudyWorkspace',
  components: {
    CryptoVis,
    TraceTimelineViewer,
  },
  data() {
    return {
      importedPayload: null,
      importedMeta: {},
      importError: '',
      activeTab: 'workspace',
      viewerKey: 0,
    }
  },
  computed: {
    effectiveSessionMode() {
      return this.importedMeta.sessionMode === 'baseline' ? 'baseline' : 'specialized'
    },
    screenshotEntries() {
      const screenshots = this.importedPayload?.currentState?.majorViewScreenshots || {}
      return Object.entries(screenshots)
        .filter(([, value]) => typeof value === 'string' && value.startsWith('data:image/'))
        .map(([name, url]) => ({ name, url }))
    },
    derivedTableEntries() {
      const tables = this.importedMeta?.derivedTables || {}
      return Object.entries(tables).map(([key, value]) => {
        const rows = Array.isArray(value) ? value : []
        return {
          key,
          count: rows.length,
          preview: rows.slice(0, 5),
        }
      })
    },
  },
  methods: {
    async onFileChosen(event) {
      const [file] = Array.from(event?.target?.files || [])
      event.target.value = ''
      if (!file) return
      try {
        const parsed = await parseImportFile(file)
        this.importedPayload = parsed
        this.importedMeta = parsed.meta || {}
        this.importError = ''
        this.activeTab = 'workspace'
        this.viewerKey += 1
      } catch (error) {
        this.importedPayload = null
        this.importedMeta = {}
        this.importError = error && error.message ? error.message : 'Failed to import study package.'
        this.viewerKey += 1
      }
    },
    formatDate(value) {
      if (!value) return '-'
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return value
      return date.toLocaleString()
    },
    formatViewName(name) {
      const labels = {
        token_distribution: 'Token Distribution',
        candlestick_chart: 'K-Line',
        behavior_details: 'Behavior Details',
      }
      return labels[name] || name
    },
    chatArtifactImages(entry) {
      const artifacts = Array.isArray(entry?.response?.artifacts) ? entry.response.artifacts : []
      return artifacts.filter((artifact) => typeof artifact?.dataUrl === 'string' || typeof artifact?.url === 'string')
    },
    toPrettyJson(value) {
      return JSON.stringify(value, null, 2)
    },
  },
}
</script>

<style scoped>
.imported-study-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 20px;
  box-sizing: border-box;
  background: #f8fafc;
  color: #1f2937;
}

.imported-study-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.imported-study-title {
  font-size: 22px;
  font-weight: 800;
  color: #111827;
}

.imported-study-subtitle {
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.imported-study-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.imported-study-btn,
.imported-study-tab {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  padding: 8px 12px;
}

.imported-study-btn:hover,
.imported-study-tab:hover {
  border-color: #94a3b8;
}

.imported-study-error {
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid #fecaca;
  border-radius: 10px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 13px;
}

.imported-study-summary,
.imported-study-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.imported-study-chip {
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

.imported-study-tab.active {
  background: #e0f2fe;
  border-color: #7dd3fc;
  color: #0c4a6e;
}

.imported-study-body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
}

.imported-study-empty {
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

.imported-study-workspace,
.imported-study-contents {
  width: 100%;
  min-height: 0;
}

.imported-study-workspace {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 1px 6px rgba(15, 23, 42, 0.08);
}

.imported-study-contents {
  overflow: auto;
  padding-right: 8px;
}

.imported-study-section {
  margin-bottom: 18px;
}

.imported-study-section h3 {
  margin: 0 0 10px;
  font-size: 16px;
  color: #0f172a;
}

.imported-study-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.imported-study-card {
  border: 1px solid #dbe5f0;
  border-radius: 12px;
  background: #ffffff;
  padding: 12px;
  box-sizing: border-box;
}

.imported-study-card-wide {
  min-width: 0;
}

.imported-study-label {
  margin-bottom: 6px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.imported-study-notes {
  margin-top: 10px;
  border: 1px solid #dbe5f0;
  border-radius: 12px;
  background: #ffffff;
  padding: 12px;
  white-space: pre-wrap;
}

.imported-study-screenshots,
.imported-study-media-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.imported-study-screenshot-card {
  width: min(320px, 100%);
  border: 1px solid #dbe5f0;
  border-radius: 12px;
  background: #ffffff;
  padding: 12px;
  box-sizing: border-box;
}

.imported-study-screenshot,
.imported-study-media {
  display: block;
  width: 100%;
  max-width: 280px;
  border-radius: 10px;
  border: 1px solid #dbe5f0;
  background: #ffffff;
}

.imported-study-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.imported-study-list-item {
  border: 1px solid #dbe5f0;
  border-radius: 12px;
  background: #ffffff;
  padding: 12px;
}

.imported-study-list-title {
  font-weight: 700;
  color: #0f172a;
}

.imported-study-list-meta {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
}

.imported-study-text-block {
  margin-top: 10px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.imported-study-empty-inline {
  color: #64748b;
  font-size: 13px;
}

.imported-study-json {
  margin: 10px 0 0;
  padding: 10px;
  border-radius: 10px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.45;
  overflow: auto;
}
</style>
