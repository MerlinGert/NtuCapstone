import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { saveRenderResult, viewConfigForKey } from './agent-browser.mjs'

const SESSION_ID = 'abcde'
const PNG_DATA_URL = `data:image/png;base64,${Buffer.from([
  0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
]).toString('base64')}`

function makeSessionDir() {
  const sessionDir = fs.mkdtempSync(path.join(os.tmpdir(), 'maniscope-agent-browser-'))
  fs.mkdirSync(path.join(sessionDir, 'artifacts'), { recursive: true })
  return sessionDir
}

test('resolves known view endpoint keys', () => {
  assert.equal(viewConfigForKey('token-distribution').viewName, 'token_distribution')
  assert.equal(viewConfigForKey('kline').viewName, 'kline_chart')
  assert.equal(viewConfigForKey('behavior-details').viewName, 'behavior_details')
})

test('rejects unknown view endpoint keys', () => {
  assert.throws(() => viewConfigForKey('unknown'), /Unknown agent visualization view/)
})

test('saves render results as session artifacts', () => {
  const sessionDir = makeSessionDir()
  const result = saveRenderResult({
    sessionId: SESSION_ID,
    sessionDir,
    viewKey: 'kline',
    artifactName: 'Oct 26 K-Line.png',
    renderResult: {
      viewName: 'candlestick_chart',
      image: { dataUrl: PNG_DATA_URL, width: 1500, height: 850 },
      dependencies: { dataDependencies: [] },
      renderMetadata: { ok: true },
    },
  })

  assert.equal(result.artifactName, 'oct-26-k-line.png')
  assert.equal(result.artifactUrl, '/api/sessions/abcde/artifacts/oct-26-k-line.png')
  assert.equal(result.image.width, 1500)
  assert.ok(fs.existsSync(result.artifactPath))
})

test('does not overwrite existing artifacts', () => {
  const sessionDir = makeSessionDir()
  const first = saveRenderResult({
    sessionId: SESSION_ID,
    sessionDir,
    viewKey: 'token-distribution',
    artifactName: 'same.png',
    renderResult: { image: { dataUrl: PNG_DATA_URL } },
  })
  const second = saveRenderResult({
    sessionId: SESSION_ID,
    sessionDir,
    viewKey: 'token-distribution',
    artifactName: 'same.png',
    renderResult: { image: { dataUrl: PNG_DATA_URL } },
  })

  assert.equal(first.artifactName, 'same.png')
  assert.equal(second.artifactName, 'same-2.png')
})

test('rejects non-png render outputs and artifact extensions', () => {
  const sessionDir = makeSessionDir()
  assert.throws(
    () =>
      saveRenderResult({
        sessionId: SESSION_ID,
        sessionDir,
        viewKey: 'behavior-details',
        renderResult: { image: { dataUrl: 'data:image/jpeg;base64,abc=' } },
      }),
    /PNG data URL/,
  )
  assert.throws(
    () =>
      saveRenderResult({
        sessionId: SESSION_ID,
        sessionDir,
        viewKey: 'behavior-details',
        artifactName: 'bad.jpg',
        renderResult: { image: { dataUrl: PNG_DATA_URL } },
      }),
    /must use the .png extension/,
  )
})
