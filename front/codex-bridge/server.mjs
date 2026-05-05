import { Codex } from '@openai/codex-sdk'
import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const SESSION_ID_RE = /^[0-9a-f]{5}$/
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FRONT_DIR = path.resolve(__dirname, '..')
const REPO_ROOT = process.env.MANISCOPE_REPO_ROOT || path.resolve(FRONT_DIR, '..')
const CHAT_ROOT = path.join(REPO_ROOT, '.maniscope-chat')
const SESSIONS_DIR = path.join(CHAT_ROOT, 'sessions')
const PORT = Number(process.env.CODEX_BRIDGE_PORT || 8787)
const IMAGE_DATA_URL_RE = /^data:image\/(png|jpeg|jpg|webp);base64,/i

function sessionDir(sessionId) {
  if (!SESSION_ID_RE.test(sessionId)) {
    const error = new Error('Session ID must be 5 lowercase hex characters')
    error.statusCode = 400
    throw error
  }
  return path.join(SESSIONS_DIR, sessionId)
}

function readJson(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'))
  } catch {
    return fallback
  }
}

function writeJson(filePath, payload) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true })
  const tmpPath = `${filePath}.tmp`
  fs.writeFileSync(tmpPath, JSON.stringify(payload, null, 2), 'utf8')
  fs.renameSync(tmpPath, filePath)
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = ''
    req.setEncoding('utf8')
    req.on('data', (chunk) => {
      body += chunk
    })
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {})
      } catch (error) {
        reject(error)
      }
    })
    req.on('error', reject)
  })
}

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache',
  })
  res.end(JSON.stringify(payload))
}

function sendSse(res, event) {
  res.write(`data: ${JSON.stringify(event)}\n\n`)
}

function safeNamePart(value) {
  return String(value || 'image')
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80) || 'image'
}

function extensionForImageType(type, fallbackName) {
  const normalized = String(type || '').toLowerCase()
  if (normalized.includes('jpeg') || normalized.includes('jpg')) return '.jpg'
  if (normalized.includes('webp')) return '.webp'
  if (String(fallbackName || '').toLowerCase().endsWith('.jpg')) return '.jpg'
  if (String(fallbackName || '').toLowerCase().endsWith('.jpeg')) return '.jpg'
  if (String(fallbackName || '').toLowerCase().endsWith('.webp')) return '.webp'
  return '.png'
}

function saveChatAttachments(sessionId, attachments) {
  if (!Array.isArray(attachments) || attachments.length === 0) return []

  const uploadDir = path.join(sessionDir(sessionId), 'chat-uploads')
  fs.mkdirSync(uploadDir, { recursive: true })
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-')

  return attachments
    .map((attachment, index) => {
      if (!attachment || typeof attachment.dataUrl !== 'string') return null
      if (!IMAGE_DATA_URL_RE.test(attachment.dataUrl)) return null

      const [, payload = ''] = attachment.dataUrl.split(',', 2)
      const extension = extensionForImageType(attachment.type, attachment.name)
      const name = `${timestamp}-${String(index + 1).padStart(2, '0')}-${safeNamePart(attachment.name)}${extension}`
      const filePath = path.join(uploadDir, name)
      fs.writeFileSync(filePath, Buffer.from(payload, 'base64'))
      return filePath
    })
    .filter(Boolean)
}

function threadCachePath(sessionId) {
  return path.join(sessionDir(sessionId), 'codex-threads.json')
}

function getThreadEntry(sessionId, threadKey) {
  const cache = readJson(threadCachePath(sessionId), {})
  return cache[threadKey] || null
}

function setThreadEntry(sessionId, threadKey, threadId) {
  const cachePath = threadCachePath(sessionId)
  const cache = readJson(cachePath, {})
  const now = new Date().toISOString()
  cache[threadKey] = {
    ...(cache[threadKey] || {}),
    threadId,
    createdAt: cache[threadKey]?.createdAt || now,
    lastUsedAt: now,
  }
  writeJson(cachePath, cache)
}

function buildThreadOptions() {
  const options = {
    workingDirectory: REPO_ROOT,
    skipGitRepoCheck: false,
    sandboxMode: process.env.CODEX_SANDBOX_MODE || 'workspace-write',
    approvalPolicy: process.env.CODEX_APPROVAL_POLICY || 'never',
    modelReasoningEffort: process.env.CODEX_REASONING_EFFORT || 'high',
    networkAccessEnabled: process.env.CODEX_NETWORK_ACCESS === 'true',
    webSearchMode: process.env.CODEX_WEB_SEARCH || 'disabled',
  }
  if (process.env.CODEX_MODEL) {
    options.model = process.env.CODEX_MODEL
  }
  return options
}

function buildTraceAnalysisPrompt(sessionId, userMessage) {
  const relativeSessionRoot = `.maniscope-chat/sessions/${sessionId}`
  return `You are a Codex agent collaborating with a user inside ManiScope.

You must analyze the current live ManiScope trace for the active session.

Read these files first:
- docs/reports/user-manual.en.md
- skills/user-trace-analysis.md
- ${relativeSessionRoot}/live-session.json
- ${relativeSessionRoot}/current-state.json

Screenshots are under:
- ${relativeSessionRoot}/images

Generated artifacts should be written under:
- ${relativeSessionRoot}/artifacts

When the user asks for trace analysis, follow skills/user-trace-analysis.md.
Produce or update:
- ${relativeSessionRoot}/artifacts/analysis-report.md
- ${relativeSessionRoot}/artifacts/trace-step-map.md

Distinguish observed user actions, user-authored annotations, and your own inferred analysis.
Use top-down recommendations and classify atomic actions as Visual or Statistical.

---

User message:
${userMessage}`
}

function buildInput(sessionId, threadKey, userMessage, isNewThread, attachmentPaths) {
  const text =
    userMessage ||
    'Please inspect the attached image input in the context of the current ManiScope session.'

  if (isNewThread && threadKey === 'trace-analysis') {
    const initialPrompt = buildTraceAnalysisPrompt(sessionId, text)
    if (attachmentPaths.length === 0) return initialPrompt
    return [
      { type: 'text', text: initialPrompt },
      ...attachmentPaths.map((imagePath) => ({ type: 'local_image', path: imagePath })),
    ]
  }
  if (attachmentPaths.length === 0) return text
  return [
    { type: 'text', text },
    ...attachmentPaths.map((imagePath) => ({ type: 'local_image', path: imagePath })),
  ]
}

function normalizeEvent(event) {
  if (event.type === 'thread.started') {
    return { type: 'thread', threadId: event.thread_id }
  }
  if (event.type === 'turn.completed') {
    return { type: 'usage', usage: event.usage }
  }
  if (event.type === 'turn.failed') {
    return { type: 'error', error: event.error?.message || 'Codex turn failed' }
  }
  if (event.type === 'error') {
    return { type: 'error', error: event.message || 'Codex stream failed' }
  }
  if (!event.item) return null

  const item = event.item
  if (item.type === 'agent_message') {
    return { type: 'agent_message', text: item.text }
  }
  if (item.type === 'reasoning') {
    return { type: 'reasoning', text: item.text }
  }
  if (item.type === 'command_execution') {
    return {
      type: 'command',
      command: item.command,
      output: item.aggregated_output || '',
      exitCode: item.exit_code ?? null,
      status: item.status,
    }
  }
  if (item.type === 'file_change') {
    return { type: 'file_change', changes: item.changes || [], status: item.status }
  }
  if (item.type === 'web_search') {
    return { type: 'web_search', query: item.query }
  }
  if (item.type === 'todo_list') {
    return { type: 'todo_list', items: item.items || [] }
  }
  if (item.type === 'mcp_tool_call') {
    return {
      type: 'mcp_tool_call',
      server: item.server,
      tool: item.tool,
      status: item.status,
      error: item.error?.message || null,
    }
  }
  if (item.type === 'error') {
    return { type: 'error', error: item.message }
  }
  return null
}

function listArtifacts(sessionId) {
  const artifactsDir = path.join(sessionDir(sessionId), 'artifacts')
  if (!fs.existsSync(artifactsDir)) return []
  return fs
    .readdirSync(artifactsDir, { withFileTypes: true })
    .filter((entry) => entry.isFile())
    .filter((entry) =>
      ['.md', '.png', '.jpg', '.jpeg', '.webp'].includes(path.extname(entry.name).toLowerCase()),
    )
    .map((entry) => {
      const filePath = path.join(artifactsDir, entry.name)
      const stat = fs.statSync(filePath)
      const extension = path.extname(entry.name).toLowerCase()
      return {
        id: entry.name.replace(/[^a-zA-Z0-9_-]+/g, '-'),
        title: entry.name,
        kind: extension === '.md' ? 'markdown' : 'image',
        path: `artifacts/${entry.name}`,
        updatedAt: stat.mtime.toISOString(),
      }
    })
}

async function handleChat(req, res, sessionId) {
  const body = await readBody(req)
  const message = String(body.message || '').trim()
  const threadKey = String(body.threadKey || 'trace-analysis')
  const attachments = Array.isArray(body.attachments) ? body.attachments : []
  if (!message && attachments.length === 0) {
    sendJson(res, 400, { error: 'message or image attachment is required' })
    return
  }

  const dir = sessionDir(sessionId)
  if (!fs.existsSync(dir)) {
    sendJson(res, 404, { error: 'session not found' })
    return
  }

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  })

  const codex = new Codex()
  const existing = getThreadEntry(sessionId, threadKey)
  const options = buildThreadOptions()
  const isNewThread = !existing?.threadId
  const thread = isNewThread
    ? codex.startThread(options)
    : codex.resumeThread(existing.threadId, options)
  const attachmentPaths = saveChatAttachments(sessionId, attachments)
  if (!message && attachments.length > 0 && attachmentPaths.length === 0) {
    sendSse(res, { type: 'error', error: 'No supported image attachments were provided.' })
    res.end()
    return
  }
  const input = buildInput(sessionId, threadKey, message, isNewThread, attachmentPaths)

  try {
    const { events } = await thread.runStreamed(input)
    for await (const event of events) {
      const normalized = normalizeEvent(event)
      if (normalized) sendSse(res, normalized)
    }

    const threadId = thread.id || existing?.threadId || ''
    if (threadId) {
      setThreadEntry(sessionId, threadKey, threadId)
    }
    for (const artifact of listArtifacts(sessionId)) {
      sendSse(res, { type: 'artifact', artifact })
    }
    sendSse(res, { type: 'done', threadId })
    res.end()
  } catch (error) {
    sendSse(res, { type: 'error', error: error?.message || String(error) })
    res.end()
  }
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url || '/', `http://${req.headers.host || '127.0.0.1'}`)
  const chatMatch = url.pathname.match(/^\/chat\/([0-9a-f]{5})\/message$/)

  if (req.method === 'GET' && url.pathname === '/health') {
    sendJson(res, 200, { ok: true })
    return
  }

  if (req.method === 'POST' && chatMatch) {
    handleChat(req, res, chatMatch[1]).catch((error) => {
      sendJson(res, error.statusCode || 500, { error: error?.message || String(error) })
    })
    return
  }

  sendJson(res, 404, { error: 'not found' })
})

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Codex bridge listening on http://127.0.0.1:${PORT}`)
})
