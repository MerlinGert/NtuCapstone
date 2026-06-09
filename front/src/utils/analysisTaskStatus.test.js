import { describe, expect, test } from 'bun:test'

import {
  analysisTaskStatusLabel,
  analysisTaskStatusTone,
  selectAnalysisTaskForBadge,
} from './analysisTaskStatus.js'

describe('analysis task status helpers', () => {
  test('prefers the task matching the active run id', () => {
    const selected = selectAnalysisTaskForBadge(
      [
        { taskId: 'newer', runId: 'run-2', status: 'running' },
        { taskId: 'target', runId: 'run-1', status: 'completed' },
      ],
      'run-1',
    )

    expect(selected.taskId).toBe('target')
  })

  test('does not fall back to stale tasks while waiting for an active run task', () => {
    const selected = selectAnalysisTaskForBadge(
      [
        { taskId: 'previous', runId: 'run-1', status: 'completed' },
      ],
      'run-2',
    )

    expect(selected).toBeNull()
  })

  test('falls back to the newest active task before terminal tasks', () => {
    const selected = selectAnalysisTaskForBadge([
      { taskId: 'latest-terminal', runId: 'run-3', status: 'completed' },
      { taskId: 'running', runId: 'run-2', status: 'running' },
      { taskId: 'older-terminal', runId: 'run-1', status: 'failed' },
    ])

    expect(selected.taskId).toBe('running')
  })

  test('labels and tones task statuses', () => {
    expect(analysisTaskStatusLabel({ status: 'starting', mode: 'full' })).toBe('Starting full analysis')
    expect(analysisTaskStatusLabel({ status: 'running', mode: 'incremental' })).toBe('Update analysis running')
    expect(analysisTaskStatusTone('completed')).toBe('success')
    expect(analysisTaskStatusTone('failed')).toBe('error')
  })
})
