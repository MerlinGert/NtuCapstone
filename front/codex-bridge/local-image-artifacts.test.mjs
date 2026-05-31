import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { materializeLocalArtifactReferences } from './local-image-artifacts.mjs'

const SESSION_ID = 'abcde'

const PNG_BYTES = Buffer.from([
  0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x00,
])
const JPG_BYTES = Buffer.from([0xff, 0xd8, 0xff, 0x00, 0x00, 0x00])
const WEBP_BYTES = Buffer.from('RIFF0000WEBP', 'ascii')

function makeFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'maniscope-chat-images-'))
  const repoRoot = path.join(root, 'repo')
  const sessionDir = path.join(root, 'sessions', SESSION_ID)
  fs.mkdirSync(path.join(sessionDir, 'images'), { recursive: true })
  fs.mkdirSync(path.join(sessionDir, 'artifacts'), { recursive: true })
  fs.mkdirSync(repoRoot, { recursive: true })
  return { root, repoRoot, sessionDir }
}

function writeFile(filePath, bytes = PNG_BYTES) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true })
  fs.writeFileSync(filePath, bytes)
  return filePath
}

function materialize(text, fixture, extra = {}) {
  return materializeLocalArtifactReferences(text, {
    sessionId: SESSION_ID,
    sessionDir: fixture.sessionDir,
    repoRoot: fixture.repoRoot,
    env: {},
    ...extra,
  })
}

test('rewrites markdown image absolute paths under the repo root', () => {
  const fixture = makeFixture()
  const imagePath = writeFile(path.join(fixture.repoRoot, 'analysis-results', 'chart.png'))

  const result = materialize(`Here is it: ![chart](${imagePath})`, fixture)

  assert.match(result.text, /!\[chart\]\(\/api\/sessions\/abcde\/artifacts\/chart-[a-f0-9]{16}\.png\)/)
  assert.equal(result.artifacts.length, 1)
  assert.equal(result.artifacts[0].kind, 'image')
  assert.ok(fs.existsSync(path.join(fixture.sessionDir, result.artifacts[0].path)))
})

test('resolves relative paths from session images and artifacts', () => {
  const fixture = makeFixture()
  writeFile(path.join(fixture.sessionDir, 'images', 'current.png'))
  writeFile(path.join(fixture.sessionDir, 'artifacts', 'existing.webp'), WEBP_BYTES)

  const result = materialize('![current](images/current.png)\n![existing](existing.webp)', fixture)

  assert.match(result.text, /!\[current\]\(\/api\/sessions\/abcde\/artifacts\/current-[a-f0-9]{16}\.png\)/)
  assert.match(result.text, /!\[existing\]\(\/api\/sessions\/abcde\/artifacts\/existing\.webp\)/)
  assert.equal(result.artifacts.length, 2)
})

test('keeps bare paths in prose and appends referenced images', () => {
  const fixture = makeFixture()
  writeFile(path.join(fixture.sessionDir, 'images', 'view.png'))

  const result = materialize('See images/view.png for the rendered view.', fixture)

  assert.match(result.text, /^See images\/view\.png for the rendered view\./)
  assert.match(result.text, /Referenced images:/)
  assert.match(result.text, /!\[view-[a-f0-9]{16}\.png\]\(\/api\/sessions\/abcde\/artifacts\/view-[a-f0-9]{16}\.png\)/)
  assert.equal(result.artifacts.length, 1)
})

test('rewrites markdown and json links to session artifact URLs', () => {
  const fixture = makeFixture()
  writeFile(path.join(fixture.sessionDir, 'artifacts', 'report.md'), '# Report\n')
  writeFile(path.join(fixture.sessionDir, 'artifacts', 'graph.json'), '{"nodes":[]}\n')

  const result = materialize(
    `Saved: [report.md](${path.join(fixture.sessionDir, 'artifacts', 'report.md')}) and [graph.json](graph.json)`,
    fixture,
  )

  assert.match(result.text, /\[report\.md\]\(\/api\/sessions\/abcde\/artifacts\/report\.md\)/)
  assert.match(result.text, /\[graph\.json\]\(\/api\/sessions\/abcde\/artifacts\/graph\.json\)/)
  assert.doesNotMatch(result.text, /Referenced files:/)
  assert.deepEqual(
    result.artifacts.map((artifact) => artifact.kind).sort(),
    ['json', 'markdown'],
  )
})

test('keeps bare markdown and json paths in prose and appends referenced files', () => {
  const fixture = makeFixture()
  writeFile(path.join(fixture.sessionDir, 'artifacts', 'report.md'), '# Report\n')
  writeFile(path.join(fixture.sessionDir, 'artifacts', 'graph.json'), '{"nodes":[]}\n')

  const result = materialize('Saved outputs:\n- report.md\n- graph.json', fixture)

  assert.match(result.text, /^Saved outputs:\n- report\.md\n- graph\.json/)
  assert.match(result.text, /Referenced files:/)
  assert.match(result.text, /- \[report\.md\]\(\/api\/sessions\/abcde\/artifacts\/report\.md\)/)
  assert.match(result.text, /- \[graph\.json\]\(\/api\/sessions\/abcde\/artifacts\/graph\.json\)/)
  assert.equal(result.artifacts.length, 2)
})

test('leaves external and existing artifact URLs unchanged', () => {
  const fixture = makeFixture()
  const text = [
    '![external](https://example.com/a.png)',
    '![artifact](/api/sessions/abcde/artifacts/already.png)',
    '![baseline](/api/base/sessions/abcde/artifacts/already.png)',
    '[external link](http://example.com/b.webp)',
  ].join('\n')

  const result = materialize(text, fixture)

  assert.equal(result.text, text)
  assert.equal(result.artifacts.length, 0)
})

test('can rewrite local references with a baseline artifact URL prefix', () => {
  const fixture = makeFixture()
  const reportPath = writeFile(path.join(fixture.repoRoot, 'baseline-report.md'), '# Report\n')

  const result = materialize(`[report](${reportPath})`, fixture, {
    artifactUrlPrefix: '/api/base/sessions/abcde/artifacts',
  })

  assert.match(result.text, /\[report\]\(\/api\/base\/sessions\/abcde\/artifacts\/baseline-report-[a-f0-9]{16}\.md\)/)
  assert.equal(result.artifacts.length, 1)
  assert.equal(result.artifacts[0].kind, 'markdown')
})

test('skips inline code and fenced code blocks', () => {
  const fixture = makeFixture()
  writeFile(path.join(fixture.sessionDir, 'images', 'code.png'))
  const text = [
    '`images/code.png`',
    '```md',
    '![code](images/code.png)',
    '```',
  ].join('\n')

  const result = materialize(text, fixture)

  assert.equal(result.text, text)
  assert.equal(result.artifacts.length, 0)
})

test('rejects absolute paths outside allowed roots', () => {
  const fixture = makeFixture()
  const outside = writeFile(path.join(fixture.root, 'outside.png'))

  const result = materialize(`![outside](${outside})`, fixture)

  assert.equal(result.text, `![outside](${outside})`)
  assert.equal(result.artifacts.length, 0)
})

test('rejects symlink escapes from allowed roots', { skip: process.platform === 'win32' }, () => {
  const fixture = makeFixture()
  const outside = writeFile(path.join(fixture.root, 'outside.png'))
  const symlinkPath = path.join(fixture.repoRoot, 'linked.png')
  fs.symlinkSync(outside, symlinkPath)

  const result = materialize(`![linked](${symlinkPath})`, fixture)

  assert.equal(result.text, `![linked](${symlinkPath})`)
  assert.equal(result.artifacts.length, 0)
})

test('rejects unsupported extensions and mismatched magic bytes', () => {
  const fixture = makeFixture()
  writeFile(path.join(fixture.repoRoot, 'not-image.gif'))
  writeFile(path.join(fixture.repoRoot, 'mismatch.png'), JPG_BYTES)
  writeFile(path.join(fixture.repoRoot, 'bad.json'), '{')

  const text = '![gif](not-image.gif)\n![mismatch](mismatch.png)\n[bad](bad.json)'
  const result = materialize(text, fixture)

  assert.equal(result.text, text)
  assert.equal(result.artifacts.length, 0)
})

test('deduplicates repeated references to the same image', () => {
  const fixture = makeFixture()
  writeFile(path.join(fixture.sessionDir, 'images', 'repeat.jpg'), JPG_BYTES)

  const result = materialize('![a](images/repeat.jpg)\n![b](images/repeat.jpg)\nimages/repeat.jpg', fixture)

  assert.equal(result.artifacts.length, 1)
  assert.equal((result.text.match(/\/api\/sessions\/abcde\/artifacts\//g) || []).length, 3)
})

test('allows explicitly configured extra image roots', () => {
  const fixture = makeFixture()
  const extraRoot = path.join(fixture.root, 'external-root')
  const imagePath = writeFile(path.join(extraRoot, 'external.png'))

  const result = materialize(`![external](${imagePath})`, fixture, {
    extraRoots: [extraRoot],
  })

  assert.match(result.text, /\/api\/sessions\/abcde\/artifacts\/external-[a-f0-9]{16}\.png/)
  assert.equal(result.artifacts.length, 1)
})
