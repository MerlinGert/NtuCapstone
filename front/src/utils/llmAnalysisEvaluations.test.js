import { describe, expect, test } from 'bun:test'

import {
  buildNodeEvaluationsPayload,
  evaluationKeyForNode,
  normalizeNodeEvaluations,
  toggleNodeEvaluation,
} from './llmAnalysisEvaluations.js'

describe('LLM analysis evaluation helpers', () => {
  test('uses canonical ID so duplicate rendered nodes share one evaluation key', () => {
    const firstInstance = { id: 'F1__a', canonicalId: 'F1', type: 'Finding' }
    const secondInstance = { id: 'F1__b', canonicalId: 'F1', type: 'Finding' }

    const evaluations = toggleNodeEvaluation({}, firstInstance, new Date('2026-06-07T00:00:00Z'))

    expect(evaluationKeyForNode(firstInstance)).toBe('F1')
    expect(evaluationKeyForNode(secondInstance)).toBe('F1')
    expect(evaluations.F1.checked).toBe(true)
  })

  test('toggling an already checked canonical node removes it from the map', () => {
    const node = { id: 'H1-instance', canonicalId: 'H1', type: 'Hypothesis' }
    const checked = toggleNodeEvaluation({}, node, new Date('2026-06-07T00:00:00Z'))
    const unchecked = toggleNodeEvaluation(checked, node, new Date('2026-06-07T00:00:01Z'))

    expect(checked.H1.nodeKind).toBe('Hypothesis')
    expect(unchecked.H1).toBeUndefined()
  })

  test('normalizes imported or exported evaluation payloads', () => {
    const normalized = normalizeNodeEvaluations({
      updatedAt: '2026-06-07T00:00:00Z',
      evaluations: {
        H1: { checked: true, nodeKind: 'Hypothesis', updatedAt: '2026-06-07T00:00:00Z' },
        F1: { checked: false, nodeKind: 'Finding', updatedAt: '2026-06-07T00:00:00Z' },
        A1: { checked: true, nodeKind: 'AnalyticActivity', updatedAt: '2026-06-07T00:00:00Z' },
      },
    })

    expect(Object.keys(normalized.evaluations)).toEqual(['H1'])
    expect(normalized.updatedAt).toBe('2026-06-07T00:00:00Z')
  })

  test('builds export payload with canonical evaluation entries only', () => {
    const payload = buildNodeEvaluationsPayload({
      sessionId: 'c3f26',
      sessionMode: 'specialized',
      updatedAt: '2026-06-07T00:00:00Z',
      evaluations: {
        F1: { checked: true, nodeKind: 'Finding', updatedAt: '2026-06-07T00:00:00Z' },
      },
    })

    expect(payload.sessionId).toBe('c3f26')
    expect(payload.evaluations.F1.checked).toBe(true)
  })
})
