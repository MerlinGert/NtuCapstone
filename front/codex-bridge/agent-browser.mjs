import fs from 'node:fs'
import path from 'node:path'

export const DEFAULT_FRONTEND_URL = 'http://127.0.0.1:3099'

const PNG_DATA_URL_RE = /^data:image\/png;base64,([a-zA-Z0-9+/=]+)$/i

const VIEW_CONFIGS = {
  'token-distribution': {
    viewName: 'token_distribution',
    renderFunction: 'renderTokenDistributionView',
    fallbackArtifactName: 'token-distribution.png',
  },
  kline: {
    viewName: 'kline_chart',
    renderFunction: 'renderCandlestickView',
    fallbackArtifactName: 'kline-chart.png',
  },
  'behavior-details': {
    viewName: 'behavior_details',
    renderFunction: 'renderBehaviorDetailsView',
    fallbackArtifactName: 'behavior-details.png',
  },
}

function httpError(message, statusCode = 500) {
  const error = new Error(message)
  error.statusCode = statusCode
  return error
}

function safeNamePart(value) {
  return String(value || 'artifact')
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 90) || 'artifact'
}

function splitArtifactName(value, fallbackName) {
  const raw = String(value || fallbackName || 'artifact.png')
  const extension = path.extname(raw).toLowerCase()
  const basename = path.basename(raw, path.extname(raw))
  if (extension && extension !== '.png') {
    throw httpError('Rendered visualization artifacts must use the .png extension', 400)
  }
  return `${safeNamePart(basename)}.png`
}

function timestampSuffix() {
  return new Date().toISOString().replace(/[:.]/g, '-')
}

function uniqueArtifactName(artifactsDir, requestedName, fallbackName) {
  const baseName = requestedName
    ? splitArtifactName(requestedName, fallbackName)
    : splitArtifactName(`${path.basename(fallbackName, '.png')}-${timestampSuffix()}.png`)
  const extension = path.extname(baseName)
  const stem = path.basename(baseName, extension)
  let candidate = baseName
  let index = 2
  while (fs.existsSync(path.join(artifactsDir, candidate))) {
    candidate = `${stem}-${index}${extension}`
    index += 1
  }
  return candidate
}

function artifactUrl(sessionId, artifactName) {
  return `/api/sessions/${sessionId}/artifacts/${encodeURIComponent(artifactName)}`
}

function pngBufferFromDataUrl(dataUrl) {
  const match = String(dataUrl || '').match(PNG_DATA_URL_RE)
  if (!match) {
    throw httpError('Render result did not contain a PNG data URL', 502)
  }
  return Buffer.from(match[1], 'base64')
}

export function viewConfigForKey(viewKey) {
  const config = VIEW_CONFIGS[viewKey]
  if (!config) {
    throw httpError(`Unknown agent visualization view: ${viewKey}`, 400)
  }
  return config
}

export function saveRenderResult({
  sessionId,
  sessionDir,
  viewKey,
  renderResult,
  artifactName = null,
}) {
  const config = viewConfigForKey(viewKey)
  const dataUrl = renderResult?.image?.dataUrl
  const pngBuffer = pngBufferFromDataUrl(dataUrl)
  const artifactsDir = path.join(sessionDir, 'artifacts')
  fs.mkdirSync(artifactsDir, { recursive: true })

  const safeArtifactName = uniqueArtifactName(
    artifactsDir,
    artifactName,
    config.fallbackArtifactName,
  )
  const artifactPath = path.join(artifactsDir, safeArtifactName)
  fs.writeFileSync(artifactPath, pngBuffer)

  const response = {
    sessionId,
    viewKey,
    viewName: renderResult.viewName || config.viewName,
    artifactName: safeArtifactName,
    artifactPath,
    artifactUrl: artifactUrl(sessionId, safeArtifactName),
    image: {
      viewName: renderResult?.image?.viewName || config.viewName,
      width: renderResult?.image?.width ?? null,
      height: renderResult?.image?.height ?? null,
    },
    dependencies: renderResult?.dependencies || null,
    renderMetadata: renderResult?.renderMetadata || null,
  }
  if (renderResult?.renderArgs) {
    response.renderArgs = renderResult.renderArgs
  }
  return response
}

export class AgentBrowserManager {
  constructor({
    frontendUrl = process.env.MANISCOPE_FRONTEND_URL || DEFAULT_FRONTEND_URL,
    navigationTimeoutMs = Number(process.env.MANISCOPE_AGENT_BROWSER_TIMEOUT_MS || 60000),
  } = {}) {
    this.frontendUrl = String(frontendUrl || DEFAULT_FRONTEND_URL).replace(/\/+$/, '')
    this.navigationTimeoutMs = navigationTimeoutMs
    this.browserPromise = null
    this.pages = new Map()
    this.queues = new Map()
  }

  async health(sessionId) {
    return this.runQueued(sessionId, async () => {
      const page = await this.ensurePage(sessionId)
      const apiInfo = await page.evaluate(() => {
        const api = window.maniScopeMajorViewApi
        return {
          ready: !!api,
          views: Array.isArray(api?.views) ? api.views : [],
        }
      })
      return {
        ok: apiInfo.ready,
        sessionId,
        frontendUrl: this.pageUrl(sessionId),
        views: apiInfo.views,
      }
    })
  }

  async getCurrentArgs(sessionId, viewKey, options = {}) {
    const config = viewConfigForKey(viewKey)
    return this.runQueued(sessionId, async () => {
      const page = await this.ensurePage(sessionId)
      return page.evaluate(
        async ({ viewName, options: renderOptions }) => {
          const api = window.maniScopeMajorViewApi
          if (!api) throw new Error('ManiScope major view API is not ready')
          if (typeof api.ensureReady === 'function') {
            await api.ensureReady(viewName, renderOptions || {})
          }
          return api.getRenderArgs(viewName, renderOptions || {})
        },
        { viewName: config.viewName, options },
      )
    })
  }

  async renderViewToArtifact({
    sessionId,
    sessionDir,
    viewKey,
    args,
    options = {},
    artifactName = null,
  }) {
    const config = viewConfigForKey(viewKey)
    if (!args || typeof args !== 'object' || Array.isArray(args)) {
      throw httpError('render args must be an object', 400)
    }
    return this.runQueued(sessionId, async () => {
      const page = await this.ensurePage(sessionId)
      const renderResult = await page.evaluate(
        async ({ viewName, renderFunction, args: renderArgs, options: renderOptions }) => {
          const api = window.maniScopeMajorViewApi
          if (!api) throw new Error('ManiScope major view API is not ready')
          if (typeof api.ensureReady === 'function') {
            await api.ensureReady(viewName, renderOptions || {})
          }
          const render = api[renderFunction]
          if (typeof render !== 'function') {
            throw new Error(`Render function ${renderFunction} is not available`)
          }
          return render(renderArgs, renderOptions || {})
        },
        {
          viewName: config.viewName,
          renderFunction: config.renderFunction,
          args,
          options,
        },
      )
      return saveRenderResult({
        sessionId,
        sessionDir,
        viewKey,
        renderResult,
        artifactName,
      })
    })
  }

  async close() {
    for (const page of this.pages.values()) {
      await page.close().catch(() => {})
    }
    this.pages.clear()
    const browser = await this.browserPromise?.catch(() => null)
    this.browserPromise = null
    await browser?.close?.().catch(() => {})
  }

  pageUrl(sessionId) {
    return `${this.frontendUrl}/${sessionId}/agent`
  }

  async runQueued(sessionId, task) {
    const previous = this.queues.get(sessionId) || Promise.resolve()
    const current = previous.catch(() => {}).then(task)
    this.queues.set(sessionId, current.catch(() => {}))
    return current
  }

  async ensureBrowser() {
    if (!this.browserPromise) {
      this.browserPromise = import('playwright')
        .then(({ chromium }) =>
          chromium.launch({
            headless: true,
          }),
        )
        .catch((error) => {
          this.browserPromise = null
          throw httpError(
            `Unable to launch Playwright Chromium for agent rendering. Run "bunx playwright install chromium" in front/ if browsers are missing. ${error?.message || error}`,
            503,
          )
        })
    }
    return this.browserPromise
  }

  async ensurePage(sessionId) {
    const cached = this.pages.get(sessionId)
    if (cached && !cached.isClosed()) {
      const ready = await cached
        .evaluate(() => !!window.maniScopeMajorViewApi)
        .catch(() => false)
      if (ready) return cached
      await cached.close().catch(() => {})
      this.pages.delete(sessionId)
    }

    const browser = await this.ensureBrowser()
    const page = await browser.newPage({
      viewport: { width: 1600, height: 1000 },
    })
    page.setDefaultTimeout(this.navigationTimeoutMs)
    page.setDefaultNavigationTimeout(this.navigationTimeoutMs)
    page.on('close', () => {
      if (this.pages.get(sessionId) === page) this.pages.delete(sessionId)
    })
    page.on('crash', () => {
      if (this.pages.get(sessionId) === page) this.pages.delete(sessionId)
    })

    try {
      await page.goto(this.pageUrl(sessionId), {
        waitUntil: 'domcontentloaded',
        timeout: this.navigationTimeoutMs,
      })
      await page.waitForFunction(
        () => !!window.maniScopeMajorViewApi && Array.isArray(window.maniScopeMajorViewApi.views),
        null,
        { timeout: this.navigationTimeoutMs },
      )
    } catch (error) {
      await page.close().catch(() => {})
      throw error
    }
    this.pages.set(sessionId, page)
    return page
  }
}
