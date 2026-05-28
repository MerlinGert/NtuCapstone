#!/usr/bin/env bun

import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import {
  applyReasoningPatches,
  buildReasoningForest,
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

function usage(): never {
  console.error('Usage: bun trace_analysis_tools/reasoning_graph/cli.ts <artifacts-dir>')
  process.exit(2)
}

const artifactsDir = process.argv[2] || 'artifacts'
if (!artifactsDir || process.argv.includes('--help') || process.argv.includes('-h')) usage()

const graphPath = join(artifactsDir, 'reasoning-graph.json')
if (!existsSync(graphPath)) {
  console.error(`error: missing ${graphPath}`)
  process.exit(1)
}

try {
  const graph = readJson(graphPath) as ReasoningGraph
  const base = validateReasoningGraph(graph, {
    requireAnsweredQuestions: true,
    fileName: 'reasoning-graph.json',
  })

  const patchLayers: PatchLayer[] = readdirSync(artifactsDir)
    .filter((name) => /^reasoning-graph-patch(?:-.+)?\.json$/.test(name))
    .map((name) => {
      const patch = validateReasoningGraphPatch(readJson(join(artifactsDir, name)), { fileName: name })
      return { name, path: join(artifactsDir, name), patch }
    })

  const orderedPatches = orderPatchLayers(patchLayers)
  const augmentedGraph = applyReasoningPatches(graph, orderedPatches)
  const forest = buildReasoningForest(augmentedGraph)
  const displayTrees = projectGraphToDisplayForest(augmentedGraph)

  console.log('Reasoning artifacts validated.')
  console.log(`Base graph: ${base.nodes.size} nodes, ${base.edges.length} edges, ${base.roots.length} roots`)
  console.log(`Patch layers: ${orderedPatches.length}${orderedPatches.length ? ` (${orderedPatches.map((patch) => patch.name).join(', ')})` : ''}`)
  console.log(`Augmented graph: ${augmentedGraph.nodes.length} nodes, ${augmentedGraph.edges.length} edges, ${(augmentedGraph.roots || []).length} roots`)
  console.log(`Projected forest: ${forest.trees.length} trees; UI display trees: ${displayTrees.length}`)
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`)
  process.exit(1)
}
