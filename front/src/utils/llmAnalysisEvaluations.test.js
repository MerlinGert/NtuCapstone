import { describe, expect, test } from 'bun:test'

import {
  buildNodeEvaluationsPayload,
  evaluationKeyForNode,
  isNodeEvaluationComplete,
  normalizeNodeEvaluations,
  updateNodeEvaluation,
} from './llmAnalysisEvaluations.js'

describe('LLM analysis evaluation helpers', () => {
  test('uses canonical ID so duplicate rendered nodes share one evaluation key', () => {
    const firstInstance = { id: 'F1__a', canonicalId: 'F1', type: 'Finding' }
    const secondInstance = { id: 'F1__b', canonicalId: 'F1', type: 'Finding' }

    const evaluations = updateNodeEvaluation({}, firstInstance, {
      associatedHypothesisId: 'H1',
      associatedHypothesisLabel: 'H1',
      relevanceToHypothesis: 'yes',
    }, new Date('2026-06-07T00:00:00Z'))

    expect(evaluationKeyForNode(firstInstance)).toBe('F1')
    expect(evaluationKeyForNode(secondInstance)).toBe('F1')
    expect(evaluations.F1.checked).toBe(true)
  })

  test('hypothesis checklist becomes complete after both required fields are filled', () => {
    const node = { id: 'H1-instance', canonicalId: 'H1', type: 'Hypothesis' }
    const partial = updateNodeEvaluation({}, node, {
      hypothesisAligned: 'yes',
    }, new Date('2026-06-07T00:00:00Z'))
    const complete = updateNodeEvaluation(partial, node, {
      findingsSufficiency: 'partially',
      note: 'Need more contradictory evidence.',
    }, new Date('2026-06-07T00:00:01Z'))

    expect(isNodeEvaluationComplete(partial.H1)).toBe(false)
    expect(complete.H1.nodeKind).toBe('Hypothesis')
    expect(complete.H1.findingsSufficiency).toBe('partially')
    expect(complete.H1.note).toBe('Need more contradictory evidence.')
    expect(isNodeEvaluationComplete(complete.H1)).toBe(true)
  })

  test('normalizes imported or exported evaluation payloads', () => {
    const normalized = normalizeNodeEvaluations({
      updatedAt: '2026-06-07T00:00:00Z',
      evaluations: {
        H1: {
          checked: false,
          nodeKind: 'Hypothesis',
          hypothesisAligned: 'unsure',
          findingsSufficiency: 'no',
          note: 'Needs more evidence',
          updatedAt: '2026-06-07T00:00:00Z',
        },
        F1: {
          checked: false,
          nodeKind: 'Finding',
          associatedHypothesisId: null,
          associatedHypothesisLabel: 'None',
          relevanceToHypothesis: 'no',
          updatedAt: '2026-06-07T00:00:00Z',
        },
        A1: { checked: true, nodeKind: 'AnalyticActivity', updatedAt: '2026-06-07T00:00:00Z' },
      },
    })

    expect(Object.keys(normalized.evaluations)).toEqual(['H1', 'F1'])
    expect(normalized.evaluations.H1.hypothesisAligned).toBe('unsure')
    expect(normalized.evaluations.F1.associatedHypothesisId).toBeNull()
    expect(normalized.updatedAt).toBe('2026-06-07T00:00:00Z')
  })

  test('builds export payload with canonical evaluation entries only', () => {
    const payload = buildNodeEvaluationsPayload({
      sessionId: 'c3f26',
      sessionMode: 'specialized',
      updatedAt: '2026-06-07T00:00:00Z',
      evaluations: {
        F1: {
          checked: true,
          nodeKind: 'Finding',
          associatedHypothesisId: 'H1',
          associatedHypothesisLabel: 'Pump hypothesis',
          relevanceToHypothesis: 'yes',
          note: 'Directly addresses the parent claim.',
          updatedAt: '2026-06-07T00:00:00Z',
        },
      },
    })

    expect(payload.sessionId).toBe('c3f26')
    expect(payload.evaluations.F1.checked).toBe(true)
    expect(payload.evaluations.F1.associatedHypothesisId).toBe('H1')
    expect(payload.evaluations.F1.note).toBe('Directly addresses the parent claim.')
  })
})
