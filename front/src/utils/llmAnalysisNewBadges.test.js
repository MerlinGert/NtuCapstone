import { describe, expect, test } from 'bun:test'

import {
  collectVisibleNewBadgeNodes,
  detectNewVisibleNodes,
  normalizeAnalysisUiState,
} from './llmAnalysisNewBadges.js'

function finding(id, overrides = {}) {
  return {
    id: `${id}-instance`,
    canonicalId: id,
    type: 'Finding',
    label: id,
    children: [],
    ...overrides,
  }
}

function hypothesis(id, children = [], overrides = {}) {
  return {
    id: `${id}-instance`,
    canonicalId: id,
    type: 'Hypothesis',
    label: id,
    children,
    ...overrides,
  }
}

describe('LLM analysis New badge helpers', () => {
  test('deduplicates visible nodes by canonical ID', () => {
    const trees = [
      hypothesis('H1', [
        finding('F1'),
        finding('F1', { id: 'F1-duplicate' }),
      ]),
    ]

    const visible = collectVisibleNewBadgeNodes(trees)

    expect(visible.map((node) => node.id)).toEqual(['H1', 'F1'])
  })

  test('suppresses badges during an initial run', () => {
    const result = detectNewVisibleNodes(
      {
        activeRun: {
          runId: 'run-1',
          suppressNewBadges: true,
          baselineVisibleNodeIds: [],
        },
        newNodeIds: {},
      },
      [hypothesis('H1', [finding('F1')])],
      new Date('2026-06-07T00:00:00Z'),
    )

    expect(result.changed).toBe(false)
    expect(result.state.newNodeIds).toEqual({})
  })

  test('marks newly visible hypothesis and finding cards in a later run', () => {
    const result = detectNewVisibleNodes(
      {
        activeRun: {
          runId: 'run-2',
          suppressNewBadges: false,
          baselineVisibleNodeIds: ['H1', 'F1'],
        },
        newNodeIds: {},
      },
      [
        hypothesis('H1', [
          finding('F1'),
          finding('F2'),
        ]),
        hypothesis('H2'),
      ],
      new Date('2026-06-07T00:00:00Z'),
    )

    expect(result.changed).toBe(true)
    expect(result.addedNodeIds.sort()).toEqual(['F2', 'H2'])
    expect(result.state.newNodeIds.F2.nodeKind).toBe('Finding')
    expect(result.state.newNodeIds.H2.nodeKind).toBe('Hypothesis')
  })

  test('normalizes imported state and ignores unsupported node kinds', () => {
    const normalized = normalizeAnalysisUiState({
      activeRun: {
        runId: 'run-3',
        suppressNewBadges: false,
        baselineVisibleNodeIds: ['H1'],
      },
      newNodeIds: {
        F1: { nodeKind: 'Finding', firstSeenAt: '2026-06-07T00:00:00Z', runId: 'run-3' },
        A1: { nodeKind: 'AnalyticActivity', firstSeenAt: '2026-06-07T00:00:00Z', runId: 'run-3' },
      },
    })

    expect(normalized.activeRun.runId).toBe('run-3')
    expect(Object.keys(normalized.newNodeIds)).toEqual(['F1'])
  })
})
