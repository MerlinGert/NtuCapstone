import assert from 'node:assert/strict'
import test from 'node:test'
import {
  checkRequiredTools,
  commandExists,
  formatPreflightError,
  runStartupPreflight,
} from './preflight.mjs'
import { uvCacheDirectory } from './thread-options.mjs'

function fakeRunner(availableCommands) {
  return (command) => ({
    status: availableCommands.has(command) ? 0 : 127,
  })
}

test('commandExists checks executable availability', () => {
  assert.equal(commandExists('uv', { runner: fakeRunner(new Set(['uv'])) }), true)
  assert.equal(commandExists('codex', { runner: fakeRunner(new Set()) }), false)
})

test('preflight requires uv, codex, and one JavaScript package manager', () => {
  assert.deepEqual(
    checkRequiredTools({ runner: fakeRunner(new Set(['uv', 'codex', 'bun'])) }).missing,
    [],
  )
  assert.deepEqual(
    checkRequiredTools({ runner: fakeRunner(new Set(['uv', 'codex', 'npm'])) }).missing,
    [],
  )
  assert.deepEqual(
    checkRequiredTools({ runner: fakeRunner(new Set(['uv'])) }).missing,
    ['codex', 'jsRuntime'],
  )
})

test('preflight error includes installation hints and bridge PATH', () => {
  const message = formatPreflightError({
    missing: ['uv', 'codex', 'jsRuntime'],
    env: { PATH: '/custom/bin' },
  })

  assert.match(message, /Codex bridge startup preflight failed/)
  assert.match(message, /Install uv/)
  assert.match(message, /npm install -g @openai\/codex/)
  assert.match(message, /Install Bun/)
  assert.match(message, /PATH used by the bridge: \/custom\/bin/)
})

test('startup preflight creates uv cache directory and returns cache path', () => {
  const mkdirCalls = []
  const result = runStartupPreflight({
    runner: fakeRunner(new Set(['uv', 'codex', 'bun'])),
    mkdirSync: (dir, options) => {
      mkdirCalls.push({ dir, options })
    },
  })

  assert.equal(result.uvCacheDir, uvCacheDirectory())
  assert.deepEqual(mkdirCalls, [{ dir: uvCacheDirectory(), options: { recursive: true } }])
})

test('startup preflight throws a clear error when required tools are missing', () => {
  assert.throws(
    () =>
      runStartupPreflight({
        env: { PATH: '/missing' },
        runner: fakeRunner(new Set()),
        mkdirSync: () => {},
      }),
    /ManiScope Codex Chat requires these local tools/,
  )
})
