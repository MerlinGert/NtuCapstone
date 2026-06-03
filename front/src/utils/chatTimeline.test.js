import { describe, expect, test } from 'bun:test'

import {
  TIMELINE_PART_TYPES,
  appendActivityToTimeline,
  appendArtifactPart,
  appendMarkdownPart,
  collectLegacyActivities,
  collectLegacyArtifacts,
  compactLegacyContent,
  normalizeMessageParts,
} from './chatTimeline.js'

function activity(overrides = {}) {
  return {
    id: overrides.id || 'a1',
    title: overrides.title || 'Inspecting trace',
    detail: overrides.detail || 'Reading current trace files.',
    category: overrides.category || 'session',
    level: overrides.level || 'detail',
    eventId: overrides.eventId || '',
    ...overrides,
  }
}

function artifact(overrides = {}) {
  return {
    id: overrides.id || 'artifact-1',
    title: overrides.title || 'report.md',
    kind: overrides.kind || 'markdown',
    path: overrides.path || 'artifacts/report.md',
    ...overrides,
  }
}

describe('chat timeline helpers', () => {
  test('preserves text, activity, artifact, text stream order', () => {
    const parts = []
    appendMarkdownPart(parts, 'p1', 'I am checking the trace.')
    appendActivityToTimeline(parts, 'p2', activity())
    appendArtifactPart(parts, 'p3', artifact())
    appendMarkdownPart(parts, 'p4', 'The report is ready.')

    expect(parts.map((part) => part.type)).toEqual([
      TIMELINE_PART_TYPES.MARKDOWN,
      TIMELINE_PART_TYPES.ACTIVITY_SEQUENCE,
      TIMELINE_PART_TYPES.ARTIFACT,
      TIMELINE_PART_TYPES.MARKDOWN,
    ])
    expect(parts[1].open).toBe(false)
    expect(parts[1].activities).toHaveLength(1)
  })

  test('collapses contiguous activities into one default-closed sequence', () => {
    const parts = []
    appendActivityToTimeline(parts, 'seq-1', activity({ id: 'a1', title: 'Planning' }))
    appendActivityToTimeline(parts, 'seq-2', activity({ id: 'a2', title: 'Running command' }))

    expect(parts).toHaveLength(1)
    expect(parts[0].type).toBe(TIMELINE_PART_TYPES.ACTIVITY_SEQUENCE)
    expect(parts[0].open).toBe(false)
    expect(parts[0].activities.map((item) => item.title)).toEqual(['Planning', 'Running command'])
  })

  test('starts a new activity sequence after markdown output', () => {
    const parts = []
    appendActivityToTimeline(parts, 'seq-1', activity({ id: 'a1', title: 'Planning' }))
    appendMarkdownPart(parts, 'text-1', 'I found the first result.')
    appendActivityToTimeline(parts, 'seq-2', activity({ id: 'a2', title: 'Running follow-up' }))

    expect(parts.map((part) => part.type)).toEqual([
      TIMELINE_PART_TYPES.ACTIVITY_SEQUENCE,
      TIMELINE_PART_TYPES.MARKDOWN,
      TIMELINE_PART_TYPES.ACTIVITY_SEQUENCE,
    ])
    expect(parts[2].activities[0].title).toBe('Running follow-up')
  })

  test('deduplicates artifact parts by stable artifact key', () => {
    const parts = []
    appendArtifactPart(parts, 'artifact-part-1', artifact({ id: 'same', title: 'old.md' }))
    appendArtifactPart(parts, 'artifact-part-2', artifact({ id: 'same', title: 'new.md' }))

    expect(parts).toHaveLength(1)
    expect(parts[0].artifact.title).toBe('new.md')
  })

  test('updates an activity with the same event id and category', () => {
    const parts = []
    appendActivityToTimeline(parts, 'seq-1', activity({
      id: 'a1',
      eventId: 'tool-1',
      category: 'tool',
      title: 'Shell command',
      status: 'running',
    }))
    appendActivityToTimeline(parts, 'seq-2', activity({
      id: 'a2',
      eventId: 'tool-1',
      category: 'tool',
      title: 'Shell command',
      status: 'completed',
      output: 'done',
    }))

    expect(parts).toHaveLength(1)
    expect(parts[0].activities).toHaveLength(1)
    expect(parts[0].activities[0].id).toBe('a1')
    expect(parts[0].activities[0].status).toBe('completed')
    expect(parts[0].activities[0].output).toBe('done')
  })

  test('converts legacy message fields into timeline parts', () => {
    const parts = normalizeMessageParts(
      {
        content: 'Legacy markdown',
        activity: [activity({ id: 'a1' })],
        artifacts: [artifact({ id: 'file-1' })],
        activityOpen: true,
      },
      'm1',
    )

    expect(parts.map((part) => part.type)).toEqual([
      TIMELINE_PART_TYPES.MARKDOWN,
      TIMELINE_PART_TYPES.ACTIVITY_SEQUENCE,
      TIMELINE_PART_TYPES.ARTIFACT,
    ])
    expect(parts[1].open).toBe(true)
    expect(compactLegacyContent(parts)).toBe('Legacy markdown')
    expect(collectLegacyActivities(parts)).toHaveLength(1)
    expect(collectLegacyArtifacts(parts)).toHaveLength(1)
  })
})
