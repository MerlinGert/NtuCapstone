import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { buildThreadOptions, rawDataDirectories, uvCacheDirectory } from './thread-options.mjs'

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

test('adds ACT, PNUT, and uv cache directories', () => {
  const frontDir = '/tmp/maniscope/front'
  const dirs = rawDataDirectories(frontDir)

  assert.deepEqual(dirs, [
    path.join(frontDir, 'public', 'data'),
    path.join(frontDir, 'public', 'data2'),
  ])
  assert.deepEqual(buildThreadOptions('/tmp/session').additionalDirectories, [
    ...rawDataDirectories(),
    uvCacheDirectory(),
  ])
})

test('does not allow caller to omit the session directory', () => {
  assert.throws(() => buildThreadOptions(), /sessionDirectory is required/)
})
