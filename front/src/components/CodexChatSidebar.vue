<template>
  <aside
    ref="sidebar"
    class="codex-chat-sidebar"
    :class="{ open, moving: !!panelDragState, resizing: !!panelResizeState }"
    :style="panelStyle"
    aria-label="Codex chat"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="handleDrop"
  >
    <div class="codex-chat-header" @pointerdown="startPanelDrag">
      <div>
        <div class="codex-chat-title">Codex Chat</div>
        <div class="codex-chat-subtitle">
          Session {{ sessionId || 'pending' }} · {{ workspaceLabel }}
        </div>
      </div>
      <button class="codex-chat-icon-btn" type="button" title="Close chat" @click="$emit('close')">
        ×
      </button>
    </div>

    <div class="codex-chat-status">
      <span :class="syncInFlight ? 'status-dot syncing' : 'status-dot'"></span>
      <span>{{ syncStatusText }}</span>
    </div>

    <div ref="messagesEl" class="codex-chat-messages" @paste="handlePaste">
      <div v-if="messages.length === 0" class="codex-chat-empty">
        {{ emptyStateText }}
      </div>

      <div
        v-for="message in messages"
        :key="message.id"
        class="codex-chat-message"
        :class="message.role === 'user' ? 'user' : 'assistant'"
      >
        <div class="message-role">{{ message.role === 'user' ? 'You' : 'Codex' }}</div>
        <div class="message-bubble">
          <div
            v-if="message.role === 'assistant' && (message.loading || message.ephemeralReasoning || (message.activity && message.activity.length))"
            class="message-status-stack"
          >
            <div v-if="message.loading" class="message-loading">
              <span class="loading-pulse"></span>
              {{ stopRequested ? 'Stopping Codex...' : 'Codex is working...' }}
            </div>
            <div v-if="message.ephemeralReasoning && message.thinkingOpen !== false" class="reasoning-bubble">
              <div class="reasoning-label">Thinking</div>
              <div class="reasoning-text">{{ message.ephemeralReasoning }}</div>
            </div>
            <div
              v-if="message.activity && message.activity.length"
              class="message-activity"
              :class="{ 'message-activity-after-thinking': hasVisibleThinking(message) }"
            >
              <div class="activity-header">
                <span>Agent activity</span>
              </div>
              <div v-if="message.activityOpen && displayedActivities(message).length" class="activity-list">
                <div
                  v-for="activity in displayedActivities(message)"
                  :key="activity.id"
                  class="activity-item"
                  :class="activityClass(activity)"
                >
                  <span class="activity-dot"></span>
                  <span class="activity-body">
                    <span class="activity-title">{{ activity.title || activity.text }}</span>
                    <span v-if="activity.detail" class="activity-detail">{{ activity.detail }}</span>
                    <span v-if="activity.output && message.activityOpen" class="activity-output">
                      {{ activity.output }}
                    </span>
                  </span>
                </div>
              </div>
              <div v-else-if="collapsedActivities(message).length" class="activity-list activity-list-collapsed">
                <div
                  v-for="activity in collapsedActivities(message)"
                  :key="activity.id"
                  class="activity-item activity-item-latest"
                  :class="activityClass(activity)"
                >
                  <span class="activity-dot"></span>
                  <span class="activity-body">
                    <span class="activity-title">{{ activity.title || activity.text }}</span>
                    <span v-if="activity.detail" class="activity-detail">{{ activity.detail }}</span>
                  </span>
                </div>
              </div>
              <div class="activity-footer">
                <button type="button" class="activity-toggle" @click="message.activityOpen = !message.activityOpen">
                  {{ activityToggleLabel(message) }}
                </button>
              </div>
            </div>
          </div>
          <div
            v-if="message.content && message.role === 'assistant'"
            class="message-markdown"
            v-html="renderMarkdown(message.content)"
          ></div>
          <div
            v-else-if="message.content"
            class="message-text"
            :class="{ 'message-preset-text': message.presetKind }"
          >
            {{ message.content }}
          </div>
          <div v-if="message.artifacts && message.artifacts.length" class="message-artifacts">
            <a
              v-for="artifact in message.artifacts"
              :key="artifact.id"
              class="artifact-link"
              :href="artifactHref(artifact)"
              target="_blank"
              rel="noreferrer"
            >
              <img
                v-if="artifact.kind === 'image'"
                class="artifact-thumb"
                :src="artifactHref(artifact)"
                :alt="artifact.title"
              />
              <span>{{ artifact.title }}</span>
            </a>
          </div>
          <div v-if="message.attachments && message.attachments.length" class="message-attachments">
            <div v-for="attachment in message.attachments" :key="attachment.id" class="attachment-pill">
              {{ attachment.name }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="sending" class="codex-chat-working">Syncing trace and preparing Codex context...</div>
    </div>

    <div v-if="attachments.length" class="codex-chat-attachments">
      <div v-for="attachment in attachments" :key="attachment.id" class="attachment-preview">
        <img :src="attachment.url" :alt="attachment.name" />
        <button type="button" title="Remove attachment" @click="removeAttachment(attachment.id)">×</button>
      </div>
    </div>

    <div v-if="dragging" class="codex-chat-drop-hint">Drop images to attach</div>

    <div class="codex-chat-input-area">
      <div v-if="sessionMode !== 'baseline'" class="codex-chat-preset-row">
        <button
          class="codex-chat-preset-btn"
          type="button"
          title="Run full trace analysis with counter-evidence search"
          :disabled="sending"
          @click="sendFullAnalysisPrompt"
        >
          Run Full Analysis
        </button>
        <button
          class="codex-chat-preset-btn codex-chat-update-btn"
          type="button"
          :title="analysisGraphAvailable ? 'Run incremental analysis against the current graph' : 'Available after reasoning-graph.json is present in LLM Analysis'"
          :disabled="sending || !analysisGraphAvailable"
          @click="sendUpdateAnalysisPrompt"
        >
          Update Analysis
        </button>
      </div>
      <textarea
        ref="inputEl"
        v-model="draft"
        class="codex-chat-input"
        placeholder="Ask Codex about the current trace..."
        rows="2"
        :disabled="sending"
        @keydown="handleKeydown"
        @paste="handlePaste"
      ></textarea>
      <div class="codex-chat-actions">
        <button
          class="codex-chat-action-btn codex-chat-secondary"
          type="button"
          title="Attach images"
          aria-label="Attach images"
          @click="$refs.fileInput.click()"
        >
          <svg class="chat-action-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M21.4 11.6 12 21a6 6 0 0 1-8.5-8.5l9.9-9.9a4 4 0 0 1 5.7 5.7l-9.9 9.9a2 2 0 0 1-2.8-2.8l9.4-9.4" />
          </svg>
        </button>
        <button
          v-if="sending"
          class="codex-chat-action-btn codex-chat-stop"
          type="button"
          :title="stopRequested ? 'Stopping Codex turn' : 'Stop the current Codex turn'"
          :aria-label="stopRequested ? 'Stopping Codex turn' : 'Stop the current Codex turn'"
          :disabled="stopRequested"
          @click="stopCodexTurn"
        >
          <svg class="chat-action-icon" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="7" y="7" width="10" height="10" rx="1.5" />
          </svg>
        </button>
        <button
          class="codex-chat-action-btn codex-chat-send"
          type="button"
          title="Send message"
          aria-label="Send message"
          :disabled="sending || (!draft.trim() && attachments.length === 0)"
          @click="sendMessage()"
        >
          <svg class="chat-action-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M22 2 11 13" />
            <path d="m22 2-7 20-4-9-9-4 20-7Z" />
          </svg>
        </button>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        multiple
        style="display:none"
        @change="handleFileInput"
      />
    </div>
    <div
      class="panel-resize-handle resize-bottom-left"
      title="Resize chat panel"
      @pointerdown="startPanelResize($event, 'bottom-left')"
    ></div>
    <div
      class="panel-resize-handle resize-bottom-right"
      title="Resize chat panel"
      @pointerdown="startPanelResize($event, 'bottom-right')"
    ></div>
  </aside>
</template>

<script>
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'

const FULL_ANALYSIS_PROMPT = 'please run a pass of full trace analysis with a subagent for finding counter-evidence.'
const UPDATE_ANALYSIS_PROMPT = `Please run an incremental trace analysis pass for the current session.

Do not redo the full trace analysis unless incremental analysis is unsafe. Refresh live-session.json, current-state.json, session git history, and the analysis artifact manifest. Compare the latest graph or patch trace anchor against the current live trace anchor.

If reasoning-graph-patch*.json files already exist, first run:

bun trace_analysis_tools/reasoning_graph/cli.ts materialize artifacts

Read current-reasoning-graph.json as the complete patched context, but do not treat it as the source of truth.

Analyze only the new user Interactions and annotations after the latest applied anchor. Use the existing materialized graph as context. Do not rewrite reasoning-graph.json unless checkpointing is required.

Write any new evidence as:

reasoning-graph-patch-incremental-<fromRevision>-<toRevision>.json

The patch must include patchType: "incremental", baseAnchor, targetAnchor, and precise provenance for the new trace range. Add new Findings, Hypotheses, Interactions, and edges only when they are supported by the new trace delta or by follow-up checks triggered by that delta.

Use update_node only to refine metadata on existing nodes. Use add_node/add_edge for new evidence and relationships. Agent-created nodes must include explanation, evidenceSummary, reasoningRole, and patchRationale.

If the new trace delta adds no material evidence, report that no patch was produced and explain exactly what delta you checked.

After writing the patch, run:

bun trace_analysis_tools/reasoning_graph/cli.ts artifacts

Fix validation errors before reporting completion. If the validator recommends checkpointing because active patch count reaches 8, run checkpoint unless I explicitly ask to preserve the patch stack.

Final response format:

# Technical Audit

Report the operational details here:
- previous anchor,
- new trace anchor,
- analyzed action and annotation range,
- patch file written,
- supporting evidence files,
- validation result,
- checkpoint status,
- unresolved warnings.

Keep this section concise and factual.

# Plain-English Summary

Explain the analytical meaning for the human analyst:
- what new user behavior was analyzed,
- what the user seemed to be checking,
- what new evidence was found,
- which Hypotheses were strengthened, weakened, or refined,
- whether a new Hypothesis was created or not,
- what caveats matter,
- what the analyst should pay attention to next.

Do not lead this section with revision numbers, digests, patch filenames, node IDs, or validation counts. Use human-readable names for Hypotheses and Findings.`
const markdown = new MarkdownIt({
  breaks: true,
  linkify: true,
})
const PANEL_LAYOUT_STORAGE_KEY = 'maniscope.codexChat.panelLayout.v1'
const PANEL_MARGIN = 8

export default {
  name: 'CodexChatSidebar',
  props: {
    open: {
      type: Boolean,
      default: false,
    },
    sessionId: {
      type: String,
      default: '',
    },
    sessionMode: {
      type: String,
      default: 'specialized',
      validator: (value) => ['specialized', 'baseline'].includes(value),
    },
    workspaceRole: {
      type: String,
      default: 'human',
      validator: (value) => ['human', 'agent'].includes(value),
    },
    syncInFlight: {
      type: Boolean,
      default: false,
    },
    lastSyncAt: {
      type: String,
      default: null,
    },
    beforeSend: {
      type: Function,
      default: null,
    },
  },
  emits: ['close', 'send'],
  data() {
    return {
      draft: '',
      messages: [],
      attachments: [],
      sending: false,
      stopRequested: false,
      dragging: false,
      nextMessageId: 1,
      nextAttachmentId: 1,
      nextActivityId: 1,
      historyLoadedForSession: '',
      panelPositioned: false,
      panelX: 0,
      panelY: 0,
      panelWidth: 520,
      panelHeight: 640,
      panelDragState: null,
      panelResizeState: null,
      analysisGraphAvailable: false,
    }
  },
  computed: {
    syncStatusText() {
      if (this.syncInFlight || this.sending) return 'Syncing live trace'
      if (this.lastSyncAt) return `Live trace synced ${new Date(this.lastSyncAt).toLocaleTimeString()}`
      return 'Live trace will sync before each message'
    },
    workspaceLabel() {
      if (this.sessionMode === 'baseline') return 'Baseline'
      return this.workspaceRole === 'agent' ? 'Agent Workspace' : 'Human Workspace'
    },
    chatApiBase() {
      return this.sessionMode === 'baseline' ? '/api/base/chat' : '/api/chat'
    },
    sessionApiBase() {
      return this.sessionMode === 'baseline' ? '/api/base/sessions' : '/api/sessions'
    },
    emptyStateText() {
      if (this.sessionMode === 'baseline') {
        return 'Ask Codex to inspect the current trace, screenshots, or raw market data.'
      }
      return 'Ask Codex to inspect the current trace, explain an interaction path, or draft a trace analysis.'
    },
    panelStyle() {
      if (!this.panelPositioned) return null
      return {
        left: `${this.panelX}px`,
        top: `${this.panelY}px`,
        right: 'auto',
        bottom: 'auto',
        width: `${this.panelWidth}px`,
        height: `${this.panelHeight}px`,
      }
    },
  },
  mounted() {
    this.restorePanelLayout()
    window.addEventListener('resize', this.clampPanelToViewport)
    window.addEventListener('maniscope-session-artifact-updated', this.handleSessionArtifactUpdated)
    this.refreshAnalysisAvailability()
  },
  beforeUnmount() {
    this.attachments.forEach((attachment) => URL.revokeObjectURL(attachment.url))
    this.detachPanelPointerListeners()
    window.removeEventListener('resize', this.clampPanelToViewport)
    window.removeEventListener('maniscope-session-artifact-updated', this.handleSessionArtifactUpdated)
  },
  watch: {
    sessionId: {
      immediate: true,
      handler(sessionId) {
        if (sessionId) {
          this.loadChatHistory(sessionId)
        } else {
          this.messages = []
          this.historyLoadedForSession = ''
          this.analysisGraphAvailable = false
        }
        this.refreshAnalysisAvailability()
      },
    },
    sessionMode() {
      this.historyLoadedForSession = ''
      if (this.sessionId) this.loadChatHistory(this.sessionId)
      this.refreshAnalysisAvailability()
    },
    open(isOpen) {
      if (isOpen) this.refreshAnalysisAvailability()
    },
  },
  methods: {
    clamp(value, min, max) {
      return Math.min(max, Math.max(min, value))
    },
    panelMinWidth() {
      return Math.min(360, Math.max(280, window.innerWidth - PANEL_MARGIN * 2))
    },
    panelMinHeight() {
      return Math.min(360, Math.max(300, window.innerHeight - PANEL_MARGIN * 2))
    },
    restorePanelLayout() {
      if (typeof window === 'undefined') return
      try {
        const saved = JSON.parse(window.localStorage.getItem(PANEL_LAYOUT_STORAGE_KEY) || 'null')
        if (!saved || typeof saved !== 'object') return
        const { x, y, width, height } = saved
        if (![x, y, width, height].every((value) => Number.isFinite(Number(value)))) return
        this.panelX = Number(x)
        this.panelY = Number(y)
        this.panelWidth = Number(width)
        this.panelHeight = Number(height)
        this.panelPositioned = true
        this.clampPanelToViewport()
      } catch (_error) {
        // Ignore invalid local layout state.
      }
    },
    savePanelLayout() {
      if (typeof window === 'undefined' || !this.panelPositioned) return
      window.localStorage.setItem(
        PANEL_LAYOUT_STORAGE_KEY,
        JSON.stringify({
          x: this.panelX,
          y: this.panelY,
          width: this.panelWidth,
          height: this.panelHeight,
        }),
      )
    },
    ensurePanelPositioned() {
      if (this.panelPositioned) return
      const rect = this.$refs.sidebar?.getBoundingClientRect?.()
      if (!rect) return
      this.panelX = Math.round(rect.left)
      this.panelY = Math.round(rect.top)
      this.panelWidth = Math.round(rect.width)
      this.panelHeight = Math.round(rect.height)
      this.panelPositioned = true
      this.clampPanelToViewport()
    },
    clampPanelToViewport() {
      if (!this.panelPositioned || typeof window === 'undefined') return
      const maxWidth = Math.max(this.panelMinWidth(), window.innerWidth - PANEL_MARGIN * 2)
      const maxHeight = Math.max(this.panelMinHeight(), window.innerHeight - PANEL_MARGIN * 2)
      this.panelWidth = this.clamp(this.panelWidth, this.panelMinWidth(), maxWidth)
      this.panelHeight = this.clamp(this.panelHeight, this.panelMinHeight(), maxHeight)
      this.panelX = this.clamp(this.panelX, PANEL_MARGIN, window.innerWidth - this.panelWidth - PANEL_MARGIN)
      this.panelY = this.clamp(this.panelY, PANEL_MARGIN, window.innerHeight - this.panelHeight - PANEL_MARGIN)
    },
    detachPanelPointerListeners() {
      window.removeEventListener('pointermove', this.handlePanelPointerMove)
      window.removeEventListener('pointerup', this.stopPanelPointerInteraction)
      window.removeEventListener('pointercancel', this.stopPanelPointerInteraction)
    },
    startPanelDrag(event) {
      if (!this.open || event.button !== 0) return
      if (event.target?.closest?.('button, a, input, textarea, .panel-resize-handle')) return
      this.ensurePanelPositioned()
      event.preventDefault()
      this.panelDragState = {
        pointerId: event.pointerId,
        startClientX: event.clientX,
        startClientY: event.clientY,
        startX: this.panelX,
        startY: this.panelY,
      }
      window.addEventListener('pointermove', this.handlePanelPointerMove)
      window.addEventListener('pointerup', this.stopPanelPointerInteraction)
      window.addEventListener('pointercancel', this.stopPanelPointerInteraction)
    },
    startPanelResize(event, edge) {
      if (!this.open || event.button !== 0) return
      this.ensurePanelPositioned()
      event.preventDefault()
      event.stopPropagation()
      this.panelResizeState = {
        edge,
        pointerId: event.pointerId,
        startClientX: event.clientX,
        startClientY: event.clientY,
        startX: this.panelX,
        startY: this.panelY,
        startWidth: this.panelWidth,
        startHeight: this.panelHeight,
      }
      window.addEventListener('pointermove', this.handlePanelPointerMove)
      window.addEventListener('pointerup', this.stopPanelPointerInteraction)
      window.addEventListener('pointercancel', this.stopPanelPointerInteraction)
    },
    handlePanelPointerMove(event) {
      if (this.panelDragState && event.pointerId === this.panelDragState.pointerId) {
        const dx = event.clientX - this.panelDragState.startClientX
        const dy = event.clientY - this.panelDragState.startClientY
        this.panelX = this.panelDragState.startX + dx
        this.panelY = this.panelDragState.startY + dy
        this.clampPanelToViewport()
      } else if (this.panelResizeState && event.pointerId === this.panelResizeState.pointerId) {
        const dx = event.clientX - this.panelResizeState.startClientX
        const dy = event.clientY - this.panelResizeState.startClientY
        const minWidth = this.panelMinWidth()
        const minHeight = this.panelMinHeight()
        const rightEdge = this.panelResizeState.startX + this.panelResizeState.startWidth
        if (this.panelResizeState.edge === 'bottom-left') {
          const maxWidth = Math.max(minWidth, rightEdge - PANEL_MARGIN)
          this.panelWidth = this.clamp(this.panelResizeState.startWidth - dx, minWidth, maxWidth)
          this.panelX = rightEdge - this.panelWidth
        } else {
          const maxWidth = Math.max(minWidth, window.innerWidth - this.panelResizeState.startX - PANEL_MARGIN)
          this.panelWidth = this.clamp(this.panelResizeState.startWidth + dx, minWidth, maxWidth)
          this.panelX = this.panelResizeState.startX
        }
        const maxHeight = Math.max(minHeight, window.innerHeight - this.panelResizeState.startY - PANEL_MARGIN)
        this.panelHeight = this.clamp(this.panelResizeState.startHeight + dy, minHeight, maxHeight)
        this.panelY = this.panelResizeState.startY
        this.clampPanelToViewport()
      }
    },
    stopPanelPointerInteraction() {
      if (!this.panelDragState && !this.panelResizeState) return
      this.panelDragState = null
      this.panelResizeState = null
      this.detachPanelPointerListeners()
      this.savePanelLayout()
    },
    renderMarkdown(content) {
      return DOMPurify.sanitize(markdown.render(content || ''))
    },
    normalizeActivity(activity, fallbackId) {
      if (typeof activity === 'string') {
        return {
          id: fallbackId,
          text: activity,
          title: activity,
          detail: '',
          output: '',
          level: 'detail',
          category: 'legacy',
          status: '',
          eventId: '',
          ephemeral: false,
        }
      }

      const payload = activity && typeof activity === 'object' ? activity : {}
      const title = String(payload.title || payload.text || payload.command || payload.type || 'Activity')
      const detail = String(payload.detail || '')
      return {
        id: payload.id || fallbackId,
        text: String(payload.text || title),
        title,
        detail,
        output: String(payload.output || ''),
        level: ['primary', 'highlight', 'detail', 'debug', 'error', 'ephemeral'].includes(payload.level)
          ? payload.level
          : 'detail',
        category: String(payload.category || payload.type || 'event'),
        status: String(payload.status || ''),
        eventId: String(payload.eventId || ''),
        ephemeral: Boolean(payload.ephemeral),
      }
    },
    normalizeHistoryMessage(message, fallbackId) {
      return {
        id: Number(message.id) || fallbackId,
        role: message.role === 'user' ? 'user' : 'assistant',
        content: String(message.content || ''),
        attachments: Array.isArray(message.attachments) ? message.attachments : [],
        activity: Array.isArray(message.activity)
          ? message.activity.map((activity, index) => this.normalizeActivity(activity, `${fallbackId}-${index + 1}`))
          : [],
        artifacts: Array.isArray(message.artifacts) ? message.artifacts : [],
        presetKind: String(message.presetKind || ''),
        activityOpen: Boolean(message.activityOpen),
        threadId: message.threadId || '',
        createdAt: message.createdAt || '',
        loading: false,
        thinkingOpen: false,
        ephemeralReasoning: '',
      }
    },
    serializeMessages() {
      return this.messages.map((message) => ({
        id: message.id,
        role: message.role,
        content: message.content || '',
        attachments: message.attachments || [],
        activity: (message.activity || []).filter((activity) => !activity.ephemeral),
        artifacts: message.artifacts || [],
        presetKind: message.presetKind || '',
        activityOpen: Boolean(message.activityOpen),
        threadId: message.threadId || '',
        createdAt: message.createdAt || '',
      }))
    },
    async loadChatHistory(sessionId = this.sessionId) {
      const historyKey = `${this.sessionMode}:${sessionId}`
      if (!sessionId || this.historyLoadedForSession === historyKey) return
      try {
        const response = await fetch(`${this.chatApiBase}/${sessionId}/history?threadKey=trace-analysis`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const payload = await response.json()
        const messages = Array.isArray(payload.messages) ? payload.messages : []
        this.messages = messages.map((message, index) => this.normalizeHistoryMessage(message, index + 1))
        this.nextMessageId = this.messages.reduce((maxId, message) => Math.max(maxId, message.id), 0) + 1
        this.nextActivityId =
          this.messages.reduce((maxId, message) => {
            const activityMax = (message.activity || []).reduce(
              (innerMax, activity) => Math.max(innerMax, Number(activity.id) || 0),
              0,
            )
            return Math.max(maxId, activityMax)
          }, 0) + 1
        this.historyLoadedForSession = historyKey
        this.scrollToBottom()
      } catch (error) {
        this.historyLoadedForSession = historyKey
        this.messages = [
          {
            id: this.nextMessageId++,
            role: 'assistant',
            content: `Error loading chat history: ${error && error.message ? error.message : String(error)}`,
            activity: [],
            artifacts: [],
          },
        ]
      }
    },
    async persistChatHistory() {
      if (!this.sessionId) return
      await fetch(`${this.chatApiBase}/${this.sessionId}/history`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          threadKey: 'trace-analysis',
          messages: this.serializeMessages(),
        }),
      })
    },
    handleKeydown(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        this.sendMessage()
      }
    },
    handleFileInput(event) {
      this.addFiles(Array.from(event.target.files || []))
      event.target.value = ''
    },
    handleDrop(event) {
      this.dragging = false
      this.addFiles(Array.from(event.dataTransfer?.files || []))
    },
    handlePaste(event) {
      const files = Array.from(event.clipboardData?.files || []).filter((file) =>
        file.type.startsWith('image/'),
      )
      if (files.length > 0) {
        event.preventDefault()
        this.addFiles(files)
      }
    },
    addFiles(files) {
      files
        .filter((file) => file.type.startsWith('image/'))
        .forEach((file) => {
          this.attachments.push({
            id: this.nextAttachmentId++,
            name: file.name || `image-${this.nextAttachmentId}.png`,
            file,
            url: URL.createObjectURL(file),
          })
        })
    },
    removeAttachment(id) {
      const index = this.attachments.findIndex((attachment) => attachment.id === id)
      if (index === -1) return
      URL.revokeObjectURL(this.attachments[index].url)
      this.attachments.splice(index, 1)
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const el = this.$refs.messagesEl
        if (el) el.scrollTop = el.scrollHeight
      })
    },
    readFileAsDataUrl(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(String(reader.result || ''))
        reader.onerror = () => reject(reader.error || new Error('Failed to read image attachment'))
        reader.readAsDataURL(file)
      })
    },
    artifactHref(artifact) {
      if (!this.sessionId || !artifact?.title) return '#'
      return `${this.sessionApiBase}/${this.sessionId}/artifacts/${encodeURIComponent(artifact.title)}`
    },
    hasReasoningGraphArtifact(manifest) {
      const current = manifest?.current || {}
      return Boolean(current.reasoningGraph || manifest?.reasoningGraph)
    },
    async refreshAnalysisAvailability() {
      if (!this.sessionId || this.sessionMode === 'baseline') {
        this.analysisGraphAvailable = false
        return
      }
      try {
        const response = await fetch(`${this.sessionApiBase}/${this.sessionId}/analysis-artifacts`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const manifest = await response.json()
        this.analysisGraphAvailable = this.hasReasoningGraphArtifact(manifest)
      } catch (error) {
        console.warn('CodexChatSidebar: failed to refresh analysis availability', error)
        this.analysisGraphAvailable = false
      }
    },
    handleSessionArtifactUpdated(event) {
      const detail = event?.detail || {}
      if (detail.sessionId && detail.sessionId !== this.sessionId) return
      if (detail.sessionMode && detail.sessionMode !== this.sessionMode) return
      const artifactName = detail.artifact?.title || detail.artifact?.name || ''
      if (artifactName === 'reasoning-graph.json') {
        this.analysisGraphAvailable = true
      } else if (/^reasoning-graph-patch(?:-.+)?\.json$/.test(artifactName)) {
        this.refreshAnalysisAvailability()
      }
    },
    notifySessionArtifactUpdated(artifact) {
      window.dispatchEvent(new CustomEvent('maniscope-session-artifact-updated', {
        detail: {
          sessionId: this.sessionId,
          sessionMode: this.sessionMode,
          artifact,
        },
      }))
    },
    hasVisibleThinking(message) {
      return Boolean(message.ephemeralReasoning && message.thinkingOpen !== false)
    },
    displayedActivities(message) {
      const activities = (message.activity || []).filter((activity) => !activity.ephemeral)
      if (message.activityOpen) return activities
      return []
    },
    collapsedActivities(message) {
      if (message.activityOpen) return []
      const activities = (message.activity || []).filter((activity) => !activity.ephemeral)
      const latest = activities[activities.length - 1]
      return latest ? [latest] : []
    },
    activityToggleLabel(message) {
      if (message.activityOpen) return 'Hide details'
      const total = (message.activity || []).filter((activity) => !activity.ephemeral).length
      return `Show ${total}`
    },
    activityClass(activity) {
      return {
        [`activity-${activity.level || 'detail'}`]: true,
        'activity-running': ['running', 'in_progress', 'preparing', 'started'].includes(activity.status),
      }
    },
    addActivity(message, activity) {
      if (!activity || !message) return
      if (!Array.isArray(message.activity)) message.activity = []

      const normalized = this.normalizeActivity(activity, this.nextActivityId++)
      if (normalized.ephemeral) return

      if (normalized.eventId) {
        const existingIndex = message.activity.findIndex(
          (item) => item.eventId === normalized.eventId && item.category === normalized.category,
        )
        if (existingIndex !== -1) {
          message.activity.splice(existingIndex, 1, {
            ...message.activity[existingIndex],
            ...normalized,
            id: message.activity[existingIndex].id,
          })
          return
        }
      }
      message.activity.push(normalized)
    },
    activeAssistantMessage() {
      for (let index = this.messages.length - 1; index >= 0; index -= 1) {
        const message = this.messages[index]
        if (message.role === 'assistant' && message.loading) return message
      }
      return null
    },
    formatUsage(usage) {
      if (!usage || typeof usage !== 'object') return ''
      const input = Number(usage.input_tokens || 0)
      const output = Number(usage.output_tokens || 0)
      const reasoning = Number(usage.reasoning_output_tokens || 0)
      return `${input} input, ${output} output, ${reasoning} reasoning tokens`
    },
    handleCodexEvent(event, assistantMessage) {
      if (!event || !event.type) return

      if (event.type === 'agent_message') {
        if (event.text) {
          assistantMessage.ephemeralReasoning = ''
          assistantMessage.content = assistantMessage.content
            ? `${assistantMessage.content}\n\n${event.text}`
            : event.text
        }
      } else if (event.type === 'reasoning') {
        assistantMessage.ephemeralReasoning = event.text || 'Working through the trace evidence...'
      } else if (event.type === 'status') {
        assistantMessage.ephemeralReasoning = event.detail || event.title || 'Codex is working...'
        this.addActivity(assistantMessage, event)
      } else if (event.type === 'command') {
        assistantMessage.ephemeralReasoning = event.status
          ? `${event.status}: ${event.command || event.title || 'Tool call'}`
          : event.command || event.title || 'Using a tool...'
        this.addActivity(assistantMessage, event)
      } else if (event.type === 'file_change') {
        assistantMessage.ephemeralReasoning = event.detail || 'Updating an artifact...'
        this.addActivity(assistantMessage, event)
      } else if (event.type === 'web_search') {
        assistantMessage.ephemeralReasoning = event.detail || 'Searching...'
        this.addActivity(assistantMessage, event)
      } else if (event.type === 'todo_list') {
        assistantMessage.ephemeralReasoning = event.detail || 'Updating the working plan...'
        this.addActivity(assistantMessage, event)
      } else if (event.type === 'mcp_tool_call') {
        assistantMessage.ephemeralReasoning = event.detail || event.title || 'Calling a tool...'
        this.addActivity(assistantMessage, event)
      } else if (event.type === 'artifact' && event.artifact) {
        const existing = assistantMessage.artifacts.some((artifact) => artifact.id === event.artifact.id)
        if (!existing) assistantMessage.artifacts.push(event.artifact)
        this.notifySessionArtifactUpdated(event.artifact)
        this.addActivity(assistantMessage, {
          level: 'highlight',
          category: 'artifact',
          title: 'Artifact ready',
          detail: event.artifact.title,
        })
      } else if (event.type === 'error') {
        this.addActivity(assistantMessage, {
          level: 'error',
          category: 'session',
          title: event.title || 'Codex error',
          detail: event.error || '',
        })
      } else if (event.type === 'thread') {
        assistantMessage.threadId = event.threadId
        this.addActivity(assistantMessage, event)
      } else if (event.type === 'usage') {
        this.addActivity(assistantMessage, {
          level: 'debug',
          category: 'session',
          title: 'Token usage',
          detail: this.formatUsage(event.usage),
        })
      } else if (event.type === 'stopped') {
        assistantMessage.ephemeralReasoning = ''
        assistantMessage.thinkingOpen = false
        assistantMessage.activityOpen = false
        assistantMessage.loading = false
        this.addActivity(assistantMessage, event)
        if (!assistantMessage.content) assistantMessage.content = 'Stopped before completion.'
      } else if (event.type === 'done') {
        assistantMessage.ephemeralReasoning = ''
        assistantMessage.thinkingOpen = false
        assistantMessage.activityOpen = false
        assistantMessage.threadId = event.threadId || assistantMessage.threadId
        this.addActivity(assistantMessage, {
          level: 'detail',
          category: 'session',
          title: 'Turn complete',
          detail: 'Codex finished this turn.',
        })
      }
    },
    async readSseStream(stream, onEvent) {
      const reader = stream.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done })

        let boundary = buffer.indexOf('\n\n')
        while (boundary !== -1) {
          const rawEvent = buffer.slice(0, boundary)
          buffer = buffer.slice(boundary + 2)
          const data = rawEvent
            .split('\n')
            .filter((line) => line.startsWith('data:'))
            .map((line) => line.slice(5).trimStart())
            .join('\n')

          if (data) {
            onEvent(JSON.parse(data))
          }
          boundary = buffer.indexOf('\n\n')
        }

        if (done) break
      }
    },
    async sendToCodex(content, codexAttachments, assistantMessage) {
      if (!this.sessionId) {
        throw new Error('No ManiScope session is active yet.')
      }

      const response = await fetch(`${this.chatApiBase}/${this.sessionId}/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          threadKey: 'trace-analysis',
          message: content,
          attachments: codexAttachments,
          includeCurrentTrace: true,
          includeCurrentViews: true,
          workspaceRole: this.workspaceRole,
          sessionMode: this.sessionMode,
        }),
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(errorText || `Chat request failed with HTTP ${response.status}`)
      }
      if (!response.body) {
        throw new Error('Chat response did not include a stream.')
      }

      await this.readSseStream(response.body, (event) => {
        this.handleCodexEvent(event, assistantMessage)
        this.scrollToBottom()
      })
    },
    async stopCodexTurn() {
      if (!this.sending || this.stopRequested || !this.sessionId) return

      this.stopRequested = true
      const assistantMessage = this.activeAssistantMessage()
      if (assistantMessage) {
        this.addActivity(assistantMessage, {
          level: 'highlight',
          category: 'session',
          title: 'Stop requested',
          detail: 'Asking Codex to stop the current turn.',
          status: 'running',
        })
      }

      try {
        const response = await fetch(`${this.chatApiBase}/${this.sessionId}/threads/trace-analysis/stop`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sessionMode: this.sessionMode }),
        })
        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(errorText || `Stop request failed with HTTP ${response.status}`)
        }
        const payload = await response.json().catch(() => ({}))
        if (!payload.stopped) {
          this.stopRequested = false
          if (assistantMessage) {
            this.addActivity(assistantMessage, {
              level: 'detail',
              category: 'session',
              title: 'No active turn',
              detail: 'The bridge did not have an active Codex turn to stop.',
            })
          }
        }
      } catch (error) {
        this.stopRequested = false
        if (assistantMessage) {
          this.addActivity(assistantMessage, {
            level: 'error',
            category: 'session',
            title: 'Stop failed',
            detail: error && error.message ? error.message : String(error),
          })
        }
      }
    },
    async sendFullAnalysisPrompt() {
      await this.sendMessage({
        contentOverride: FULL_ANALYSIS_PROMPT,
        displayContent: 'Run full analysis',
        presetKind: 'full_analysis',
        includeAttachments: false,
        clearDraft: false,
      })
    },
    async sendUpdateAnalysisPrompt() {
      if (!this.analysisGraphAvailable) return
      await this.sendMessage({
        contentOverride: UPDATE_ANALYSIS_PROMPT,
        displayContent: 'Update analysis',
        presetKind: 'update_analysis',
        includeAttachments: false,
        clearDraft: false,
      })
    },
    async sendMessage(options = {}) {
      const contentOverride = typeof options.contentOverride === 'string' ? options.contentOverride : null
      const displayContentOverride = typeof options.displayContent === 'string' ? options.displayContent : null
      const presetKind = typeof options.presetKind === 'string' ? options.presetKind : ''
      const includeAttachments = options.includeAttachments !== false
      const clearDraft = options.clearDraft !== false
      const content = (contentOverride ?? this.draft).trim()
      const displayContent = (displayContentOverride ?? content).trim()
      const attachmentSource = includeAttachments ? this.attachments : []
      if (this.sending || (!content && attachmentSource.length === 0)) return

      let assistantMessage = null
      const pendingAttachments = [...attachmentSource]
      const attachments = attachmentSource.map((attachment) => ({
        id: attachment.id,
        name: attachment.name,
        type: attachment.file.type,
      }))

      this.messages.push({
        id: this.nextMessageId++,
        role: 'user',
        content: displayContent,
        attachments,
        presetKind,
        createdAt: new Date().toISOString(),
      })
      if (clearDraft) this.draft = ''
      this.sending = true
      this.stopRequested = false
      this.scrollToBottom()

      try {
        const codexAttachments = await Promise.all(
          pendingAttachments.map(async (attachment) => ({
            name: attachment.name,
            type: attachment.file.type,
            dataUrl: await this.readFileAsDataUrl(attachment.file),
          })),
        )
        if (includeAttachments) {
          pendingAttachments.forEach((attachment) => URL.revokeObjectURL(attachment.url))
          this.attachments = []
        }

        if (this.beforeSend) {
          await this.beforeSend()
        }
        this.$emit('send', { content, attachments })
        const nextAssistantMessage = {
          id: this.nextMessageId++,
          role: 'assistant',
          content: '',
          loading: true,
          activity: [],
          artifacts: [],
          activityOpen: false,
          thinkingOpen: true,
          ephemeralReasoning: '',
          createdAt: new Date().toISOString(),
        }
        this.messages.push(nextAssistantMessage)
        assistantMessage = this.messages[this.messages.length - 1]
        this.scrollToBottom()
        await this.sendToCodex(content, codexAttachments, assistantMessage)
        assistantMessage.loading = false
        assistantMessage.ephemeralReasoning = ''
        if (!assistantMessage.content && assistantMessage.artifacts.length > 0) {
          assistantMessage.content = 'Generated artifacts are available below.'
        }
      } catch (error) {
        const errorText = error && error.message ? error.message : String(error)
        if (assistantMessage) {
          this.addActivity(assistantMessage, {
            level: 'error',
            category: 'session',
            title: 'Chat request failed',
            detail: errorText,
          })
        } else {
          this.messages.push({
            id: this.nextMessageId++,
            role: 'assistant',
            content: `Error: ${errorText}`,
            activity: [],
            artifacts: [],
            createdAt: new Date().toISOString(),
          })
        }
      } finally {
        if (assistantMessage) {
          assistantMessage.loading = false
          assistantMessage.ephemeralReasoning = ''
          assistantMessage.thinkingOpen = false
          assistantMessage.activityOpen = false
        }
        await this.persistChatHistory().catch((error) => {
          console.error('CodexChatSidebar: failed to persist chat history', error)
        })
        this.sending = false
        this.stopRequested = false
        this.scrollToBottom()
      }
    },
  },
}
</script>

<style scoped>
.codex-chat-sidebar {
  position: fixed;
  top: 58px;
  right: 16px;
  bottom: 16px;
  width: min(520px, 42vw);
  min-width: 360px;
  min-height: 360px;
  max-width: calc(100vw - 16px);
  max-height: calc(100vh - 16px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #dbe3ec;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.22);
  z-index: 3000;
  overflow: hidden;
  transform: translateX(calc(100% + 32px));
  opacity: 0;
  pointer-events: none;
  transition:
    transform 0.2s ease,
    opacity 0.2s ease;
}

.codex-chat-sidebar.open {
  transform: translateX(0);
  opacity: 1;
  pointer-events: auto;
}

.codex-chat-sidebar.moving,
.codex-chat-sidebar.resizing {
  transition: none;
  user-select: none;
}

.codex-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  flex-shrink: 0;
  cursor: grab;
  touch-action: none;
}

.codex-chat-sidebar.moving .codex-chat-header {
  cursor: grabbing;
}

.codex-chat-title {
  font-size: 14px;
  font-weight: 700;
  color: #243044;
}

.codex-chat-subtitle {
  margin-top: 2px;
  font-size: 11px;
  color: #64748b;
}

.codex-chat-icon-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-size: 22px;
  line-height: 1;
}

.codex-chat-icon-btn:hover {
  background: #e2e8f0;
  color: #334155;
}

.codex-chat-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-bottom: 1px solid #edf2f7;
  color: #64748b;
  font-size: 11px;
  flex-shrink: 0;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #38a169;
}

.status-dot.syncing {
  background: #3182ce;
}

.codex-chat-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px;
  background: #f8fafc;
}

.codex-chat-empty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.5;
  padding: 24px;
}

.codex-chat-message {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.codex-chat-message.user {
  align-items: flex-end;
}

.codex-chat-message.assistant {
  align-items: flex-start;
}

.message-role {
  font-size: 10px;
  color: #64748b;
  padding: 0 4px;
}

.message-bubble {
  max-width: 88%;
  border-radius: 8px;
  padding: 9px 10px;
  font-size: 13px;
  line-height: 1.45;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #243044;
}

.codex-chat-message.user .message-bubble {
  background: #2b6cb0;
  color: #fff;
  border-color: #2b6cb0;
}

.message-text {
  white-space: pre-wrap;
}

.message-preset-text {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.34);
  padding: 2px 8px;
  font-weight: 700;
  white-space: nowrap;
}

.message-preset-text::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.75;
}

.message-status-stack {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-bottom: 8px;
}

.message-markdown {
  overflow-wrap: anywhere;
}

.message-markdown :deep(p) {
  margin: 0 0 8px;
}

.message-markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.message-markdown :deep(ul),
.message-markdown :deep(ol) {
  margin: 6px 0 8px 18px;
  padding: 0;
}

.message-markdown :deep(code) {
  background: #f1f5f9;
  border-radius: 4px;
  padding: 1px 4px;
  font-size: 12px;
}

.message-markdown :deep(pre) {
  overflow-x: auto;
  background: #f1f5f9;
  border-radius: 6px;
  padding: 8px;
}

.message-markdown :deep(img) {
  display: block;
  max-width: 100%;
  height: auto;
  max-height: 360px;
  margin: 8px 0;
  border: 1px solid #dbe3ef;
  border-radius: 6px;
  object-fit: contain;
}

.message-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  font-size: 12px;
}

.loading-pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #3182ce;
  box-shadow: 0 0 0 0 rgba(49, 130, 206, 0.45);
  animation: codex-pulse 1.25s ease-out infinite;
}

.reasoning-bubble {
  padding: 7px 8px;
  border: 1px solid #bfdbfe;
  border-left: 3px solid #3182ce;
  border-radius: 6px;
  background: #eff6ff;
  color: #334155;
}

.reasoning-label {
  font-size: 10px;
  font-weight: 700;
  color: #2b6cb0;
  text-transform: uppercase;
}

.reasoning-text {
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.35;
  white-space: pre-wrap;
}

.message-activity {
  padding-top: 0;
  padding-bottom: 6px;
  border-bottom: 1px solid #edf2f7;
}

.message-activity-after-thinking {
  border-top: 1px solid #edf2f7;
  padding-top: 6px;
}

.activity-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
}

.activity-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 5px;
}

.activity-toggle {
  border: none;
  background: transparent;
  color: #2b6cb0;
  font-size: 11px;
  font-weight: 700;
  padding: 0;
  cursor: pointer;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 6px;
}

.activity-list-collapsed {
  margin-top: 5px;
}

.activity-item {
  display: grid;
  grid-template-columns: 8px 1fr;
  gap: 6px;
  align-items: start;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 5px 6px;
  background: #f8fafc;
  color: #475569;
  font-size: 11px;
  line-height: 1.35;
}

.activity-item-latest {
  padding: 4px 6px;
  font-size: 10.5px;
  background: #fff;
}

.activity-dot {
  width: 7px;
  height: 7px;
  margin-top: 3px;
  border-radius: 50%;
  background: #94a3b8;
}

.activity-body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.activity-title {
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-detail,
.activity-output {
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-output {
  max-height: 94px;
  overflow-y: auto;
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 10px;
}

.activity-highlight {
  border-color: #bfdbfe;
  background: #eff6ff;
}

.activity-highlight .activity-dot {
  background: #3182ce;
}

.activity-primary {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.activity-primary .activity-dot {
  background: #38a169;
}

.activity-error {
  border-color: #fecaca;
  background: #fff1f2;
  color: #991b1b;
}

.activity-error .activity-dot {
  background: #e53e3e;
}

.activity-debug {
  opacity: 0.75;
}

.activity-running .activity-dot {
  animation: codex-pulse 1.25s ease-out infinite;
}

.message-artifacts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.artifact-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #2b6cb0;
  background: #ebf8ff;
  border: 1px solid #bee3f8;
  border-radius: 6px;
  padding: 4px 7px;
  font-size: 11px;
  text-decoration: none;
}

.artifact-link:hover {
  background: #dbeafe;
}

.artifact-thumb {
  width: 54px;
  height: 38px;
  border-radius: 4px;
  object-fit: cover;
  border: 1px solid #bfdbfe;
}

.message-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 6px;
}

.attachment-pill {
  font-size: 11px;
  border-radius: 999px;
  padding: 2px 7px;
  background: rgba(226, 232, 240, 0.75);
}

.codex-chat-working {
  color: #64748b;
  font-size: 12px;
}

.codex-chat-attachments {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 8px 12px;
  border-top: 1px solid #e2e8f0;
  background: #fff;
  flex-shrink: 0;
}

.attachment-preview {
  position: relative;
  width: 58px;
  height: 58px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  overflow: hidden;
  flex: 0 0 auto;
  background: #f8fafc;
}

.attachment-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.attachment-preview button {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.75);
  color: #fff;
  cursor: pointer;
  line-height: 1;
}

.codex-chat-drop-hint {
  position: absolute;
  inset: 48px 12px 88px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed #3182ce;
  border-radius: 8px;
  background: rgba(235, 248, 255, 0.92);
  color: #2b6cb0;
  font-weight: 700;
  z-index: 1;
}

.codex-chat-input-area {
  padding: 10px 12px 12px;
  border-top: 1px solid #e2e8f0;
  background: #fff;
  flex-shrink: 0;
}

.codex-chat-preset-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.codex-chat-preset-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  background: #eff6ff;
  color: #1d4ed8;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  line-height: 18px;
  padding: 5px 10px;
}

.codex-chat-update-btn {
  border-color: #c4b5fd;
  background: #f5f3ff;
  color: #6d28d9;
}

.codex-chat-preset-btn:hover {
  background: #dbeafe;
}

.codex-chat-update-btn:hover {
  background: #ede9fe;
}

.codex-chat-preset-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.panel-resize-handle {
  position: absolute;
  bottom: 0;
  width: 18px;
  height: 18px;
  z-index: 3;
  opacity: 0.55;
  touch-action: none;
}

.panel-resize-handle::after {
  content: '';
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 8px;
  height: 8px;
  border-right: 2px solid #94a3b8;
  border-bottom: 2px solid #94a3b8;
}

.panel-resize-handle:hover {
  opacity: 1;
}

.resize-bottom-right {
  right: 0;
  cursor: nwse-resize;
}

.resize-bottom-left {
  left: 0;
  cursor: nesw-resize;
  transform: scaleX(-1);
}

.codex-chat-input {
  width: 100%;
  resize: vertical;
  min-height: 54px;
  max-height: 150px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 8px;
  font-family: inherit;
  font-size: 13px;
  color: #243044;
  box-sizing: border-box;
}

.codex-chat-input:focus {
  outline: none;
  border-color: #3182ce;
  box-shadow: 0 0 0 2px rgba(49, 130, 206, 0.16);
}

.codex-chat-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.codex-chat-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 6px;
  padding: 0;
  cursor: pointer;
}

.chat-action-icon {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.chat-action-icon rect {
  fill: currentColor;
  stroke: none;
}

.codex-chat-secondary {
  background: #edf2f7;
  color: #334155;
}

.codex-chat-stop {
  background: #fff1f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.codex-chat-send {
  background: #2b6cb0;
  color: #fff;
  margin-left: auto;
}

.codex-chat-secondary:disabled,
.codex-chat-stop:disabled,
.codex-chat-send:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

@keyframes codex-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(49, 130, 206, 0.35);
  }
  70% {
    box-shadow: 0 0 0 7px rgba(49, 130, 206, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(49, 130, 206, 0);
  }
}

@media (max-width: 760px) {
  .codex-chat-sidebar {
    top: 52px;
    right: 0;
    bottom: 0;
    width: 100vw;
    min-width: 0;
  }
}
</style>
