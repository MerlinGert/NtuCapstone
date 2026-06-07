const EVALUABLE_NODE_TYPES = new Set(['Hypothesis', 'Finding'])

function nowIso(now = new Date()) {
  return now instanceof Date ? now.toISOString() : new Date(now).toISOString()
}

export function evaluationKeyForNode(node) {
  if (!node || typeof node !== 'object') return ''
  return String(node.canonicalId || node.id || '').trim()
}

export function isEvaluableAnalysisNode(node) {
  return EVALUABLE_NODE_TYPES.has(String(node?.type || node?.kind || ''))
}

export function normalizeNodeEvaluations(payload) {
  const source = payload && typeof payload === 'object' ? payload : {}
  const rawEvaluations = source.evaluations && typeof source.evaluations === 'object'
    ? source.evaluations
    : {}
  const evaluations = {}
  Object.entries(rawEvaluations).forEach(([key, entry]) => {
    if (!key || !entry || typeof entry !== 'object') return
    if (entry.checked !== true) return
    const nodeKind = String(entry.nodeKind || '')
    if (!EVALUABLE_NODE_TYPES.has(nodeKind)) return
    evaluations[key] = {
      checked: true,
      nodeKind,
      updatedAt: typeof entry.updatedAt === 'string' ? entry.updatedAt : null,
    }
  })
  return {
    updatedAt: typeof source.updatedAt === 'string' ? source.updatedAt : null,
    evaluations,
  }
}

export function toggleNodeEvaluation(evaluations, node, now = new Date()) {
  const key = evaluationKeyForNode(node)
  if (!key || !isEvaluableAnalysisNode(node)) {
    return normalizeNodeEvaluations({ evaluations }).evaluations
  }
  const next = { ...normalizeNodeEvaluations({ evaluations }).evaluations }
  if (next[key]?.checked) {
    delete next[key]
    return next
  }
  next[key] = {
    checked: true,
    nodeKind: String(node.type || node.kind),
    updatedAt: nowIso(now),
  }
  return next
}

export function buildNodeEvaluationsPayload({
  sessionId = null,
  sessionMode = 'specialized',
  evaluations = {},
  updatedAt = null,
} = {}) {
  const normalized = normalizeNodeEvaluations({ updatedAt, evaluations })
  return {
    sessionId,
    sessionMode,
    updatedAt: normalized.updatedAt,
    evaluations: normalized.evaluations,
  }
}
