const EVALUABLE_NODE_TYPES = new Set(['Hypothesis', 'Finding'])
const HYPOTHESIS_ALIGNMENT_OPTIONS = new Set(['yes', 'no', 'unsure'])
const HYPOTHESIS_SUFFICIENCY_OPTIONS = new Set(['yes', 'no', 'partially', 'unsure'])
const FINDING_RELEVANCE_OPTIONS = new Set(['yes', 'no', 'unsure'])
const EVALUATION_FIELD_KEYS = [
  'checked',
  'nodeKind',
  'updatedAt',
  'hypothesisAligned',
  'findingsSufficiency',
  'associatedHypothesisId',
  'associatedHypothesisLabel',
  'relevanceToHypothesis',
  'note',
]

function nowIso(now = new Date()) {
  return now instanceof Date ? now.toISOString() : new Date(now).toISOString()
}

function hasOwn(obj, key) {
  return Object.prototype.hasOwnProperty.call(obj || {}, key)
}

function sanitizeOption(value, allowedValues) {
  if (value == null) return null
  const normalized = String(value).trim().toLowerCase()
  return allowedValues.has(normalized) ? normalized : null
}

function sanitizeOptionalText(value) {
  if (value == null) return null
  const normalized = String(value).trim()
  return normalized || null
}

function normalizeSingleEntry(rawEntry, fallbackNodeKind = '') {
  if (!rawEntry || typeof rawEntry !== 'object') return null
  const nodeKind = String(rawEntry.nodeKind || fallbackNodeKind || '')
  if (!EVALUABLE_NODE_TYPES.has(nodeKind)) return null

  const entry = {
    nodeKind,
    updatedAt: typeof rawEntry.updatedAt === 'string' ? rawEntry.updatedAt : null,
  }
  const hypothesisAligned = sanitizeOption(rawEntry.hypothesisAligned, HYPOTHESIS_ALIGNMENT_OPTIONS)
  const findingsSufficiency = sanitizeOption(rawEntry.findingsSufficiency, HYPOTHESIS_SUFFICIENCY_OPTIONS)
  const relevanceToHypothesis = sanitizeOption(rawEntry.relevanceToHypothesis, FINDING_RELEVANCE_OPTIONS)
  const note = sanitizeOptionalText(rawEntry.note)

  if (hypothesisAligned) entry.hypothesisAligned = hypothesisAligned
  if (findingsSufficiency) entry.findingsSufficiency = findingsSufficiency
  if (relevanceToHypothesis) entry.relevanceToHypothesis = relevanceToHypothesis
  if (note) entry.note = note

  if (hasOwn(rawEntry, 'associatedHypothesisId')) {
    entry.associatedHypothesisId = rawEntry.associatedHypothesisId == null
      ? null
      : sanitizeOptionalText(rawEntry.associatedHypothesisId)
  }
  const associatedHypothesisLabel = sanitizeOptionalText(rawEntry.associatedHypothesisLabel)
  if (associatedHypothesisLabel) entry.associatedHypothesisLabel = associatedHypothesisLabel

  entry.checked = rawEntry.checked === true || isNodeEvaluationComplete(entry)
  return hasMeaningfulEvaluationContent(entry) ? entry : null
}

function hasMeaningfulEvaluationContent(entry) {
  if (!entry || typeof entry !== 'object') return false
  if (entry.checked === true) return true
  if (entry.hypothesisAligned || entry.findingsSufficiency || entry.relevanceToHypothesis) return true
  if (hasOwn(entry, 'associatedHypothesisId')) return true
  return Boolean(sanitizeOptionalText(entry.note))
}

export function evaluationKeyForNode(node) {
  if (!node || typeof node !== 'object') return ''
  return String(node.canonicalId || node.id || '').trim()
}

export function isEvaluableAnalysisNode(node) {
  return EVALUABLE_NODE_TYPES.has(String(node?.type || node?.kind || ''))
}

export function isNodeEvaluationComplete(entry) {
  if (!entry || typeof entry !== 'object') return false
  const nodeKind = String(entry.nodeKind || '')
  if (nodeKind === 'Hypothesis') {
    return Boolean(entry.hypothesisAligned && entry.findingsSufficiency)
  }
  if (nodeKind === 'Finding') {
    return hasOwn(entry, 'associatedHypothesisId') && Boolean(entry.relevanceToHypothesis)
  }
  return false
}

export function normalizeNodeEvaluations(payload) {
  const source = payload && typeof payload === 'object' ? payload : {}
  const rawEvaluations = source.evaluations && typeof source.evaluations === 'object'
    ? source.evaluations
    : {}
  const evaluations = {}
  Object.entries(rawEvaluations).forEach(([key, entry]) => {
    if (!key) return
    const normalizedEntry = normalizeSingleEntry(entry)
    if (!normalizedEntry) return
    evaluations[key] = normalizedEntry
  })
  return {
    updatedAt: typeof source.updatedAt === 'string' ? source.updatedAt : null,
    evaluations,
  }
}

export function updateNodeEvaluation(evaluations, node, patch = {}, now = new Date()) {
  const key = evaluationKeyForNode(node)
  if (!key || !isEvaluableAnalysisNode(node)) {
    return normalizeNodeEvaluations({ evaluations }).evaluations
  }
  const normalized = normalizeNodeEvaluations({ evaluations }).evaluations
  const nodeKind = String(node.type || node.kind)
  const nextEntry = {
    ...(normalized[key] || {}),
    nodeKind,
    updatedAt: nowIso(now),
  }

  if (nodeKind === 'Hypothesis') {
    if (hasOwn(patch, 'hypothesisAligned')) {
      const value = sanitizeOption(patch.hypothesisAligned, HYPOTHESIS_ALIGNMENT_OPTIONS)
      if (value) nextEntry.hypothesisAligned = value
      else delete nextEntry.hypothesisAligned
    }
    if (hasOwn(patch, 'findingsSufficiency')) {
      const value = sanitizeOption(patch.findingsSufficiency, HYPOTHESIS_SUFFICIENCY_OPTIONS)
      if (value) nextEntry.findingsSufficiency = value
      else delete nextEntry.findingsSufficiency
    }
  }

  if (nodeKind === 'Finding') {
    if (hasOwn(patch, 'associatedHypothesisId')) {
      nextEntry.associatedHypothesisId = patch.associatedHypothesisId == null
        ? null
        : sanitizeOptionalText(patch.associatedHypothesisId)
    }
    if (hasOwn(patch, 'associatedHypothesisLabel')) {
      const label = patch.associatedHypothesisId == null
        ? 'None'
        : sanitizeOptionalText(patch.associatedHypothesisLabel)
      if (label) nextEntry.associatedHypothesisLabel = label
      else delete nextEntry.associatedHypothesisLabel
    }
    if (hasOwn(patch, 'relevanceToHypothesis')) {
      const value = sanitizeOption(patch.relevanceToHypothesis, FINDING_RELEVANCE_OPTIONS)
      if (value) nextEntry.relevanceToHypothesis = value
      else delete nextEntry.relevanceToHypothesis
    }
  }

  if (hasOwn(patch, 'note')) {
    const value = sanitizeOptionalText(patch.note)
    if (value) nextEntry.note = value
    else delete nextEntry.note
  }

  nextEntry.checked = isNodeEvaluationComplete(nextEntry)
  const normalizedEntry = normalizeSingleEntry(nextEntry, nodeKind)
  const next = { ...normalized }
  if (!normalizedEntry) {
    delete next[key]
    return next
  }
  next[key] = normalizedEntry
  return next
}

export function toggleNodeEvaluation(evaluations, node, now = new Date()) {
  const key = evaluationKeyForNode(node)
  if (!key || !isEvaluableAnalysisNode(node)) {
    return normalizeNodeEvaluations({ evaluations }).evaluations
  }
  const normalized = normalizeNodeEvaluations({ evaluations }).evaluations
  if (normalized[key]) {
    const next = { ...normalized }
    delete next[key]
    return next
  }
  return updateNodeEvaluation(
    normalized,
    node,
    String(node.type || node.kind) === 'Hypothesis'
      ? { hypothesisAligned: 'yes', findingsSufficiency: 'yes' }
      : {
          associatedHypothesisId: null,
          associatedHypothesisLabel: 'None',
          relevanceToHypothesis: 'yes',
        },
    now,
  )
}

export function buildNodeEvaluationsPayload({
  sessionId = null,
  sessionMode = 'specialized',
  evaluations = {},
  updatedAt = null,
} = {}) {
  const normalized = normalizeNodeEvaluations({ updatedAt, evaluations })
  const payloadEvaluations = {}
  Object.entries(normalized.evaluations).forEach(([key, entry]) => {
    const nextEntry = {}
    EVALUATION_FIELD_KEYS.forEach((field) => {
      if (hasOwn(entry, field)) nextEntry[field] = entry[field]
    })
    payloadEvaluations[key] = nextEntry
  })
  return {
    sessionId,
    sessionMode,
    updatedAt: normalized.updatedAt,
    evaluations: payloadEvaluations,
  }
}
