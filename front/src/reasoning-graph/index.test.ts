import { describe, expect, test } from 'bun:test'
import { existsSync, mkdtempSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  applyReasoningPatches,
  checkpointRecommended,
  materializeReasoningGraph,
  orderPatchLayers,
  projectGraphToDisplayForest,
  validateReasoningGraph,
  validateReasoningGraphPatch,
  type ReasoningGraph,
  type ReasoningGraphPatch,
  type TraceAnchor,
} from './index'

const TEST_DIR = dirname(fileURLToPath(import.meta.url))

function anchor(traceRevision: number, actionCount = traceRevision, annotationCount = 0): TraceAnchor {
  return {
    sessionId: 'abcde',
    traceRevision,
    actionCount,
    annotationCount,
    lastActionId: actionCount ? `A${actionCount}` : undefined,
    lastAnnotationId: annotationCount ? `N${annotationCount}` : undefined,
    traceDigest: `sha256:${traceRevision}-${actionCount}-${annotationCount}`,
  }
}

function baseGraph(): ReasoningGraph {
  return {
    version: 1,
    trace: 'fixture',
    analysisAnchor: anchor(3, 3, 1),
    latestAnchor: anchor(3, 3, 1),
    roots: ['H1'],
    nodes: [
      {
        id: 'H1',
        kind: 'Hypothesis',
        space: 'Intention',
        scope: 'High',
        label: 'Coordinated activity hypothesis',
        confidence: 'Inference',
        provenance: ['annotation:1'],
        explanation: 'The trace suggests coordinated ACT behavior.',
      },
      {
        id: 'AQ1',
        kind: 'AnalyticQuestion',
        space: 'Intention',
        scope: 'Mid',
        label: 'Do the selected wallets behave together?',
        confidence: 'Inference',
        provenance: ['action:1'],
        explanation: 'The user appears to test whether selected wallets act as a cohort.',
      },
      {
        id: 'AA1',
        kind: 'AnalyticActivity',
        space: 'Action',
        scope: 'Mid',
        label: 'Inspect selected wallet behavior',
        confidence: 'Direct evidence',
        provenance: ['action:1'],
        activityType: 'Visual Analysis',
        explanation: 'The user inspected a visual behavior card.',
      },
      {
        id: 'I1',
        kind: 'Interaction',
        space: 'Action',
        scope: 'Low',
        label: 'Click behavior card',
        confidence: 'Direct evidence',
        provenance: ['action:1'],
        interactionType: 'Visualization Action',
        salience: 'primary',
        explanation: 'The click selects a behavior card for inspection.',
      },
      {
        id: 'F_LOW1',
        kind: 'Finding',
        space: 'Finding',
        scope: 'Low',
        label: 'The selected card shows clustered activity',
        confidence: 'Direct evidence',
        provenance: ['screenshot:card.png'],
        explanation: 'The card visually groups wallet activity in a suspicious window.',
      },
      {
        id: 'F_MID1',
        kind: 'Finding',
        space: 'Finding',
        scope: 'Mid',
        label: 'The selected wallets act as a visible cohort',
        confidence: 'Strong inference',
        provenance: ['screenshot:card.png'],
        explanation: 'The visual card evidence answers the cohort-behavior question.',
      },
    ],
    edges: [
      { source: 'H1', target: 'AQ1', relation: 'contains', rationale: 'The hypothesis contains this question.' },
      { source: 'AQ1', target: 'AA1', relation: 'motivates', rationale: 'The question motivates visual inspection.' },
      { source: 'AA1', target: 'I1', relation: 'contains', rationale: 'The activity contains the click interaction.' },
      { source: 'AA1', target: 'F_LOW1', relation: 'produces', rationale: 'The activity produced the low-level finding.' },
      { source: 'F_LOW1', target: 'F_MID1', relation: 'supports', rationale: 'The low-level observation supports the answer finding.' },
      { source: 'F_MID1', target: 'AQ1', relation: 'answers', rationale: 'The finding answers the analytic question.' },
      { source: 'F_MID1', target: 'H1', relation: 'supports', rationale: 'The answer supports the hypothesis.' },
    ],
  }
}

function patch(id = 'F_AGENT1', relation: 'supports' | 'refines' | 'contradicts' = 'refines'): ReasoningGraphPatch {
  const interactionId = `AI_${id}`
  return {
    version: 1,
    runId: `patch-${id}`,
    patchType: 'main',
    description: 'Agent follow-up evidence.',
    operations: [
      {
        op: 'add_node',
        node: {
          id: interactionId,
          kind: 'Interaction',
          space: 'Action',
          scope: 'Low',
          label: 'Compute follow-up statistics',
          confidence: 'Direct evidence',
          provenance: ['data:fixture.csv'],
          interactionType: 'Data Action',
          salience: 'primary',
          actor: 'agent',
          source: 'followup_investigation',
          planRef: { strategyId: 'RS1' },
          explanation: 'The agent computed a follow-up statistic.',
          evidenceSummary: 'Fixture calculation.',
          reasoningRole: 'Produces a follow-up finding.',
          patchRationale: 'This is new follow-up evidence.',
        },
      },
      {
        op: 'add_node',
        node: {
          id,
          kind: 'Finding',
          space: 'Finding',
          scope: 'Mid',
          label: `${relation} finding`,
          confidence: 'Strong inference',
          provenance: ['data:fixture.csv'],
          actor: 'agent',
          source: 'followup_investigation',
          planRef: { strategyId: 'RS1' },
          explanation: 'The agent finding changes how the hypothesis should be read.',
          evidenceSummary: 'Fixture evidence.',
          reasoningRole: 'Adds follow-up evidence.',
          patchRationale: 'This finding belongs in the augmented graph.',
        },
      },
      {
        op: 'add_edge',
        edge: {
          source: interactionId,
          target: id,
          relation: 'produces',
          rationale: 'The calculation produced the finding.',
        },
      },
      {
        op: 'add_edge',
        edge: {
          source: id,
          target: 'H1',
          relation,
          rationale: 'The finding updates the hypothesis.',
        },
      },
    ],
  }
}

function incrementalPatch(id = 'F_INC1', from = anchor(3, 3, 1), to = anchor(4, 4, 1)): ReasoningGraphPatch {
  return {
    ...patch(id, 'supports'),
    runId: `incremental-${from.traceRevision}-${to.traceRevision}`,
    patchType: 'incremental',
    baseAnchor: from,
    targetAnchor: to,
  }
}

describe('reasoning graph validation', () => {
  test('accepts a valid graph', () => {
    const result = validateReasoningGraph(baseGraph(), { requireAnsweredQuestions: true })
    expect(result.nodes.size).toBe(6)
    expect(result.edges.length).toBe(7)
  })

  test('rejects invalid refines target direction', () => {
    const graph = baseGraph()
    graph.edges.push({
      source: 'F_MID1',
      target: 'F_LOW1',
      relation: 'refines',
      rationale: 'Invalidly refines a Finding.',
    })
    expect(() => validateReasoningGraph(graph, { requireAnsweredQuestions: true })).toThrow(/refines must point/)
  })

  test('requires analytic questions to have mid-level answer findings', () => {
    const graph = baseGraph()
    graph.edges = graph.edges.filter((edge) => edge.relation !== 'answers')
    expect(() => validateReasoningGraph(graph, { requireAnsweredQuestions: true })).toThrow(/incoming answers edges/)
  })
})

describe('reasoning graph patches', () => {
  test('validates and applies a patch', () => {
    const augmented = applyReasoningPatches(baseGraph(), [
      { name: 'reasoning-graph-patch.json', patch: patch('F_AGENT1', 'refines') },
    ])
    expect(augmented.nodes.some((node) => node.id === 'F_AGENT1')).toBe(true)
    expect(augmented.edges.some((edge) => edge.source === 'F_AGENT1' && edge.relation === 'refines')).toBe(true)
  })

  test('rejects duplicate patch nodes', () => {
    const first = patch('F_AGENT1', 'supports')
    const second = patch('F_AGENT2', 'supports')
    second.operations[0] = first.operations[0]
    expect(() => applyReasoningPatches(baseGraph(), [
      { name: 'reasoning-graph-patch.json', patch: first },
      { name: 'reasoning-graph-patch-002.json', patch: second },
    ])).toThrow(/duplicates existing node/)
  })

  test('rejects missing patch fields', () => {
    const badPatch = patch()
    delete (badPatch.operations[0] as any).node.patchRationale
    expect(() => validateReasoningGraphPatch(badPatch)).toThrow(/missing follow-up fields/)
  })

  test('rejects support-only skeptical patch findings', () => {
    expect(() => validateReasoningGraphPatch(patch('F_SKEPTICAL_SUPPORT', 'supports'), {
      fileName: 'reasoning-graph-patch-skeptical.json',
    })).toThrow(/skeptical patch Finding F_SKEPTICAL_SUPPORT/)
  })

  test('requires anchors for incremental patches', () => {
    const badPatch = patch('F_INCREMENTAL', 'supports')
    badPatch.patchType = 'incremental'
    expect(() => validateReasoningGraphPatch(badPatch, {
      fileName: 'reasoning-graph-patch-incremental-3-4.json',
    })).toThrow(/incremental patches must include baseAnchor and targetAnchor/)
  })

  test('applies incremental patches only when the base anchor matches', () => {
    const graph = baseGraph()
    const goodPatch = incrementalPatch('F_INCREMENTAL_OK')
    const augmented = applyReasoningPatches(graph, [
      { name: 'reasoning-graph-patch-incremental-3-4.json', patch: goodPatch },
    ])
    expect(augmented.latestAnchor?.traceRevision).toBe(4)

    const badPatch = incrementalPatch('F_INCREMENTAL_BAD', anchor(99, 99, 1), anchor(100, 100, 1))
    expect(() => applyReasoningPatches(graph, [
      { name: 'reasoning-graph-patch-incremental-99-100.json', patch: badPatch },
    ])).toThrow(/does not match graph latest anchor/)
  })

  test('orders and deduplicates patches by preferred names and runId', () => {
    const canonical = patch('F_AGENT1', 'supports')
    canonical.runId = 'same-run'
    const duplicate = patch('F_AGENT2', 'supports')
    duplicate.runId = 'same-run'
    const skeptical = patch('F_AGENT3', 'contradicts')
    const ordered = orderPatchLayers([
      { name: 'reasoning-graph-patch-skeptical.json', patch: skeptical },
      { name: 'reasoning-graph-patch-001-abcdef.json', patch: duplicate },
      { name: 'reasoning-graph-patch.json', patch: canonical },
    ])
    expect(ordered.map((item) => item.name)).toEqual([
      'reasoning-graph-patch.json',
      'reasoning-graph-patch-skeptical.json',
    ])
  })

  test('orders incremental patches by numeric trace revision', () => {
    const ordered = orderPatchLayers([
      { name: 'reasoning-graph-patch-incremental-10-11.json', patch: incrementalPatch('F_INC11', anchor(10), anchor(11)) },
      { name: 'reasoning-graph-patch-incremental-4-5.json', patch: incrementalPatch('F_INC5', anchor(4), anchor(5)) },
      { name: 'reasoning-graph-patch-skeptical.json', patch: patch('F_SKEPTICAL', 'contradicts') },
    ])
    expect(ordered.map((item) => item.name)).toEqual([
      'reasoning-graph-patch-skeptical.json',
      'reasoning-graph-patch-incremental-4-5.json',
      'reasoning-graph-patch-incremental-10-11.json',
    ])
  })

  test('materializes graph with source metadata and checkpoint recommendation', () => {
    const graph = baseGraph()
    const layers = Array.from({ length: 8 }, (_, index) => {
      const from = anchor(index + 3, index + 3, 1)
      const to = anchor(index + 4, index + 4, 1)
      return {
        name: `reasoning-graph-patch-incremental-${from.traceRevision}-${to.traceRevision}.json`,
        patch: incrementalPatch(`F_INC_${index}`, from, to),
      }
    })
    const materialized = materializeReasoningGraph(graph, layers, {
      generatedAt: '2026-05-28T00:00:00Z',
    })
    expect(materialized.materializedFrom?.base).toBe('reasoning-graph.json')
    expect(materialized.materializedFrom?.patches).toHaveLength(8)
    expect(materialized.materializedFrom?.checkpointRecommended).toBe(true)
    expect(materialized.latestAnchor?.traceRevision).toBe(11)
    expect(checkpointRecommended(layers)).toBe(true)
  })
})

describe('reasoning graph cli', () => {
  function writeFixtureArtifacts(patchCount = 8): string {
    const dir = mkdtempSync(join(tmpdir(), 'reasoning-graph-'))
    const graph = baseGraph()
    writeFileSync(join(dir, 'reasoning-graph.json'), `${JSON.stringify(graph, null, 2)}\n`, 'utf8')
    Array.from({ length: patchCount }, (_, index) => {
      const from = anchor(index + 3, index + 3, 1)
      const to = anchor(index + 4, index + 4, 1)
      const layer = incrementalPatch(`F_CLI_${index}`, from, to)
      writeFileSync(
        join(dir, `reasoning-graph-patch-incremental-${from.traceRevision}-${to.traceRevision}.json`),
        `${JSON.stringify(layer, null, 2)}\n`,
        'utf8',
      )
    })
    return dir
  }

  test('materialize command writes current-reasoning-graph.json', () => {
    const dir = writeFixtureArtifacts(1)
    const result = Bun.spawnSync({
      cmd: ['bun', join(TEST_DIR, 'cli.ts'), 'materialize', dir],
      cwd: TEST_DIR,
      stdout: 'pipe',
      stderr: 'pipe',
    })
    expect(result.exitCode).toBe(0)
    expect(existsSync(join(dir, 'current-reasoning-graph.json'))).toBe(true)
    const materialized = JSON.parse(readFileSync(join(dir, 'current-reasoning-graph.json'), 'utf8'))
    expect(materialized.materializedFrom.patches).toHaveLength(1)
  })

  test('checkpoint command archives old base and patches and writes new base', () => {
    const dir = writeFixtureArtifacts(8)
    const duplicate = incrementalPatch('F_DUPLICATE', anchor(3, 3, 1), anchor(4, 4, 1))
    duplicate.runId = 'incremental-3-4'
    writeFileSync(
      join(dir, 'reasoning-graph-patch-incremental-3-4-copy.json'),
      `${JSON.stringify(duplicate, null, 2)}\n`,
      'utf8',
    )
    const result = Bun.spawnSync({
      cmd: ['bun', join(TEST_DIR, 'cli.ts'), 'checkpoint', dir],
      cwd: TEST_DIR,
      stdout: 'pipe',
      stderr: 'pipe',
    })
    expect(result.exitCode).toBe(0)
    expect(readdirSync(dir).filter((name) => /^reasoning-graph-patch/.test(name))).toHaveLength(0)
    const checkpointDirs = readdirSync(join(dir, 'checkpoints'))
    expect(checkpointDirs).toHaveLength(1)
    const archiveDir = join(dir, 'checkpoints', checkpointDirs[0])
    expect(existsSync(join(archiveDir, 'reasoning-graph.json'))).toBe(true)
    expect(readdirSync(archiveDir).filter((name) => /^reasoning-graph-patch/.test(name))).toHaveLength(9)
    const newBase = JSON.parse(readFileSync(join(dir, 'reasoning-graph.json'), 'utf8'))
    expect(newBase.checkpointHistory).toHaveLength(1)
    expect(newBase.materializedFrom.patches).toHaveLength(8)
  })
})

describe('display projection', () => {
  test('projects support, refine, and contradict findings into hypothesis trees', () => {
    const augmented = applyReasoningPatches(baseGraph(), [
      { name: 'reasoning-graph-patch.json', patch: patch('F_SUPPORT', 'supports') },
      { name: 'reasoning-graph-patch-001.json', patch: patch('F_REFINE', 'refines') },
      { name: 'reasoning-graph-patch-skeptical.json', patch: patch('F_CONTRA', 'contradicts') },
    ])
    const trees = projectGraphToDisplayForest(augmented)
    const labels = JSON.stringify(trees)
    expect(trees).toHaveLength(1)
    expect(labels).toContain('F_SUPPORT')
    expect(labels).toContain('F_REFINE')
    expect(labels).toContain('F_CONTRA')
    expect(labels).toContain('contradicts')
  })

  test('shows the stronger caveat relation when a finding is nested through support', () => {
    const caveatPatch = patch('F_CAVEAT', 'refines')
    caveatPatch.operations.push({
      op: 'add_edge',
      edge: {
        source: 'F_CAVEAT',
        target: 'F_MID1',
        relation: 'supports',
        rationale: 'The caveat qualifies the supporting finding.',
      },
    })
    const augmented = applyReasoningPatches(baseGraph(), [
      { name: 'reasoning-graph-patch-skeptical.json', patch: caveatPatch },
    ])
    const trees = projectGraphToDisplayForest(augmented)
    const stack = [...trees]
    let caveat = null
    while (stack.length) {
      const node = stack.pop()
      if (node?.canonicalId === 'F_CAVEAT') {
        caveat = node
        break
      }
      stack.push(...(node?.children || []))
    }
    expect(caveat?.relation).toBe('supports')
    expect(caveat?.displayRelation).toBe('refines')
  })

})
