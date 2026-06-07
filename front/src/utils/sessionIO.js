// ezio: session import/export utility for action/annotation/tree data
import { strToU8, zipSync, unzipSync } from 'fflate'

const EXPORT_VERSION = '2.1'

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value))
}

function normalizeNamePart(value) {
  return String(value || 'unknown')
    .replace(/[^a-zA-Z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase() || 'unknown'
}

function dataUrlToBytes(dataUrl) {
  if (!dataUrl || typeof dataUrl !== 'string') return null
  const match = dataUrl.match(/^data:image\/[a-zA-Z0-9.+-]+(;[^,]*)?,(.*)$/)
  if (!match) return null
  const metadata = match[1] || ''
  const payload = match[2] || ''
  let binary = ''
  if (metadata.includes(';base64')) {
    binary = atob(payload)
  } else {
    binary = decodeURIComponent(payload)
  }
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }
  return bytes
}

function bytesToBase64(bytes) {
  let binary = ''
  const chunkSize = 8192
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize))
  }
  return btoa(binary)
}

function imageMimeTypeFromPath(path) {
  const value = String(path || '').toLowerCase()
  if (value.endsWith('.jpg') || value.endsWith('.jpeg')) return 'image/jpeg'
  if (value.endsWith('.webp')) return 'image/webp'
  if (value.endsWith('.gif')) return 'image/gif'
  return 'image/png'
}

function imageBytesToDataUrl(bytes, path = '') {
  return `data:${imageMimeTypeFromPath(path)};base64,${bytesToBase64(bytes)}`
}

function stripSnapshotsFromActions(actions) {
  return actions.map((action) => {
    const copy = { ...action }
    delete copy.sourceSnapshot
    delete copy.targetSnapshot
    return copy
  })
}

function stripSketchFromAnnotations(annotations) {
  return annotations.map((annotation) => ({ ...annotation, sketchDataUrl: null }))
}

function ensureImagePath(path, bytes, images, metadata = {}) {
  if (!bytes) return null
  images.push({
    path,
    bytes,
    ...metadata,
  })
  return path
}

function extractSnapshotImages(actions, images) {
  return actions.map((action, actionIndex) => {
    const copy = { ...action }
    ;['sourceSnapshot', 'targetSnapshot'].forEach((field) => {
      if (!Array.isArray(copy[field])) return
      copy[field] = copy[field].map((snapshot, snapshotIndex) => {
        if (!snapshot || !snapshot.dataUrl) return snapshot
        const bytes = dataUrlToBytes(snapshot.dataUrl)
        const imagePath = `images/action-${String(actionIndex + 1).padStart(4, '0')}-${field === 'sourceSnapshot' ? 'source' : 'target'}-${normalizeNamePart(snapshot.viewName || copy[field === 'sourceSnapshot' ? 'sourceView' : 'targetView'])}-${String(snapshotIndex + 1).padStart(2, '0')}.png`
        ensureImagePath(imagePath, bytes, images, {
          kind: field,
          actionIndex,
          snapshotIndex,
        })
        const snapshotCopy = { ...snapshot, imagePath }
        delete snapshotCopy.dataUrl
        return snapshotCopy
      })
    })
    return copy
  })
}

function extractAnnotationImages(annotations, images) {
  return annotations.map((annotation, annotationIndex) => {
    const copy = { ...annotation }
    if (copy.sketchDataUrl) {
      const bytes = dataUrlToBytes(copy.sketchDataUrl)
      const idPart = copy.id !== undefined ? copy.id : annotationIndex + 1
      const imagePath = `images/annotation-${String(idPart).padStart(4, '0')}-${normalizeNamePart(copy.sourceView)}.png`
      ensureImagePath(imagePath, bytes, images, {
        kind: 'annotation',
        annotationIndex,
      })
      copy.sketchImagePath = imagePath
    }
    delete copy.sketchDataUrl
    return copy
  })
}

function extractCurrentStateImages(currentState, images) {
  const copy = cloneJson(currentState || {})
  if (!copy.majorViewScreenshots || typeof copy.majorViewScreenshots !== 'object') return copy
  const nextScreenshots = {}
  Object.entries(copy.majorViewScreenshots).forEach(([viewName, value]) => {
    if (typeof value !== 'string' || !value.startsWith('data:image/')) {
      nextScreenshots[viewName] = value
      return
    }
    const bytes = dataUrlToBytes(value)
    const imagePath = `images/current-${normalizeNamePart(viewName)}.png`
    ensureImagePath(imagePath, bytes, images, {
      kind: 'current_state',
      viewName,
    })
    nextScreenshots[viewName] = imagePath
  })
  copy.majorViewScreenshots = nextScreenshots
  return copy
}

function extractChatAttachmentImages(chatbotLogs, images) {
  return chatbotLogs.map((entry, entryIndex) => {
    const copy = { ...entry }
    const attachments = Array.isArray(copy.promptAttachments) ? copy.promptAttachments : []
    copy.promptAttachments = attachments.map((attachment, attachmentIndex) => {
      const attachmentCopy = { ...attachment }
      if (attachmentCopy.dataUrl) {
        const bytes = dataUrlToBytes(attachmentCopy.dataUrl)
        const imagePath = `images/chat-${String(entryIndex + 1).padStart(4, '0')}-prompt-${String(attachmentIndex + 1).padStart(2, '0')}-${normalizeNamePart(attachmentCopy.name)}.png`
        ensureImagePath(imagePath, bytes, images, {
          kind: 'chat_prompt_attachment',
          entryIndex,
          attachmentIndex,
        })
        attachmentCopy.imagePath = imagePath
      }
      delete attachmentCopy.dataUrl
      return attachmentCopy
    })
    return copy
  })
}

async function fetchImageBytes(url) {
  if (!url || typeof url !== 'string') return null
  try {
    const response = await fetch(url)
    if (!response.ok) return null
    const buffer = await response.arrayBuffer()
    return new Uint8Array(buffer)
  } catch (error) {
    return null
  }
}

async function extractChatArtifactImages(chatbotLogs, images) {
  const logs = cloneJson(chatbotLogs || [])
  for (let logIndex = 0; logIndex < logs.length; logIndex += 1) {
    const entry = logs[logIndex]
    const artifacts = Array.isArray(entry?.response?.artifacts) ? entry.response.artifacts : []
    for (let artifactIndex = 0; artifactIndex < artifacts.length; artifactIndex += 1) {
      const artifact = artifacts[artifactIndex]
      if (!artifact || artifact.kind !== 'image') continue
      const imageUrl = artifact.url || artifact.href || artifact.path || null
      const bytes = await fetchImageBytes(imageUrl)
      if (!bytes) continue
      const extension = String(artifact.title || '').toLowerCase().endsWith('.webp') ? 'webp' : 'png'
      const imagePath = `images/chat-${String(logIndex + 1).padStart(4, '0')}-artifact-${String(artifactIndex + 1).padStart(2, '0')}-${normalizeNamePart(artifact.title || artifact.id)}.${extension}`
      ensureImagePath(imagePath, bytes, images, {
        kind: 'chat_response_artifact',
        logIndex,
        artifactIndex,
      })
      artifact.exportImagePath = imagePath
    }
  }
  return logs
}

function collectNestedImageRefs(value, refs) {
  if (!value) return
  if (Array.isArray(value)) {
    value.forEach((item) => collectNestedImageRefs(item, refs))
    return
  }
  if (typeof value === 'object') {
    const directPath = value.path || value.src || value.href || value.url || null
    if (typeof directPath === 'string') refs.push(directPath)
    Object.values(value).forEach((item) => collectNestedImageRefs(item, refs))
    return
  }
  if (typeof value !== 'string') return
  const parts = value.split('|').map((item) => item.trim()).filter(Boolean)
  parts.forEach((part) => refs.push(part))
}

function normalizeAnalysisImageRef(text) {
  if (!text || typeof text !== 'string') return ''
  const trimmed = text.trim()
  const apiImagePath = zipLocalImagePathFromRef(trimmed)
  if (apiImagePath) return apiImagePath
  const prefixed = trimmed.match(/^(?:screenshot|render|image):(.+\.(?:png|jpe?g|webp))$/i)
  if (prefixed) return prefixed[1].trim().replace(/\\/g, '/')
  const bare = trimmed.match(/^(.+\.(?:png|jpe?g|webp))$/i)
  return bare ? bare[1].trim().replace(/\\/g, '/') : ''
}

function zipLocalImagePathFromRef(ref) {
  if (!ref || typeof ref !== 'string') return ''
  const trimmed = ref.trim()
  if (trimmed.startsWith('../images/')) return trimmed.slice(3).replace(/\\/g, '/')
  if (trimmed.startsWith('images/')) return trimmed.replace(/\\/g, '/')
  const directApiMatch = trimmed.match(/^\/api\/(?:base\/)?sessions\/[^/]+\/images\/(.+)$/i)
  if (directApiMatch) return `images/${decodeURIComponent(directApiMatch[1])}`.replace(/\\/g, '/')
  try {
    const url = new URL(trimmed)
    const urlMatch = url.pathname.match(/^\/api\/(?:base\/)?sessions\/[^/]+\/images\/(.+)$/i)
    if (urlMatch) return `images/${decodeURIComponent(urlMatch[1])}`.replace(/\\/g, '/')
  } catch (error) {
    // ignore parse failures for non-URL refs
  }
  return ''
}

function resolveImageFileKeyFromRef(ref, imageFiles) {
  if (!ref || typeof ref !== 'string') return ''
  const localPath = zipLocalImagePathFromRef(ref) || ref.trim()
  if (imageFiles[localPath]) return localPath

  const normalized = normalizeAnalysisImageRef(ref)
  if (normalized && imageFiles[normalized]) return normalized

  const bareMatch = String(ref).trim().match(/([^/]+\.(?:png|jpe?g|webp|gif))$/i)
  if (!bareMatch) return ''
  const bareName = bareMatch[1]
  const matches = Object.keys(imageFiles).filter((key) => key === bareName || key.endsWith(`/${bareName}`))
  return matches.length === 1 ? matches[0] : ''
}

async function extractLlmAnalysisImages(llmAnalysis, images) {
  const analysis = cloneJson(llmAnalysis || null)
  if (!analysis || typeof analysis !== 'object') return null
  const refs = []
  const existingImagePaths = new Set(images.map((image) => image.path))
  collectNestedImageRefs(analysis.displayForest, refs)
  collectNestedImageRefs(analysis.reasoningGraph, refs)
  collectNestedImageRefs(analysis.augmentedReasoningGraph, refs)
  collectNestedImageRefs(analysis.graphPatches, refs)

  const refMap = new Map()
  for (const rawRef of refs) {
    const normalized = normalizeAnalysisImageRef(rawRef)
    if (!normalized || refMap.has(rawRef)) continue
    if (existingImagePaths.has(normalized)) {
      refMap.set(rawRef, normalized)
      refMap.set(normalized, normalized)
      continue
    }
    if (/^(https?:|data:|blob:|file:)/i.test(normalized)) continue
    let sourcePath = normalized
    while (sourcePath.startsWith('./')) sourcePath = sourcePath.slice(2)
    if (sourcePath.startsWith('../')) sourcePath = sourcePath.replace(/^\.\.\//, '')
    if (sourcePath.includes('..')) continue
    const bytes = await fetchImageBytes(sourcePath)
    if (!bytes) continue
    const fileName = sourcePath.split('/').filter(Boolean).pop() || `analysis-image-${images.length + 1}.png`
    const exportPath = `images/llm-analysis/${fileName}`
    ensureImagePath(exportPath, bytes, images, {
      kind: 'llm_analysis',
      sourcePath,
    })
    refMap.set(rawRef, exportPath)
    if (normalized !== rawRef) {
      refMap.set(normalized, exportPath)
    }
  }

  if (!refMap.size) return analysis

  const rewrite = (value) => {
    if (!value) return value
    if (Array.isArray(value)) return value.map((item) => rewrite(item))
    if (typeof value === 'object') {
      const copy = {}
      Object.entries(value).forEach(([key, item]) => {
        if (typeof item === 'string' && refMap.has(item)) {
          copy[key] = refMap.get(item)
        } else {
          copy[key] = rewrite(item)
        }
      })
      return copy
    }
    if (typeof value === 'string') {
      const parts = value.split('|')
      let changed = false
      const next = parts.map((part) => {
        const trimmed = part.trim()
        if (refMap.has(trimmed)) {
          changed = true
          return refMap.get(trimmed)
        }
        const normalized = normalizeAnalysisImageRef(trimmed)
        if (normalized && refMap.has(normalized)) {
          changed = true
          return refMap.get(normalized)
        }
        return part
      })
      return changed ? next.join(' | ') : value
    }
    return value
  }

  return rewrite(analysis)
}

function restoreLlmAnalysisImages(llmAnalysis, imageFiles) {
  const analysis = cloneJson(llmAnalysis || null)
  if (!analysis || typeof analysis !== 'object') return null

  const resolveImageDataUrl = (path) => {
    const imageFileKey = resolveImageFileKeyFromRef(path, imageFiles)
    if (!imageFileKey) return null
    const imgBytes = imageFiles[imageFileKey]
    if (!imgBytes) return null
    const mimeType = imageMimeTypeFromPath(imageFileKey)
    return `data:${mimeType};base64,${bytesToBase64(imgBytes)}`
  }

  const rewrite = (value) => {
    if (!value) return value
    if (Array.isArray(value)) return value.map((item) => rewrite(item))
    if (typeof value === 'object') {
      const copy = {}
      Object.entries(value).forEach(([key, item]) => {
        if (typeof item === 'string') {
          copy[key] = resolveImageDataUrl(item) || item
        } else {
          copy[key] = rewrite(item)
        }
      })
      return copy
    }
    if (typeof value === 'string') {
      const parts = value.split('|')
      let changed = false
      const next = parts.map((part) => {
        const trimmed = part.trim()
        const dataUrl = resolveImageDataUrl(trimmed)
        if (!dataUrl) return part
        changed = true
        return dataUrl
      })
      return changed ? next.join(' | ') : value
    }
    return value
  }

  return rewrite(analysis)
}

function normalizeInteractionTrace(actions, studyInfo, sessionMode, coin, currentState) {
  return (actions || []).map((action, index) => ({
    index: index + 1,
    timestamp: action.timestamp || null,
    userId: action.userId || studyInfo.participantId || null,
    condition: action.condition || (sessionMode === 'baseline' ? 'baseline' : 'full ManiScope'),
    dataset: action.dataset || coin || null,
    sessionOrder: action.sessionOrder || studyInfo.sessionOrder || null,
    view: action.view || action.sourceView || null,
    actionType: action.actionType || null,
    targetObject: cloneJson(action.targetObject || action.actionInfo || {}),
    currentSystemState: cloneJson(action.currentSystemState || action.relatedViewWithViewState || currentState || {}),
    sourceView: action.sourceView || null,
    targetView: action.targetView || null,
    rawActionInfo: cloneJson(action.actionInfo || {}),
  }))
}

function normalizeUserNotes(annotations) {
  return (annotations || []).map((annotation) => ({
    id: annotation.id,
    timestamp: annotation.timestamp || null,
    linkedView: annotation.linkedView || annotation.sourceView || null,
    selectedObject: cloneJson(annotation.selectedObject || {}),
    timeWindow: annotation.timeWindow || null,
    noteText: annotation.text || '',
    noteKind: annotation.noteKind || (annotation.isFinding ? 'finding' : 'finding'),
    sourceView: annotation.sourceView || null,
    selectedItems: cloneJson(annotation.selectedItems || []),
    sketchImagePath: annotation.sketchImagePath || null,
  }))
}

function normalizeChatbotLogs(chatbotLogs, studyInfo, sessionMode, coin) {
  return (chatbotLogs || []).map((entry) => ({
    id: entry.id,
    timestamp: entry.timestamp || null,
    userId: entry.participantId || studyInfo.participantId || null,
    condition: entry.condition || (sessionMode === 'baseline' ? 'baseline' : 'full ManiScope'),
    dataset: entry.dataset || coin || null,
    sessionOrder: entry.sessionOrder || studyInfo.sessionOrder || null,
    triggerType: entry.triggerType || 'manual',
    userPrompt: entry.prompt || '',
    promptAttachments: cloneJson(entry.promptAttachments || []),
    promptContext: cloneJson(entry.promptContext || {}),
    systemResponse: entry.response?.text || '',
    responseTypes: cloneJson(entry.response?.responseTypes || []),
    clicked: Boolean(entry.response?.clicked),
    expanded: Boolean(entry.response?.expanded),
    accepted: entry.response?.accepted ?? null,
    used: Boolean(entry.response?.used),
    usedAt: entry.response?.usedAt || null,
    responseLinkedEvidence: cloneJson(entry.response?.linkedEvidence || {}),
    responseArtifacts: cloneJson(entry.response?.artifacts || []),
  }))
}

function normalizeLlmAnalysisTrace(llmAnalysisTrace, studyInfo, sessionMode, coin) {
  return (llmAnalysisTrace || []).map((entry, index) => ({
    index: index + 1,
    traceKey: entry?.traceKey || null,
    timestamp: entry?.timestamp || null,
    artifactModifiedAt: entry?.artifactModifiedAt || null,
    eventType: entry?.eventType || null,
    label: entry?.label || '',
    sessionId: entry?.sessionId || null,
    condition: entry?.condition || (sessionMode === 'baseline' ? 'baseline' : 'full ManiScope'),
    dataset: entry?.dataset || coin || null,
    sessionOrder: entry?.sessionOrder || studyInfo.sessionOrder || null,
    artifactName: entry?.artifactName || null,
    patchName: entry?.patchName || null,
    patchCount: Number.isFinite(entry?.patchCount) ? entry.patchCount : null,
    stats: cloneJson(entry?.stats || {}),
    currentSystemState: cloneJson(entry?.currentSystemState || {}),
  }))
}

export async function buildExportArchive({
  sessionId,
  sessionMode,
  coin,
  userActionSequence,
  annotationRecords,
  snapshotCategories,
  snapshotQuality,
  annotationSeqId,
  includeSnapshots,
  currentState,
  studyInfo,
  analysisMilestones,
  chatbotLogs,
  llmAnalysisTrace,
  llmAnalysis,
}) {
  const images = []
  const nextStudyInfo = {
    participantId: String(studyInfo?.participantId || ''),
    sessionOrder: String(studyInfo?.sessionOrder || ''),
    studyNotes: String(studyInfo?.studyNotes || ''),
    condition: sessionMode === 'baseline' ? 'baseline' : 'full ManiScope',
    dataset: coin || null,
  }

  const actions = includeSnapshots
    ? extractSnapshotImages(cloneJson(userActionSequence || []), images)
    : stripSnapshotsFromActions(cloneJson(userActionSequence || []))
  const annotations = includeSnapshots
    ? extractAnnotationImages(cloneJson(annotationRecords || []), images)
    : stripSketchFromAnnotations(cloneJson(annotationRecords || []))
  const studyLogsWithAttachments = includeSnapshots
    ? extractChatAttachmentImages(cloneJson(chatbotLogs || []), images)
    : cloneJson(chatbotLogs || []).map((entry) => ({
      ...entry,
      promptAttachments: (entry.promptAttachments || []).map((attachment) => ({
        ...attachment,
        dataUrl: null,
      })),
    }))
  const studyLogs = includeSnapshots
    ? await extractChatArtifactImages(studyLogsWithAttachments, images)
    : studyLogsWithAttachments
  const exportedLlmAnalysis = includeSnapshots
    ? await extractLlmAnalysisImages(llmAnalysis, images)
    : cloneJson(llmAnalysis || null)
  const exportedCurrentState = includeSnapshots
    ? extractCurrentStateImages(currentState || {}, images)
    : cloneJson(currentState || {})

  const payload = {
    exportVersion: EXPORT_VERSION,
    exportFormat: 'maniscope-user-study-zip',
    exportedAt: new Date().toISOString(),
    sessionId: sessionId || null,
    sessionMode: sessionMode || 'specialized',
    coin: coin || null,
    includesSnapshots: !!includeSnapshots,
    imageDirectory: includeSnapshots ? 'images' : null,
    imageCount: images.length,
    config: {
      snapshotCategories: snapshotCategories ? cloneJson(snapshotCategories) : null,
      snapshotQuality: snapshotQuality || null,
    },
    annotationSeqId: Number.isFinite(annotationSeqId) ? annotationSeqId : 0,
    studyInfo: nextStudyInfo,
    analysisMilestones: cloneJson(analysisMilestones || []),
    llmAnalysisTrace: cloneJson(llmAnalysisTrace || []),
    llmAnalysis: exportedLlmAnalysis,
    currentState: exportedCurrentState,
    userActionSequence: actions,
    annotationRecords: annotations,
    chatbotLogs: studyLogs,
    derivedTables: {
      interactionTrace: normalizeInteractionTrace(actions, nextStudyInfo, sessionMode, coin, exportedCurrentState),
      userNotes: normalizeUserNotes(annotations),
      chatbotLogs: normalizeChatbotLogs(studyLogs, nextStudyInfo, sessionMode, coin),
      analysisMilestones: cloneJson(analysisMilestones || []),
      llmAnalysisTrace: normalizeLlmAnalysisTrace(llmAnalysisTrace, nextStudyInfo, sessionMode, coin),
    },
  }

  return { payload, images }
}

function pad2(n) {
  return n < 10 ? '0' + n : '' + n
}

function buildBaseFileName(coin) {
  const d = new Date()
  const stamp =
    d.getFullYear() +
    pad2(d.getMonth() + 1) +
    pad2(d.getDate()) +
    '-' +
    pad2(d.getHours()) +
    pad2(d.getMinutes()) +
    pad2(d.getSeconds())
  const coinPart = coin ? `-${coin}` : ''
  return `maniscope-session${coinPart}-${stamp}`
}

function buildZipFileName(coin) {
  return `${buildBaseFileName(coin)}.zip`
}

export function downloadZipArchive({ payload, images }, coin) {
  const json = JSON.stringify(payload, null, 2)
  const files = {
    'session.json': strToU8(json),
  }
  images.forEach((image) => {
    files[image.path] = image.bytes
  })
  const zipped = zipSync(files, { level: 0 })
  const blob = new Blob([zipped], { type: 'application/zip' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = buildZipFileName(coin)
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function validatePayload(obj) {
  if (!obj || typeof obj !== 'object') throw new Error('Invalid session file: not an object')
  if (!obj.exportVersion) throw new Error('Invalid session file: missing exportVersion')
  if (!Array.isArray(obj.userActionSequence))
    throw new Error('Invalid session file: userActionSequence must be an array')
  if (!Array.isArray(obj.annotationRecords))
    throw new Error('Invalid session file: annotationRecords must be an array')
}

function resolveImageDataUrl(imageSources, imagePath) {
  if (!imagePath || !imageSources || Object.keys(imageSources).length === 0) return ''
  const value = imageSources[imagePath]
  if (!value) return ''
  if (typeof value === 'string') return value
  if (value instanceof Uint8Array) return imageBytesToDataUrl(value, imagePath)
  return ''
}

function restoreReferencedImages(payload, imageSources) {
  if (!imageSources || Object.keys(imageSources).length === 0) return payload

  payload.userActionSequence = payload.userActionSequence.map((action) => {
    const copy = { ...action }
    ;['sourceSnapshot', 'targetSnapshot'].forEach((field) => {
      if (!Array.isArray(copy[field])) return
      copy[field] = copy[field].map((snapshot) => {
        if (!snapshot || !snapshot.imagePath) return snapshot
        const dataUrl = resolveImageDataUrl(imageSources, snapshot.imagePath)
        if (!dataUrl) return snapshot
        const s = { ...snapshot, dataUrl }
        delete s.imagePath
        return s
      })
    })
    return copy
  })

  payload.annotationRecords = payload.annotationRecords.map((anno) => {
    if (!anno.sketchImagePath) return anno
    const dataUrl = resolveImageDataUrl(imageSources, anno.sketchImagePath)
    if (!dataUrl) return anno
    const a = { ...anno, sketchDataUrl: dataUrl }
    delete a.sketchImagePath
    return a
  })

  return payload
}

export function normalizeImportPayload(parsed, imageSources = {}) {
  validatePayload(parsed)
  const payload = cloneJson(parsed)
  restoreReferencedImages(payload, imageSources)

  if (payload.currentState?.majorViewScreenshots) {
    Object.entries(payload.currentState.majorViewScreenshots).forEach(([viewName, imagePath]) => {
      const dataUrl = resolveImageDataUrl(imageSources, imagePath)
      if (dataUrl) payload.currentState.majorViewScreenshots[viewName] = dataUrl
    })
  }

  if (Array.isArray(payload.chatbotLogs)) {
    payload.chatbotLogs = payload.chatbotLogs.map((entry) => ({
      ...entry,
      promptAttachments: Array.isArray(entry.promptAttachments)
        ? entry.promptAttachments.map((attachment) => {
            if (!attachment?.imagePath) return attachment
            const dataUrl = resolveImageDataUrl(imageSources, attachment.imagePath)
            if (!dataUrl) return attachment
            return {
              ...attachment,
              dataUrl,
            }
          })
        : [],
      response: entry.response && typeof entry.response === 'object'
        ? {
            ...entry.response,
            artifacts: Array.isArray(entry.response.artifacts)
              ? entry.response.artifacts.map((artifact) => {
                  if (!artifact?.exportImagePath) return artifact
                  const dataUrl = resolveImageDataUrl(imageSources, artifact.exportImagePath)
                  if (!dataUrl) return artifact
                  return {
                    ...artifact,
                    dataUrl,
                    url: artifact.url || dataUrl,
                  }
                })
              : [],
          }
        : entry.response,
    }))
  }

  if (payload.llmAnalysis) {
    payload.llmAnalysis = restoreLlmAnalysisImages(payload.llmAnalysis, imageSources)
  }

  const maxAnnId = payload.annotationRecords.reduce(
    (m, a) => (Number.isFinite(a?.id) && a.id > m ? a.id : m),
    -1
  )
  return {
    userActionSequence: payload.userActionSequence,
    annotationRecords: payload.annotationRecords,
    annotationSeqId: Number.isFinite(payload.annotationSeqId)
      ? payload.annotationSeqId
      : maxAnnId + 1,
    studyInfo: payload.studyInfo || null,
    analysisMilestones: Array.isArray(payload.analysisMilestones) ? payload.analysisMilestones : [],
    chatbotLogs: Array.isArray(payload.chatbotLogs) ? payload.chatbotLogs : [],
    llmAnalysisTrace: Array.isArray(payload.llmAnalysisTrace) ? payload.llmAnalysisTrace : [],
    llmAnalysis: payload.llmAnalysis || null,
    currentState: payload.currentState || null,
    isPatchTraceOnlyForTesting: payload.isPatchTraceOnlyForTesting === true,
    meta: {
      exportVersion: payload.exportVersion,
      exportFormat: payload.exportFormat || null,
      exportedAt: payload.exportedAt || null,
      sessionId: payload.sessionId || null,
      sessionMode: payload.sessionMode || null,
      coin: payload.coin || null,
      includesSnapshots: !!payload.includesSnapshots,
      imageCount: Number.isFinite(payload.imageCount) ? payload.imageCount : 0,
      imageDirectory: payload.imageDirectory || null,
      config: payload.config || null,
      derivedTables: cloneJson(payload.derivedTables || {}),
    },
  }
}

export function parseImportFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('Failed to read file'))

    const processPayload = (parsed, imageSources) => {
      try {
        resolve(normalizeImportPayload(parsed, imageSources))
      } catch (err) {
        reject(err instanceof Error ? err : new Error(String(err)))
      }
    }

    if (file.name.endsWith('.zip') || file.type === 'application/zip') {
      reader.onload = () => {
        try {
          const arrayBuffer = reader.result
          const uint8 = new Uint8Array(arrayBuffer)
          const unzipped = unzipSync(uint8)

          const jsonEntry = unzipped['session.json']
          if (!jsonEntry) throw new Error('Invalid zip: missing session.json')
          const jsonText = new TextDecoder().decode(jsonEntry)
          const parsed = JSON.parse(jsonText)

          const imageSources = {}
          Object.keys(unzipped).forEach((key) => {
            if (key.startsWith('images/')) {
              imageSources[key] = unzipped[key]
            }
          })

          processPayload(parsed, imageSources)
        } catch (err) {
          reject(err instanceof Error ? err : new Error(String(err)))
        }
      }
      reader.readAsArrayBuffer(file)
    } else {
      reader.onload = () => {
        try {
          const parsed = JSON.parse(String(reader.result || ''))
          const imageSources = parsed && typeof parsed.images === 'object' && parsed.images
            ? parsed.images
            : {}
          processPayload(parsed, imageSources)
        } catch (err) {
          reject(err instanceof Error ? err : new Error(String(err)))
        }
      }
      reader.readAsText(file)
    }
  })
}
