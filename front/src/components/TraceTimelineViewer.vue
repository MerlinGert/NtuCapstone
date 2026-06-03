<template>
  <div class="trace-timeline-viewer">
    <div v-if="!hasTimelineData" class="trace-empty">
      No timestamped user actions or chat turns found in this archive.
    </div>

    <template v-else>
      <div class="trace-summary">
        <span class="trace-chip">{{ userEvents.length }} user events</span>
        <span class="trace-chip">{{ chatWindows.length }} chat turns</span>
        <span class="trace-chip">{{ activityEvents.length }} agent activity events</span>
        <span class="trace-chip">
          {{ estimatedActivityCount }} estimated activity timestamps
        </span>
        <span v-if="meanResponseMs !== null" class="trace-chip">
          Avg response {{ formatDuration(meanResponseMs) }}
        </span>
        <span v-if="timeRangeLabel" class="trace-chip">
          Window {{ timeRangeLabel }}
        </span>
      </div>

      <div class="trace-legend">
        <span class="trace-legend-item">
          <span class="trace-legend-swatch trace-user"></span>
          User interaction
        </span>
        <span class="trace-legend-item">
          <span class="trace-legend-swatch trace-chat-window"></span>
          LLM request -> response window
        </span>
        <span class="trace-legend-item">
          <span class="trace-legend-swatch trace-response"></span>
          LLM response
        </span>
        <span class="trace-legend-item">
          <span class="trace-legend-swatch trace-activity"></span>
          Agent activity / reasoning
        </span>
        <span class="trace-legend-item">
          <span class="trace-legend-swatch trace-llm-analysis"></span>
          LLM analysis artifact
        </span>
        <span class="trace-legend-item">
          <span class="trace-legend-swatch trace-estimated"></span>
          Estimated timing inside turn
        </span>
      </div>

      <div class="trace-axis">
        <div class="trace-axis-label">
          <div>{{ formatClock(timelineStart) }}</div>
          <div class="trace-axis-offset">+0s</div>
        </div>
        <div class="trace-axis-line"></div>
        <div class="trace-axis-label trace-axis-label-end">
          <div>{{ formatClock(timelineEnd) }}</div>
          <div class="trace-axis-offset">+{{ formatDuration(timelineEnd - timelineStart) }}</div>
        </div>
      </div>

      <div class="trace-lanes">
        <div class="trace-lane">
          <div class="trace-lane-header">
            <div class="trace-lane-title">User Interaction</div>
            <div class="trace-lane-subtitle">Recorded clicks, view switches, notes, and controls</div>
          </div>
          <div class="trace-track">
            <div class="trace-track-line"></div>
            <button
              v-for="event in userEvents"
              :key="event.key"
              type="button"
              class="trace-point trace-point-user"
              :class="{ active: selectedKey === event.key }"
              :style="pointStyle(event.atMs)"
              :title="event.tooltip"
              @click="selectedKey = event.key"
            ></button>
          </div>
        </div>

        <div class="trace-lane">
          <div class="trace-lane-header">
            <div class="trace-lane-title">LLM Request / Response</div>
            <div class="trace-lane-subtitle">Each bar spans from prompt send time to final assistant reply</div>
          </div>
          <div class="trace-track trace-track-window">
            <div class="trace-track-line"></div>
            <button
              v-for="window in chatWindows"
              :key="window.key"
              type="button"
              class="trace-window"
              :class="{ active: selectedKey === window.key }"
              :style="windowStyle(window)"
              :title="window.tooltip"
              @click="selectedKey = window.key"
            >
              <span class="trace-window-label">Turn {{ window.index }}</span>
              <span class="trace-window-duration">{{ formatDuration(window.durationMs) }}</span>
            </button>
            <button
              v-for="event in responseEvents"
              :key="event.key"
              type="button"
              class="trace-point trace-point-response"
              :class="{ active: selectedKey === event.key }"
              :style="pointStyle(event.atMs)"
              :title="event.tooltip"
              @click="selectedKey = event.key"
            ></button>
          </div>
        </div>

        <div class="trace-lane">
          <div class="trace-lane-header">
            <div class="trace-lane-title">Agent Activity / Reasoning</div>
            <div class="trace-lane-subtitle">
              {{ activitySubtitle }}
            </div>
          </div>
          <div class="trace-track">
            <div class="trace-track-line"></div>
            <button
              v-for="event in activityEvents"
              :key="event.key"
              type="button"
              class="trace-point trace-point-activity"
              :class="{ active: selectedKey === event.key, estimated: event.estimated }"
              :style="pointStyle(event.atMs)"
              :title="event.tooltip"
              @click="selectedKey = event.key"
            ></button>
          </div>
        </div>

        <div class="trace-lane">
          <div class="trace-lane-header">
            <div class="trace-lane-title">LLM Analysis Artifacts</div>
            <div class="trace-lane-subtitle">
              User reasoning graph arrival and later findings / patch updates recorded by the analysis panel
            </div>
          </div>
          <div class="trace-track">
            <div class="trace-track-line"></div>
            <button
              v-for="event in llmAnalysisEvents"
              :key="event.key"
              type="button"
              class="trace-point trace-point-llm-analysis"
              :class="{ active: selectedKey === event.key }"
              :style="pointStyle(event.atMs)"
              :title="event.tooltip"
              @click="selectedKey = event.key"
            ></button>
          </div>
        </div>
      </div>

      <div v-if="selectedItem" class="trace-detail">
        <div class="trace-detail-header">
          <div>
            <div class="trace-detail-title">{{ selectedItem.title }}</div>
            <div class="trace-detail-meta">
              {{ selectedItem.kindLabel }} · {{ formatClock(selectedItem.atMs) }} · +{{ formatDuration(selectedItem.atMs - timelineStart) }}
            </div>
          </div>
          <div v-if="selectedItem.durationMs !== null" class="trace-detail-duration">
            {{ formatDuration(selectedItem.durationMs) }}
          </div>
        </div>
        <div v-if="selectedItem.description" class="trace-detail-text">
          {{ selectedItem.description }}
        </div>
        <div v-if="selectedItem.badges?.length" class="trace-detail-badges">
          <span
            v-for="badge in selectedItem.badges"
            :key="badge"
            class="trace-detail-badge"
          >
            {{ badge }}
          </span>
        </div>
        <pre v-if="selectedItem.payload" class="trace-detail-json">{{ prettyJson(selectedItem.payload) }}</pre>
      </div>
    </template>
  </div>
</template>

<script>
const VIEW_LABELS = {
  token_distribution: 'Token Distribution',
  candlestick_chart: 'K-Line',
  behavior_details: 'Behavior Details',
  control_panel: 'Control Panel',
  chat: 'Chat',
  llm_analysis: 'LLM Analysis',
}

export default {
  name: 'TraceTimelineViewer',
  props: {
    actions: {
      type: Array,
      default: () => [],
    },
    chatbotLogs: {
      type: Array,
      default: () => [],
    },
    llmAnalysisTrace: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      selectedKey: '',
    }
  },
  computed: {
    userEvents() {
      return (this.actions || [])
        .map((action, index) => {
          const atMs = this.parseTimestamp(action?.timestamp)
          if (atMs === null) return null
          const actionType = this.formatActionType(action?.actionType)
          const view = this.formatView(action?.view || action?.sourceView || action?.targetView)
          const description = [
            action?.sourceView ? `Source: ${this.formatView(action.sourceView)}` : '',
            action?.targetView && action.targetView !== action.sourceView
              ? `Target: ${this.formatView(action.targetView)}`
              : '',
            action?.actionInfo ? this.summarizeActionInfo(action.actionInfo) : '',
          ].filter(Boolean).join(' | ')
          return {
            key: `user-${index}`,
            kind: 'user',
            kindLabel: 'User interaction',
            index: index + 1,
            atMs,
            title: `${actionType}${view ? ` · ${view}` : ''}`,
            description,
            badges: [action?.actionType || 'unknown'],
            payload: action,
            tooltip: `${actionType}${view ? ` · ${view}` : ''}\n${this.formatClock(atMs)}`,
            durationMs: null,
          }
        })
        .filter(Boolean)
    },
    chatWindows() {
      return (this.chatbotLogs || [])
        .map((entry, index) => {
          const promptMs = this.parseTimestamp(entry?.timestamp)
          const responseMs = this.parseTimestamp(entry?.response?.timestamp)
          if (promptMs === null && responseMs === null) return null
          const startMs = promptMs !== null ? promptMs : responseMs
          const endMs = responseMs !== null ? responseMs : promptMs
          const durationMs =
            promptMs !== null && responseMs !== null && responseMs >= promptMs
              ? responseMs - promptMs
              : 0
          return {
            key: `chat-window-${index}`,
            kind: 'chat_window',
            kindLabel: 'LLM request/response window',
            index: index + 1,
            atMs: startMs,
            startMs,
            endMs,
            durationMs,
            title: `Turn ${index + 1} · ${entry?.triggerType || 'manual'}`,
            description: entry?.prompt || '',
            badges: [
              entry?.triggerType || 'manual',
              ...(Array.isArray(entry?.response?.responseTypes) ? entry.response.responseTypes : []),
            ].filter(Boolean),
            payload: entry,
            tooltip: `Turn ${index + 1}\n${this.formatClock(startMs)} -> ${this.formatClock(endMs)}\n${this.formatDuration(durationMs)}`,
          }
        })
        .filter(Boolean)
    },
    responseEvents() {
      return this.chatWindows
        .filter((window) => Number.isFinite(window.endMs))
        .map((window) => ({
          key: `${window.key}-response`,
          kind: 'response',
          kindLabel: 'LLM response',
          index: window.index,
          atMs: window.endMs,
          title: `${window.title} response`,
          description: window.payload?.response?.text || '',
          badges: Array.isArray(window.payload?.response?.responseTypes)
            ? window.payload.response.responseTypes
            : [],
          payload: window.payload?.response || null,
          tooltip: `${window.title} response\n${this.formatClock(window.endMs)}`,
          durationMs: null,
        }))
    },
    activityEvents() {
      return this.chatWindows.flatMap((window) => {
        const activities = Array.isArray(window.payload?.response?.activity)
          ? window.payload.response.activity
          : []
        return activities
          .map((activity, index) => this.normalizeActivityEvent(activity, window, index, activities.length))
          .filter(Boolean)
      })
    },
    llmAnalysisEvents() {
      return (this.llmAnalysisTrace || [])
        .map((entry, index) => {
          const atMs = this.parseTimestamp(entry?.timestamp)
          if (atMs === null) return null
          return {
            key: entry?.traceKey || `llm-analysis-${index}`,
            kind: 'llm_analysis',
            kindLabel: 'LLM analysis artifact',
            atMs,
            index: index + 1,
            title: entry?.label || entry?.eventType || `LLM analysis event ${index + 1}`,
            description: [
              entry?.artifactName ? `Artifact: ${entry.artifactName}` : '',
              entry?.artifactModifiedAt ? `Artifact mtime: ${entry.artifactModifiedAt}` : '',
            ].filter(Boolean).join('\n'),
            badges: [
              entry?.eventType || 'llm_analysis',
              entry?.patchName || '',
              Number.isFinite(entry?.patchCount) ? `${entry.patchCount} patches` : '',
            ].filter(Boolean),
            payload: entry,
            tooltip: `${entry?.label || entry?.eventType || 'LLM analysis event'}\n${this.formatClock(atMs)}`,
            durationMs: null,
          }
        })
        .filter(Boolean)
    },
    estimatedActivityCount() {
      return this.activityEvents.filter((event) => event.estimated).length
    },
    allTimedItems() {
      return [
        ...this.userEvents,
        ...this.chatWindows,
        ...this.responseEvents,
        ...this.activityEvents,
        ...this.llmAnalysisEvents,
      ]
        .filter((item) => Number.isFinite(item?.atMs))
    },
    hasTimelineData() {
      return this.allTimedItems.length > 0
    },
    timelineStart() {
      if (!this.hasTimelineData) return 0
      return Math.min(...this.allTimedItems.map((item) => item.atMs))
    },
    timelineEnd() {
      if (!this.hasTimelineData) return 1000
      const maxMs = Math.max(...this.allTimedItems.map((item) => item.atMs))
      return maxMs === this.timelineStart ? maxMs + 1000 : maxMs
    },
    meanResponseMs() {
      const durations = this.chatWindows
        .map((window) => window.durationMs)
        .filter((value) => Number.isFinite(value) && value >= 0)
      if (!durations.length) return null
      return durations.reduce((sum, value) => sum + value, 0) / durations.length
    },
    timeRangeLabel() {
      if (!this.hasTimelineData) return ''
      return `${this.formatClock(this.timelineStart)} - ${this.formatClock(this.timelineEnd)}`
    },
    activitySubtitle() {
      return this.estimatedActivityCount > 0
        ? 'Estimated positions are distributed within each request-response window when raw timestamps are absent'
        : 'Activity points use recorded timestamps from assistant events'
    },
    selectedItem() {
      if (!this.selectedKey) return null
      return this.allTimedItems.find((item) => item.key === this.selectedKey) || null
    },
  },
  watch: {
    hasTimelineData: {
      immediate: true,
      handler(value) {
        if (!value) {
          this.selectedKey = ''
          return
        }
        if (this.selectedKey && this.selectedItem) return
        this.selectedKey = this.llmAnalysisEvents[0]?.key
          || this.chatWindows[0]?.key
          || this.userEvents[0]?.key
          || this.activityEvents[0]?.key
          || ''
      },
    },
  },
  methods: {
    parseTimestamp(value) {
      if (!value) return null
      const ms = new Date(value).getTime()
      return Number.isFinite(ms) ? ms : null
    },
    formatClock(ms) {
      if (!Number.isFinite(ms)) return '-'
      return new Date(ms).toLocaleTimeString(undefined, {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    },
    formatDuration(ms) {
      if (!Number.isFinite(ms)) return '-'
      if (ms < 1000) return `${Math.round(ms)}ms`
      const totalSeconds = ms / 1000
      if (totalSeconds < 60) return `${totalSeconds.toFixed(totalSeconds < 10 ? 1 : 0)}s`
      const minutes = Math.floor(totalSeconds / 60)
      const seconds = totalSeconds % 60
      return `${minutes}m ${seconds.toFixed(seconds < 10 ? 1 : 0)}s`
    },
    percentAt(ms) {
      if (!this.hasTimelineData) return 0
      const range = this.timelineEnd - this.timelineStart || 1
      return ((ms - this.timelineStart) / range) * 100
    },
    pointStyle(ms) {
      return {
        left: `${this.percentAt(ms)}%`,
      }
    },
    windowStyle(window) {
      const start = this.percentAt(window.startMs)
      const end = this.percentAt(window.endMs)
      const width = Math.max(end - start, 0.8)
      return {
        left: `${start}%`,
        width: `${width}%`,
      }
    },
    formatActionType(value) {
      if (!value) return 'Unknown action'
      return String(value)
        .split('_')
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' ')
    },
    formatView(value) {
      if (!value) return ''
      return VIEW_LABELS[value] || String(value)
        .split('_')
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' ')
    },
    summarizeActionInfo(value) {
      if (!value) return ''
      if (typeof value === 'string') return value
      if (Array.isArray(value)) return `${value.length} merged events`
      const keys = Object.keys(value).slice(0, 4)
      return keys.map((key) => `${key}: ${this.formatInlineValue(value[key])}`).join(', ')
    },
    formatInlineValue(value) {
      if (Array.isArray(value)) return `[${value.length}]`
      if (value && typeof value === 'object') return '{...}'
      return String(value)
    },
    extractActivityTimestamp(activity) {
      if (!activity || typeof activity !== 'object') return null
      const candidates = [
        activity.timestamp,
        activity.createdAt,
        activity.startedAt,
        activity.finishedAt,
        activity.time,
      ]
      for (const candidate of candidates) {
        const parsed = this.parseTimestamp(candidate)
        if (parsed !== null) return parsed
      }
      return null
    },
    normalizeActivityEvent(activity, window, index, total) {
      const parsedAt = this.extractActivityTimestamp(activity)
      const hasExplicitTimestamp = parsedAt !== null
      let atMs = parsedAt
      if (atMs === null) {
        if (!Number.isFinite(window.startMs)) return null
        if (Number.isFinite(window.endMs) && window.endMs >= window.startMs && total > 0) {
          const ratio = (index + 1) / (total + 1)
          atMs = window.startMs + (window.endMs - window.startMs) * ratio
        } else {
          atMs = window.startMs
        }
      }
      const title = String(activity?.title || activity?.text || activity?.command || activity?.category || 'Activity')
      const detail = [activity?.detail, activity?.output].filter(Boolean).join('\n')
      return {
        key: `${window.key}-activity-${index}`,
        kind: 'activity',
        kindLabel: hasExplicitTimestamp ? 'Agent activity' : 'Agent activity (estimated)',
        atMs,
        index: index + 1,
        title: `${window.title} · ${title}`,
        description: detail,
        badges: [
          activity?.category || activity?.type || 'activity',
          activity?.status || '',
          hasExplicitTimestamp ? 'timestamped' : 'estimated',
        ].filter(Boolean),
        payload: activity,
        tooltip: `${title}\n${this.formatClock(atMs)}${hasExplicitTimestamp ? '' : '\nEstimated inside turn'}`,
        durationMs: null,
        estimated: !hasExplicitTimestamp,
      }
    },
    prettyJson(value) {
      return JSON.stringify(value, null, 2)
    },
  },
}
</script>

<style scoped>
.trace-timeline-viewer {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.trace-empty {
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
  background: #ffffff;
  color: #64748b;
  padding: 20px;
  text-align: center;
  font-size: 14px;
}

.trace-summary,
.trace-legend,
.trace-detail-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.trace-chip,
.trace-detail-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid #d8e0ec;
  background: #ffffff;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.trace-legend {
  color: #475569;
  font-size: 12px;
  font-weight: 600;
}

.trace-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.trace-legend-swatch {
  width: 16px;
  height: 8px;
  border-radius: 999px;
  display: inline-block;
}

.trace-user {
  background: #0ea5e9;
}

.trace-chat-window {
  background: rgba(147, 51, 234, 0.18);
  border: 1px solid rgba(147, 51, 234, 0.45);
  box-sizing: border-box;
}

.trace-response {
  background: #7c3aed;
}

.trace-activity {
  background: #f97316;
}

.trace-estimated {
  background: #ffffff;
  border: 2px dashed #f97316;
  box-sizing: border-box;
}

.trace-llm-analysis {
  background: #ec4899;
}

.trace-axis {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 12px;
  align-items: center;
}

.trace-axis-line {
  height: 2px;
  background: linear-gradient(90deg, #cbd5e1 0%, #94a3b8 100%);
  border-radius: 999px;
}

.trace-axis-label {
  font-size: 12px;
  font-weight: 700;
  color: #334155;
}

.trace-axis-offset {
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
}

.trace-axis-label-end {
  text-align: right;
}

.trace-lanes {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.trace-lane {
  border: 1px solid #dbe5f0;
  border-radius: 14px;
  background: #ffffff;
  padding: 14px;
}

.trace-lane-header {
  margin-bottom: 12px;
}

.trace-lane-title {
  font-size: 14px;
  font-weight: 800;
  color: #0f172a;
}

.trace-lane-subtitle {
  margin-top: 3px;
  font-size: 12px;
  color: #64748b;
}

.trace-track {
  position: relative;
  height: 48px;
}

.trace-track-window {
  height: 60px;
}

.trace-track-line {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 2px;
  background: #e2e8f0;
  transform: translateY(-50%);
  border-radius: 999px;
}

.trace-point,
.trace-window {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  border: none;
  cursor: pointer;
  transition: box-shadow 120ms ease, transform 120ms ease;
}

.trace-point:hover,
.trace-window:hover,
.trace-point.active,
.trace-window.active {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18);
}

.trace-point {
  width: 14px;
  height: 14px;
  border-radius: 999px;
}

.trace-point-user {
  background: #0ea5e9;
}

.trace-point-response {
  background: #7c3aed;
}

.trace-point-activity {
  background: #f97316;
}

.trace-point-llm-analysis {
  background: #ec4899;
}

.trace-point-activity.estimated {
  background: #ffffff;
  border: 2px dashed #f97316;
}

.trace-window {
  height: 24px;
  min-width: 12px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(147, 51, 234, 0.14);
  border: 1px solid rgba(147, 51, 234, 0.38);
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #581c87;
  font-size: 11px;
  font-weight: 800;
  overflow: hidden;
  white-space: nowrap;
}

.trace-window-label,
.trace-window-duration {
  pointer-events: none;
}

.trace-detail {
  border: 1px solid #dbe5f0;
  border-radius: 14px;
  background: #ffffff;
  padding: 14px;
}

.trace-detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.trace-detail-title {
  font-size: 15px;
  font-weight: 800;
  color: #0f172a;
}

.trace-detail-meta {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.trace-detail-duration {
  font-size: 12px;
  font-weight: 800;
  color: #7c3aed;
  white-space: nowrap;
}

.trace-detail-text {
  margin-top: 10px;
  color: #334155;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.trace-detail-json {
  margin: 10px 0 0;
  padding: 12px;
  border-radius: 10px;
  background: #f8fafc;
  color: #334155;
  overflow: auto;
  font-size: 12px;
  line-height: 1.5;
}
</style>
