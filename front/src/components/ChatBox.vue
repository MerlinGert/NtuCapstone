<template>
  <div class="chatbox-container">
    <!-- Header -->
    <div class="chatbox-header">
      <span class="chatbox-title">AI Assistant</span>
      <button class="chatbox-clear-btn" @click="clearMessages" title="Clear chat">✕</button>
    </div>

    <!-- Messages area -->
    <div class="chatbox-messages" ref="messagesEl">
      <div v-if="messages.length === 0" class="chatbox-empty">
        Ask anything about the current visualization...
      </div>
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="chatbox-msg"
        :class="msg.role === 'user' ? 'chatbox-msg--user' : 'chatbox-msg--assistant'"
      >
        <div class="chatbox-bubble">
          <span class="chatbox-role">{{ msg.role === 'user' ? 'You' : 'AI' }}</span>
          <div class="chatbox-text" v-html="formatMessage(msg.content)"></div>
        </div>
      </div>
      <div v-if="loading" class="chatbox-msg chatbox-msg--assistant">
        <div class="chatbox-bubble">
          <span class="chatbox-role">AI</span>
          <div class="chatbox-typing">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Input area -->
    <div class="chatbox-input-area">
      <textarea
        ref="inputEl"
        v-model="inputText"
        class="chatbox-input"
        placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
        :disabled="loading"
        rows="2"
        @keydown="handleKeydown"
      ></textarea>
      <button
        class="chatbox-send-btn"
        :disabled="loading || !inputText.trim()"
        @click="sendMessage"
      >
        {{ loading ? '…' : '↑' }}
      </button>
    </div>

    <!-- Error -->
    <div v-if="errorMsg" class="chatbox-error">{{ errorMsg }}</div>
  </div>
</template>

<script>
const OPENAI_API_KEY = import.meta.env.VITE_OPENAI_API_KEY || ''
const OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions'
const SYSTEM_PROMPT = `You are an AI assistant helping analysts investigate cryptocurrency market manipulation using the ManiScope visualization tool. The tool displays token holder distributions, entity detection results, manipulation patterns (round-trip trading, same-direction trading), and candlestick charts. Answer questions concisely and insightfully.`

export default {
  name: 'ChatBox',
  data() {
    return {
      messages: [],
      inputText: '',
      loading: false,
      errorMsg: '',
    }
  },
  methods: {
    handleKeydown(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        this.sendMessage()
      }
    },
    async sendMessage() {
      const text = this.inputText.trim()
      if (!text || this.loading) return

      this.inputText = ''
      this.errorMsg = ''
      this.messages.push({ role: 'user', content: text })
      this.loading = true
      this.$nextTick(() => this.scrollToBottom())

      try {
        const response = await fetch(OPENAI_API_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${OPENAI_API_KEY}`,
          },
          body: JSON.stringify({
            model: 'gpt-4o-mini',
            messages: [
              { role: 'system', content: SYSTEM_PROMPT },
              ...this.messages,
            ],
            max_tokens: 1024,
            temperature: 0.7,
          }),
        })

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}))
          throw new Error(errData?.error?.message || `HTTP ${response.status}`)
        }

        const data = await response.json()
        const reply = data.choices?.[0]?.message?.content ?? '(No response)'
        this.messages.push({ role: 'assistant', content: reply })
      } catch (err) {
        this.errorMsg = `Error: ${err.message}`
        // remove the user message bubble on failure so user can retry
        this.messages.pop()
        this.inputText = text
      } finally {
        this.loading = false
        this.$nextTick(() => this.scrollToBottom())
      }
    },
    clearMessages() {
      this.messages = []
      this.errorMsg = ''
    },
    scrollToBottom() {
      const el = this.$refs.messagesEl
      if (el) el.scrollTop = el.scrollHeight
    },
    formatMessage(text) {
      // Basic markdown: bold, code, newlines
      return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>')
    },
  },
}
</script>

<style scoped>
.chatbox-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  font-size: 12px;
  font-family: inherit;
  overflow: hidden;
}

.chatbox-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.chatbox-title {
  font-weight: 700;
  font-size: 12px;
  color: #2d3748;
}

.chatbox-clear-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #a0aec0;
  font-size: 11px;
  padding: 2px 4px;
  border-radius: 3px;
  line-height: 1;
}
.chatbox-clear-btn:hover { color: #718096; background: #edf2f7; }

.chatbox-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chatbox-empty {
  color: #a0aec0;
  font-size: 11px;
  text-align: center;
  margin-top: 20px;
  font-style: italic;
}

.chatbox-msg {
  display: flex;
}

.chatbox-msg--user {
  justify-content: flex-end;
}

.chatbox-msg--assistant {
  justify-content: flex-start;
}

.chatbox-bubble {
  max-width: 90%;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chatbox-role {
  font-size: 10px;
  font-weight: 700;
  color: #a0aec0;
  padding: 0 2px;
}

.chatbox-msg--user .chatbox-role {
  text-align: right;
  color: #4a90d9;
}

.chatbox-text {
  padding: 6px 9px;
  border-radius: 8px;
  line-height: 1.5;
  color: #2d3748;
  background: #edf2f7;
  word-break: break-word;
}

.chatbox-msg--user .chatbox-text {
  background: #3182ce;
  color: #fff;
}

.chatbox-text code {
  background: rgba(0,0,0,0.1);
  border-radius: 3px;
  padding: 0 3px;
  font-size: 11px;
}

/* Typing indicator */
.chatbox-typing {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 10px;
  background: #edf2f7;
  border-radius: 8px;
}
.chatbox-typing span {
  width: 6px;
  height: 6px;
  background: #a0aec0;
  border-radius: 50%;
  animation: bounce 1.2s infinite;
}
.chatbox-typing span:nth-child(2) { animation-delay: 0.2s; }
.chatbox-typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-5px); }
}

.chatbox-input-area {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  padding: 6px 8px;
  border-top: 1px solid #e2e8f0;
  flex-shrink: 0;
  background: #f8fafc;
}

.chatbox-input {
  flex: 1;
  resize: none;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 5px 8px;
  font-size: 12px;
  font-family: inherit;
  color: #2d3748;
  outline: none;
  background: #fff;
  line-height: 1.4;
  transition: border-color 0.15s;
}
.chatbox-input:focus { border-color: #3182ce; }
.chatbox-input:disabled { background: #f7fafc; }

.chatbox-send-btn {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  border: none;
  background: #3182ce;
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}
.chatbox-send-btn:hover:not(:disabled) { background: #2b6cb0; }
.chatbox-send-btn:disabled { background: #bee3f8; cursor: not-allowed; }

.chatbox-error {
  padding: 4px 8px;
  background: #fff5f5;
  color: #c53030;
  font-size: 11px;
  border-top: 1px solid #fed7d7;
  flex-shrink: 0;
}
</style>
