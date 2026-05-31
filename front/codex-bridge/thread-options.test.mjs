import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import {
  buildCodexClientOptions,
  buildThreadOptions,
  rawDataDirectories,
  sharedUvCacheDirectory,
} from './thread-options.mjs'

test('builds specialized thread options with session directory as workspace', () => {
  const sessionDir = '/tmp/maniscope/.maniscope-chat/sessions/abcde'
  const options = buildThreadOptions(sessionDir)

  assert.equal(options.workingDirectory, sessionDir)
  assert.equal(options.sandboxMode, 'workspace-write')
  assert.equal(options.approvalPolicy, 'never')
  assert.equal(options.model, 'gpt-5.5')
  assert.equal(options.modelReasoningEffort, 'xhigh')
  assert.equal(options.networkAccessEnabled, true)
})

test('builds baseline thread options with baseline session directory as workspace', () => {
  const sessionDir = '/tmp/maniscope/.maniscope-chat/baseline-sessions/abcde'
  const options = buildThreadOptions(sessionDir)

  assert.equal(options.workingDirectory, sessionDir)
  assert.equal(options.sandboxMode, 'workspace-write')
  assert.equal(options.networkAccessEnabled, true)
})

test('adds only raw data directories as additional directories', () => {
  const frontDir = '/tmp/maniscope/front'
  const dirs = rawDataDirectories(frontDir)

  assert.deepEqual(dirs, [
    path.join(frontDir, 'public', 'data'),
    path.join(frontDir, 'public', 'data2'),
  ])
  assert.deepEqual(buildThreadOptions('/tmp/session').additionalDirectories, rawDataDirectories())
})

test('builds Codex client options with repo-local uv cache writable root', () => {
  const repoRoot = '/tmp/maniscope'
  const options = buildCodexClientOptions({
    env: { PATH: '/bin', UV_CACHE_DIR: '/old/cache' },
    repoRoot,
  })
  const uvCacheDir = sharedUvCacheDirectory(repoRoot)

  assert.equal(options.env.PATH, '/bin')
  assert.equal(options.env.UV_CACHE_DIR, uvCacheDir)
  assert.deepEqual(options.config.sandbox_workspace_write.writable_roots, [uvCacheDir])
  assert.equal(options.config.sandbox_workspace_write.network_access, true)
})

test('does not allow caller to omit the session directory', () => {
  assert.throws(() => buildThreadOptions(), /sessionDirectory is required/)
})
