import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
export const FRONT_DIR = path.resolve(__dirname, '..')
export const REPO_ROOT = process.env.MANISCOPE_REPO_ROOT || path.resolve(FRONT_DIR, '..')
export const CODEX_AGENT_MODEL = 'gpt-5.5'
export const CODEX_AGENT_REASONING_EFFORT = 'xhigh'

export function rawDataDirectories(frontDir = FRONT_DIR) {
  return [
    path.join(frontDir, 'public', 'data'),
    path.join(frontDir, 'public', 'data2'),
  ]
}

export function buildThreadOptions(sessionDirectory) {
  if (!sessionDirectory || typeof sessionDirectory !== 'string') {
    throw new Error('sessionDirectory is required')
  }
  return {
    workingDirectory: sessionDirectory,
    skipGitRepoCheck: false,
    sandboxMode: 'workspace-write',
    approvalPolicy: 'never',
    model: CODEX_AGENT_MODEL,
    modelReasoningEffort: CODEX_AGENT_REASONING_EFFORT,
    networkAccessEnabled: true,
    webSearchMode: process.env.CODEX_WEB_SEARCH || 'disabled',
    additionalDirectories: rawDataDirectories(),
  }
}
