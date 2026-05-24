import { Codex } from '@openai/codex-sdk'
import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { materializeLocalImageReferences } from './local-image-artifacts.mjs'

const SESSION_ID_RE = /^[0-9a-f]{5}$/
const THREAD_KEY_RE = /^[a-zA-Z0-9_-]{1,64}$/
const WORKSPACE_ROLE_RE = /^(human|agent)$/
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FRONT_DIR = path.resolve(__dirname, '..')
const REPO_ROOT = process.env.MANISCOPE_REPO_ROOT || path.resolve(FRONT_DIR, '..')
const CHAT_ROOT = path.join(REPO_ROOT, '.maniscope-chat')
const SESSIONS_DIR = path.join(CHAT_ROOT, 'sessions')
const DEFAULT_CODEX_BRIDGE_PORT = 8787
const PORT = Number(process.env.CODEX_BRIDGE_PORT || DEFAULT_CODEX_BRIDGE_PORT)
const IMAGE_DATA_URL_RE = /^data:image\/(png|jpeg|jpg|webp);base64,/i
const activeTurns = new Map()

function sessionDir(sessionId) {
  if (!SESSION_ID_RE.test(sessionId)) {
    const error = new Error('Session ID must be 5 lowercase hex characters')
    error.statusCode = 400
    throw error
  }
  return path.join(SESSIONS_DIR, sessionId)
}

function validateThreadKey(threadKey) {
  if (!THREAD_KEY_RE.test(threadKey)) {
    const error = new Error('Thread key must use letters, numbers, underscores, or hyphens')
    error.statusCode = 400
    throw error
  }
  return threadKey
}

function validateWorkspaceRole(workspaceRole) {
  if (!WORKSPACE_ROLE_RE.test(workspaceRole)) {
    const error = new Error('workspaceRole must be human or agent')
    error.statusCode = 400
    throw error
  }
  return workspaceRole
}

function activeTurnKey(sessionId, threadKey) {
  return `${sessionId}:${threadKey}`
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

function startProgressHeartbeat(res, shouldStop) {
  const notes = [
    {
      title: 'Inspecting trace context',
      detail: 'Reading the live trace, current state, and available screenshots.',
    },
    {
      title: 'Mapping evidence',
      detail: 'Relating observed Interactions to intentions, Findings, and possible Insights.',
    },
    {
      title: 'Planning investigation',
      detail: 'Checking which visual or statistical Analytic Activities are useful next.',
    },
    {
      title: 'Waiting for Codex output',
      detail: 'The agent is still working and will stream the next event when available.',
    },
  ]
  let index = 0
  return setInterval(() => {
    if (shouldStop()) return
    const note = notes[index % notes.length]
    index += 1
    sendSse(res, {
      type: 'status',
      status: 'working',
      level: 'highlight',
      category: 'progress',
      title: note.title,
      detail: note.detail,
    })
  }, 5000)
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

function resolveSessionFile(sessionId, relativePath) {
  if (!relativePath || path.isAbsolute(relativePath)) return null
  const dir = sessionDir(sessionId)
  const filePath = path.resolve(dir, relativePath)
  const relative = path.relative(dir, filePath)
  if (relative.startsWith('..') || path.isAbsolute(relative)) return null
  if (!fs.existsSync(filePath)) return null
  return filePath
}

function workspaceCurrentStatePath(sessionId, workspaceRole) {
  const dir = sessionDir(sessionId)
  if (workspaceRole === 'human') return path.join(dir, 'current-state.json')
  return path.join(dir, 'workspaces', workspaceRole, 'current-state.json')
}

function currentViewImagePaths(sessionId, workspaceRole = 'human') {
  const currentState = readJson(workspaceCurrentStatePath(sessionId, workspaceRole), {})
  const screenshots = currentState.majorViewScreenshots
  if (!screenshots || typeof screenshots !== 'object') return []

  return Object.values(screenshots)
    .map((relativePath) => resolveSessionFile(sessionId, relativePath))
    .filter(Boolean)
}

function uniquePaths(paths) {
  return Array.from(new Set(paths))
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

function buildTraceAnalysisPrompt(sessionId, userMessage, workspaceRole = 'human') {
  const relativeSessionRoot = `.maniscope-chat/sessions/${sessionId}`
  const activeWorkspaceState =
    workspaceRole === 'agent'
      ? `${relativeSessionRoot}/workspaces/agent/current-state.json`
      : `${relativeSessionRoot}/workspaces/human/current-state.json`
  const workspaceContext =
    workspaceRole === 'agent'
      ? `The user is chatting from the Agent Workspace. The agent workspace is a private exploratory ManiScope page: use ${activeWorkspaceState} for current agent-side screenshots and view state, and do not mutate or append to the human trace when doing UI exploration. The canonical human current state remains ${relativeSessionRoot}/current-state.json and represents the user's active context.`
      : `The user is chatting from the Human Workspace. Use ${relativeSessionRoot}/current-state.json as the user's active current view state, and treat ${activeWorkspaceState} as the mirrored human workspace state.`
  return `You are a Codex agent collaborating with a user inside ManiScope.

You are embedded in the active ManiScope session. The canonical live trace is
shared, but human and agent visual workspaces have separate current states.
The user is asking from inside the application and expects a collaborator, not
a report generator by default.

Active chat workspace role: ${workspaceRole}
${workspaceContext}

Start every trace-dependent turn by refreshing context. Read these files first:
- docs/reports/user-manual.en.md
- docs/ui-analysis/major-view-render-api.md
- ${relativeSessionRoot}/live-session.json
- ${relativeSessionRoot}/current-state.json
- ${activeWorkspaceState}

Workspace state model:
- ${relativeSessionRoot}/live-session.json is the canonical user trace. It contains human user actions, annotations, imported trace data, reordered trace, and user-authored notes.
- ${relativeSessionRoot}/current-state.json is the backward-compatible canonical human current state.
- ${relativeSessionRoot}/workspaces/human/current-state.json mirrors the human workspace current state.
- ${relativeSessionRoot}/workspaces/agent/current-state.json is private exploratory agent state.
- Both workspaces read the canonical trace, but only human-facing trace operations write it in this stage.
- Agent visual exploration may change agent workspace state and generated artifacts, but must not alter the human workspace state or canonical user trace unless the user explicitly asks for a durable artifact or reasoning patch.

Screenshots and generated evidence are under:
- ${relativeSessionRoot}/images
- ${relativeSessionRoot}/artifacts

The latest major-view screenshots are also attached to this turn as image inputs when available.

Live trace refresh protocol:
- Before answering a trace-dependent question, reread live-session.json, current-state.json, and the active workspace current-state file. Do not rely only on memory from prior turns.
- The session directory is a git repository when trace versioning is enabled. Use it to inspect what changed quickly:
  - git -C ${relativeSessionRoot} log --oneline -n 10
  - git -C ${relativeSessionRoot} status --short
  - git -C ${relativeSessionRoot} diff HEAD~1..HEAD -- live-session.json current-state.json workspaces/human/current-state.json workspaces/agent/current-state.json
- If HEAD~1 is unavailable because the session has only one commit, inspect the latest full trace files instead.
- If you do not know which session commit was last analyzed, say you are refreshing from the latest full trace, then inspect the latest trace state directly.
- Treat new user Interactions, annotations, settings changes, imports, and trace reorders from the session git history as updates to the User Reasoning Forest.
- Treat human current state as the user's active visual context. Treat agent current state as the agent's exploratory visual context.
- Treat evidence that you produce through follow-up analysis as agent follow-up evidence. When durable artifacts are requested, add it through a Reasoning Graph Patch instead of silently rewriting the user's original reasoning.

Core methodology:

1. Use three mapped analysis spaces.
   - Intention Space: Task, AnalyticQuestion, Hypothesis.
   - Action Space: Interaction, AnalyticActivity, InvestigationStrategy.
   - Finding Space: Finding, Insight.
   - A Task motivates one or more Interactions and produces a local Finding.
   - An AnalyticQuestion motivates an AnalyticActivity and produces a Finding.
   - A Hypothesis motivates an InvestigationStrategy and produces or revises an Insight.
   - State evidence and rationale when you infer an AnalyticQuestion, Hypothesis, mid-level Finding, or Insight.

2. Type low-level Interactions precisely.
   - Data Action: query, filter, retrieve, aggregate, or compute from data or model outputs. This includes statistics not displayed in the GUI.
   - Model Action: change detector parameters, rerun detection, change grouping rules, choose model settings, vary thresholds, or otherwise alter model outputs.
   - Visualization Action: inspect, navigate, select, zoom, compare, change display settings, read GUI-displayed statistics, or interpret trace screenshots and ManiScope views.
   - Synthesis Action: annotate, summarize, connect Findings, update a Hypothesis, write a note, or create a traceability link.

3. Type mid-level AnalyticActivities by the evidence needed for the Finding.
   - Visual Analysis contains one or more Visualization Actions, and the Finding depends on visual inspection, screenshots, GUI-displayed evidence, rendered view evidence, or visual comparison.
   - Statistical Analysis contains no Visualization Actions; the Finding comes from data, model outputs, backend endpoints, scripts, command-line queries, or custom computation.
   - Model Actions and Synthesis Actions do not determine the AnalyticActivity type by themselves.
   - If one candidate activity mixes visual inspection and custom computation, split it into a Visual Analysis activity and a Statistical Analysis activity, then synthesize the results.

4. Use reasoning forests when the task needs traceability.
   - Reasoning Support Graph: canonical shared-node graph of Interactions, Tasks, AnalyticQuestions, AnalyticActivities, Findings, Insights, Hypotheses, and InvestigationStrategies.
   - User Reasoning Forest: descriptive forest reconstructed from the user's trace, rooted at user-authored or analyst-inferred Hypotheses.
   - Recommendation Plan Forest: prescriptive forest of Reasoning Gaps, Expansion Rationales, InvestigationStrategies, AnalyticActivities, Recommended Interactions, and Expected Findings.
   - Follow-up Investigation Forest: descriptive forest of evidence produced by executing recommendations.
   - Reasoning Graph Patch: machine-readable additions or updates that merge follow-up evidence into the canonical graph.
   - Augmented Reasoning Forest: regenerated forest after applying Reasoning Graph Patches.

Evidence discipline:
- Distinguish logged Interactions, derived UI state, trace screenshots, attached screenshots, user-authored annotations, user-authored Findings or Insights, newly rendered visual evidence, raw-data validation, model-output validation, and your own inferred analysis.
- Use trace screenshots to reconstruct what the user actually saw.
- Use current render APIs to generate new visual evidence when investigating a visual question. Do not merely copy trace screenshots and present them as new visual analysis.
- Treat rendered views as qualitative evidence for timing, density, grouping, and visual comparison. Use raw data or backend endpoints for exact counts and amounts, especially when Behavior Details event dots may be downsampled.
- For model-derived claims, such as suspicious labels, entity groups, manipulation boxes, links, components, and detector cards, consider a Model Action robustness check by varying parameters or rerunning detection. If that check is unavailable or unnecessary, explain why.
- If a conclusion is uncertain, say what would confirm, weaken, or falsify it.

Choose the evidence route before acting:
- Use Visual Analysis when a claim depends on spatial clusters, visible grouping, detector boundaries, links, card alignment, price-window alignment, behavior timelines, manipulation boxes, balance shapes, screenshots, rendered images, or values displayed by the GUI.
- Use Statistical Analysis when a claim depends on exact counts, exact timestamps, exact amounts, transfer paths, wallet overlap, cohort market share, profit/loss, final balances, medians, means, detector-output overlap, or other derived values not displayed by the GUI.
- Use Model Actions when the claim depends on detector outputs, model-generated suspicious labels, entity groups, manipulation boxes, link construction, component membership, or threshold-sensitive groupings.
- Use Synthesis Actions when the work is to record, compare, qualify, or connect evidence already produced by visual, data, or model work.
- Use visual, statistical, model, and synthesis evidence together when the claim needs them, but keep them as distinct Interactions or AnalyticActivities. Do not default to script-side statistics.

Major ManiScope views and when to use them:
- Token Distribution View: use for holder distribution, suspicious clusters, entity boundaries, relationship links, connected components, selected or highlighted entities, and detector grouping structure.
- K-Line View: use for price phases, manipulation windows, card timing, card cohorts, round-trip versus same-direction card placement, granularity changes, and alignment between suspicious behavior and price movement.
- Behavior Details View: use for selected wallet or cohort timelines, buy/sell/transfer sequence, related users, sequential versus absolute time, manipulation boxes, balance areas, residual holdings, accumulation, exits, and role comparison.

Rendering policy:
- The frontend exposes major-view render helpers through window.maniScopeMajorViewApi after CryptoVis mounts.
- The available views are token_distribution, candlestick_chart or kline_chart, and behavior_details.
- For a new visual investigation, render focused views rather than relying only on attached trace images.
- For K-line windows, prefer an explicit visibleTimeWindow and cardAlignment: 'visible_window' when focusing on a suspicious time range.
- For Behavior Details, provide selectedUser or selectedUsersList plus fetched behaviorData; use strict rendering when an empty view would be misleading.
- Use larger dimensions or full-quality captures when labels, card text, or timelines matter.
- Save rendered evidence images when they support a Finding, Insight, Hypothesis, recommendation, or Reasoning Graph Patch. For trace analysis artifacts, save them under analysis-results/continued-investigation-assets or another assets folder inside analysis-results.

Response and execution modes:

Mode A: lightweight chat.
- Answer directly in chat using the live trace context.
- Still refresh live-session.json and current-state.json if the answer depends on current trace state.
- Keep the answer concise, but name uncertainty and evidence type.

Mode B: trace refresh and trace-dependent Q&A.
- Inspect the session git log or diff when the user asks what changed, continues after using the UI, or asks a follow-up that may depend on new trace patches.
- Update your interpretation of the User Reasoning Forest when new user Interactions or annotations appear.
- Explain whether the answer is based on the previous analysis, new trace evidence, or both.

Mode C: full trace analysis.
- Reconstruct the interaction timeline, selected users, selected cards, time windows, screenshots, annotations, and current view state.
- Infer Tasks, AnalyticQuestions, Hypotheses, Interactions, AnalyticActivities, Findings, and Insights with evidence and rationale.
- Chat-first by default. Produce durable files only if the user asks for them or if an in-depth investigation needs persistent evidence.

Mode D: recommendation planning.
- Present recommendations top-down, starting from a Hypothesis or AnalyticQuestion and ending with executable Interactions.
- Use precise terms: InvestigationStrategy, AnalyticActivity, and Interaction. Avoid generic action language.
- Distinguish Evidence Completion from Hypothesis Expansion:
  - Evidence Completion fills a Reasoning Gap in the existing User Reasoning Forest.
  - Hypothesis Expansion proposes a related new Hypothesis and grows a new branch or tree.
- Each InvestigationStrategy must operationalize the Hypothesis through concrete targets, analytic contrasts, search concepts, decision criteria, or falsification criteria. Do not merely restate the Hypothesis.
- Each InvestigationStrategy should include a target outcome and at least one AnalyticActivity.
- Each recommended Interaction must be labeled Data Action, Model Action, Visualization Action, or Synthesis Action.
- Each recommended AnalyticActivity must be labeled Visual Analysis or Statistical Analysis.

Mode E: autonomous investigation.
- If the user asks you to investigate, explore, validate, or continue analysis, first state a short InvestigationStrategy plan, even if the user did not explicitly ask for a plan.
- Then execute the needed Visual Analysis, Statistical Analysis, Model Actions, and Synthesis Actions unless the user asks for planning-only.
- For broad or deep investigations, ask the Codex runtime to spawn a subagent with functions.spawn_agent when that tool is available. Give the subagent a bounded evidence-gathering task and continue useful non-overlapping work locally. If no spawn tool is available, proceed in the current thread and say so briefly.
- Convert recommendation-plan Interactions into concrete visual checks, data queries, model robustness checks, or synthesis steps.
- Report completed checks, blocked checks, evidence, Findings, Insights, and unresolved gaps.

Mode F: artifact-writing.
- Use chat-first output unless the user asks for files or durable analysis artifacts.
- If writing full trace artifacts for a trace folder, place them under TRACE/analysis-results.
- If writing session-local live-chat artifacts, place generated evidence under ${relativeSessionRoot}/artifacts unless the user names a different output path.
- Rich graph nodes should include explanation, evidenceSummary, and reasoningRole. Agent-created patch nodes must also include patchRationale.
- Original trace evidence belongs to the User Reasoning Forest. Agent follow-up evidence belongs in a Reasoning Graph Patch and then in the Augmented Reasoning Forest.

Be visibly collaborative while working:
- Send concise progress updates as user-facing working notes when you start reading context, inspect trace evidence, run a command, render a view, save an artifact, calculate statistics, rerun or vary model outputs, spawn a subagent, or change investigation direction.
- Keep progress updates factual and short. Do not wait until the final answer if the task takes more than a moment.
- Final conclusions must be grounded in trace evidence, rendered visual evidence, model output, data, or stated assumptions.

Use focused reads and queries. Avoid broad filesystem scans or dumping entire large files unless the user explicitly asks for exhaustive output.

---

User message:
${userMessage}`
}

function buildInput(sessionId, threadKey, userMessage, isNewThread, attachmentPaths, workspaceRole = 'human') {
  const text =
    userMessage ||
    'Please inspect the attached image input in the context of the current ManiScope session.'

  if (isNewThread && threadKey === 'trace-analysis') {
    const promptText = buildTraceAnalysisPrompt(sessionId, text, workspaceRole)
    if (attachmentPaths.length === 0) return promptText
    return [
      { type: 'text', text: promptText },
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
  if (!event || typeof event !== 'object') return null

  if (event.type === 'thread.started') {
    return {
      type: 'thread',
      threadId: event.thread_id || event.threadId,
      level: 'detail',
      category: 'session',
      title: 'Codex thread ready',
    }
  }
  if (event.type === 'turn.started') {
    return {
      type: 'status',
      status: 'started',
      level: 'highlight',
      category: 'session',
      title: 'Codex started',
      detail: 'Reading the live trace and current view context.',
    }
  }
  if (event.type === 'turn.completed') {
    return {
      type: 'usage',
      usage: event.usage,
      level: 'debug',
      category: 'session',
      title: 'Turn completed',
    }
  }
  if (event.type === 'turn.failed') {
    return {
      type: 'error',
      error: event.error?.message || 'Codex turn failed',
      level: 'error',
      category: 'session',
      title: 'Codex turn failed',
    }
  }
  if (event.type === 'error') {
    return {
      type: 'error',
      error: event.message || 'Codex stream failed',
      level: 'error',
      category: 'session',
      title: 'Codex stream failed',
    }
  }
  if (event.type === 'agent_message') {
    return {
      type: 'agent_message',
      text: event.message || event.text || '',
      level: 'primary',
      category: 'message',
      title: 'Codex response',
    }
  }
  if (event.type === 'message') {
    const text = extractMessageText(event)
    if (text) {
      return {
        type: 'agent_message',
        text,
        level: 'primary',
        category: 'message',
        title: 'Codex response',
      }
    }
  }
  if (!event.item) return null

  const item = event.item
  const eventId = item.id || item.call_id || item.callId || ''
  const status = normalizeItemStatus(item, event.type)
  if (item.type === 'agent_message') {
    return {
      type: 'agent_message',
      text: item.message || item.text || '',
      level: 'primary',
      category: 'message',
      title: 'Codex response',
      eventId,
    }
  }
  if (item.type === 'message') {
    const text = extractMessageText(item)
    if (text) {
      return {
        type: 'agent_message',
        text,
        level: 'primary',
        category: 'message',
        title: 'Codex response',
        eventId,
      }
    }
  }
  if (item.type === 'reasoning') {
    return {
      type: 'reasoning',
      text: reasoningText(item),
      level: 'ephemeral',
      category: 'reasoning',
      title: 'Thinking',
      eventId,
      ephemeral: true,
    }
  }
  if (item.type === 'command_execution') {
    return {
      type: 'command',
      level: levelForStatus(status, item.exit_code),
      category: 'tool',
      title: 'Shell command',
      command: item.command,
      detail: item.command,
      output: truncateText(item.aggregated_output || ''),
      exitCode: item.exit_code ?? null,
      status,
      eventId,
    }
  }
  if (item.type === 'function_call') {
    const command = describeFunctionCall(item)
    return {
      type: 'command',
      level: levelForStatus(status, null),
      category: 'tool',
      title: 'Tool call',
      command,
      detail: command,
      status,
      eventId,
    }
  }
  if (item.type === 'function_call_output') {
    return {
      type: 'command',
      level: levelForStatus(status, null),
      category: 'tool',
      title: 'Tool output',
      command: 'Tool output received',
      detail: 'Tool output received',
      output: truncateText(item.output || ''),
      status,
      eventId,
    }
  }
  if (item.type === 'file_change') {
    const changes = item.changes || []
    return {
      type: 'file_change',
      level: levelForStatus(status, null),
      category: 'artifact',
      title: 'File changes',
      detail: `${status || 'completed'} (${changes.length})`,
      changes,
      status,
      eventId,
    }
  }
  if (item.type === 'web_search') {
    return {
      type: 'web_search',
      level: 'detail',
      category: 'tool',
      title: 'Web search',
      detail: item.query || '',
      query: item.query,
      eventId,
    }
  }
  if (item.type === 'todo_list') {
    const items = item.items || []
    const completed = items.filter((todo) => todo.completed || todo.status === 'completed').length
    return {
      type: 'todo_list',
      level: 'highlight',
      category: 'plan',
      title: 'Plan progress',
      detail: `${completed}/${items.length} items complete`,
      items,
      eventId,
    }
  }
  if (item.type === 'mcp_tool_call') {
    return {
      type: 'mcp_tool_call',
      level: levelForStatus(status, item.error ? 1 : null),
      category: 'tool',
      title: item.tool || 'MCP tool',
      detail: item.server ? `${item.server}${status ? `: ${status}` : ''}` : status,
      server: item.server,
      tool: item.tool,
      status,
      error: item.error?.message || null,
      eventId,
    }
  }
  if (item.type === 'error') {
    return {
      type: 'error',
      error: item.message,
      level: 'error',
      category: 'session',
      title: 'Codex error',
      eventId,
    }
  }
  return null
}

function normalizeItemStatus(item, eventType) {
  if (item.status) return item.status
  if (eventType === 'item.started') return 'running'
  if (eventType === 'item.updated') return 'running'
  if (eventType === 'item.completed') return 'completed'
  return ''
}

function levelForStatus(status, exitCode) {
  if (exitCode !== null && exitCode !== undefined && exitCode !== 0) return 'error'
  if (status === 'failed' || status === 'error') return 'error'
  if (status === 'completed' || status === 'succeeded') return 'detail'
  if (status === 'running' || status === 'in_progress') return 'highlight'
  return 'detail'
}

function truncateText(value, maxLength = 900) {
  const text = String(value || '')
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength - 3)}...`
}

function reasoningText(item) {
  if (typeof item.text === 'string') return item.text
  if (typeof item.summary === 'string') return item.summary
  if (Array.isArray(item.summary)) {
    return item.summary
      .map((part) => {
        if (typeof part === 'string') return part
        if (part && typeof part.text === 'string') return part.text
        return ''
      })
      .filter(Boolean)
      .join('\n')
  }
  return ''
}

function extractMessageText(item) {
  if (typeof item.text === 'string') return item.text
  if (typeof item.message === 'string') return item.message
  if (!Array.isArray(item.content)) return ''
  return item.content
    .map((part) => {
      if (!part || typeof part !== 'object') return ''
      if (typeof part.text === 'string') return part.text
      if (typeof part.output_text === 'string') return part.output_text
      return ''
    })
    .filter(Boolean)
    .join('\n\n')
}

function describeFunctionCall(item) {
  const name = item.name || item.tool || 'Tool call'
  if (name !== 'exec_command') return name
  try {
    const args = typeof item.arguments === 'string' ? JSON.parse(item.arguments) : item.arguments
    if (args?.cmd) return args.cmd
  } catch {
    // Fall through to the generic tool name.
  }
  return name
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

function materializeAgentMessageEvent(sessionId, event) {
  if (!event || event.type !== 'agent_message' || !event.text) {
    return { event, artifacts: [] }
  }
  try {
    const result = materializeLocalImageReferences(event.text, {
      sessionId,
      sessionDir: sessionDir(sessionId),
      repoRoot: REPO_ROOT,
      env: process.env,
    })
    return {
      event: { ...event, text: result.text },
      artifacts: result.artifacts,
    }
  } catch (error) {
    console.warn('Codex bridge: failed to materialize local image references', error)
    return { event, artifacts: [] }
  }
}

async function handleChat(req, res, sessionId) {
  const body = await readBody(req)
  const message = String(body.message || '').trim()
  const threadKey = validateThreadKey(String(body.threadKey || 'trace-analysis'))
  const workspaceRole = validateWorkspaceRole(String(body.workspaceRole || 'human'))
  const attachments = Array.isArray(body.attachments) ? body.attachments : []
  const includeCurrentViews = body.includeCurrentViews !== false
  if (!message && attachments.length === 0) {
    sendJson(res, 400, { error: 'message or image attachment is required' })
    return
  }

  const dir = sessionDir(sessionId)
  if (!fs.existsSync(dir)) {
    sendJson(res, 404, { error: 'session not found' })
    return
  }

  const codex = new Codex()
  const existing = getThreadEntry(sessionId, threadKey)
  const options = buildThreadOptions()
  const isNewThread = !existing?.threadId
  const thread = isNewThread
    ? codex.startThread(options)
    : codex.resumeThread(existing.threadId, options)
  const attachmentPaths = saveChatAttachments(sessionId, attachments)
  if (!message && attachments.length > 0 && attachmentPaths.length === 0) {
    sendJson(res, 400, { error: 'No supported image attachments were provided.' })
    return
  }
  const inputImagePaths = uniquePaths([
    ...(includeCurrentViews ? currentViewImagePaths(sessionId, workspaceRole) : []),
    ...attachmentPaths,
  ])
  const input = buildInput(
    sessionId,
    threadKey,
    message,
    isNewThread,
    inputImagePaths,
    workspaceRole,
  )
  const turnKey = activeTurnKey(sessionId, threadKey)
  if (activeTurns.has(turnKey)) {
    sendJson(res, 409, { error: 'A Codex turn is already running for this thread.' })
    return
  }

  const controller = new AbortController()
  activeTurns.set(turnKey, {
    controller,
    sessionId,
    threadKey,
    startedAt: new Date().toISOString(),
  })

  let streamClosed = false
  const finishStream = () => {
    if (streamClosed) return
    streamClosed = true
    res.end()
  }
  res.on('close', () => {
    if (streamClosed) return
    const activeTurn = activeTurns.get(turnKey)
    if (activeTurn?.controller === controller) {
      controller.abort()
    }
  })

  res.writeHead(200, {
    'Content-Type': 'text/event-stream; charset=utf-8',
    'Cache-Control': 'no-cache',
    'X-Accel-Buffering': 'no',
    Connection: 'keep-alive',
  })
  res.flushHeaders?.()
  sendSse(res, {
    type: 'status',
    status: 'preparing',
    level: 'highlight',
    category: 'session',
    title: 'Preparing Codex context',
    detail:
      workspaceRole === 'agent'
        ? 'Syncing shared trace files and attaching agent workspace screenshots.'
        : 'Syncing shared trace files and attaching human workspace screenshots.',
  })
  const progressHeartbeat = startProgressHeartbeat(
    res,
    () => streamClosed || controller.signal.aborted,
  )

  try {
    const { events } = await thread.runStreamed(input, { signal: controller.signal })
    for await (const event of events) {
      if (controller.signal.aborted) break
      const normalized = normalizeEvent(event)
      if (normalized) {
        const materialized = materializeAgentMessageEvent(sessionId, normalized)
        sendSse(res, materialized.event)
        for (const artifact of materialized.artifacts) {
          sendSse(res, { type: 'artifact', artifact })
        }
      }
    }

    const threadId = thread.id || existing?.threadId || ''
    if (threadId) {
      setThreadEntry(sessionId, threadKey, threadId)
    }
    for (const artifact of listArtifacts(sessionId)) {
      sendSse(res, { type: 'artifact', artifact })
    }
    if (controller.signal.aborted) {
      sendSse(res, {
        type: 'stopped',
        level: 'highlight',
        category: 'session',
        title: 'Codex stopped',
        detail: 'The current turn was stopped before completion.',
      })
    } else {
      sendSse(res, { type: 'done', threadId })
    }
  } catch (error) {
    if (controller.signal.aborted) {
      sendSse(res, {
        type: 'stopped',
        level: 'highlight',
        category: 'session',
        title: 'Codex stopped',
        detail: 'The current turn was stopped before completion.',
      })
    } else {
      sendSse(res, {
        type: 'error',
        error: error?.message || String(error),
        level: 'error',
        category: 'session',
        title: 'Codex error',
      })
    }
  } finally {
    clearInterval(progressHeartbeat)
    const activeTurn = activeTurns.get(turnKey)
    if (activeTurn?.controller === controller) activeTurns.delete(turnKey)
    finishStream()
  }
}

async function handleStop(req, res, sessionId, threadKey) {
  validateThreadKey(threadKey)
  sessionDir(sessionId)
  await readBody(req).catch(() => ({}))

  const turnKey = activeTurnKey(sessionId, threadKey)
  const activeTurn = activeTurns.get(turnKey)
  if (!activeTurn) {
    sendJson(res, 200, { sessionId, threadKey, stopped: false })
    return
  }

  activeTurn.controller.abort()
  sendJson(res, 200, { sessionId, threadKey, stopped: true })
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url || '/', `http://${req.headers.host || '127.0.0.1'}`)
  const chatMatch = url.pathname.match(/^\/chat\/([0-9a-f]{5})\/message$/)
  const stopMatch = url.pathname.match(/^\/chat\/([0-9a-f]{5})\/threads\/([a-zA-Z0-9_-]{1,64})\/stop$/)

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

  if (req.method === 'POST' && stopMatch) {
    handleStop(req, res, stopMatch[1], stopMatch[2]).catch((error) => {
      sendJson(res, error.statusCode || 500, { error: error?.message || String(error) })
    })
    return
  }

  sendJson(res, 404, { error: 'not found' })
})

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Codex bridge listening on http://127.0.0.1:${PORT}`)
})
