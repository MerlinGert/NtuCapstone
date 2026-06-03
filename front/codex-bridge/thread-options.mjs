import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
export const FRONT_DIR = path.resolve(__dirname, '..')
export const REPO_ROOT = process.env.MANISCOPE_REPO_ROOT || path.resolve(FRONT_DIR, '..')
export const CODEX_AGENT_MODEL = 'gpt-5.5'
export const CODEX_AGENT_REASONING_EFFORT = 'xhigh'
export const CODEX_AGENT_SERVICE_TIER = 'fast'

export function sharedUvCacheDirectory(repoRoot = REPO_ROOT) {
  return path.join(repoRoot, '.maniscope-chat', 'shared-uv-cache')
}

export function rawDataDirectories(frontDir = FRONT_DIR) {
  return [
    path.join(frontDir, 'public', 'data'),
    path.join(frontDir, 'public', 'data2'),
  ]
}

export function agentAdditionalDirectories() {
  return rawDataDirectories()
}

export function buildCodexClientOptions({
  env = process.env,
  repoRoot = REPO_ROOT,
} = {}) {
  const uvCacheDir = sharedUvCacheDirectory(repoRoot)
  return {
    env: {
      ...env,
      UV_CACHE_DIR: uvCacheDir,
    },
    config: {
      service_tier: CODEX_AGENT_SERVICE_TIER,
      sandbox_workspace_write: {
        writable_roots: [uvCacheDir],
        network_access: true,
      },
    },
  }
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
    additionalDirectories: agentAdditionalDirectories(),
  }
}
