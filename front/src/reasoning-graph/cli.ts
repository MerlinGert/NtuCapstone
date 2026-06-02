#!/usr/bin/env bun

import { existsSync, mkdirSync, readdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import {
  CHECKPOINT_PATCH_THRESHOLD,
  CURRENT_REASONING_GRAPH_NAME,
  applyReasoningPatches,
  buildReasoningForest,
  checkpointRecommended,
  materializeReasoningGraph,
  orderPatchLayers,
  projectGraphToDisplayForest,
  validateReasoningGraph,
  validateReasoningGraphPatch,
  type PatchLayer,
  type ReasoningGraph,
} from './index'

function readJson(path: string): unknown {
  return JSON.parse(readFileSync(path, 'utf8'))
}

function writeJson(path: string, payload: unknown): void {
  writeFileSync(path, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
}

function usage(): never {
  console.error([
    'Usage:',
    '  bun trace_analysis_tools/reasoning_graph/cli.ts <artifacts-dir>',
    '  bun trace_analysis_tools/reasoning_graph/cli.ts validate <artifacts-dir>',
    '  bun trace_analysis_tools/reasoning_graph/cli.ts materialize <artifacts-dir>',
    '  bun trace_analysis_tools/reasoning_graph/cli.ts checkpoint <artifacts-dir>',
  ].join('\n'))
  process.exit(2)
}

function parseArgs(): { command: 'validate' | 'materialize' | 'checkpoint'; artifactsDir: string } {
  if (process.argv.includes('--help') || process.argv.includes('-h')) usage()
  const first = process.argv[2]
  if (!first) return { command: 'validate', artifactsDir: 'artifacts' }
  if (first === 'validate' || first === 'materialize' || first === 'checkpoint') {
    return { command: first, artifactsDir: process.argv[3] || 'artifacts' }
  }
  return { command: 'validate', artifactsDir: first }
}

function loadArtifacts(artifactsDir: string): {
  graphPath: string
  graph: ReasoningGraph
  patchLayers: PatchLayer[]
  orderedPatches: PatchLayer[]
} {
  const graphPath = join(artifactsDir, 'reasoning-graph.json')
  if (!existsSync(graphPath)) {
    console.error(`error: missing ${graphPath}`)
    process.exit(1)
  }

  const graph = readJson(graphPath) as ReasoningGraph
  const patchLayers: PatchLayer[] = readdirSync(artifactsDir)
    .filter((name) => /^reasoning-graph-patch(?:-.+)?\.json$/.test(name))
    .map((name) => {
      const patch = validateReasoningGraphPatch(readJson(join(artifactsDir, name)), { fileName: name })
      return { name, path: join(artifactsDir, name), patch }
    })
  const orderedPatches = orderPatchLayers(patchLayers)
  return { graphPath, graph, patchLayers, orderedPatches }
}

function validateArtifacts(artifactsDir: string): {
  graph: ReasoningGraph
  orderedPatches: PatchLayer[]
  augmentedGraph: ReasoningGraph
} {
  const { graph, orderedPatches } = loadArtifacts(artifactsDir)
  const base = validateReasoningGraph(graph, {
    fileName: 'reasoning-graph.json',
  })
  const augmentedGraph = applyReasoningPatches(graph, orderedPatches)
  const augmented = validateReasoningGraph(augmentedGraph, { fileName: 'augmented reasoning graph' })
  const forest = buildReasoningForest(augmentedGraph)
  const displayTrees = projectGraphToDisplayForest(augmentedGraph)
  const warnings = Array.from(new Set([...base.warnings, ...augmented.warnings]))

  console.log('Reasoning artifacts validated.')
  console.log(`Base graph: ${base.nodes.size} nodes, ${base.edges.length} edges, ${base.roots.length} roots`)
  console.log(`Patch layers: ${orderedPatches.length}${orderedPatches.length ? ` (${orderedPatches.map((patch) => patch.name).join(', ')})` : ''}`)
  console.log(`Augmented graph: ${augmentedGraph.nodes.length} nodes, ${augmentedGraph.edges.length} edges, ${(augmentedGraph.roots || []).length} roots`)
  console.log(`Projected forest: ${forest.trees.length} trees; UI display trees: ${displayTrees.length}`)
  if (checkpointRecommended(orderedPatches)) {
    console.log(`Checkpoint recommended: active patch count ${orderedPatches.length} >= ${CHECKPOINT_PATCH_THRESHOLD}`)
  }
  if (warnings.length) {
    console.warn('Warnings:')
    for (const warning of warnings) console.warn(`- ${warning}`)
  }
  return { graph, orderedPatches, augmentedGraph }
}

function materializeArtifacts(artifactsDir: string): ReasoningGraph {
  const { graph, orderedPatches } = loadArtifacts(artifactsDir)
  const materialized = materializeReasoningGraph(graph, orderedPatches)
  const outputPath = join(artifactsDir, CURRENT_REASONING_GRAPH_NAME)
  writeJson(outputPath, materialized)
  validateReasoningGraph(materialized, {
    fileName: CURRENT_REASONING_GRAPH_NAME,
  })
  console.log(`Materialized graph written: ${outputPath}`)
  console.log(`Patch layers applied: ${orderedPatches.length}`)
  if (checkpointRecommended(orderedPatches)) {
    console.log(`Checkpoint recommended: active patch count ${orderedPatches.length} >= ${CHECKPOINT_PATCH_THRESHOLD}`)
  }
  return materialized
}

function timestampId(): string {
  return new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z')
}

function checkpointArtifacts(artifactsDir: string): void {
  const { graphPath, graph, orderedPatches } = loadArtifacts(artifactsDir)
  const rootPatchNames = readdirSync(artifactsDir)
    .filter((name) => /^reasoning-graph-patch(?:-.+)?\.json$/.test(name))
  const checkpointId = `checkpoint-${timestampId()}`
  const archiveDir = join(artifactsDir, 'checkpoints', checkpointId)
  mkdirSync(archiveDir, { recursive: true })

  const materialized = materializeReasoningGraph(graph, orderedPatches)
  materialized.checkpointHistory = [
    ...(Array.isArray(graph.checkpointHistory) ? graph.checkpointHistory : []),
    {
      checkpointId,
      createdAt: materialized.materializedFrom?.generatedAt,
      archivedTo: `checkpoints/${checkpointId}`,
      materializedFrom: materialized.materializedFrom,
    },
  ]
  materialized.materializedFrom = {
    ...(materialized.materializedFrom as NonNullable<ReasoningGraph['materializedFrom']>),
    base: `checkpoints/${checkpointId}/reasoning-graph.json`,
    patches: (materialized.materializedFrom?.patches || []).map((patch) => ({
      ...patch,
      name: `checkpoints/${checkpointId}/${patch.name}`,
    })),
    checkpointRecommended: false,
  }

  validateReasoningGraph(materialized, {
    fileName: 'checkpoint materialized graph',
  })

  renameSync(graphPath, join(archiveDir, 'reasoning-graph.json'))
  for (const name of rootPatchNames) {
    const path = join(artifactsDir, name)
    if (existsSync(path)) renameSync(path, join(archiveDir, name))
  }
  writeJson(graphPath, materialized)
  writeJson(join(artifactsDir, CURRENT_REASONING_GRAPH_NAME), materialized)
  console.log(`Checkpoint created: ${checkpointId}`)
  console.log(`Archived previous graph and ${rootPatchNames.length} root patch files to ${archiveDir}`)
  console.log(`Active patch layers applied: ${orderedPatches.length}`)
}

const { command, artifactsDir } = parseArgs()
if (!artifactsDir) usage()

try {
  if (command === 'validate') validateArtifacts(artifactsDir)
  if (command === 'materialize') materializeArtifacts(artifactsDir)
  if (command === 'checkpoint') checkpointArtifacts(artifactsDir)
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`)
  process.exit(1)
}
