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
const SYSTEM_PROMPT = `你是 ManiScope 的内置 AI 分析助手。ManiScope 是一个用于评估加密货币市场交易型价格操纵风险的可视化分析仪表板。以下是完整的系统手册，你需要熟读并依此回答用户关于系统操作、参数含义、分析方法的所有问题。回答要简洁、专业、有洞察力。

---
# ManiScope 用户手册

## ManiScope 是什么
ManiScope 是一个用于评估加密货币市场交易型价格操纵风险的可视化分析仪表板。当前前端聚焦于去中心化交易所中的 memecoin 活动，并内置 ACT 和 PNUT 两个 Solana 代币数据集。系统会加载预先计算好的交易日志、转账日志、按小时粒度的余额快照，以及每个用户的行为序列，然后在这些数据之上运行实体检测、链接检测和操纵检测。ManiScope 更适合作为调查员的分析工作台，而不是实时监控系统。

## 屏幕布局
仪表板分成三列：左列是 Control Panel；中列上方是 Token Distribution 视图，下方是带标签页的调查面板（User Actions / Annotations / Action Tree）；右列上方是 K 线和操纵卡片视图，下方是 Behavior Details。

## Control Panel
包含四组配置，按顺序为：Snapshot Configuration、Entity Detection、Manipulation Detection、Link Configuration。

### Snapshot Configuration
- Snapshot Time：从当前代币数据集中选择整点时间戳。
- Top Holders Threshold：头部持有者集合覆盖的供应比例，默认 0.3。
- Related User Threshold：相对于最小头部持有者余额的比例筛选，默认 0.2。
- Update Snapshot：重新加载快照，并自动重跑实体检测、链接检测和操纵检测。

### Entity Detection
把钱包聚类成群组，含三组可折叠规则：
- Network Based（默认关闭）：含 Direct Transfer、Min Tx Count（默认3）、Min Volume、Funding Relationship（默认开）、Same Sender、Same Recipient。
- Similarity Based（默认开启）：含 Trading Action Sequence（关）、Balance Sequence（开，粒度1h，相似度0.6）、Earning Sequence（关）。
- Manipulation Based（默认关闭）：Max Time Diff 为 2。
检测结果在 Token Distribution 中显示为橙色虚线实体边界。

### Manipulation Detection
检测可疑交易模式，两组规则：
- Round Trip（默认开启）：检测买入后卖出/卖出后买入，净持仓回到起点且收益有限。默认：Max Time Diff=120，Max Position Diff=100，Max Earning=1000，Enable Entity Based=是。
- Same Direction（默认开启）：检测连续同向动作。默认：Max Time Diff=10，Min Seq Length=5，Max Diff Direction=0，Enable Entity Based=是。
基于实体的检测会先合并同一实体内钱包的交易再运行检测器，可揭示协同行为。

### Link Configuration
检测持有者之间更柔性的两两关系，默认设置：
- Network Based 关闭，Direct Transfer 开，Min Tx Count=1。
- Similarity Based 开，Trading Action Sequence 开（Action Only，Min Seq Length=3，Max Time Diff=120）。
- Manipulation Based 开，Max Time Diff=120。
实体检测用于严格分组；链接检测用于探索更弱的关系线索。

## Token Distribution View
显示当前快照的节点链接分布图。视觉编码：节点大小=余额；红色描边=被操纵检测标记；蓝色描边=未被标记；橙色虚线边界=实体群组；灰色链接=链接检测关系（需开启 Show Links）。点击节点选择用户并填充 Behavior Details。

## K-Line And Manipulation View
把价格变化与操纵事件结合。蜡烛图上方为 Round Trip 卡片，下方为 Same Direction 卡片。每张卡片显示时间范围、约略金额和动作序列图形。点击卡片把参与用户加载到 Behavior Details。粒度选项：1m/5m/15m/30m/1h/1d/3d/1w。

## Behavior Details View
点击用户节点或操纵卡片后显示。行为图包含：动作圆点（买入/卖出/转账）、余额历史、收益条形。控件包括 Show Related Users、Sequential Time（按事件顺序而非绝对时间）、Show Manipulation Boxes、Sync Time。

## User Actions / Annotations / Action Tree
- User Actions：记录所有交互事件，可展开查看 JSON 细节和截图。
- Annotations：通过相机按钮或 Alt+S 快捷键创建的标注，含草图和文字。
- Action Tree：把动作和标注可视化为树，代币切换/快照更新形成主分支。Create Insight 按钮可将多个标注组合成高层洞察。

## 推荐工作流
1. 选择 ACT 或 PNUT。
2. 选择快照时间，调整阈值，点击 Update Snapshot。
3. 扫视 Token Distribution，关注红色描边密集区域和橙色实体边界。
4. 在 K 线视图寻找卡片密集的时间区间。
5. 点击可疑节点或操纵卡片，查看 Behavior Details。
6. 用 Sequential Time、Show Manipulation Boxes、Sync Time 深入分析。
7. 用相机按钮标注证据，用 Action Tree 整理洞察。
8. 导出会话 JSON。

## 注意事项
- Update Snapshot 不只是视觉刷新，会重跑所有检测。
- Enable Entity Based 的操纵检测依赖实体结果，Run Detection 可能联动更新操纵结果。
- Sequential Time 改变横轴含义，比较钱包动作顺序时开启，与 K 线对齐时关闭。
- 仪表板目前不在主 UI 显示钱包标签（交易所地址、合约地址等），解读时需注意。
---`

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
            model: 'gpt-4o',
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
