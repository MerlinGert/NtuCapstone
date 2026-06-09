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
  node codex-bridge/check-subagent-nesting.mjs [--session-id <id>]
  node codex-bridge/check-subagent-nesting.mjs --session-dir <path>

This starts a Codex SDK thread with the same ManiScope bridge thread options.
The top-level agent is asked to spawn one subagent, and that subagent is asked
to spawn one nested subagent. The script prints the final answer and streamed
item summaries so nested delegation support can be inspected manually.
`
}

function sessionDirectoryFromArgs(args) {
  if (args.sessionDir) return path.resolve(args.sessionDir)
  if (args.sessionId) return path.join(DEFAULT_SESSION_ROOT, args.sessionId)
  const stamp = new Date().toISOString().replace(/[^0-9]/g, '').slice(0, 14)
  return path.join(DEFAULT_SESSION_ROOT, `subagent-nesting-check-${stamp}`)
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

function nestingPrompt({ sessionDir }) {
  return `You are running a one-turn ManiScope Codex subagent nesting diagnostic.

Do not edit repository files. Do not create durable artifacts except small temporary files inside this session directory if a subagent needs them:

${sessionDir}

Your task is to test whether nested subagents work in this Codex runtime.

Instructions for the top-level agent:
1. Attempt to spawn exactly one L1 subagent using the available subagent tool, if it exists.
2. When spawning the L1 subagent, use fork_context: true only. Do not specify agent_type, model, reasoning_effort, or other configuration fields.
3. Give the L1 subagent this exact assignment:

"""
You are the L1 subagent in a nested-spawn diagnostic. Attempt to spawn exactly one L2 subagent using the available subagent tool, if it exists. Use fork_context: true only. Do not specify agent_type, model, reasoning_effort, or other configuration fields.

Ask the L2 subagent to reply with the exact sentinel NESTED_SUBAGENT_L2_OK and a one-sentence note saying whether it believes it is running as a nested subagent.

After the L2 subagent finishes, report whether you saw the sentinel NESTED_SUBAGENT_L2_OK. If you cannot spawn an L2 subagent because no subagent tool is available or the tool fails, report that explicitly.
"""

4. If no subagent tool is available at the top level, do not improvise. Report that explicitly.
5. Do not run unrelated commands.

Final response format:

Nested subagent spawn: PASS | FAIL | INCONCLUSIVE
Top-level subagent tool available: yes | no | unknown
L1 reported L2 sentinel: yes | no | unknown
Evidence:
- <brief concrete evidence, including any tool error text or subagent result text>`
}

function truncate(value, maxLength = 2000) {
  if (value == null) return value
  const text = typeof value === 'string' ? value : JSON.stringify(value)
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength)}... [truncated ${text.length - maxLength} chars]`
}

function summarizeItem(item) {
  if (!item || typeof item !== 'object') return item
  const summary = {}
  for (const key of [
    'type',
    'status',
    'title',
    'id',
    'itemId',
    'agent_id',
    'agentId',
    'command',
    'exit_code',
    'exitCode',
    'name',
    'role',
  ]) {
    if (item[key] !== undefined) summary[key] = item[key]
  }
  for (const key of [
    'text',
    'content',
    'finalResponse',
    'aggregated_output',
    'output',
    'error',
    'message',
  ]) {
    if (item[key] !== undefined) summary[key] = truncate(item[key])
  }
  if (Object.keys(summary).length === 0) {
    return JSON.parse(truncate(item, 2000))
  }
  return summary
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

  const threadOptions = buildThreadOptions(sessionDir)
  const codexOptions = buildCodexClientOptions()
  console.log('Starting Codex nested-subagent diagnostic with options:')
  console.log(JSON.stringify({
    codexOptions: {
      env: {
        UV_CACHE_DIR: codexOptions.env?.UV_CACHE_DIR,
      },
      config: codexOptions.config,
    },
    threadOptions,
  }, null, 2))

  const codex = new Codex(codexOptions)
  const thread = codex.startThread(threadOptions)
  const turn = await thread.run(nestingPrompt({ sessionDir }))

  console.log('\nCodex thread:', thread.id || '(thread id unavailable)')
  console.log('\nStream item summaries:')
  for (const [index, item] of (turn.items || []).entries()) {
    console.log(JSON.stringify({
      index,
      ...summarizeItem(item),
    }, null, 2))
  }

  console.log('\nFinal response:')
  console.log(turn.finalResponse || '(no final response)')
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error)
  process.exit(1)
})
