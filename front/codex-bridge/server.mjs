import { Codex } from '@openai/codex-sdk'
import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import { AgentBrowserManager } from './agent-browser.mjs'
import { materializeLocalArtifactReferences } from './local-image-artifacts.mjs'
import { runStartupPreflight } from './preflight.mjs'
import {
  buildCodexClientOptions,
  buildThreadOptions,
  rawDataDirectories,
  FRONT_DIR,
  REPO_ROOT,
} from './thread-options.mjs'

const SESSION_ID_RE = /^[0-9a-f]{5}$/
const THREAD_KEY_RE = /^[a-zA-Z0-9_-]{1,64}$/
const WORKSPACE_ROLE_RE = /^(human|agent)$/
const SESSION_MODE_RE = /^(specialized|baseline)$/
const CHAT_ROOT = path.join(REPO_ROOT, '.maniscope-chat')
const SESSIONS_DIR = path.join(CHAT_ROOT, 'sessions')
const BASELINE_SESSIONS_DIR = path.join(CHAT_ROOT, 'baseline-sessions')
const DEFAULT_CODEX_BRIDGE_PORT = 8787
const PORT = Number(process.env.CODEX_BRIDGE_PORT || DEFAULT_CODEX_BRIDGE_PORT)
const DEFAULT_BACKEND_URL = 'http://127.0.0.1:8099'
const BACKEND_URL = process.env.MANISCOPE_BACKEND_URL || DEFAULT_BACKEND_URL
const RAW_DATA_DIRS = rawDataDirectories(FRONT_DIR)
const ARTIFACT_POLL_INTERVAL_MS = 500
const IMAGE_DATA_URL_RE = /^data:image\/(png|jpeg|jpg|webp);base64,/i
const activeTurns = new Map()
const agentBrowser = new AgentBrowserManager()

function validateSessionMode(sessionMode) {
  if (!SESSION_MODE_RE.test(sessionMode)) {
    const error = new Error('sessionMode must be specialized or baseline')
    error.statusCode = 400
    throw error
  }
  return sessionMode
}

function sessionDir(sessionId, sessionMode = 'specialized') {
  if (!SESSION_ID_RE.test(sessionId)) {
    const error = new Error('Session ID must be 5 lowercase hex characters')
    error.statusCode = 400
    throw error
  }
  const root = validateSessionMode(sessionMode) === 'baseline' ? BASELINE_SESSIONS_DIR : SESSIONS_DIR
  return path.join(root, sessionId)
}

function existingSessionDir(sessionId, sessionMode = 'specialized') {
  const dir = sessionDir(sessionId, sessionMode)
  if (!fs.existsSync(dir)) {
    const error = new Error('session not found')
    error.statusCode = 404
    throw error
  }
  return dir
}

function validateThreadKey(threadKey) {
  if (!THREAD_KEY_RE.test(threadKey)) {
    const error = new Error('Thread key must use letters, numbers, underscores, or hyphens')
    error.statusCode = 400
    throw error
  }
  return threadKey
}

function validateWorkspaceRole(workspaceRole, sessionMode = 'specialized') {
  if (!WORKSPACE_ROLE_RE.test(workspaceRole)) {
    const error = new Error('workspaceRole must be human or agent')
    error.statusCode = 400
    throw error
  }
  if (sessionMode === 'baseline' && workspaceRole !== 'human') {
    const error = new Error('baseline chat only supports the human workspace')
    error.statusCode = 400
    throw error
  }
  return workspaceRole
}

function activeTurnKey(sessionMode, sessionId, threadKey) {
  return `${sessionMode}:${sessionId}:${threadKey}`
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

function startProgressHeartbeat(res, shouldStop, sessionMode = 'specialized') {
  const notes =
    sessionMode === 'baseline'
      ? [
          {
            title: 'Inspecting session context',
            detail: 'Reading the current trace, screenshots, and available data files.',
          },
          {
            title: 'Checking evidence',
            detail: 'Comparing trace evidence, screenshots, and raw data where useful.',
          },
          {
            title: 'Preparing response',
            detail: 'Organizing observations and next checks for the user.',
          },
          {
            title: 'Waiting for Codex output',
            detail: 'The agent is still working and will stream the next event when available.',
          },
        ]
      : [
          {
            title: 'Inspecting trace context',
            detail: 'Reading the live trace, current state, and available screenshots.',
          },
          {
            title: 'Mapping evidence',
            detail: 'Relating observed Interactions to intentions, Findings, and possible Hypotheses.',
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

function saveChatAttachments(sessionId, attachments, sessionMode = 'specialized') {
  if (!Array.isArray(attachments) || attachments.length === 0) return []

  const uploadDir = path.join(sessionDir(sessionId, sessionMode), 'chat-uploads')
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

function resolveSessionFile(sessionId, relativePath, sessionMode = 'specialized') {
  if (!relativePath || path.isAbsolute(relativePath)) return null
  const dir = sessionDir(sessionId, sessionMode)
  const filePath = path.resolve(dir, relativePath)
  const relative = path.relative(dir, filePath)
  if (relative.startsWith('..') || path.isAbsolute(relative)) return null
  if (!fs.existsSync(filePath)) return null
  return filePath
}

function workspaceCurrentStatePath(sessionId, workspaceRole, sessionMode = 'specialized') {
  const dir = sessionDir(sessionId, sessionMode)
  if (workspaceRole === 'human') return path.join(dir, 'current-state.json')
  if (sessionMode === 'baseline') return path.join(dir, 'current-state.json')
  return path.join(dir, 'workspaces', workspaceRole, 'current-state.json')
}

function currentViewImagePaths(sessionId, workspaceRole = 'human', sessionMode = 'specialized') {
  const currentState = readJson(workspaceCurrentStatePath(sessionId, workspaceRole, sessionMode), {})
  const screenshots = currentState.majorViewScreenshots
  if (!screenshots || typeof screenshots !== 'object') return []

  return Object.values(screenshots)
    .map((relativePath) => resolveSessionFile(sessionId, relativePath, sessionMode))
    .filter(Boolean)
}

function uniquePaths(paths) {
  return Array.from(new Set(paths))
}

function threadCachePath(sessionId, sessionMode = 'specialized') {
  return path.join(sessionDir(sessionId, sessionMode), 'codex-threads.json')
}

function getThreadEntry(sessionId, threadKey, sessionMode = 'specialized') {
  const cache = readJson(threadCachePath(sessionId, sessionMode), {})
  return cache[threadKey] || null
}

function setThreadEntry(sessionId, threadKey, threadId, sessionMode = 'specialized') {
  const cachePath = threadCachePath(sessionId, sessionMode)
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

function buildSpecializedThreadBootstrapPrompt(sessionId, userMessage, workspaceRole = 'human') {
  const relativeSessionRoot = '.'
  const sessionRoot = sessionDir(sessionId, 'specialized')
  const actRawDataDir = RAW_DATA_DIRS[0]
  const pnutRawDataDir = RAW_DATA_DIRS[1]
  const activeWorkspaceState =
    workspaceRole === 'agent'
      ? `${relativeSessionRoot}/workspaces/agent/current-state.json`
      : `${relativeSessionRoot}/workspaces/human/current-state.json`
  const workspaceContext =
    workspaceRole === 'agent'
      ? `The user is chatting from the Agent Workspace. The agent workspace is a private exploratory ManiScope page: use ${activeWorkspaceState} for current agent-side screenshots and view state, and do not mutate or append to the human trace when doing UI exploration. The canonical human current state remains ${relativeSessionRoot}/current-state.json and represents the user's active context.`
      : `The user is chatting from the Human Workspace. Use ${relativeSessionRoot}/current-state.json as the user's active current view state, and treat ${activeWorkspaceState} as the mirrored human workspace state.`
  return `# Role And Collaboration Contract

You are a Codex agent collaborating with a user inside ManiScope. You are embedded in the active ManiScope session. The canonical live trace is shared, but human and agent visual workspaces have separate current states.

The user is asking from inside the application and expects a practical collaborator, not a report generator by default. Work chat-first unless the user asks for durable files or the task requires persistent evidence. Ground conclusions in trace evidence, rendered visual evidence, model output, raw data, or explicit assumptions.

Active chat workspace role: ${workspaceRole}
${workspaceContext}

# Mode Selection

First choose the narrowest mode that satisfies the user request. If multiple modes apply, follow the broader playbook but keep the response readable.

- Lightweight chat: answer a narrow question directly. Refresh current trace files if the answer depends on trace state. Keep it concise and name evidence type and uncertainty.
- Trace-dependent Q&A: when the user asks what changed, continues after using the UI, or asks a follow-up that may depend on new trace patches, inspect the live trace and session git history. If prior graph artifacts exist, compare their latest trace anchor with the current live traceAnchor.
- Full trace analysis: trigger when the user asks for full, comprehensive, complete, end-to-end, or artifact-producing trace analysis, or asks to analyze a trace without scoping the request to a narrow question. Unless explicitly scoped down, run trace reconstruction, recommendation planning, skeptical review, follow-up investigation, graph patching, validation, and artifact writing.
- Incremental trace analysis: trigger when the user asks what changed, asks to continue or refine an existing analysis, or when reasoning-graph.json already exists and the live trace has advanced beyond the latest graph or patch anchor.
- Recommendation planning: trigger when the user asks what to do next, asks for recommendations, or asks how to test a Hypothesis or AnalyticQuestion.
- Autonomous investigation: trigger when the user asks you to investigate, explore, validate, test, or continue analysis. First state a short InvestigationStrategy plan, then execute the needed checks unless the user asks for planning-only.
- Artifact writing: trigger when the user asks for files, durable analysis artifacts, graph JSON, patches, reports, exports, or persistent evidence.

# Always Refresh Context

For every trace-dependent turn, read these files first:
- session-references/user-manual.en.md
- session-references/major-view-render-api.md
- ${relativeSessionRoot}/live-session.json
- ${relativeSessionRoot}/current-state.json
- ${activeWorkspaceState}

Use session git history as a quick change index when trace versioning is enabled:
- git -C ${relativeSessionRoot} log --oneline -n 10
- git -C ${relativeSessionRoot} status --short
- git -C ${relativeSessionRoot} diff HEAD~1..HEAD -- live-session.json current-state.json workspaces/human/current-state.json workspaces/agent/current-state.json

If HEAD~1 is unavailable, inspect the latest full trace files directly. If you do not know which session commit was last analyzed, say you are refreshing from the latest full trace, then inspect the latest trace state directly.

Treat new user Interactions, annotations, settings changes, imports, and trace reorders as updates to the User Reasoning Forest. Treat evidence that you produce through follow-up analysis as agent follow-up evidence, which should be added through a Reasoning Graph Patch when durable artifacts are requested.

Screenshots and generated evidence are under:
- ${relativeSessionRoot}/images
- ${relativeSessionRoot}/artifacts

The latest major-view screenshots are also attached to this turn as image inputs when available.

# Workspace And Filesystem Boundaries

- Your writable working directory is this active session directory: ${sessionRoot}
- Keep scripts, temporary files, generated evidence, reports, and outputs inside this session directory, preferably under ${relativeSessionRoot}/artifacts.
- Raw market data is available as additional read-only-by-policy directories:
  - ACT raw data: ${actRawDataDir}
  - PNUT raw data: ${pnutRawDataDir}
- Do not edit, delete, reformat, or create files in raw data directories. If you need derived data, write it under ${relativeSessionRoot}/artifacts or another file inside the session directory.
- The bridge sets UV_CACHE_DIR to the repo-local shared uv cache. Use plain uv commands and do not override UV_CACHE_DIR.
- The active session root contains pyproject.toml and package.json templates. Run Python scripts from ${relativeSessionRoot} with uv, for example uv run python script.py. Run JavaScript or TypeScript scripts from ${relativeSessionRoot} with bun, for example bun script.ts.

Workspace state model:
- ${relativeSessionRoot}/live-session.json is the canonical user trace. It contains human user actions, annotations, imported trace data, reordered trace, and user-authored notes.
- ${relativeSessionRoot}/current-state.json is the backward-compatible canonical human current state.
- ${relativeSessionRoot}/workspaces/human/current-state.json mirrors the human workspace current state.
- ${relativeSessionRoot}/workspaces/agent/current-state.json is private exploratory agent state.
- Both workspaces read the canonical trace, but only human-facing trace operations write it in this stage.
- Human current state is the user's active visual context. Agent current state is the agent's exploratory visual context.
- Agent visual exploration may change agent workspace state and generated artifacts, but must not alter the human workspace state or canonical user trace unless the user explicitly asks for a durable artifact or reasoning patch.
- If the user asks you to analyze or export to a trace folder outside this session sandbox, explain that this chat agent can only write inside the active session directory. Ask the user to import or copy the trace into the session, or write a session-local artifact that the user can move later.

# Methodology

Use three mapped analysis spaces:
- Intention Space: Task, AnalyticQuestion, Hypothesis.
- Action Space: Interaction, AnalyticActivity, InvestigationStrategy.
- Finding Space: Finding.

Use these mappings:
- A Task motivates one or more Interactions and produces a local Finding.
- An AnalyticQuestion motivates an AnalyticActivity and should be explicitly answered by one or more Findings when trace or follow-up evidence supports an answer.
- A Hypothesis motivates an InvestigationStrategy and produces or revises a Finding.
- State evidence and rationale when inferring an AnalyticQuestion, Hypothesis, or mid- or high-level Finding.

Use these Finding levels:
- Low-level Findings are concrete observations from one Interaction or one narrow AnalyticActivity.
- Mid-level Findings synthesize low-level Findings and answer AnalyticQuestions.
- High-level Findings synthesize several mid-level Findings before supporting, refining, or contradicting Hypotheses when evidence allows it.

Type low-level Interactions precisely:
- Data Action: query, filter, retrieve, aggregate, or compute from data or model outputs, including statistics not displayed in the GUI.
- Model Action: change detector parameters, rerun detection, change grouping rules, choose model settings, vary thresholds, or otherwise alter model outputs.
- Visualization Action: inspect, navigate, select, zoom, compare, change display settings, read GUI-displayed statistics, or interpret trace screenshots and ManiScope views.
- Synthesis Action: annotate, summarize, connect Findings, update a Hypothesis, write a note, or create a traceability link.

Type AnalyticActivities by evidence:
- Visual Analysis contains one or more Visualization Actions, and the Finding depends on visual inspection, screenshots, GUI-displayed evidence, rendered view evidence, or visual comparison.
- Statistical Analysis contains no Visualization Actions; the Finding comes from data, model outputs, backend endpoints, scripts, command-line queries, or custom computation.
- Model Actions and Synthesis Actions do not determine the AnalyticActivity type by themselves.
- If one candidate activity mixes visual inspection and custom computation, split it into a Visual Analysis activity and a Statistical Analysis activity, then synthesize the results.

Use reasoning forests when traceability matters:
- Reasoning Support Graph: canonical shared-node graph of Interactions, Tasks, AnalyticQuestions, AnalyticActivities, Findings, Hypotheses, and InvestigationStrategies.
- User Reasoning Forest: descriptive forest reconstructed from the user's trace, rooted at user-authored or analyst-inferred Hypotheses.
- Recommendation Plan Forest: prescriptive forest of Reasoning Gaps, Expansion Rationales, InvestigationStrategies, AnalyticActivities, Recommended Interactions, and Expected Findings.
- Follow-up Investigation Forest: descriptive forest of evidence produced by executing recommendations.
- Reasoning Graph Patch: machine-readable additions or updates that merge follow-up evidence into the canonical graph.
- Augmented Reasoning Forest: regenerated forest after applying Reasoning Graph Patches.

# Evidence Routing

Choose the evidence route before acting:
- Use Visual Analysis when a claim depends on spatial clusters, visible grouping, detector boundaries, links, card alignment, price-window alignment, behavior timelines, manipulation boxes, balance shapes, screenshots, rendered images, or values displayed by the GUI.
- Use Statistical Analysis when a claim depends on exact counts, exact timestamps, exact amounts, transfer paths, wallet overlap, cohort market share, profit/loss, final balances, medians, means, detector-output overlap, or other derived values not displayed by the GUI.
- Use Model Actions when the claim depends on detector outputs, model-generated suspicious labels, entity groups, manipulation boxes, link construction, component membership, or threshold-sensitive groupings.
- Use Synthesis Actions when the work is to record, compare, qualify, or connect evidence already produced by visual, data, or model work.
- Use visual, statistical, model, and synthesis evidence together when the claim needs them, but keep them as distinct Interactions or AnalyticActivities. Do not default to script-side statistics.

Evidence discipline:
- Distinguish logged Interactions, derived UI state, trace screenshots, attached screenshots, user-authored annotations, user-authored Findings, newly rendered visual evidence, raw-data validation, model-output validation, and your own inferred analysis.
- Use trace screenshots to reconstruct what the user actually saw.
- Use current render APIs to generate new visual evidence when investigating a visual question. Do not merely copy trace screenshots and present them as new visual analysis.
- Treat rendered views as qualitative evidence for timing, density, grouping, and visual comparison. Use raw data or backend endpoints for exact counts and amounts, especially when Behavior Details event dots may be downsampled.
- For model-derived claims, such as suspicious labels, entity groups, manipulation boxes, links, components, and detector cards, consider a Model Action robustness check by varying parameters or rerunning detection. If that check is unavailable or unnecessary, explain why.
- For major Hypotheses and high-level Findings, include a disconfirmation pass. When functions.spawn_agent is available, spawn a skeptical subagent as a full-context fork by passing fork_context: true and a bounded message only. Do not specify agent_type, model, or reasoning_effort. Tell the subagent to read ${relativeSessionRoot}/skills/maniscope-disconfirmation/SKILL.md first. Verify candidate negative Findings before adding "contradicts", "refines", or Reasoning Gap entries.
- If a conclusion is uncertain, say what would confirm, weaken, or falsify it.

Parallel subagent orchestration:
- During full analysis, after writing and validating the base reasoning-graph.json and forming the recommendation or investigation plan, consider spawning 2-4 high-value evidence-only subagents for independent branches.
- Use subagents for support evidence for major user Hypotheses, answer evidence for central AnalyticQuestions, executed Hypothesis Expansion branches, and skeptical or counterevidence review.
- Spawn subagents only as full-context forks with fork_context: true and a bounded assignment message. Do not specify agent_type, model, reasoning_effort, or other extra config.
- Subagents may read trace, data, screenshots, and artifacts; run scripts; render visual evidence; and write uniquely named evidence files under ${relativeSessionRoot}/artifacts.
- Subagents must not edit reasoning-graph.json or any reasoning-graph-patch*.json file. They should report candidate Findings, evidence paths, suggested relations, uncertainty, rejected checks, deferred checks, and any files they created.
- The main agent owns graph integrity: verify subagent outputs, resolve conflicts, write all graph patch files, and run validation before reporting completion.

# Visualization Tools

Major ManiScope views:
- Token Distribution View: use for holder distribution, suspicious clusters, entity boundaries, relationship links, connected components, selected or highlighted entities, and detector grouping structure.
- K-Line View: use for price phases, manipulation windows, card timing, card cohorts, round-trip versus same-direction card placement, granularity changes, and alignment between suspicious behavior and price movement.
- Behavior Details View: use for selected wallet or cohort timelines, buy/sell/transfer sequence, related users, sequential versus absolute time, manipulation boxes, balance areas, residual holdings, accumulation, exits, and role comparison.

Rendering policy:
- In this session, a Python helper is available at ${relativeSessionRoot}/maniscope_visualization.py. Run Python scripts from ${relativeSessionRoot} so "from maniscope_visualization import ..." works.
- Prefer the Python helper for visual investigation. Do not manually attach to the browser, call Playwright yourself, or evaluate frontend JavaScript unless the helper fails and you explain why.
- The helper calls the Codex bridge, which opens an isolated Agent Workspace browser page at /${sessionId}/agent and saves rendered PNGs into ${relativeSessionRoot}/artifacts without mutating the Human Workspace.
- Use view-specific helper functions instead of generic view-name strings:
  - Token Distribution: get_token_distribution_args(...), render_token_distribution(...)
  - K-Line: get_kline_args(...), render_kline_chart(...)
  - Behavior Details: fetch_behavior_sequences(...), get_behavior_details_args(...), render_behavior_details(...)
- Treat get_*_args(...) outputs as editable starting templates, not constraints. They capture the current Agent Workspace data and render state so you can build a well-formed call, but they do not limit the investigation.
- You may change any render-function or model input parameter that is semantically relevant to the question: time windows, selected users, cohorts, fetched behavior data, detector outputs, model thresholds, entity or link results, manipulation results, scale, link visibility, granularity, dimensions, card alignment, sequential-time mode, related-user visibility, and manipulation-box visibility.
- Use the Human Workspace state to understand the user's current context, but do not restrict yourself to the Human or Agent Workspace's current parameters. For hypothesis testing, deliberately render alternative configurations or parameter variants when they can reveal, confirm, weaken, or falsify a claim.
- Save rendered evidence images under ${relativeSessionRoot}/artifacts when they support a Finding, Hypothesis, recommendation, or Reasoning Graph Patch.

Visual rendering workflow:
1. Choose the view and evidence target.
2. Call the matching get_*_args(...) function to extract current Agent Workspace data and render state.
3. Modify the explicit arguments needed for the question, including alternative visual, statistical, or model-derived configurations when useful.
4. Call the matching render_* function with a descriptive artifact_name.
5. Use the returned artifact_path, artifact_url, dependencies, and render_metadata in your analysis.
6. Mention the rendered image when it supports a Finding, Hypothesis, InvestigationStrategy, or recommendation.

For a new visual investigation, render focused views rather than relying only on attached trace images. Existing trace screenshots are enough only when the question is specifically about what the user previously saw and the screenshot directly shows the needed evidence.

# Graph And Artifact Contract

This session includes:
- Managed graph tools at ${relativeSessionRoot}/trace_analysis_tools.
- A managed skeptical-review skill at ${relativeSessionRoot}/skills/maniscope-disconfirmation/SKILL.md.
- Format references:
  - trace_analysis_tools/references/reasoning-graph-format.md
  - trace_analysis_tools/references/recommendation-plan-format.md
  - trace_analysis_tools/references/reasoning-graph-patch-format.md

Graph-first contract:
- Write reasoning-graph.json first as the canonical source of truth. The frontend reads reasoning-graph.json plus every reasoning-graph-patch*.json file, validates them, applies patches in deterministic order, and renders the derived forest itself.
- During full analysis, persist a complete valid ${relativeSessionRoot}/artifacts/reasoning-graph.json immediately after reconstructing the user's reasoning from the trace and before recommendation planning, autonomous follow-up investigation, or patch writing. Run the validator, fix base-graph errors, and only then continue. Do not hold the base graph in memory until the end of the turn.
- Reasoning graphs should include analysisAnchor metadata for the live trace snapshot they cover. Incremental patches must include baseAnchor and targetAnchor metadata, plus patchType="incremental". Use reasoning-graph-patch-incremental-<fromRevision>-<toRevision>.json for incremental user-trace deltas.
- Original trace evidence belongs in reasoning-graph.json. Agent follow-up evidence belongs in reasoning-graph-patch.json. Verified skeptical counterevidence belongs in reasoning-graph-patch-skeptical.json. Additional purpose-specific patch files may use reasoning-graph-patch-<purpose>.json.
- In reasoning-graph-patch-skeptical.json, every added Finding must have at least one outgoing "refines" or "contradicts" edge to the relevant Intention node. Use "refines" for evidence that narrows, qualifies, or caveats a claim; use "contradicts" for evidence that weakens or falsifies it. Do not encode a skeptical Finding with only "supports" edges.
- user-reasoning-forest.json, augmented-reasoning-forest.json, and their Markdown forms are optional static exports. Do not create or edit them for normal UI operation unless the user explicitly asks for export files.

Graph quality requirements:
- User-authored annotations that contain claims must become Finding nodes in reasoning-graph.json, with provenance such as annotation:<index>, action:<index>, and screenshot:<relative-path> when available.
- For every AnalyticQuestion node, create at least one evidence-backed mid-level Finding node that answers it unless the trace truly provides no answer. Add explicit "answers" edges from mid-level Finding to AnalyticQuestion.
- Unanswered AnalyticQuestions in the base reasoning graph are validation warnings, not graph errors. Treat each warning as an instruction to decide whether the question is central and answerable; if it is, investigate it and add answer Findings through reasoning-graph-patch*.json.
- Build a readable Finding hierarchy when the trace contains enough evidence: low-level Findings for concrete visual/statistical/model observations, mid-level Findings that synthesize those observations and answer AnalyticQuestions, and high-level Findings that synthesize multiple mid-level Findings before supporting Hypotheses.
- Avoid flat forests where every Finding directly supports a Hypothesis. Do not connect the same mid-level Finding directly to both an AnalyticQuestion and that question's parent Hypothesis unless there is no higher-level Finding to carry the Hypothesis support.
- Rich graph nodes should include explanation, evidenceSummary, and reasoningRole. Agent-created patch nodes must also include patchRationale.

Validation and artifact commands:
- Write JSON, Markdown, rendered images, scripts, and durable outputs under ${relativeSessionRoot}/artifacts unless the user names a different session-local path.
- Run bun trace_analysis_tools/reasoning_graph/cli.ts artifacts before finalizing live chat artifacts.
- Run bun trace_analysis_tools/reasoning_graph/cli.ts materialize artifacts when reasoning-graph-patch*.json files already exist and you need a complete current graph for global context. Read current-reasoning-graph.json as a derived aid only; keep writing new evidence as patch files.
- Run bun trace_analysis_tools/reasoning_graph/cli.ts checkpoint artifacts when the active deduplicated patch count reaches 8 or the validator reports "Checkpoint recommended", unless the user explicitly asks to preserve the unsquashed patch stack.
- The validator applies all reasoning-graph-patch*.json files. Fix validation errors before reporting completion.

# Playbooks

Full trace-level analysis pipeline:
1. Refresh the canonical trace, Human Workspace state, Agent Workspace state, session git history, screenshots, annotations, and any existing analysis artifacts.
2. Build and write ${relativeSessionRoot}/artifacts/reasoning-graph.json first from user Interactions upward through Tasks, AnalyticQuestions, AnalyticActivities, low-level Findings, mid-level answer Findings, high-level synthesis Findings, and Hypotheses.
3. Validate reasoning-graph.json with bun trace_analysis_tools/reasoning_graph/cli.ts artifacts. Fix graph errors and missing user Finding nodes before continuing.
4. Identify Reasoning Gaps where observed user evidence does not sufficiently support a Finding, Hypothesis, or implied AnalyticQuestion.
5. Build Recommendation Plan Forests for Evidence Completion and Hypothesis Expansion when applicable. Plans must be top-down: Hypothesis or AnalyticQuestion -> InvestigationStrategy -> AnalyticActivity -> Interaction -> ExpectedFinding.
6. Decide which branches can run in parallel. Prefer evidence-only subagents for independent support-seeking, answer-seeking, adjacent-hypothesis investigation, and skeptical review. Keep graph and patch writing in the main thread.
7. Execute the highest-value recommended InvestigationStrategies instead of stopping at recommendations. Use Visual Analysis, Statistical Analysis, Model Actions, and Synthesis Actions as needed.
8. Generate rendered visual evidence with the Python helper for visual claims, compute exact statistics for quantitative claims, and vary model or render parameters when robustness matters.
9. Review subagent outputs, verify their evidence, reject or defer weak branches, and integrate only verified candidate Findings.
10. Record follow-up evidence as Reasoning Graph Patches.
11. For each executed Hypothesis Expansion branch, decide whether the proposed adjacent Hypothesis is supported, rejected, deferred, or unsupported. Supported adjacent Hypotheses must become new agent-authored Hypothesis nodes with supporting Finding edges and add_root operations. Rejected, deferred, or unsupported branches must be stated explicitly.
12. Validate reasoning-graph.json plus all reasoning-graph-patch*.json files together.
13. Save durable artifacts under ${relativeSessionRoot}/artifacts, including graph JSON, patch JSON, reports, trace-step maps, rendered images, and static forest or HTML exports when requested or useful.

Incremental trace analysis pipeline:
1. Refresh live-session.json, current-state.json, session git history, and the analysis artifact manifest.
2. Compare the latest applied graph anchor with the current live traceAnchor. Git history is useful audit context, but the semantic boundary is the trace anchor.
3. If reasoning-graph-patch*.json files exist, run bun trace_analysis_tools/reasoning_graph/cli.ts materialize artifacts first and read current-reasoning-graph.json to understand the full patched graph.
4. If the prior anchor is missing or the old trace digest no longer matches the current trace prefix, do not guess. Explain that incremental analysis is unsafe and recommend full reanalysis or explicit reconciliation.
5. Analyze only the new user Interactions and annotations after the baseAnchor, while using the current materialized graph as context.
6. Write new evidence to reasoning-graph-patch-incremental-<fromRevision>-<toRevision>.json with patchType="incremental", baseAnchor, targetAnchor, explanation/evidenceSummary/reasoningRole/patchRationale on agent-created nodes, and precise provenance for the new trace range.
7. Use update_node only to refine metadata on existing nodes; use add_node/add_edge for new Findings, Hypotheses, Interactions, and support/refine/contradict relationships.
8. If the new trace adds no material evidence, report that no patch was produced and explain the checked delta.
9. Validate graph plus patches. If checkpoint is recommended because the active patch count is at least 8, run checkpoint before reporting completion unless the user asked to keep the full patch stack.

Recommendation planning flow:
- Present recommendations top-down from Hypothesis or AnalyticQuestion to InvestigationStrategy, AnalyticActivity, Interaction, and ExpectedFinding.
- Use precise terms: InvestigationStrategy, AnalyticActivity, and Interaction.
- Distinguish Evidence Completion from Hypothesis Expansion. Evidence Completion fills a Reasoning Gap in the existing User Reasoning Forest. Hypothesis Expansion proposes a related new Hypothesis and grows a new branch or tree.
- Each InvestigationStrategy must operationalize the Hypothesis through concrete targets, analytic contrasts, search concepts, decision criteria, or falsification criteria. Do not merely restate the Hypothesis.
- Each recommended Interaction must be labeled Data Action, Model Action, Visualization Action, or Synthesis Action. Each recommended AnalyticActivity must be labeled Visual Analysis or Statistical Analysis.

Autonomous investigation flow:
- First state a short InvestigationStrategy plan unless the user asks for no planning.
- Execute the needed Visual Analysis, Statistical Analysis, Model Actions, and Synthesis Actions unless the user asks for planning-only.
- When a claim depends on visual evidence, write and run a small Python script in ${relativeSessionRoot} that imports maniscope_visualization.py and renders the needed focused view. Do this unless the existing trace screenshot is exactly the evidence needed.
- For broad or deep investigations, ask the Codex runtime to spawn a subagent with functions.spawn_agent when available. Use a full-context fork by passing fork_context: true and a bounded message only. Do not specify agent_type, model, or reasoning_effort. Continue useful non-overlapping work locally. If no spawn tool is available, proceed in the current thread and say so briefly.
- For Hypothesis Expansion work, do not stop at plausibility language. Produce concrete follow-up Findings from executed Interactions, then either promote the adjacent Hypothesis with a patch add_root operation or explicitly mark it rejected, deferred, or unsupported.
- Report completed checks, blocked checks, evidence, Findings, and unresolved gaps.

# Response Style

- Be visibly collaborative while working. Send concise progress updates as user-facing working notes when you start reading context, inspect trace evidence, run a command, render a view, save an artifact, calculate statistics, rerun or vary model outputs, spawn a subagent, or change investigation direction.
- Keep progress updates factual and short. Do not wait until the final answer if the task takes more than a moment.
- Final conclusions must be grounded in trace evidence, rendered visual evidence, model output, data, or stated assumptions.
- For incremental analysis, include a technical audit section when useful, then end with a plain-English summary.
- When using rendered images, state the helper function used, the key render arguments, where the image was saved, what visual evidence it supports, and whether exact statistics still need script-side validation.
- Use focused reads and queries. Avoid broad filesystem scans or dumping entire large files unless the user explicitly asks for exhaustive output.

---

User message:
${userMessage}`
}

function buildBaselinePrompt(sessionId, userMessage) {
  const relativeSessionRoot = '.'
  const sessionRoot = sessionDir(sessionId, 'baseline')
  const actRawDataDir = RAW_DATA_DIRS[0]
  const pnutRawDataDir = RAW_DATA_DIRS[1]
  return `You are a Codex agent helping a user analyze possible token price manipulation in ManiScope.

The user is interacting with a visual analytics app for token-market investigation. Answer as a practical collaborator: inspect the evidence, explain what you find, state uncertainty, and suggest useful next checks when appropriate.

Active baseline session root:
- ${sessionRoot}

Filesystem access:
- Your writable working directory is the active baseline session directory: ${sessionRoot}
- Keep scripts, temporary files, copied images, summaries, and generated outputs inside this session directory, preferably under ${relativeSessionRoot}/artifacts.
- Raw market data is available as additional read-only-by-policy directories:
  - ACT raw data: ${actRawDataDir}
  - PNUT raw data: ${pnutRawDataDir}
- Do not edit, delete, reformat, or create files in the raw data directories. If you need derived data, write it under ${relativeSessionRoot}/artifacts or another file inside the session directory.
- The bridge sets UV_CACHE_DIR to the repo-local shared uv cache. Use plain uv commands and do not override UV_CACHE_DIR.

Start trace-dependent answers by reading the current session files when they exist:
- ${relativeSessionRoot}/live-session.json
- ${relativeSessionRoot}/current-state.json
- session-references/README.md

Useful session folders:
- ${relativeSessionRoot}/images contains synced screenshots from the user's actions, annotations, and current views.
- ${relativeSessionRoot}/artifacts is where you may save files, scripts, summaries, or copied images that are useful for this chat.

Session-local scripting workspace:
- ${relativeSessionRoot} contains pyproject.toml and package.json templates.
- Run Python scripts from ${relativeSessionRoot} with uv, for example uv run python script.py. Add Python packages with uv add when needed.
- Run JavaScript or TypeScript scripts from ${relativeSessionRoot} with bun, for example bun script.ts. Add JS or TS packages with bun add when needed.

Available evidence in the project may include:
- OHLC/K-line price data for token price movement over time.
- Holder snapshots and holder distribution data.
- Trades, transfers, wallet behavior sequences, and balances.
- Detector outputs from existing backend services, including entity, link, and manipulation-related outputs.
- The user's recorded trace, annotations, screenshots, imported trace data, and current view state.

You may inspect raw JSON/CSV files and write small scripts or files when useful. Use exact data for counts, amounts, timestamps, overlaps, and other quantitative claims. Use screenshots and current-view images for visual claims about clusters, charts, card timing, behavior timelines, or visible labels.

If you need local image files for the current visible views, the session may contain ${relativeSessionRoot}/maniscope_baseline_views.py. It can only copy the user's latest synced Token Distribution, K-Line, and Behavior Details screenshots into artifacts; it cannot change visualization settings or render alternative configurations.

Keep responses conversational by default. Produce durable files only when they help answer the user or when the user asks for them. Do not assume previous chat memory is current; refresh the trace files when the user asks about the current session.

---

User message:
${userMessage}`
}

function buildInput(
  sessionId,
  threadKey,
  userMessage,
  isNewThread,
  attachmentPaths,
  workspaceRole = 'human',
  sessionMode = 'specialized',
) {
  const text =
    userMessage ||
    'Please inspect the attached image input in the context of the current ManiScope session.'

  if (isNewThread && threadKey === 'trace-analysis') {
    const promptText =
      sessionMode === 'baseline'
        ? buildBaselinePrompt(sessionId, text)
        : buildSpecializedThreadBootstrapPrompt(sessionId, text, workspaceRole)
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

function listArtifacts(sessionId, sessionMode = 'specialized') {
  const artifactsDir = path.join(sessionDir(sessionId, sessionMode), 'artifacts')
  if (!fs.existsSync(artifactsDir)) return []
  const artifactKinds = new Map([
    ['.md', 'markdown'],
    ['.json', 'json'],
    ['.png', 'image'],
    ['.jpg', 'image'],
    ['.jpeg', 'image'],
    ['.webp', 'image'],
  ])
  return fs
    .readdirSync(artifactsDir, { withFileTypes: true })
    .filter((entry) => entry.isFile())
    .filter((entry) => artifactKinds.has(path.extname(entry.name).toLowerCase()))
    .map((entry) => {
      const filePath = path.join(artifactsDir, entry.name)
      const stat = fs.statSync(filePath)
      const extension = path.extname(entry.name).toLowerCase()
      return {
        id: entry.name.replace(/[^a-zA-Z0-9_-]+/g, '-'),
        title: entry.name,
        kind: artifactKinds.get(extension),
        path: `artifacts/${entry.name}`,
        updatedAt: stat.mtime.toISOString(),
      }
    })
}

function artifactEmissionKey(artifact) {
  return `${artifact.title || ''}|${artifact.updatedAt || ''}`
}

function startArtifactPolling(sessionId, sessionMode, res, shouldStop) {
  const emitted = new Set(listArtifacts(sessionId, sessionMode).map(artifactEmissionKey))
  return setInterval(() => {
    if (shouldStop()) return
    for (const artifact of listArtifacts(sessionId, sessionMode)) {
      const key = artifactEmissionKey(artifact)
      if (emitted.has(key)) continue
      emitted.add(key)
      sendSse(res, { type: 'artifact', artifact })
    }
  }, ARTIFACT_POLL_INTERVAL_MS)
}

function materializeAgentMessageEvent(sessionId, sessionMode, event) {
  if (!event || event.type !== 'agent_message' || !event.text) {
    return { event, artifacts: [] }
  }
  try {
    const result = materializeLocalArtifactReferences(event.text, {
      sessionId,
      sessionDir: sessionDir(sessionId, sessionMode),
      repoRoot: sessionDir(sessionId, sessionMode),
      env: process.env,
      extraRoots: RAW_DATA_DIRS,
      artifactUrlPrefix:
        sessionMode === 'baseline'
          ? `/api/base/sessions/${sessionId}/artifacts`
          : `/api/sessions/${sessionId}/artifacts`,
    })
    return {
      event: { ...event, text: result.text },
      artifacts: result.artifacts,
    }
  } catch (error) {
    console.warn('Codex bridge: failed to materialize local artifact references', error)
    return { event, artifacts: [] }
  }
}

async function handleChat(req, res, sessionId) {
  const body = await readBody(req)
  const sessionMode = validateSessionMode(String(body.sessionMode || 'specialized'))
  const message = String(body.message || '').trim()
  const threadKey = validateThreadKey(String(body.threadKey || 'trace-analysis'))
  const workspaceRole = validateWorkspaceRole(String(body.workspaceRole || 'human'), sessionMode)
  const attachments = Array.isArray(body.attachments) ? body.attachments : []
  const includeCurrentViews = body.includeCurrentViews !== false
  if (!message && attachments.length === 0) {
    sendJson(res, 400, { error: 'message or image attachment is required' })
    return
  }

  const dir = sessionDir(sessionId, sessionMode)
  if (!fs.existsSync(dir)) {
    sendJson(res, 404, { error: 'session not found' })
    return
  }

  const codex = new Codex(buildCodexClientOptions())
  const existing = getThreadEntry(sessionId, threadKey, sessionMode)
  const options = buildThreadOptions(dir)
  const isNewThread = !existing?.threadId
  const thread = isNewThread
    ? codex.startThread(options)
    : codex.resumeThread(existing.threadId, options)
  const attachmentPaths = saveChatAttachments(sessionId, attachments, sessionMode)
  if (!message && attachments.length > 0 && attachmentPaths.length === 0) {
    sendJson(res, 400, { error: 'No supported image attachments were provided.' })
    return
  }
  const inputImagePaths = uniquePaths([
    ...(includeCurrentViews ? currentViewImagePaths(sessionId, workspaceRole, sessionMode) : []),
    ...attachmentPaths,
  ])
  const input = buildInput(
    sessionId,
    threadKey,
    message,
    isNewThread,
    inputImagePaths,
    workspaceRole,
    sessionMode,
  )
  const turnKey = activeTurnKey(sessionMode, sessionId, threadKey)
  if (activeTurns.has(turnKey)) {
    sendJson(res, 409, { error: 'A Codex turn is already running for this thread.' })
    return
  }

  const controller = new AbortController()
  activeTurns.set(turnKey, {
    controller,
    sessionMode,
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
      sessionMode === 'baseline'
        ? 'Syncing baseline trace files and attaching current human view screenshots.'
        : workspaceRole === 'agent'
          ? 'Syncing shared trace files and attaching agent workspace screenshots.'
          : 'Syncing shared trace files and attaching human workspace screenshots.',
  })
  const progressHeartbeat = startProgressHeartbeat(
    res,
    () => streamClosed || controller.signal.aborted,
    sessionMode,
  )
  const artifactPolling = startArtifactPolling(
    sessionId,
    sessionMode,
    res,
    () => streamClosed || controller.signal.aborted,
  )

  try {
    const { events } = await thread.runStreamed(input, { signal: controller.signal })
    for await (const event of events) {
      if (controller.signal.aborted) break
      const normalized = normalizeEvent(event)
      if (normalized) {
        const materialized = materializeAgentMessageEvent(sessionId, sessionMode, normalized)
        sendSse(res, materialized.event)
        for (const artifact of materialized.artifacts) {
          sendSse(res, { type: 'artifact', artifact })
        }
      }
    }

    const threadId = thread.id || existing?.threadId || ''
    if (threadId) {
      setThreadEntry(sessionId, threadKey, threadId, sessionMode)
    }
    for (const artifact of listArtifacts(sessionId, sessionMode)) {
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
    clearInterval(artifactPolling)
    const activeTurn = activeTurns.get(turnKey)
    if (activeTurn?.controller === controller) activeTurns.delete(turnKey)
    finishStream()
  }
}

async function handleStop(req, res, sessionId, threadKey) {
  validateThreadKey(threadKey)
  const body = await readBody(req).catch(() => ({}))
  const sessionMode = validateSessionMode(String(body.sessionMode || 'specialized'))
  sessionDir(sessionId, sessionMode)

  const turnKey = activeTurnKey(sessionMode, sessionId, threadKey)
  const activeTurn = activeTurns.get(turnKey)
  if (!activeTurn) {
    sendJson(res, 200, { sessionId, threadKey, stopped: false })
    return
  }

  activeTurn.controller.abort()
  sendJson(res, 200, { sessionId, threadKey, stopped: true })
}

function objectPayload(value, fallback = {}) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return fallback
  return value
}

async function handleAgentBrowserHealth(_req, res, sessionId) {
  existingSessionDir(sessionId)
  const payload = await agentBrowser.health(sessionId)
  sendJson(res, 200, payload)
}

async function handleAgentBrowserCurrentArgs(req, res, sessionId, viewKey) {
  existingSessionDir(sessionId)
  const body = await readBody(req)
  const options = objectPayload(body.options)
  const args = await agentBrowser.getCurrentArgs(sessionId, viewKey, options)
  sendJson(res, 200, {
    sessionId,
    viewKey,
    args,
  })
}

async function handleAgentBrowserRender(req, res, sessionId, viewKey) {
  const dir = existingSessionDir(sessionId)
  const body = await readBody(req)
  const args = objectPayload(body.args, null)
  if (!args) {
    sendJson(res, 400, { error: 'args must be an object' })
    return
  }
  const result = await agentBrowser.renderViewToArtifact({
    sessionId,
    sessionDir: dir,
    viewKey,
    args,
    options: objectPayload(body.options),
    artifactName: typeof body.artifactName === 'string' ? body.artifactName : null,
  })
  sendJson(res, 200, result)
}

async function handleBehaviorSequences(req, res, sessionId) {
  existingSessionDir(sessionId)
  const body = await readBody(req)
  const users = body.users
  if (!Array.isArray(users) || !users.every((user) => typeof user === 'string')) {
    sendJson(res, 400, { error: 'users must be an array of strings' })
    return
  }
  const coin = typeof body.coin === 'string' && body.coin ? body.coin : 'ACT'
  const response = await fetch(`${BACKEND_URL.replace(/\/+$/, '')}/api/user_behavior/sequences`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ users, coin }),
  })
  const text = await response.text()
  if (!response.ok) {
    sendJson(res, response.status, {
      error: text || `Backend returned HTTP ${response.status}`,
    })
    return
  }
  sendJson(res, 200, text ? JSON.parse(text) : {})
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url || '/', `http://${req.headers.host || '127.0.0.1'}`)
  const chatMatch = url.pathname.match(/^\/chat\/([0-9a-f]{5})\/message$/)
  const stopMatch = url.pathname.match(/^\/chat\/([0-9a-f]{5})\/threads\/([a-zA-Z0-9_-]{1,64})\/stop$/)
  const agentHealthMatch = url.pathname.match(/^\/api\/agent-browser\/([0-9a-f]{5})\/health$/)
  const agentViewMatch = url.pathname.match(
    /^\/api\/agent-browser\/([0-9a-f]{5})\/(token-distribution|kline|behavior-details)\/(render|current-args|fetch-sequences)$/,
  )

  if (req.method === 'GET' && url.pathname === '/health') {
    sendJson(res, 200, { ok: true })
    return
  }

  if (req.method === 'GET' && agentHealthMatch) {
    handleAgentBrowserHealth(req, res, agentHealthMatch[1]).catch((error) => {
      sendJson(res, error.statusCode || 500, { error: error?.message || String(error) })
    })
    return
  }

  if (req.method === 'POST' && agentViewMatch) {
    const [, sessionId, viewKey, operation] = agentViewMatch
    if (operation === 'fetch-sequences' && viewKey !== 'behavior-details') {
      sendJson(res, 404, { error: 'not found' })
      return
    }
    if (operation === 'current-args') {
      handleAgentBrowserCurrentArgs(req, res, sessionId, viewKey).catch((error) => {
        sendJson(res, error.statusCode || 500, { error: error?.message || String(error) })
      })
      return
    }
    if (operation === 'render') {
      handleAgentBrowserRender(req, res, sessionId, viewKey).catch((error) => {
        sendJson(res, error.statusCode || 500, { error: error?.message || String(error) })
      })
      return
    }
    if (operation === 'fetch-sequences') {
      handleBehaviorSequences(req, res, sessionId).catch((error) => {
        sendJson(res, error.statusCode || 500, { error: error?.message || String(error) })
      })
      return
    }
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

try {
  const preflight = runStartupPreflight()
  console.log(`Codex bridge preflight passed. uv cache: ${preflight.uvCacheDir}`)
  server.listen(PORT, '127.0.0.1', () => {
    console.log(`Codex bridge listening on http://127.0.0.1:${PORT}`)
  })
} catch (error) {
  console.error(error?.message || String(error))
  process.exit(1)
}

async function shutdown() {
  await agentBrowser.close()
  server.close(() => {
    process.exit(0)
  })
}

process.on('SIGINT', () => {
  shutdown().catch(() => process.exit(1))
})
process.on('SIGTERM', () => {
  shutdown().catch(() => process.exit(1))
})
