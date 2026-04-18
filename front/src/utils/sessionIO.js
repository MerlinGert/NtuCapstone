// ezio: session import/export utility for action/annotation/tree data

const EXPORT_VERSION = '1.0'

function stripSnapshotsFromActions(actions) {
  return actions.map((a) => {
    const copy = { ...a }
    delete copy.sourceSnapshot
    delete copy.targetSnapshot
    return copy
  })
}

function stripSketchFromAnnotations(annotations) {
  return annotations.map((a) => ({ ...a, sketchDataUrl: null }))
}

export function buildExportPayload({
  coin,
  userActionSequence,
  annotationRecords,
  snapshotCategories,
  snapshotQuality,
  annotationSeqId,
  includeSnapshots,
}) {
  const actions = includeSnapshots
    ? JSON.parse(JSON.stringify(userActionSequence))
    : stripSnapshotsFromActions(userActionSequence)
  const annotations = includeSnapshots
    ? JSON.parse(JSON.stringify(annotationRecords))
    : stripSketchFromAnnotations(annotationRecords)

  return {
    exportVersion: EXPORT_VERSION,
    exportedAt: new Date().toISOString(),
    coin: coin || null,
    includesSnapshots: !!includeSnapshots,
    config: {
      snapshotCategories: snapshotCategories
        ? JSON.parse(JSON.stringify(snapshotCategories))
        : null,
      snapshotQuality: snapshotQuality || null,
    },
    annotationSeqId: Number.isFinite(annotationSeqId) ? annotationSeqId : 0,
    userActionSequence: actions,
    annotationRecords: annotations,
  }
}

function pad2(n) {
  return n < 10 ? '0' + n : '' + n
}

function buildFileName(coin) {
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
  return `maniscope-session${coinPart}-${stamp}.json`
}

export function downloadJsonFile(payload, coin) {
  const json = JSON.stringify(payload, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = buildFileName(coin)
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  // revoke after a tick so Safari can finish the download
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

export function parseImportFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('Failed to read file'))
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result || ''))
        validatePayload(parsed)
        const maxAnnId = parsed.annotationRecords.reduce(
          (m, a) => (Number.isFinite(a?.id) && a.id > m ? a.id : m),
          -1
        )
        resolve({
          userActionSequence: parsed.userActionSequence,
          annotationRecords: parsed.annotationRecords,
          annotationSeqId: Number.isFinite(parsed.annotationSeqId)
            ? parsed.annotationSeqId
            : maxAnnId + 1,
          meta: {
            exportVersion: parsed.exportVersion,
            exportedAt: parsed.exportedAt || null,
            coin: parsed.coin || null,
            includesSnapshots: !!parsed.includesSnapshots,
            config: parsed.config || null,
          },
        })
      } catch (err) {
        reject(err instanceof Error ? err : new Error(String(err)))
      }
    }
    reader.readAsText(file)
  })
}

