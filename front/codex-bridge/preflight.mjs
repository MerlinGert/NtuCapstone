import fs from 'node:fs'
import { spawnSync } from 'node:child_process'
import { sharedUvCacheDirectory } from './thread-options.mjs'

const INSTALLATION_HINTS = {
  uv: 'Install uv: https://docs.astral.sh/uv/getting-started/installation/',
  codex: 'Install Codex CLI with npm install -g @openai/codex or brew install --cask codex, then run codex to authenticate.',
  jsRuntime: 'Install Bun from https://bun.sh/docs/installation or install Node.js/npm from https://nodejs.org/',
}

export function commandExists(command, { env = process.env, runner = spawnSync } = {}) {
  const result = runner(command, ['--version'], {
    env,
    encoding: 'utf8',
    stdio: 'ignore',
  })
  return result.status === 0
}

export function checkRequiredTools({ env = process.env, runner = spawnSync } = {}) {
  const missing = []
  if (!commandExists('uv', { env, runner })) missing.push('uv')
  if (!commandExists('codex', { env, runner })) missing.push('codex')

  const hasBun = commandExists('bun', { env, runner })
  const hasNpm = commandExists('npm', { env, runner })
  if (!hasBun && !hasNpm) missing.push('jsRuntime')

  return {
    missing,
    hasBun,
    hasNpm,
  }
}

export function formatPreflightError({ missing, env = process.env }) {
  const lines = [
    'Codex bridge startup preflight failed.',
    '',
    'ManiScope Codex Chat requires these local tools before the bridge can start:',
  ]

  for (const key of missing) {
    if (key === 'jsRuntime') {
      lines.push('- one of: bun or npm')
    } else {
      lines.push(`- ${key}`)
    }
  }

  lines.push('', 'Installation instructions:')
  for (const key of missing) {
    lines.push(`- ${INSTALLATION_HINTS[key]}`)
  }
  lines.push('', `PATH used by the bridge: ${env.PATH || '(empty)'}`)

  return lines.join('\n')
}

export function ensureUvCacheDirectory({ mkdirSync = fs.mkdirSync } = {}) {
  const cacheDir = sharedUvCacheDirectory()
  mkdirSync(cacheDir, { recursive: true })
  return cacheDir
}

export function runStartupPreflight({ env = process.env, runner = spawnSync, mkdirSync = fs.mkdirSync } = {}) {
  const uvCacheDir = ensureUvCacheDirectory({ mkdirSync })
  const result = checkRequiredTools({ env, runner })
  if (result.missing.length > 0) {
    throw new Error(formatPreflightError({ missing: result.missing, env }))
  }
  return {
    ...result,
    uvCacheDir,
  }
}
