import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'

const IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.webp'])
const TEXT_ARTIFACT_EXTENSIONS = new Set(['.md', '.json'])
const SUPPORTED_ARTIFACT_EXTENSIONS = new Set([...IMAGE_EXTENSIONS, ...TEXT_ARTIFACT_EXTENSIONS])
const DEFAULT_MAX_IMAGE_BYTES = 25 * 1024 * 1024
const DEFAULT_MAX_TEXT_ARTIFACT_BYTES = 25 * 1024 * 1024
const MARKDOWN_REF_RE = /(!?)\[([^\]]*)\]\(([^)]*)\)/g
const BARE_ARTIFACT_PATH_RE =
  /(^|[\s([{"'=])((?:\/|\.{1,2}\/|[A-Za-z0-9_.-]+\/|[A-Za-z0-9_.-]+)[^\s<>"'`)]*?\.(?:png|jpe?g|webp|md|json))/gi
const CODE_BLOCK_OR_INLINE_RE = /(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`)/g

function safeNamePart(value) {
  return String(value || 'artifact')
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80) || 'artifact'
}

function pathInsideRoot(filePath, rootPath) {
  const relative = path.relative(rootPath, filePath)
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative))
}

function existingRealPath(filePath) {
  try {
    return fs.realpathSync.native(filePath)
  } catch {
    return null
  }
}

function existingRootRealPath(rootPath) {
  try {
    if (!path.isAbsolute(rootPath)) return null
    if (!fs.existsSync(rootPath)) return null
    return fs.realpathSync.native(rootPath)
  } catch {
    return null
  }
}

function parseExtraRoots(value) {
  return String(value || '')
    .split(path.delimiter)
    .map((entry) => entry.trim())
    .filter(Boolean)
}

function uniqueValues(values) {
  return Array.from(new Set(values.filter(Boolean)))
}

function imageKindForExtension(extension) {
  const normalized = extension.toLowerCase()
  if (normalized === '.png') return 'png'
  if (normalized === '.jpg' || normalized === '.jpeg') return 'jpg'
  if (normalized === '.webp') return 'webp'
  return ''
}

function extensionForImageKind(kind) {
  if (kind === 'jpg') return '.jpg'
  if (kind === 'webp') return '.webp'
  return '.png'
}

function artifactKindForExtension(extension) {
  const normalized = String(extension || '').toLowerCase()
  if (IMAGE_EXTENSIONS.has(normalized)) return 'image'
  if (normalized === '.md') return 'markdown'
  if (normalized === '.json') return 'json'
  return ''
}

function detectImageKind(filePath) {
  const fd = fs.openSync(filePath, 'r')
  try {
    const header = Buffer.alloc(12)
    const bytesRead = fs.readSync(fd, header, 0, header.length, 0)
    if (
      bytesRead >= 8 &&
      header[0] === 0x89 &&
      header[1] === 0x50 &&
      header[2] === 0x4e &&
      header[3] === 0x47 &&
      header[4] === 0x0d &&
      header[5] === 0x0a &&
      header[6] === 0x1a &&
      header[7] === 0x0a
    ) {
      return 'png'
    }
    if (bytesRead >= 3 && header[0] === 0xff && header[1] === 0xd8 && header[2] === 0xff) {
      return 'jpg'
    }
    if (
      bytesRead >= 12 &&
      header.toString('ascii', 0, 4) === 'RIFF' &&
      header.toString('ascii', 8, 12) === 'WEBP'
    ) {
      return 'webp'
    }
    return ''
  } finally {
    fs.closeSync(fd)
  }
}

function artifactObject(sessionDir, artifactName) {
  const filePath = path.join(sessionDir, 'artifacts', artifactName)
  const stat = fs.statSync(filePath)
  const kind = artifactKindForExtension(path.extname(artifactName)) || 'file'
  return {
    id: artifactName.replace(/[^a-zA-Z0-9_-]+/g, '-'),
    title: artifactName,
    kind,
    path: `artifacts/${artifactName}`,
    updatedAt: stat.mtime.toISOString(),
  }
}

function parseMarkdownDestination(rawDestination) {
  const raw = String(rawDestination || '').trim()
  if (!raw) return null
  if (raw.startsWith('<')) {
    const end = raw.indexOf('>')
    if (end > 1) {
      return {
        destination: raw.slice(1, end),
        suffix: raw.slice(end + 1),
      }
    }
  }
  const titleMatch = raw.match(/^(\S+)(\s+(?:"[^"]*"|'[^']*'|\([^)]*\)))?$/)
  if (titleMatch) {
    return {
      destination: titleMatch[1],
      suffix: titleMatch[2] || '',
    }
  }
  return {
    destination: raw,
    suffix: '',
  }
}

function isBrowserUrl(value) {
  const normalized = String(value || '').toLowerCase()
  return (
    normalized.startsWith('http://') ||
    normalized.startsWith('https://') ||
    normalized.startsWith('data:') ||
    normalized.startsWith('blob:') ||
    normalized.startsWith('/api/sessions/') ||
    normalized.startsWith('/api/base/sessions/')
  )
}

function isSupportedArtifactPath(value) {
  if (!value || isBrowserUrl(value)) return false
  return SUPPORTED_ARTIFACT_EXTENSIONS.has(path.extname(value).toLowerCase())
}

function removeUrlDecoration(value) {
  return String(value || '')
    .replace(/[?#].*$/, '')
    .trim()
}

function buildResolutionCandidates(reference, roots) {
  const cleaned = removeUrlDecoration(reference)
  if (!cleaned || isBrowserUrl(cleaned)) return []
  if (path.isAbsolute(cleaned)) return [cleaned]
  return roots.candidateRoots.map((root) => path.resolve(root, cleaned))
}

function normalizeRoots({ sessionDir, repoRoot, env = process.env, extraRoots = [] }) {
  const sessionArtifacts = path.join(sessionDir, 'artifacts')
  const sessionImages = path.join(sessionDir, 'images')
  const envArtifactRoots = parseExtraRoots(env.MANISCOPE_CHAT_ARTIFACT_ROOTS)
  const envImageRoots = parseExtraRoots(env.MANISCOPE_CHAT_IMAGE_ROOTS)
  const configuredExtraRoots = Array.isArray(extraRoots) ? extraRoots : parseExtraRoots(extraRoots)

  const candidateRoots = uniqueValues([sessionDir, sessionArtifacts, sessionImages, repoRoot])
  const allowedRootInputs = uniqueValues([
    sessionDir,
    repoRoot,
    ...configuredExtraRoots,
    ...envArtifactRoots,
    ...envImageRoots,
  ])
  const allowedRoots = uniqueValues(allowedRootInputs.map(existingRootRealPath))
  return { candidateRoots, allowedRoots }
}

function maxImageBytesFromEnv(env = process.env) {
  const parsed = Number(env.MANISCOPE_CHAT_MAX_IMAGE_BYTES)
  if (Number.isFinite(parsed) && parsed > 0) return parsed
  return DEFAULT_MAX_IMAGE_BYTES
}

function maxTextArtifactBytesFromEnv(env = process.env) {
  const parsed = Number(env.MANISCOPE_CHAT_MAX_ARTIFACT_BYTES)
  if (Number.isFinite(parsed) && parsed > 0) return parsed
  return DEFAULT_MAX_TEXT_ARTIFACT_BYTES
}

function createArtifactName(realPath, stat, extension) {
  const basename = path.basename(realPath, path.extname(realPath))
  const hash = crypto
    .createHash('sha256')
    .update(realPath)
    .update('\0')
    .update(String(stat.size))
    .update('\0')
    .update(String(stat.mtimeMs))
    .digest('hex')
    .slice(0, 16)
  return `${safeNamePart(basename)}-${hash}${extension}`
}

function directArtifactName(realPath, artifactsRealDir) {
  if (!artifactsRealDir) return null
  if (path.dirname(realPath) !== artifactsRealDir) return null
  return path.basename(realPath)
}

function validJsonFile(filePath) {
  try {
    JSON.parse(fs.readFileSync(filePath, 'utf8'))
    return true
  } catch {
    return false
  }
}

function artifactUrl(sessionId, artifactName, artifactUrlPrefix = null) {
  if (artifactUrlPrefix) {
    return `${artifactUrlPrefix.replace(/\/+$/, '')}/${encodeURIComponent(artifactName)}`
  }
  return `/api/sessions/${sessionId}/artifacts/${encodeURIComponent(artifactName)}`
}

function splitMarkdownProtectedSegments(text) {
  const segments = []
  let lastIndex = 0
  for (const match of String(text || '').matchAll(CODE_BLOCK_OR_INLINE_RE)) {
    if (match.index > lastIndex) {
      segments.push({ protected: false, text: text.slice(lastIndex, match.index) })
    }
    segments.push({ protected: true, text: match[0] })
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < text.length) segments.push({ protected: false, text: text.slice(lastIndex) })
  return segments
}

function makeMaterializer(options) {
  const sessionDir = options.sessionDir
  const artifactsDir = path.join(sessionDir, 'artifacts')
  const roots = normalizeRoots(options)
  const maxImageBytes = options.maxImageBytes || maxImageBytesFromEnv(options.env)
  const maxTextArtifactBytes =
    options.maxTextArtifactBytes || maxTextArtifactBytesFromEnv(options.env)
  const materializedByRealPath = new Map()
  const artifactsByName = new Map()

  fs.mkdirSync(artifactsDir, { recursive: true })
  const artifactsRealDir = existingRootRealPath(artifactsDir)

  const materializeReference = (reference) => {
    if (!isSupportedArtifactPath(reference)) return null

    for (const candidate of buildResolutionCandidates(reference, roots)) {
      if (!fs.existsSync(candidate)) continue
      const realPath = existingRealPath(candidate)
      if (!realPath) continue
      if (!roots.allowedRoots.some((root) => pathInsideRoot(realPath, root))) continue

      const stat = fs.statSync(realPath)
      if (!stat.isFile()) continue

      const extension = path.extname(candidate).toLowerCase()
      const artifactKind = artifactKindForExtension(extension)
      if (!artifactKind) continue
      let artifactExtension = extension

      if (artifactKind === 'image') {
        if (stat.size > maxImageBytes) continue
        const extensionKind = imageKindForExtension(extension)
        if (!extensionKind) continue
        const detectedKind = detectImageKind(realPath)
        if (!detectedKind || detectedKind !== extensionKind) continue
        artifactExtension = extensionForImageKind(detectedKind)
      } else {
        if (stat.size > maxTextArtifactBytes) continue
        if (artifactKind === 'json' && !validJsonFile(realPath)) continue
      }

      const cached = materializedByRealPath.get(realPath)
      if (cached) return cached

      const artifactName =
        directArtifactName(realPath, artifactsRealDir) ||
        createArtifactName(realPath, stat, artifactExtension)
      const artifactPath = path.join(artifactsDir, artifactName)
      if (realPath !== artifactPath && !fs.existsSync(artifactPath)) {
        fs.copyFileSync(realPath, artifactPath)
      }

      const artifact = artifactObject(sessionDir, artifactName)
      const result = {
        artifact,
        url: artifactUrl(options.sessionId, artifactName, options.artifactUrlPrefix),
      }
      materializedByRealPath.set(realPath, result)
      artifactsByName.set(artifactName, artifact)
      return result
    }
    return null
  }

  return {
    artifactsByName,
    materializeReference,
  }
}

function rewriteMarkdownReferences(segment, materializer) {
  return segment.replace(MARKDOWN_REF_RE, (fullMatch, bang, label, rawDestination) => {
    const parsed = parseMarkdownDestination(rawDestination)
    if (!parsed) return fullMatch
    const materialized = materializer.materializeReference(parsed.destination)
    if (!materialized) return fullMatch
    const marker = bang && materialized.artifact.kind === 'image' ? '!' : ''
    return `${marker}[${label}](${materialized.url}${parsed.suffix})`
  })
}

function collectBareArtifactReferences(segment, materializer, appendedReferences) {
  String(segment || '').replace(BARE_ARTIFACT_PATH_RE, (fullMatch, prefix, reference) => {
    const materialized = materializer.materializeReference(reference)
    if (materialized) appendedReferences.set(materialized.artifact.title, materialized)
    return fullMatch
  })
}

function appendBareArtifactReferences(segment, materializer, appendedReferences) {
  let lastIndex = 0
  String(segment || '').replace(MARKDOWN_REF_RE, (fullMatch, bang, label, rawDestination, offset) => {
    collectBareArtifactReferences(segment.slice(lastIndex, offset), materializer, appendedReferences)
    lastIndex = offset + fullMatch.length
    return fullMatch
  })
  collectBareArtifactReferences(segment.slice(lastIndex), materializer, appendedReferences)
}

function referencedArtifactsBlock(materializedReferences) {
  const references = Array.from(materializedReferences.values())
  if (references.length === 0) return ''
  const images = references.filter(({ artifact }) => artifact.kind === 'image')
  const files = references.filter(({ artifact }) => artifact.kind !== 'image')
  const sections = []
  if (images.length > 0) {
    sections.push(`Referenced images:\n\n${images.map(({ artifact, url }) => `![${artifact.title}](${url})`).join('\n\n')}`)
  }
  if (files.length > 0) {
    sections.push(`Referenced files:\n\n${files.map(({ artifact, url }) => `- [${artifact.title}](${url})`).join('\n')}`)
  }
  return `\n\n${sections.join('\n\n')}`
}

export function materializeLocalArtifactReferences(text, options) {
  const content = String(text || '')
  if (!content) return { text: content, artifacts: [] }

  const materializer = makeMaterializer(options)
  const appendedReferences = new Map()
  const rewritten = splitMarkdownProtectedSegments(content)
    .map((segment) => {
      if (segment.protected) return segment.text
      const markdownRewritten = rewriteMarkdownReferences(segment.text, materializer)
      appendBareArtifactReferences(markdownRewritten, materializer, appendedReferences)
      return markdownRewritten
    })
    .join('')

  const finalText = `${rewritten}${referencedArtifactsBlock(appendedReferences)}`
  return {
    text: finalText,
    artifacts: Array.from(materializer.artifactsByName.values()),
  }
}

export const materializeLocalImageReferences = materializeLocalArtifactReferences

export const testInternals = {
  artifactUrl,
  artifactKindForExtension,
  detectImageKind,
  imageKindForExtension,
  isSupportedArtifactPath,
  splitMarkdownProtectedSegments,
}
