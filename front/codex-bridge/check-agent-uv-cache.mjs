#!/usr/bin/env node
import { Codex } from '@openai/codex-sdk'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  buildCodexClientOptions,
  buildThreadOptions,
  sharedUvCacheDirectory,
} from './thread-options.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FRONT_DIR = path.resolve(__dirname, '..')
const REPO_ROOT = path.resolve(FRONT_DIR, '..')
const DEFAULT_SESSION_ROOT = path.join(REPO_ROOT, '.maniscope-chat', 'sessions')

function parseArgs(argv) {
  const args = {
    sessionDir: null,
    sessionId: null,
  }
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    if (arg === '--session-dir') {
      args.sessionDir = argv[index + 1]
      index += 1
    } else if (arg === '--session-id') {
      args.sessionId = argv[index + 1]
      index += 1
    } else if (arg === '--help' || arg === '-h') {
      args.help = true
    } else {
      throw new Error(`Unknown argument: ${arg}`)
    }
  }
  return args
}

function usage() {
  return `Usage:
  node codex-bridge/check-agent-uv-cache.mjs [--session-id <id>]
  node codex-bridge/check-agent-uv-cache.mjs --session-dir <path>

This starts a Codex SDK thread with the same ManiScope bridge thread options and
asks that agent to probe whether it can write to the configured UV_CACHE_DIR.
`
}

function sessionDirectoryFromArgs(args) {
  if (args.sessionDir) return path.resolve(args.sessionDir)
  if (args.sessionId) return path.join(DEFAULT_SESSION_ROOT, args.sessionId)
  const stamp = new Date().toISOString().replace(/[^0-9]/g, '').slice(0, 14)
  return path.join(DEFAULT_SESSION_ROOT, `uv-cache-check-${stamp}`)
}

function ensureSessionDirectory(sessionDir) {
  fs.mkdirSync(sessionDir, { recursive: true })
  if (!fs.existsSync(path.join(sessionDir, '.git'))) {
    const result = spawnSync('git', ['init', '-q'], {
      cwd: sessionDir,
      encoding: 'utf8',
    })
    if (result.status !== 0) {
      throw new Error(`Failed to initialize git repo in ${sessionDir}: ${result.stderr || result.stdout}`)
    }
  }
}

function diagnosticPrompt({ sessionDir, cacheDir }) {
  const command = `node <<'NODE'
const child_process = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const cacheDir = process.env.UV_CACHE_DIR;
const result = {
  cwd: process.cwd(),
  home: os.homedir(),
  cacheDir,
  exists: fs.existsSync(cacheDir),
  isDirectory: false,
  canWrite: false,
  uvRunExit: null,
  uvRunOutput: null,
  errorCode: null,
  errorMessage: null,
};

try {
  const stat = fs.statSync(cacheDir);
  result.isDirectory = stat.isDirectory();
  const probePath = path.join(cacheDir, \`codex-uv-cache-probe-\${process.pid}-\${Date.now()}.tmp\`);
  fs.writeFileSync(probePath, 'uv cache probe\\n');
  fs.unlinkSync(probePath);
  result.canWrite = true;
} catch (error) {
  result.errorCode = error && error.code ? error.code : null;
  result.errorMessage = error && error.message ? error.message : String(error);
}

const uv = child_process.spawnSync('uv', [
  'run',
  'python',
  '-c',
  'import os; print(os.environ.get("UV_CACHE_DIR"))',
], { encoding: 'utf8' });
result.uvRunExit = uv.status;
result.uvRunOutput = (uv.stdout + uv.stderr).trim();

console.log('UV_CACHE_ACCESS_RESULT=' + JSON.stringify(result));
process.exit(result.canWrite && result.uvRunExit === 0 ? 0 : 2);
NODE`

  return `You are running a one-turn ManiScope Codex bridge diagnostic.

Do not edit project files. Do not create durable artifacts. Run this shell command exactly from the current working directory:

\`\`\`bash
${command}
\`\`\`

Then report whether the agent runtime can write to the uv cache directory.

Expected working directory: ${sessionDir}
Expected uv cache directory: ${cacheDir}
Final response format:
UV cache access: PASS or FAIL
<paste the UV_CACHE_ACCESS_RESULT JSON>`
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  if (args.help) {
    console.log(usage())
    return
  }

  const sessionDir = sessionDirectoryFromArgs(args)
  ensureSessionDirectory(sessionDir)
  fs.mkdirSync(sharedUvCacheDirectory(), { recursive: true })

  const options = buildThreadOptions(sessionDir)
  const codexOptions = buildCodexClientOptions()
  console.log('Starting Codex uv-cache diagnostic with options:')
  console.log(JSON.stringify({ codexOptions, threadOptions: options }, null, 2))

  const codex = new Codex(codexOptions)
  const thread = codex.startThread(options)
  const prompt = diagnosticPrompt({
    sessionDir,
    cacheDir: sharedUvCacheDirectory(),
  })
  const turn = await thread.run(prompt)

  console.log('\nCodex thread:', thread.id || '(thread id unavailable)')
  for (const item of turn.items || []) {
    if (item.type === 'command_execution') {
      console.log('\nCommand:', item.command)
      console.log(item.aggregated_output || '')
      console.log('Exit code:', item.exit_code)
    }
  }
  console.log('\nFinal response:')
  console.log(turn.finalResponse || '(no final response)')
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error)
  process.exit(1)
})
