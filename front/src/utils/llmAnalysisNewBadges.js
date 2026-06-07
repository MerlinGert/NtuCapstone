import {
  evaluationKeyForNode,
  isEvaluableAnalysisNode,
} from './llmAnalysisEvaluations.js'

function nowIso(now = new Date()) {
  return now instanceof Date ? now.toISOString() : new Date(now).toISOString()
}

function normalizeNodeIdList(value) {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => String(item || '').trim())
    .filter(Boolean)
}

function normalizeActiveRun(activeRun) {
  if (!activeRun || typeof activeRun !== 'object') return null
  const runId = String(activeRun.runId || '').trim()
  if (!runId) return null
  return {
    runId,
    startedAt: typeof activeRun.startedAt === 'string' ? activeRun.startedAt : null,
    suppressNewBadges: activeRun.suppressNewBadges === true,
    baselineVisibleNodeIds: normalizeNodeIdList(activeRun.baselineVisibleNodeIds),
  }
}

export function normalizeAnalysisUiState(payload) {
  const source = payload && typeof payload === 'object' ? payload : {}
  const rawNewNodeIds = source.newNodeIds && typeof source.newNodeIds === 'object'
    ? source.newNodeIds
    : {}
  const newNodeIds = {}
  Object.entries(rawNewNodeIds).forEach(([key, entry]) => {
    const nodeId = String(key || '').trim()
    if (!nodeId || !entry || typeof entry !== 'object') return
    const nodeKind = String(entry.nodeKind || '')
    if (!['Hypothesis', 'Finding'].includes(nodeKind)) return
    newNodeIds[nodeId] = {
      nodeKind,
      firstSeenAt: typeof entry.firstSeenAt === 'string' ? entry.firstSeenAt : null,
      runId: typeof entry.runId === 'string' ? entry.runId : null,
    }
  })
  return {
    sessionId: source.sessionId || null,
    sessionMode: source.sessionMode || 'specialized',
    updatedAt: typeof source.updatedAt === 'string' ? source.updatedAt : null,
    activeRun: normalizeActiveRun(source.activeRun),
    newNodeIds,
  }
}

export function buildAnalysisUiStatePayload({
  sessionId = null,
  sessionMode = 'specialized',
  updatedAt = null,
  activeRun = null,
  newNodeIds = {},
} = {}) {
  const normalized = normalizeAnalysisUiState({
    sessionId,
    sessionMode,
    updatedAt,
    activeRun,
    newNodeIds,
  })
  return normalized
}

export function collectVisibleNewBadgeNodes(trees) {
  const nodesById = new Map()
  const visit = (node) => {
    if (!node || typeof node !== 'object') return
    if (isEvaluableAnalysisNode(node)) {
      const key = evaluationKeyForNode(node)
      if (key && !nodesById.has(key)) {
        nodesById.set(key, {
          id: key,
          nodeKind: String(node.type || node.kind),
        })
      }
    }
    const children = Array.isArray(node.children) ? node.children : []
    children.forEach((child) => visit(child))
  }
  ;(Array.isArray(trees) ? trees : []).forEach((tree) => visit(tree))
  return Array.from(nodesById.values())
}

export function detectNewVisibleNodes(uiState, trees, now = new Date()) {
  const normalized = normalizeAnalysisUiState(uiState)
  const activeRun = normalized.activeRun
  if (!activeRun || activeRun.suppressNewBadges) {
    return {
      changed: false,
      state: normalized,
      addedNodeIds: [],
    }
  }

  const baseline = new Set(activeRun.baselineVisibleNodeIds)
  const nextNewNodeIds = { ...normalized.newNodeIds }
  const firstSeenAt = nowIso(now)
  const addedNodeIds = []
  collectVisibleNewBadgeNodes(trees).forEach((node) => {
    if (baseline.has(node.id) || nextNewNodeIds[node.id]) return
    nextNewNodeIds[node.id] = {
      nodeKind: node.nodeKind,
      firstSeenAt,
      runId: activeRun.runId,
    }
    addedNodeIds.push(node.id)
  })

  return {
    changed: addedNodeIds.length > 0,
    addedNodeIds,
    state: {
      ...normalized,
      updatedAt: addedNodeIds.length > 0 ? firstSeenAt : normalized.updatedAt,
      newNodeIds: nextNewNodeIds,
    },
  }
}
