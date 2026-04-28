// ezio: session import/export utility for action/annotation/tree data
import { strToU8, zipSync, unzipSync } from 'fflate'

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
  const match = dataUrl.match(/^data:image\/png(;[^,]*)?,(.*)$/)
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
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes
}

function extractSnapshotImages(actions, images) {
  return actions.map((action, actionIndex) => {
    const copy = { ...action }
    ;['sourceSnapshot', 'targetSnapshot'].forEach((field) => {
      if (!Array.isArray(copy[field])) return
      copy[field] = copy[field].map((snapshot, snapshotIndex) => {
        if (!snapshot || !snapshot.dataUrl) return snapshot
        const bytes = dataUrlToBytes(snapshot.dataUrl)
        const imageName = [
          'action',
          String(actionIndex + 1).padStart(4, '0'),
          field === 'sourceSnapshot' ? 'source' : 'target',
          normalizeNamePart(snapshot.viewName || copy[field === 'sourceSnapshot' ? 'sourceView' : 'targetView']),
          String(snapshotIndex + 1).padStart(2, '0'),
        ].join('-') + '.png'
        const imagePath = `images/${imageName}`
        if (bytes) {
          images.push({
            path: imagePath,
            bytes,
            kind: field,
            actionIndex,
            snapshotIndex,
          })
        }
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
      if (bytes) {
        images.push({
          path: imagePath,
          bytes,
          kind: 'annotation',
          annotationIndex,
        })
      }
      copy.sketchImagePath = imagePath
    }
    delete copy.sketchDataUrl
    return copy
  })
}

export function buildExportArchive({
  coin,
  userActionSequence,
  annotationRecords,
  snapshotCategories,
  snapshotQuality,
  annotationSeqId,
  includeSnapshots,
}) {
  const images = []
  const actions = includeSnapshots
    ? extractSnapshotImages(cloneJson(userActionSequence), images)
    : stripSnapshotsFromActions(userActionSequence)
  const annotations = includeSnapshots
    ? extractAnnotationImages(cloneJson(annotationRecords), images)
    : stripSketchFromAnnotations(annotationRecords)

  const payload = {
    exportVersion: EXPORT_VERSION,
    exportFormat: 'zip-with-images',
    exportedAt: new Date().toISOString(),
    coin: coin || null,
    includesSnapshots: !!includeSnapshots,
    imageDirectory: includeSnapshots ? 'images' : null,
    imageCount: images.length,
    config: {
      snapshotCategories: snapshotCategories
        ? cloneJson(snapshotCategories)
        : null,
      snapshotQuality: snapshotQuality || null,
    },
    annotationSeqId: Number.isFinite(annotationSeqId) ? annotationSeqId : 0,
    userActionSequence: actions,
    annotationRecords: annotations,
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

export function parseImportFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('Failed to read file'))

    const uint8ToBase64 = (bytes) => {
      let binary = ''
      const chunkSize = 8192
      for (let i = 0; i < bytes.length; i += chunkSize) {
        binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize))
      }
      return btoa(binary)
    }

    const processPayload = (parsed, imageFiles) => {
      try {
        validatePayload(parsed)

        // Restore image dataUrls from zip image files if available
        if (imageFiles && Object.keys(imageFiles).length > 0) {
          // Restore snapshots in actions
          parsed.userActionSequence = parsed.userActionSequence.map((action) => {
            const copy = { ...action }
            ;['sourceSnapshot', 'targetSnapshot'].forEach((field) => {
              if (!Array.isArray(copy[field])) return
              copy[field] = copy[field].map((snapshot) => {
                if (!snapshot || !snapshot.imagePath) return snapshot
                const imgBytes = imageFiles[snapshot.imagePath]
                if (!imgBytes) return snapshot
                const b64 = uint8ToBase64(imgBytes)
                const s = { ...snapshot, dataUrl: `data:image/png;base64,${b64}` }
                delete s.imagePath
                return s
              })
            })
            return copy
          })

          // Restore sketchDataUrl in annotations
          parsed.annotationRecords = parsed.annotationRecords.map((anno) => {
            if (!anno.sketchImagePath) return anno
            const imgBytes = imageFiles[anno.sketchImagePath]
            if (!imgBytes) return anno
            const b64 = uint8ToBase64(imgBytes)
            const a = { ...anno, sketchDataUrl: `data:image/png;base64,${b64}` }
            delete a.sketchImagePath
            return a
          })
        }

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

          // Collect image files: keys that start with "images/"
          const imageFiles = {}
          Object.keys(unzipped).forEach((key) => {
            if (key.startsWith('images/')) {
              imageFiles[key] = unzipped[key]
            }
          })

          processPayload(parsed, imageFiles)
        } catch (err) {
          reject(err instanceof Error ? err : new Error(String(err)))
        }
      }
      reader.readAsArrayBuffer(file)
    } else {
      reader.onload = () => {
        try {
          const parsed = JSON.parse(String(reader.result || ''))
          processPayload(parsed, {})
        } catch (err) {
          reject(err instanceof Error ? err : new Error(String(err)))
        }
      }
      reader.readAsText(file)
    }
  })
}
