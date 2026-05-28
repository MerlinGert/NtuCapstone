export type ReasoningKind =
  | 'Interaction'
  | 'Task'
  | 'AnalyticQuestion'
  | 'Hypothesis'
  | 'AnalyticActivity'
  | 'InvestigationStrategy'
  | 'Finding'

export type ReasoningSpace = 'Intention' | 'Action' | 'Finding'
export type ReasoningScope = 'Low' | 'Mid' | 'High'

export type ReasoningRelation =
  | 'motivates'
  | 'produces'
  | 'answers'
  | 'supports'
  | 'refines'
  | 'contradicts'
  | 'contains'
  | 'derived_from'

export interface ReasoningNode {
  id: string
  kind: ReasoningKind
  space: ReasoningSpace
  scope: ReasoningScope
  label: string
  confidence: string
  provenance: string[]
  salience?: 'primary' | 'supporting' | 'low'
  interactionType?: 'Data Action' | 'Model Action' | 'Visualization Action' | 'Synthesis Action'
  activityType?: 'Visual Analysis' | 'Statistical Analysis'
  explanation?: string
  evidenceSummary?: string
  reasoningRole?: string
  patchRationale?: string
  actor?: string
  source?: string
  planRef?: Record<string, unknown>
  [key: string]: unknown
}

export interface ReasoningEdge {
  source: string
  target: string
  relation: ReasoningRelation
  rationale: string
  [key: string]: unknown
}

export interface ReasoningGraph {
  version: 1
  trace: string
  nodes: ReasoningNode[]
  edges: ReasoningEdge[]
  roots?: string[]
  patchesApplied?: Array<Record<string, unknown>>
  [key: string]: unknown
}

export type PatchOperation =
  | { op: 'add_node'; node: ReasoningNode }
  | { op: 'add_edge'; edge: ReasoningEdge }
  | { op: 'update_node'; id: string; set: Record<string, unknown> }
  | { op: 'add_root'; id: string }

export interface ReasoningGraphPatch {
  version: 1
  runId: string
  description?: string
  operations: PatchOperation[]
  [key: string]: unknown
}

export interface PatchLayer {
  name: string
  patch: ReasoningGraphPatch
  path?: string
}

export interface ValidationResult {
  nodes: Map<string, ReasoningNode>
  edges: ReasoningEdge[]
  roots: string[]
}

export interface ForestNode {
  instanceId: string
  canonicalId: string
  parentInstanceId: string | null
  relationToParent: ReasoningRelation | null
  kind: ReasoningKind
  space: ReasoningSpace
  scope: ReasoningScope
  label: string
  confidence?: string
  salience?: string
  interactionType?: string
  activityType?: string
  provenance: string[]
  explanation?: string
  evidenceSummary?: string
  reasoningRole?: string
  patchRationale?: string
  actor?: string
  source?: string
  planRef?: Record<string, unknown>
  [key: string]: unknown
}

export interface ForestTree {
  root: string
  rootLabel: string
  nodes: ForestNode[]
  edges: Array<{ source: string; target: string; relation: ReasoningRelation }>
}

export interface ReasoningForest {
  version: 1
  sourceTrace: string
  sourceGraphVersion: 1
  trees: ForestTree[]
}

export interface DisplayReasoningNode {
  id: string
  canonicalId: string
  instanceId: string
  parentInstanceId?: string | null
  relation?: ReasoningRelation | ''
  displayRelation?: ReasoningRelation | ''
  relationToParent?: ReasoningRelation | null
  type: ReasoningKind
  kind: ReasoningKind
  label: string
  confidence?: string
  salience?: string
  interactionType?: string
  activityType?: string
  provenance?: string[]
  explanation?: string
  evidenceSummary?: string
  reasoningRole?: string
  patchRationale?: string
  actor?: string
  source: 'user' | 'patch'
  originalSource?: string
  children: DisplayReasoningNode[]
  [key: string]: unknown
}

export class ReasoningGraphError extends Error {
  fileName?: string

  constructor(message: string, fileName?: string) {
    super(fileName ? `${fileName}: ${message}` : message)
    this.name = 'ReasoningGraphError'
    this.fileName = fileName
  }
}

const ALLOWED_RELATIONS = new Set<ReasoningRelation>([
  'motivates',
  'produces',
  'answers',
  'supports',
  'refines',
  'contradicts',
  'contains',
  'derived_from',
])

const ALLOWED_KINDS = new Set<ReasoningKind>([
  'Interaction',
  'Task',
  'AnalyticQuestion',
  'Hypothesis',
  'AnalyticActivity',
  'InvestigationStrategy',
  'Finding',
])

const ALLOWED_SPACES = new Set<ReasoningSpace>(['Intention', 'Action', 'Finding'])
const ALLOWED_SCOPES = new Set<ReasoningScope>(['Low', 'Mid', 'High'])
const ALLOWED_INTERACTION_TYPES = new Set([
  'Data Action',
  'Model Action',
  'Visualization Action',
  'Synthesis Action',
])
const ALLOWED_ACTIVITY_TYPES = new Set(['Visual Analysis', 'Statistical Analysis'])
const ALLOWED_SALIENCE = new Set(['primary', 'supporting', 'low'])

const KIND_ALLOWED_SPACES: Record<ReasoningKind, Set<ReasoningSpace>> = {
  Interaction: new Set(['Action']),
  Task: new Set(['Intention']),
  AnalyticQuestion: new Set(['Intention']),
  Hypothesis: new Set(['Intention']),
  AnalyticActivity: new Set(['Action']),
  InvestigationStrategy: new Set(['Action']),
  Finding: new Set(['Finding']),
}

const KIND_ALLOWED_SCOPES: Record<ReasoningKind, Set<ReasoningScope>> = {
  Interaction: new Set(['Low']),
  Task: new Set(['Low']),
  AnalyticQuestion: new Set(['Mid']),
  Hypothesis: new Set(['High']),
  AnalyticActivity: new Set(['Mid']),
  InvestigationStrategy: new Set(['High']),
  Finding: new Set(['Low', 'Mid', 'High']),
}

const SCOPE_RANK: Record<ReasoningScope, number> = {
  Low: 1,
  Mid: 2,
  High: 3,
}

const SALIENCE_ORDER: Record<string, number> = {
  primary: 0,
  supporting: 1,
  low: 2,
}

const KIND_ORDER: Record<string, number> = {
  Hypothesis: 0,
  Finding: 1,
  AnalyticQuestion: 2,
  Task: 3,
  InvestigationStrategy: 4,
  AnalyticActivity: 5,
  Interaction: 6,
}

const DISPLAY_RELATION_PRIORITY: Partial<Record<ReasoningRelation, number>> = {
  contradicts: 3,
  refines: 2,
  supports: 1,
}

const REQUIRED_EXPLANATION_KINDS = new Set([
  'Hypothesis',
  'Finding',
  'AnalyticQuestion',
  'Task',
  'InvestigationStrategy',
  'AnalyticActivity',
])

const DETAIL_FIELDS = ['explanation', 'evidenceSummary', 'reasoningRole', 'patchRationale'] as const
const PATCH_NODE_REQUIRED_FIELDS = [
  'actor',
  'source',
  'planRef',
  'explanation',
  'evidenceSummary',
  'reasoningRole',
  'patchRationale',
] as const

function fail(message: string, fileName?: string): never {
  throw new ReasoningGraphError(message, fileName)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function requireString(value: unknown, path: string, fileName?: string): string {
  if (typeof value !== 'string' || !value.trim()) fail(`${path} must be a non-empty string`, fileName)
  return value
}

function requireObject(value: unknown, path: string, fileName?: string): Record<string, unknown> {
  if (!isRecord(value)) fail(`${path} must be an object`, fileName)
  return value
}

function requireArray(value: unknown, path: string, fileName?: string): unknown[] {
  if (!Array.isArray(value)) fail(`${path} must be a list`, fileName)
  return value
}

function requireStringList(value: unknown, path: string, fileName?: string): string[] {
  const list = requireArray(value, path, fileName)
  list.forEach((item, index) => {
    if (typeof item !== 'string' || !item.trim()) {
      fail(`${path}[${index}] must be a non-empty string`, fileName)
    }
  })
  return list as string[]
}

function validateOptionalDetailFields(node: Record<string, unknown>, nodeId: string, fileName?: string): void {
  for (const field of DETAIL_FIELDS) {
    if (field in node && node[field] != null) requireString(node[field], `node ${nodeId}.${field}`, fileName)
  }
}

function validateNode(node: Record<string, unknown>, index: number, nodes: Map<string, ReasoningNode>, fileName?: string): ReasoningNode {
  const nodeId = requireString(node.id, `nodes[${index}].id`, fileName)
  if (nodes.has(nodeId)) fail(`duplicate node id: ${nodeId}`, fileName)

  const kind = requireString(node.kind, `nodes[${index}].kind`, fileName) as ReasoningKind
  if (!ALLOWED_KINDS.has(kind)) fail(`node ${nodeId} has unknown kind: ${kind}`, fileName)

  const space = requireString(node.space, `node ${nodeId}.space`, fileName) as ReasoningSpace
  if (!ALLOWED_SPACES.has(space)) fail(`node ${nodeId} has unknown space: ${space}`, fileName)
  if (!KIND_ALLOWED_SPACES[kind].has(space)) {
    fail(`node ${nodeId} kind ${kind} must use space: ${Array.from(KIND_ALLOWED_SPACES[kind]).sort().join(', ')}`, fileName)
  }

  const scope = requireString(node.scope, `node ${nodeId}.scope`, fileName) as ReasoningScope
  if (!ALLOWED_SCOPES.has(scope)) fail(`node ${nodeId} has unknown scope: ${scope}`, fileName)
  if (!KIND_ALLOWED_SCOPES[kind].has(scope)) {
    fail(`node ${nodeId} kind ${kind} must use scope: ${Array.from(KIND_ALLOWED_SCOPES[kind]).sort().join(', ')}`, fileName)
  }

  requireString(node.label, `node ${nodeId}.label`, fileName)
  requireString(node.confidence, `node ${nodeId}.confidence`, fileName)
  requireStringList(node.provenance, `node ${nodeId}.provenance`, fileName)

  if (kind === 'Interaction') {
    const interactionType = requireString(node.interactionType, `node ${nodeId}.interactionType`, fileName)
    if (!ALLOWED_INTERACTION_TYPES.has(interactionType)) {
      fail(`Interaction node ${nodeId} has unknown interactionType: ${interactionType}`, fileName)
    }
    const salience = requireString(node.salience, `node ${nodeId}.salience`, fileName)
    if (!ALLOWED_SALIENCE.has(salience)) fail(`Interaction node ${nodeId} has unknown salience: ${salience}`, fileName)
  }

  if (kind === 'AnalyticActivity') {
    const activityType = requireString(node.activityType, `node ${nodeId}.activityType`, fileName)
    if (!ALLOWED_ACTIVITY_TYPES.has(activityType)) {
      fail(`AnalyticActivity node ${nodeId} has unknown activityType: ${activityType}`, fileName)
    }
  }

  const requiresExplanation = REQUIRED_EXPLANATION_KINDS.has(kind)
    || (kind === 'Interaction' && (node.salience === 'primary' || node.actor === 'agent'))
  if (requiresExplanation) requireString(node.explanation, `node ${nodeId}.explanation`, fileName)
  validateOptionalDetailFields(node, nodeId, fileName)

  return node as unknown as ReasoningNode
}

function validateRelationDirection(edge: ReasoningEdge, index: number, nodes: Map<string, ReasoningNode>, fileName?: string): void {
  const source = nodes.get(edge.source)
  const target = nodes.get(edge.target)
  if (!source || !target) fail(`edges[${index}] references missing source or target`, fileName)

  if (edge.relation === 'motivates') {
    if (source.space !== 'Intention' || target.space !== 'Action') {
      fail(`edges[${index}] motivates must point from Intention to Action`, fileName)
    }
    return
  }

  if (edge.relation === 'produces') {
    if (source.space !== 'Action' || target.space !== 'Finding') {
      fail(`edges[${index}] produces must point from Action to Finding`, fileName)
    }
    return
  }

  if (edge.relation === 'supports') {
    if (source.space !== 'Finding' || !['Finding', 'Intention'].includes(target.space)) {
      fail(`edges[${index}] supports must point from Finding to Finding or Intention`, fileName)
    }
    return
  }

  if (edge.relation === 'answers') {
    if (source.space !== 'Finding' || target.kind !== 'AnalyticQuestion') {
      fail(`edges[${index}] answers must point from Finding to AnalyticQuestion`, fileName)
    }
    if (source.scope !== 'Mid') fail(`edges[${index}] answers must use a Mid-scope Finding as source`, fileName)
    return
  }

  if (edge.relation === 'refines' || edge.relation === 'contradicts') {
    if (source.space !== 'Finding' || target.space !== 'Intention') {
      fail(`edges[${index}] ${edge.relation} must point from Finding to Intention`, fileName)
    }
    return
  }

  if (edge.relation === 'contains') {
    if (SCOPE_RANK[source.scope] <= SCOPE_RANK[target.scope]) {
      fail(`edges[${index}] contains must point from a higher-scope node to a lower-scope node`, fileName)
    }
    return
  }

  if (edge.relation === 'derived_from') return
  fail(`edges[${index}] has unknown relation: ${edge.relation}`, fileName)
}

function validateAnalyticQuestionsAnswered(nodes: Map<string, ReasoningNode>, edges: ReasoningEdge[], fileName?: string): void {
  const answeredQuestionIds = new Set(edges.filter((edge) => edge.relation === 'answers').map((edge) => edge.target))
  const unansweredQuestions = Array.from(nodes.entries())
    .filter(([, node]) => node.kind === 'AnalyticQuestion')
    .map(([nodeId]) => nodeId)
    .filter((nodeId) => !answeredQuestionIds.has(nodeId))
  if (unansweredQuestions.length) {
    fail(
      `AnalyticQuestion nodes must have incoming answers edges from Findings: ${unansweredQuestions.sort().join(', ')}`,
      fileName,
    )
  }
}

export function validateReasoningGraph(
  graph: unknown,
  options: { requireAnsweredQuestions?: boolean; fileName?: string } = {},
): ValidationResult {
  const { requireAnsweredQuestions = false, fileName } = options
  const root = requireObject(graph, 'graph', fileName)
  if (root.version !== 1) fail('graph.version must be 1', fileName)
  requireString(root.trace, 'graph.trace', fileName)

  const rawNodes = requireArray(root.nodes, 'graph.nodes', fileName)
  const rawEdges = requireArray(root.edges, 'graph.edges', fileName)
  const nodes = new Map<string, ReasoningNode>()
  rawNodes.forEach((rawNode, index) => {
    const node = validateNode(requireObject(rawNode, `nodes[${index}]`, fileName), index, nodes, fileName)
    nodes.set(node.id, node)
  })

  const edges = rawEdges.map((rawEdge, index) => {
    const edge = requireObject(rawEdge, `edges[${index}]`, fileName)
    const source = requireString(edge.source, `edges[${index}].source`, fileName)
    const target = requireString(edge.target, `edges[${index}].target`, fileName)
    const relation = requireString(edge.relation, `edges[${index}].relation`, fileName) as ReasoningRelation
    if (source === target) fail(`edges[${index}] cannot be a self-edge: ${source}`, fileName)
    if (!nodes.has(source)) fail(`edges[${index}] references missing source node: ${source}`, fileName)
    if (!nodes.has(target)) fail(`edges[${index}] references missing target node: ${target}`, fileName)
    if (!ALLOWED_RELATIONS.has(relation)) fail(`edges[${index}] has unknown relation: ${relation}`, fileName)
    requireString(edge.rationale, `edges[${index}].rationale`, fileName)
    const typedEdge = edge as unknown as ReasoningEdge
    validateRelationDirection(typedEdge, index, nodes, fileName)
    return typedEdge
  })

  const rawRoots = root.roots ?? Array.from(nodes.values()).filter((node) => node.kind === 'Hypothesis').map((node) => node.id)
  if (!Array.isArray(rawRoots) || rawRoots.some((item) => typeof item !== 'string')) {
    fail('graph.roots must be a list of node ids', fileName)
  }
  const roots = rawRoots as string[]
  const missingRoots = roots.filter((rootId) => !nodes.has(rootId))
  if (missingRoots.length) fail(`graph.roots references missing nodes: ${missingRoots.join(', ')}`, fileName)
  const duplicateRoots = Array.from(new Set(roots.filter((rootId, index) => roots.indexOf(rootId) !== index))).sort()
  if (duplicateRoots.length) fail(`graph.roots contains duplicate nodes: ${duplicateRoots.join(', ')}`, fileName)
  const nonHypothesisRoots = roots.filter((rootId) => nodes.get(rootId)?.kind !== 'Hypothesis')
  if (nonHypothesisRoots.length) fail(`graph.roots must contain only Hypothesis nodes: ${nonHypothesisRoots.join(', ')}`, fileName)
  if (!roots.length) fail('no Hypothesis roots found', fileName)

  if (requireAnsweredQuestions) validateAnalyticQuestionsAnswered(nodes, edges, fileName)
  return { nodes, edges, roots }
}

function validatePatchNode(node: Record<string, unknown>, index: number, fileName?: string): ReasoningNode {
  const nodeId = requireString(node.id, `operations[${index}].node.id`, fileName)
  const missing = PATCH_NODE_REQUIRED_FIELDS.filter((field) => !(field in node))
  if (missing.length) {
    fail(`add_node operation for ${nodeId} is missing follow-up fields: ${missing.join(', ')}`, fileName)
  }
  for (const field of PATCH_NODE_REQUIRED_FIELDS) {
    if (field === 'planRef') {
      const planRef = requireObject(node.planRef, `add_node ${nodeId}.planRef`, fileName)
      if (!Object.keys(planRef).length) fail(`add_node ${nodeId}.planRef must not be empty`, fileName)
      continue
    }
    requireString(node[field], `add_node ${nodeId}.${field}`, fileName)
  }
  return node as unknown as ReasoningNode
}

function isSkepticalPatchFile(fileName?: string): boolean {
  return /(^|[/\\])reasoning-graph-patch-skeptical\.json$/i.test(String(fileName || ''))
}

function validateSkepticalPatchFindings(rawOperations: unknown[], fileName?: string): void {
  const addedFindings = new Set<string>()
  const qualifiedFindings = new Set<string>()

  rawOperations.forEach((rawOperation, index) => {
    const operation = requireObject(rawOperation, `operations[${index}]`, fileName)
    const op = requireString(operation.op, `operations[${index}].op`, fileName)

    if (op === 'add_node') {
      const node = requireObject(operation.node, `operations[${index}].node`, fileName)
      if (node.kind === 'Finding') addedFindings.add(requireString(node.id, `operations[${index}].node.id`, fileName))
    }

    if (op === 'add_edge') {
      const edge = requireObject(operation.edge, `operations[${index}].edge`, fileName)
      const relation = requireString(edge.relation, `operations[${index}].edge.relation`, fileName)
      if (relation === 'refines' || relation === 'contradicts') {
        qualifiedFindings.add(requireString(edge.source, `operations[${index}].edge.source`, fileName))
      }
    }
  })

  for (const findingId of addedFindings) {
    if (qualifiedFindings.has(findingId)) continue
    fail(
      `skeptical patch Finding ${findingId} must have an outgoing refines or contradicts edge; `
      + 'supports may only be additional context, not the only skeptical relation',
      fileName,
    )
  }
}

export function validateReasoningGraphPatch(
  patch: unknown,
  options: { fileName?: string } = {},
): ReasoningGraphPatch {
  const { fileName } = options
  const root = requireObject(patch, 'patch', fileName)
  if (root.version !== 1) fail('patch.version must be 1', fileName)
  requireString(root.runId, 'patch.runId', fileName)
  const rawOperations = requireArray(root.operations, 'patch.operations', fileName)
  if (!rawOperations.length) fail('patch.operations must not be empty', fileName)

  rawOperations.forEach((rawOperation, index) => {
    const operation = requireObject(rawOperation, `operations[${index}]`, fileName)
    const op = requireString(operation.op, `operations[${index}].op`, fileName)
    if (!['add_node', 'add_edge', 'update_node', 'add_root'].includes(op)) {
      fail(`operations[${index}] has unknown op: ${op}`, fileName)
    }
    if (op === 'add_node') validatePatchNode(requireObject(operation.node, `operations[${index}].node`, fileName), index, fileName)
    if (op === 'add_edge') requireObject(operation.edge, `operations[${index}].edge`, fileName)
    if (op === 'update_node') {
      requireString(operation.id, `operations[${index}].id`, fileName)
      const updates = requireObject(operation.set, `operations[${index}].set`, fileName)
      if (!Object.keys(updates).length) fail(`operations[${index}].set must not be empty`, fileName)
      if ('id' in updates) fail(`operations[${index}].set must not change node id`, fileName)
    }
    if (op === 'add_root') requireString(operation.id, `operations[${index}].id`, fileName)
  })

  if (isSkepticalPatchFile(fileName)) validateSkepticalPatchFindings(rawOperations, fileName)

  return root as unknown as ReasoningGraphPatch
}

function edgeKey(edge: Pick<ReasoningEdge, 'source' | 'target' | 'relation'>): string {
  return `${edge.source}\u0000${edge.target}\u0000${edge.relation}`
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

export function applyReasoningPatch(baseGraph: ReasoningGraph, patch: ReasoningGraphPatch, fileName?: string): ReasoningGraph {
  validateReasoningGraph(baseGraph, { requireAnsweredQuestions: true })
  const validatedPatch = validateReasoningGraphPatch(patch, { fileName })
  const graph = cloneJson(baseGraph)
  graph.nodes = Array.isArray(graph.nodes) ? graph.nodes : []
  graph.edges = Array.isArray(graph.edges) ? graph.edges : []
  graph.roots = Array.isArray(graph.roots) ? graph.roots : validateReasoningGraph(graph).roots

  const nodesById = new Map(graph.nodes.map((node) => [node.id, node]))
  const edgeKeys = new Set(graph.edges.map(edgeKey))

  validatedPatch.operations.forEach((operation, index) => {
    if (operation.op === 'add_node') {
      const node = cloneJson(operation.node)
      if (nodesById.has(node.id)) fail(`operations[${index}] add_node duplicates existing node: ${node.id}`, fileName)
      graph.nodes.push(node)
      nodesById.set(node.id, node)
      return
    }

    if (operation.op === 'add_edge') {
      const edge = cloneJson(operation.edge)
      const key = edgeKey(edge)
      if (edgeKeys.has(key)) {
        fail(`operations[${index}] add_edge duplicates existing edge: ${edge.source} -> ${edge.target} (${edge.relation})`, fileName)
      }
      graph.edges.push(edge)
      edgeKeys.add(key)
      return
    }

    if (operation.op === 'update_node') {
      const node = nodesById.get(operation.id)
      if (!node) fail(`operations[${index}] update_node references missing node: ${operation.id}`, fileName)
      Object.assign(node, cloneJson(operation.set))
      return
    }

    if (operation.op === 'add_root') {
      if (graph.roots?.includes(operation.id)) fail(`operations[${index}] add_root duplicates existing root: ${operation.id}`, fileName)
      graph.roots = [...(graph.roots || []), operation.id]
    }
  })

  graph.patchesApplied = [
    ...(Array.isArray(graph.patchesApplied) ? graph.patchesApplied : []),
    {
      runId: validatedPatch.runId,
      description: validatedPatch.description || '',
      operationCount: validatedPatch.operations.length,
    },
  ]
  validateReasoningGraph(graph, { requireAnsweredQuestions: true, fileName: fileName ? `${fileName} applied` : undefined })
  return graph
}

function patchSortKey(name: string): [number, number, string] {
  if (name === 'reasoning-graph-patch.json') return [0, 0, name]
  const numbered = name.match(/^reasoning-graph-patch-(\d+)\.json$/)
  if (numbered) return [1, Number(numbered[1]), name]
  if (name === 'reasoning-graph-patch-skeptical.json') return [2, 0, name]
  if (/^reasoning-graph-patch-.+\.json$/.test(name)) return [3, 0, name]
  return [4, 0, name]
}

export function comparePatchNames(a: string, b: string): number {
  const left = patchSortKey(a)
  const right = patchSortKey(b)
  return left[0] - right[0] || left[1] - right[1] || left[2].localeCompare(right[2])
}

export function orderPatchLayers<T extends { name: string; patch?: ReasoningGraphPatch }>(layers: T[]): T[] {
  const ordered = [...layers].sort((a, b) => comparePatchNames(a.name, b.name))
  const seenRunIds = new Set<string>()
  return ordered.filter((layer) => {
    const runId = layer.patch?.runId
    if (!runId) return true
    if (seenRunIds.has(runId)) return false
    seenRunIds.add(runId)
    return true
  })
}

export function applyReasoningPatches(baseGraph: ReasoningGraph, layers: PatchLayer[]): ReasoningGraph {
  return orderPatchLayers(layers).reduce(
    (graph, layer) => applyReasoningPatch(graph, layer.patch, layer.name),
    cloneJson(baseGraph),
  )
}

function projectedChildParent(edge: ReasoningEdge): { child: string; parent: string; relation: ReasoningRelation } {
  if (['produces', 'answers', 'supports', 'refines', 'contradicts'].includes(edge.relation)) {
    return { child: edge.source, parent: edge.target, relation: edge.relation }
  }
  if (['motivates', 'contains', 'derived_from'].includes(edge.relation)) {
    return { child: edge.target, parent: edge.source, relation: edge.relation }
  }
  fail(`unknown relation: ${edge.relation}`)
}

function sortChildEntries(entries: Array<{ child: string; relation: ReasoningRelation }>, nodes: Map<string, ReasoningNode>) {
  return [...entries].sort((a, b) => {
    const left = nodes.get(a.child)
    const right = nodes.get(b.child)
    if (!left || !right) return a.child.localeCompare(b.child)
    return (SALIENCE_ORDER[String(left.salience || 'supporting')] ?? 1) - (SALIENCE_ORDER[String(right.salience || 'supporting')] ?? 1)
      || (KIND_ORDER[left.kind] ?? 99) - (KIND_ORDER[right.kind] ?? 99)
      || a.child.localeCompare(b.child)
      || a.relation.localeCompare(b.relation)
  })
}

function forestNodeFromReasoningNode(
  node: ReasoningNode,
  instanceId: string,
  parentInstanceId: string | null,
  relationToParent: ReasoningRelation | null,
): ForestNode {
  const treeNode: ForestNode = {
    instanceId,
    canonicalId: node.id,
    parentInstanceId,
    relationToParent,
    kind: node.kind,
    space: node.space,
    scope: node.scope,
    label: node.label || node.id,
    confidence: node.confidence,
    salience: node.salience,
    interactionType: node.interactionType,
    activityType: node.activityType,
    provenance: Array.isArray(node.provenance) ? node.provenance : [],
  }
  for (const field of ['actor', 'source', 'planRef', ...DETAIL_FIELDS]) {
    if (node[field] != null) treeNode[field] = node[field]
  }
  return treeNode
}

function validateTreeLeaves(root: string, treeNodes: ForestNode[], treeEdges: Array<{ source: string; target: string }>): void {
  if (!treeEdges.length) fail(`tree rooted at ${root} has no support edges`)
  const parentIds = new Set(treeEdges.map((edge) => edge.target))
  const nonInteractionLeaves = treeNodes.filter((node) => !parentIds.has(node.instanceId) && node.kind !== 'Interaction')
  if (nonInteractionLeaves.length) {
    fail(
      `tree rooted at ${root} has non-Interaction leaves: `
      + nonInteractionLeaves.map((node) => `${node.instanceId} (${node.kind})`).join(', '),
    )
  }
}

export function buildReasoningForest(graph: ReasoningGraph): ReasoningForest {
  const { nodes, edges, roots } = validateReasoningGraph(graph, { requireAnsweredQuestions: true })
  const childrenByParent = new Map<string, Array<{ child: string; relation: ReasoningRelation }>>()
  for (const edge of edges) {
    const { child, parent, relation } = projectedChildParent(edge)
    childrenByParent.set(parent, [...(childrenByParent.get(parent) || []), { child, relation }])
  }

  const trees = roots.map((root) => {
    const treeNodes: ForestNode[] = []
    const treeEdges: Array<{ source: string; target: string; relation: ReasoningRelation }> = []

    const visit = (
      canonicalId: string,
      parentInstanceId: string | null,
      relationToParent: ReasoningRelation | null,
      path: string[],
      indexPath: number[],
    ): string => {
      if (path.includes(canonicalId)) fail(`support projection contains a cycle: ${[...path, canonicalId].join(' -> ')}`)
      const instanceId = parentInstanceId == null ? canonicalId : `${canonicalId}@${root}.${indexPath.join('.')}`
      const node = nodes.get(canonicalId)
      if (!node) fail(`support projection references missing node: ${canonicalId}`)
      treeNodes.push(forestNodeFromReasoningNode(node, instanceId, parentInstanceId, relationToParent))
      if (parentInstanceId != null && relationToParent != null) {
        treeEdges.push({ source: instanceId, target: parentInstanceId, relation: relationToParent })
      }
      sortChildEntries(childrenByParent.get(canonicalId) || [], nodes).forEach((entry, childIndex) => {
        visit(entry.child, instanceId, entry.relation, [...path, canonicalId], [...indexPath, childIndex + 1])
      })
      return instanceId
    }

    visit(root, null, null, [], [])
    validateTreeLeaves(root, treeNodes, treeEdges)
    return {
      root,
      rootLabel: nodes.get(root)?.label || root,
      nodes: treeNodes,
      edges: treeEdges,
    }
  })

  return {
    version: 1,
    sourceTrace: graph.trace,
    sourceGraphVersion: graph.version,
    trees,
  }
}

function displayNodeFromForestNode(node: ForestNode): DisplayReasoningNode {
  const source = node.actor === 'agent' || node.source === 'followup_investigation' ? 'patch' : 'user'
  return {
    ...node,
    id: node.canonicalId,
    canonicalId: node.canonicalId,
    instanceId: node.instanceId,
    parentInstanceId: node.parentInstanceId,
    relation: node.relationToParent || '',
    displayRelation: node.relationToParent || '',
    relationToParent: node.relationToParent,
    type: node.kind,
    kind: node.kind,
    label: node.label || node.canonicalId,
    source,
    originalSource: typeof node.source === 'string' ? node.source : '',
    children: [],
  }
}

function preferredDisplayRelation(current: ReasoningRelation | '' | undefined, candidate: ReasoningRelation): ReasoningRelation {
  const currentPriority = current ? DISPLAY_RELATION_PRIORITY[current] ?? 0 : 0
  const candidatePriority = DISPLAY_RELATION_PRIORITY[candidate] ?? 0
  return candidatePriority > currentPriority ? candidate : current as ReasoningRelation
}

function semanticRelationOverrides(edges: ReasoningEdge[]): Map<string, ReasoningRelation> {
  const overrides = new Map<string, ReasoningRelation>()
  for (const edge of edges) {
    if (edge.relation !== 'contradicts' && edge.relation !== 'refines') continue
    overrides.set(edge.source, preferredDisplayRelation(overrides.get(edge.source) || '', edge.relation))
  }
  return overrides
}

function applyDisplayRelationOverrides(
  nodes: DisplayReasoningNode[],
  overrides: Map<string, ReasoningRelation>,
): DisplayReasoningNode[] {
  return nodes.map((node) => {
    const override = overrides.get(node.canonicalId)
    const displayRelation = override
      ? preferredDisplayRelation(node.displayRelation || node.relation || '', override)
      : node.displayRelation
    return {
      ...node,
      displayRelation,
      children: applyDisplayRelationOverrides(node.children || [], overrides),
    }
  })
}

function buildTreeFromForest(tree: ForestTree): DisplayReasoningNode | null {
  const byInstance = new Map<string, DisplayReasoningNode>()
  for (const node of tree.nodes) byInstance.set(node.instanceId, displayNodeFromForestNode(node))
  for (const node of tree.nodes) {
    if (!node.parentInstanceId) continue
    const parent = byInstance.get(node.parentInstanceId)
    const child = byInstance.get(node.instanceId)
    if (parent && child) parent.children.push(child)
  }
  return byInstance.get(tree.root)
    || Array.from(byInstance.values()).find((node) => !node.parentInstanceId)
    || null
}

function isVisibleReasoningNode(node: DisplayReasoningNode): boolean {
  return node.type === 'Hypothesis' || node.type === 'Finding'
}

function reasoningNodeDedupKey(node: DisplayReasoningNode): string {
  if (node.type !== 'Hypothesis' && node.type !== 'Finding') return ''
  return `${node.source || 'user'}:${node.type}:${node.canonicalId || node.id}`
}

function collectDescendantReasoningKeys(node: DisplayReasoningNode, keys: Set<string>): void {
  for (const child of node.children || []) {
    const key = reasoningNodeDedupKey(child)
    if (key) keys.add(key)
    collectDescendantReasoningKeys(child, keys)
  }
}

function pruneDuplicateVisibleAncestors(nodes: DisplayReasoningNode[]): DisplayReasoningNode[] {
  const descendantKeys = new Set<string>()
  nodes.forEach((node) => collectDescendantReasoningKeys(node, descendantKeys))
  return nodes.filter((node) => {
    const key = reasoningNodeDedupKey(node)
    return !key || !descendantKeys.has(key)
  })
}

function dedupeDisplayNodes(nodes: DisplayReasoningNode[]): DisplayReasoningNode[] {
  const deduped: DisplayReasoningNode[] = []
  const byCanonicalNode = new Map<string, DisplayReasoningNode>()
  for (const node of nodes) {
    const key = reasoningNodeDedupKey(node)
    if (!key || !byCanonicalNode.has(key)) {
      if (key) byCanonicalNode.set(key, node)
      deduped.push(node)
      continue
    }
    const existing = byCanonicalNode.get(key)
    if (!existing) continue
    existing.children = dedupeDisplayNodes([...(existing.children || []), ...(node.children || [])])
    if (!existing.relation && node.relation) existing.relation = node.relation
  }
  return pruneDuplicateVisibleAncestors(deduped)
}

function projectReasoningNode(node: DisplayReasoningNode): DisplayReasoningNode[] {
  const visibleChildren = dedupeDisplayNodes((node.children || []).flatMap((child) => projectReasoningNode(child)))
  if (!isVisibleReasoningNode(node)) return visibleChildren
  return [{ ...node, children: visibleChildren }]
}

export function projectGraphToDisplayForest(graph: ReasoningGraph): DisplayReasoningNode[] {
  const forest = buildReasoningForest(graph)
  const displayTrees = dedupeDisplayNodes(
    forest.trees
      .map(buildTreeFromForest)
      .filter((tree): tree is DisplayReasoningNode => Boolean(tree))
      .flatMap((tree) => projectReasoningNode(tree))
      .filter((node) => node.type === 'Hypothesis'),
  )
  return applyDisplayRelationOverrides(displayTrees, semanticRelationOverrides(graph.edges))
}
