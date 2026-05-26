import { Codex } from '@openai/codex-sdk'
import http from 'node:http'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { AgentBrowserManager } from './agent-browser.mjs'
import { materializeLocalArtifactReferences } from './local-image-artifacts.mjs'

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
const DEFAULT_BACKEND_URL = 'http://127.0.0.1:8099'
const BACKEND_URL = process.env.MANISCOPE_BACKEND_URL || DEFAULT_BACKEND_URL
const DEFAULT_CODEX_NETWORK_ACCESS_ENABLED = true
const IMAGE_DATA_URL_RE = /^data:image\/(png|jpeg|jpg|webp);base64,/i
const activeTurns = new Map()
const agentBrowser = new AgentBrowserManager()

function sessionDir(sessionId) {
  if (!SESSION_ID_RE.test(sessionId)) {
    const error = new Error('Session ID must be 5 lowercase hex characters')
    error.statusCode = 400
    throw error
  }
  return path.join(SESSIONS_DIR, sessionId)
}

function existingSessionDir(sessionId) {
  const dir = sessionDir(sessionId)
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

function booleanEnv(name, defaultValue) {
  const value = process.env[name]
  if (value === undefined || value === '') return defaultValue
  const normalized = value.trim().toLowerCase()
  if (['1', 'true', 'yes', 'on'].includes(normalized)) return true
  if (['0', 'false', 'no', 'off'].includes(normalized)) return false
  return defaultValue
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
    networkAccessEnabled: booleanEnv(
      'CODEX_NETWORK_ACCESS',
      DEFAULT_CODEX_NETWORK_ACCESS_ENABLED,
    ),
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
   - Finding Space: Finding.
   - A Task motivates one or more Interactions and produces a local Finding.
   - An AnalyticQuestion motivates an AnalyticActivity and must be explicitly answered by one or more Findings.
   - A Hypothesis motivates an InvestigationStrategy and produces or revises a Finding.
   - State evidence and rationale when you infer an AnalyticQuestion, Hypothesis, or mid- or high-level Finding.

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
   - Reasoning Support Graph: canonical shared-node graph of Interactions, Tasks, AnalyticQuestions, AnalyticActivities, Findings, Hypotheses, and InvestigationStrategies.
   - User Reasoning Forest: descriptive forest reconstructed from the user's trace, rooted at user-authored or analyst-inferred Hypotheses.
   - Recommendation Plan Forest: prescriptive forest of Reasoning Gaps, Expansion Rationales, InvestigationStrategies, AnalyticActivities, Recommended Interactions, and Expected Findings.
   - Follow-up Investigation Forest: descriptive forest of evidence produced by executing recommendations.
   - Reasoning Graph Patch: machine-readable additions or updates that merge follow-up evidence into the canonical graph.
   - Augmented Reasoning Forest: regenerated forest after applying Reasoning Graph Patches.

Evidence discipline:
- Distinguish logged Interactions, derived UI state, trace screenshots, attached screenshots, user-authored annotations, user-authored Findings, newly rendered visual evidence, raw-data validation, model-output validation, and your own inferred analysis.
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
- Use this visual rendering workflow:
  1. Choose the view and evidence target.
  2. Call the matching get_*_args(...) function to extract current Agent Workspace data and render state.
  3. Modify the explicit arguments needed for the question, including alternative visual, statistical, or model-derived configurations when useful.
  4. Call the matching render_* function with a descriptive artifact_name.
  5. Use the returned artifact_path, artifact_url, dependencies, and render_metadata in your analysis.
  6. Mention the rendered image when it supports a Finding, Hypothesis, InvestigationStrategy, or recommendation.
- For a new visual investigation, render focused views rather than relying only on attached trace images. Existing trace screenshots are enough only when the question is specifically about what the user previously saw and the screenshot directly shows the needed evidence.
- For Token Distribution, use render_token_distribution for holder clusters, links, entity boundaries, suspicious user locations, selected entities, and detector grouping structure.
- For K-Line, use render_kline_chart for price phases, manipulation card timing, time-window alignment, and cohort comparison. Prefer visible_time_window and card_alignment="visible_window" when focusing on a suspicious time range.
- For Behavior Details, use fetch_behavior_sequences before rendering when behavior_data is not already available. Use render_behavior_details for wallet or cohort timelines, role comparison, buy/sell/transfer order, balance trajectories, residual holdings, exits, and manipulation boxes. Use strict rendering when an empty view would be misleading.
- Use larger dimensions or full-quality renders when labels, card text, timelines, or dense event patterns matter.
- Save rendered evidence images when they support a Finding, Hypothesis, recommendation, or Reasoning Graph Patch. For trace analysis artifacts, save them under analysis-results/continued-investigation-assets or another assets folder inside analysis-results.

Session-local trace-analysis tools:
- This session includes a managed tool bundle at ${relativeSessionRoot}/trace_analysis_tools. Run graph, forest, plan, and patch validation scripts from ${relativeSessionRoot}.
- Read the copied format references before writing durable artifacts:
  - trace_analysis_tools/references/reasoning-graph-format.md
  - trace_analysis_tools/references/recommendation-plan-format.md
  - trace_analysis_tools/references/reasoning-graph-patch-format.md
- Graph-first contract: write reasoning-graph.json first as the canonical source of truth. Then mechanically generate user-reasoning-forest.json and user-reasoning-forest.md with trace_analysis_tools/scripts/reasoning_graph_to_forest.py. Do not hand-author or manually edit user-reasoning-forest.json.
- user-reasoning-forest.json is a generated projection with duplicated tree instances and canonical node references. It is not the source of truth; reasoning-graph.json is.
- For every AnalyticQuestion node, create at least one evidence-backed Finding node that answers it, unless the trace truly provides no answer. Add explicit "answers" edges from Finding -> AnalyticQuestion. Do not rely only on shared Hypothesis membership, nearby AnalyticActivities, or prose explanations. If the answer is partial or caveated, encode that in the Finding label, confidence, explanation, and rationale.
- User-authored annotations that contain claims must become Finding nodes in reasoning-graph.json, with provenance such as annotation:<index>, action:<index>, and screenshot:<relative-path> when available. Do not leave user Findings only in prose or only in reasoning-graph-patch.json.
- Agent follow-up evidence belongs in reasoning-graph-patch.json, then in augmented-reasoning-graph.json and augmented-reasoning-forest.json after applying the patch script.
- For every executed Hypothesis Expansion branch, explicitly resolve the proposed adjacent Hypothesis in the follow-up evidence. If follow-up Findings support it, create a new agent-authored Hypothesis node in the Reasoning Graph Patch, connect supporting agent Findings to it, include an add_root operation, and regenerate the Augmented Reasoning Forest so the adjacent Hypothesis appears as a separate tree. If evidence does not support it, mark it rejected, deferred, or unsupported in the follow-up report and add a contradicts or refines Finding when evidence warrants it. Do not silently fold Hypothesis Expansion evidence into the original user Hypothesis only.
- For live chat session artifacts, write JSON and Markdown under ${relativeSessionRoot}/artifacts unless the user names a different path. For exported trace-folder analyses, write under TRACE/analysis-results.
- Use these session-local commands for live chat artifacts:
  - python3 trace_analysis_tools/scripts/reasoning_graph_to_forest.py artifacts/reasoning-graph.json --json-out artifacts/user-reasoning-forest.json --md-out artifacts/user-reasoning-forest.md
  - python3 trace_analysis_tools/scripts/recommendation_plan_to_forest.py artifacts/recommendation-plan-graph.json --json-out artifacts/recommendation-plan-forest.json --md-out artifacts/recommendation-plan-forest.md
  - python3 trace_analysis_tools/scripts/apply_reasoning_graph_patch.py artifacts/reasoning-graph.json artifacts/reasoning-graph-patch.json --out artifacts/augmented-reasoning-graph.json --forest-json-out artifacts/augmented-reasoning-forest.json --forest-md-out artifacts/augmented-reasoning-forest.md
- Before finalizing a full trace artifact set, verify that reasoning-graph.json validates, that user-reasoning-forest.json was generated from it, that every AnalyticQuestion has at least one incoming "answers" edge from a Finding or is marked as an unresolved Reasoning Gap, and that trace annotations with user claims appear as user Finding nodes rather than being lost.

Full trace-level analysis pipeline:
- Trigger this pipeline when the user asks for full, comprehensive, complete, end-to-end, or artifact-producing trace analysis, or when they ask to analyze a trace without scoping the request to a narrow question.
- Unless the user explicitly scopes the task down, combine trace reconstruction, recommendation planning, autonomous follow-up investigation, graph patching, forest regeneration, and artifact writing into one complete workflow.
- Execute the pipeline in this order:
  1. Refresh the canonical trace, Human Workspace state, Agent Workspace state, session git history, screenshots, annotations, and any existing analysis artifacts.
  2. Build reasoning-graph.json first from user Interactions upward through Tasks, AnalyticQuestions, AnalyticActivities, Findings, and Hypotheses. Keep raw Interactions as leaves, preserve evidence links, convert user-authored claim annotations into Finding nodes, and connect Findings back to the AnalyticQuestions they answer with explicit "answers" edges.
  3. Run trace_analysis_tools/scripts/reasoning_graph_to_forest.py to generate user-reasoning-forest.json and user-reasoning-forest.md from reasoning-graph.json. If the generated forest is missing user Findings present in annotations, fix the graph and regenerate the forest.
  4. Identify Reasoning Gaps where the observed user evidence does not sufficiently support a Finding, Hypothesis, or implied AnalyticQuestion.
  5. Build Recommendation Plan Forests for both Evidence Completion and Hypothesis Expansion when applicable. Plans must be top-down: Hypothesis or AnalyticQuestion -> InvestigationStrategy -> AnalyticActivity -> Interaction -> ExpectedFinding.
  6. Execute the highest-value recommended InvestigationStrategies instead of stopping at recommendations. Use Visual Analysis, Statistical Analysis, Model Actions, and Synthesis Actions as needed.
  7. Generate new rendered visual evidence with the Python helper for visual claims, compute exact statistics for quantitative claims, and vary model or render parameters when robustness matters.
  8. Record follow-up evidence as Reasoning Graph Patches, including explanation, evidenceSummary, reasoningRole, and patchRationale for agent-created patch nodes.
  9. For each executed Hypothesis Expansion branch, decide whether the proposed adjacent Hypothesis is supported, rejected, deferred, or unsupported. Supported adjacent Hypotheses must become new agent-authored Hypothesis nodes with supporting Finding edges and add_root operations. Rejected, deferred, or unsupported branches must be stated explicitly in the follow-up report, not hidden inside evidence for the original Hypothesis.
  10. Apply the patch script to regenerate the Augmented Reasoning Forest, and generate Follow-up Investigation Forests or executed adjacent hypothesis forests for Hypothesis Expansion work.
  11. Save durable artifacts under TRACE/analysis-results for trace-folder analyses or ${relativeSessionRoot}/artifacts for live-chat session analyses, including graph JSON, forests, trace-step maps, rendered images, and an HTML viewer when requested or useful.
- If time, tool access, missing data, or rendering failures prevent a complete pipeline, say which stages were completed, which were blocked, and what exact evidence or tool would unblock the remaining stages.

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
- Infer Tasks, AnalyticQuestions, Hypotheses, Interactions, AnalyticActivities, and Findings with evidence and rationale.
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
- When a claim depends on visual evidence, write and run a small Python script in ${relativeSessionRoot} that imports maniscope_visualization.py and renders the needed focused view. Do this unless the existing trace screenshot is exactly the evidence needed.
- Do not only cite old trace screenshots for a new visual investigation. Use newly rendered evidence when investigating a new visual question, then pair it with statistical or model checks when exact values or robustness matter.
- For broad or deep investigations, ask the Codex runtime to spawn a subagent with functions.spawn_agent when that tool is available. Give the subagent a bounded evidence-gathering task and continue useful non-overlapping work locally. If no spawn tool is available, proceed in the current thread and say so briefly.
- Convert recommendation-plan Interactions into concrete visual checks, data queries, model robustness checks, or synthesis steps.
- For Hypothesis Expansion work, do not stop at plausibility language. Produce concrete follow-up Findings from executed Interactions, then either promote the adjacent Hypothesis with a patch add_root operation or explicitly mark it rejected, deferred, or unsupported.
- Report completed checks, blocked checks, evidence, Findings, and unresolved gaps.

Mode F: artifact-writing.
- Use chat-first output unless the user asks for files or durable analysis artifacts.
- If writing full trace artifacts for a trace folder, place them under TRACE/analysis-results.
- If writing session-local live-chat artifacts, place generated evidence under ${relativeSessionRoot}/artifacts unless the user names a different output path.
- Write reasoning-graph.json first, then generate user-reasoning-forest.json and user-reasoning-forest.md with the session-local trace_analysis_tools script. Do not manually create a forest that bypasses graph validation.
- When you create AnalyticQuestion nodes, also create direct answer Findings and "answers" edges. A generated forest that contains questions but no answer Findings is incomplete even if the Hypothesis has other support.
- Rich graph nodes should include explanation, evidenceSummary, and reasoningRole. Agent-created patch nodes must also include patchRationale.
- Original trace evidence belongs to the User Reasoning Forest. Agent follow-up evidence belongs in a Reasoning Graph Patch and then in the Augmented Reasoning Forest.

Be visibly collaborative while working:
- Send concise progress updates as user-facing working notes when you start reading context, inspect trace evidence, run a command, render a view, save an artifact, calculate statistics, rerun or vary model outputs, spawn a subagent, or change investigation direction.
- Keep progress updates factual and short. Do not wait until the final answer if the task takes more than a moment.
- Final conclusions must be grounded in trace evidence, rendered visual evidence, model output, data, or stated assumptions.
- When using rendered images, state the helper function used, the key render arguments, where the image was saved, what visual evidence it supports, and whether exact statistics still need script-side validation.

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

function materializeAgentMessageEvent(sessionId, event) {
  if (!event || event.type !== 'agent_message' || !event.text) {
    return { event, artifacts: [] }
  }
  try {
    const result = materializeLocalArtifactReferences(event.text, {
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
    console.warn('Codex bridge: failed to materialize local artifact references', error)
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

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Codex bridge listening on http://127.0.0.1:${PORT}`)
})

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
