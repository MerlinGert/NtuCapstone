<template>
  <aside
    class="codex-chat-sidebar"
    :class="{ open }"
    aria-label="Codex chat"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="handleDrop"
  >
    <div class="codex-chat-header">
      <div>
        <div class="codex-chat-title">Codex Chat</div>
        <div class="codex-chat-subtitle">Session {{ sessionId || 'pending' }}</div>
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
        Ask Codex to inspect the current trace, explain an interaction path, or draft a trace analysis.
      </div>

      <div
        v-for="message in messages"
        :key="message.id"
        class="codex-chat-message"
        :class="message.role === 'user' ? 'user' : 'assistant'"
      >
        <div class="message-role">{{ message.role === 'user' ? 'You' : 'Codex' }}</div>
        <div class="message-bubble">
          <div v-if="message.content" class="message-text">{{ message.content }}</div>
          <div v-if="message.loading" class="message-loading">Codex is working...</div>
          <div v-if="message.activity && message.activity.length" class="message-activity">
            <div v-for="activity in message.activity" :key="activity.id" class="activity-item">
              {{ activity.text }}
            </div>
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
              {{ artifact.title }}
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
        <button class="codex-chat-secondary" type="button" title="Attach images" @click="$refs.fileInput.click()">
          Attach
        </button>
        <button
          class="codex-chat-send"
          type="button"
          :disabled="sending || (!draft.trim() && attachments.length === 0)"
          @click="sendMessage"
        >
          {{ sending ? 'Sending...' : 'Send' }}
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
  </aside>
</template>

<script>
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
      dragging: false,
      nextMessageId: 1,
      nextAttachmentId: 1,
      nextActivityId: 1,
    }
  },
  computed: {
    syncStatusText() {
      if (this.syncInFlight || this.sending) return 'Syncing live trace'
      if (this.lastSyncAt) return `Live trace synced ${new Date(this.lastSyncAt).toLocaleTimeString()}`
      return 'Live trace will sync before each message'
    },
  },
  beforeUnmount() {
    this.attachments.forEach((attachment) => URL.revokeObjectURL(attachment.url))
  },
  methods: {
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
      return `/api/sessions/${this.sessionId}/artifacts/${encodeURIComponent(artifact.title)}`
    },
    addActivity(message, text) {
      if (!text) return
      message.activity.push({
        id: this.nextActivityId++,
        text,
      })
    },
    handleCodexEvent(event, assistantMessage) {
      if (!event || !event.type) return

      if (event.type === 'agent_message') {
        if (event.text) {
          assistantMessage.content = assistantMessage.content
            ? `${assistantMessage.content}\n\n${event.text}`
            : event.text
        }
      } else if (event.type === 'reasoning') {
        this.addActivity(assistantMessage, event.text ? `Reasoning: ${event.text}` : 'Reasoning update')
      } else if (event.type === 'command') {
        const status = event.status ? `${event.status}: ` : ''
        this.addActivity(assistantMessage, `${status}${event.command || 'Command execution'}`)
      } else if (event.type === 'file_change') {
        const count = Array.isArray(event.changes) ? event.changes.length : 0
        this.addActivity(assistantMessage, `File changes ${event.status || 'completed'} (${count})`)
      } else if (event.type === 'web_search') {
        this.addActivity(assistantMessage, `Web search: ${event.query || ''}`.trim())
      } else if (event.type === 'todo_list') {
        const items = Array.isArray(event.items) ? event.items : []
        const completed = items.filter((item) => item.completed).length
        this.addActivity(assistantMessage, `Plan progress: ${completed}/${items.length} items complete`)
      } else if (event.type === 'mcp_tool_call') {
        this.addActivity(assistantMessage, `${event.status || 'Tool'}: ${event.tool || 'MCP tool'}`)
      } else if (event.type === 'artifact' && event.artifact) {
        assistantMessage.artifacts.push(event.artifact)
      } else if (event.type === 'error') {
        assistantMessage.content = assistantMessage.content
          ? `${assistantMessage.content}\n\nError: ${event.error}`
          : `Error: ${event.error}`
      } else if (event.type === 'thread') {
        assistantMessage.threadId = event.threadId
      } else if (event.type === 'done') {
        assistantMessage.threadId = event.threadId || assistantMessage.threadId
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

      const response = await fetch(`/api/chat/${this.sessionId}/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          threadKey: 'trace-analysis',
          message: content,
          attachments: codexAttachments,
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
    async sendMessage() {
      const content = this.draft.trim()
      if (this.sending || (!content && this.attachments.length === 0)) return

      let assistantMessage = null
      const pendingAttachments = [...this.attachments]
      const attachments = this.attachments.map((attachment) => ({
        id: attachment.id,
        name: attachment.name,
        type: attachment.file.type,
      }))

      this.messages.push({
        id: this.nextMessageId++,
        role: 'user',
        content,
        attachments,
      })
      this.draft = ''
      this.sending = true
      this.scrollToBottom()

      try {
        const codexAttachments = await Promise.all(
          pendingAttachments.map(async (attachment) => ({
            name: attachment.name,
            type: attachment.file.type,
            dataUrl: await this.readFileAsDataUrl(attachment.file),
          })),
        )
        pendingAttachments.forEach((attachment) => URL.revokeObjectURL(attachment.url))
        this.attachments = []

        if (this.beforeSend) {
          await this.beforeSend()
        }
        this.$emit('send', { content, attachments })
        assistantMessage = {
          id: this.nextMessageId++,
          role: 'assistant',
          content: '',
          loading: true,
          activity: [],
          artifacts: [],
        }
        this.messages.push(assistantMessage)
        this.scrollToBottom()
        await this.sendToCodex(content, codexAttachments, assistantMessage)
        assistantMessage.loading = false
        if (!assistantMessage.content && assistantMessage.artifacts.length > 0) {
          assistantMessage.content = 'Generated artifacts are available below.'
        }
      } catch (error) {
        this.messages.push({
          id: this.nextMessageId++,
          role: 'assistant',
          content: `Error: ${error && error.message ? error.message : String(error)}`,
        })
      } finally {
        if (assistantMessage) assistantMessage.loading = false
        this.sending = false
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
  min-width: 380px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #dbe3ec;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.22);
  z-index: 3000;
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

.codex-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  flex-shrink: 0;
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

.message-loading {
  color: #64748b;
  font-size: 12px;
}

.message-activity {
  margin-top: 7px;
  border-top: 1px solid #edf2f7;
  padding-top: 6px;
}

.activity-item {
  color: #64748b;
  font-size: 11px;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.message-artifacts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.artifact-link {
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
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}

.codex-chat-secondary,
.codex-chat-send {
  border: none;
  border-radius: 6px;
  padding: 7px 10px;
  font-size: 12px;
  cursor: pointer;
}

.codex-chat-secondary {
  background: #edf2f7;
  color: #334155;
}

.codex-chat-send {
  background: #2b6cb0;
  color: #fff;
}

.codex-chat-send:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
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
