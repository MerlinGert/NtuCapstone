export const TIMELINE_PART_TYPES = {
  MARKDOWN: 'markdown',
  ACTIVITY_SEQUENCE: 'activity_sequence',
  ARTIFACT: 'artifact',
}

function safeString(value) {
  return value == null ? '' : String(value)
}

export function artifactKey(artifact) {
  if (!artifact || typeof artifact !== 'object') return ''
  return safeString(artifact.id || artifact.path || artifact.title || artifact.name)
}

function activityKey(activity) {
  if (!activity || typeof activity !== 'object' || !activity.eventId) return ''
  return `${activity.eventId}:${activity.category || ''}`
}

function cloneArtifact(artifact) {
  return artifact && typeof artifact === 'object' ? { ...artifact } : artifact
}

function cloneActivity(activity) {
  return activity && typeof activity === 'object' ? { ...activity } : activity
}

function normalizeActivitySequence(part, fallbackId) {
  const activities = Array.isArray(part.activities)
    ? part.activities.map((activity) => cloneActivity(activity)).filter(Boolean)
    : []
  return {
    id: safeString(part.id || fallbackId),
    type: TIMELINE_PART_TYPES.ACTIVITY_SEQUENCE,
    activities,
    open: Boolean(part.open),
  }
}

function normalizePart(part, fallbackId) {
  if (!part || typeof part !== 'object') return null
  if (part.type === TIMELINE_PART_TYPES.MARKDOWN) {
    const text = safeString(part.text)
    return text
      ? {
          id: safeString(part.id || fallbackId),
          type: TIMELINE_PART_TYPES.MARKDOWN,
          text,
        }
      : null
  }
  if (part.type === TIMELINE_PART_TYPES.ARTIFACT) {
    if (!part.artifact || typeof part.artifact !== 'object') return null
    return {
      id: safeString(part.id || fallbackId),
      type: TIMELINE_PART_TYPES.ARTIFACT,
      artifact: cloneArtifact(part.artifact),
    }
  }
  if (part.type === TIMELINE_PART_TYPES.ACTIVITY_SEQUENCE) {
    const normalized = normalizeActivitySequence(part, fallbackId)
    return normalized.activities.length ? normalized : null
  }
  return null
}

export function normalizeMessageParts(message, fallbackId = 'message') {
  const sourceParts = Array.isArray(message?.parts) ? message.parts : []
  const normalizedParts = sourceParts
    .map((part, index) => normalizePart(part, `${fallbackId}-part-${index + 1}`))
    .filter(Boolean)

  if (normalizedParts.length) return normalizedParts

  const legacyParts = []
  const content = safeString(message?.content)
  if (content) {
    legacyParts.push({
      id: `${fallbackId}-legacy-content`,
      type: TIMELINE_PART_TYPES.MARKDOWN,
      text: content,
    })
  }

  const activities = Array.isArray(message?.activity)
    ? message.activity.map((activity) => cloneActivity(activity)).filter((activity) => !activity?.ephemeral)
    : []
  if (activities.length) {
    legacyParts.push({
      id: `${fallbackId}-legacy-activity`,
      type: TIMELINE_PART_TYPES.ACTIVITY_SEQUENCE,
      activities,
      open: Boolean(message?.activityOpen),
    })
  }

  const seenArtifacts = new Set()
  const artifacts = Array.isArray(message?.artifacts) ? message.artifacts : []
  artifacts.forEach((artifact, index) => {
    const key = artifactKey(artifact)
    if (!key || seenArtifacts.has(key)) return
    seenArtifacts.add(key)
    legacyParts.push({
      id: `${fallbackId}-legacy-artifact-${index + 1}`,
      type: TIMELINE_PART_TYPES.ARTIFACT,
      artifact: cloneArtifact(artifact),
    })
  })

  return legacyParts
}

export function appendMarkdownPart(parts, id, text) {
  const normalizedText = safeString(text)
  if (!normalizedText) return null
  const targetParts = Array.isArray(parts) ? parts : []
  const latest = targetParts[targetParts.length - 1]
  if (latest?.type === TIMELINE_PART_TYPES.MARKDOWN) {
    latest.text = latest.text ? `${latest.text}\n\n${normalizedText}` : normalizedText
    return latest
  }
  const part = {
    id: safeString(id),
    type: TIMELINE_PART_TYPES.MARKDOWN,
    text: normalizedText,
  }
  targetParts.push(part)
  return part
}

export function appendArtifactPart(parts, id, artifact) {
  const key = artifactKey(artifact)
  if (!key) return null
  const targetParts = Array.isArray(parts) ? parts : []
  for (const part of targetParts) {
    if (part?.type === TIMELINE_PART_TYPES.ARTIFACT && artifactKey(part.artifact) === key) {
      part.artifact = {
        ...part.artifact,
        ...cloneArtifact(artifact),
      }
      return part
    }
  }

  const part = {
    id: safeString(id),
    type: TIMELINE_PART_TYPES.ARTIFACT,
    artifact: cloneArtifact(artifact),
  }
  targetParts.push(part)
  return part
}

export function appendActivityToTimeline(parts, sequenceId, activity) {
  if (!activity || activity.ephemeral) return null
  const targetParts = Array.isArray(parts) ? parts : []
  const normalizedActivity = cloneActivity(activity)
  const key = activityKey(normalizedActivity)

  if (key) {
    for (const part of targetParts) {
      if (part?.type !== TIMELINE_PART_TYPES.ACTIVITY_SEQUENCE || !Array.isArray(part.activities)) continue
      const index = part.activities.findIndex((item) => activityKey(item) === key)
      if (index !== -1) {
        part.activities.splice(index, 1, {
          ...part.activities[index],
          ...normalizedActivity,
          id: part.activities[index].id,
        })
        return part
      }
    }
  }

  let sequence = targetParts[targetParts.length - 1]
  if (sequence?.type !== TIMELINE_PART_TYPES.ACTIVITY_SEQUENCE) {
    sequence = {
      id: safeString(sequenceId),
      type: TIMELINE_PART_TYPES.ACTIVITY_SEQUENCE,
      activities: [],
      open: false,
    }
    targetParts.push(sequence)
  }
  sequence.activities.push(normalizedActivity)
  return sequence
}

export function compactLegacyContent(parts) {
  return (Array.isArray(parts) ? parts : [])
    .filter((part) => part?.type === TIMELINE_PART_TYPES.MARKDOWN && part.text)
    .map((part) => part.text)
    .join('\n\n')
}

export function collectLegacyActivities(parts) {
  return (Array.isArray(parts) ? parts : [])
    .filter((part) => part?.type === TIMELINE_PART_TYPES.ACTIVITY_SEQUENCE && Array.isArray(part.activities))
    .flatMap((part) => part.activities)
    .filter((activity) => !activity?.ephemeral)
}

export function collectLegacyArtifacts(parts) {
  const seen = new Set()
  const artifacts = []
  ;(Array.isArray(parts) ? parts : []).forEach((part) => {
    if (part?.type !== TIMELINE_PART_TYPES.ARTIFACT) return
    const key = artifactKey(part.artifact)
    if (!key || seen.has(key)) return
    seen.add(key)
    artifacts.push(cloneArtifact(part.artifact))
  })
  return artifacts
}
