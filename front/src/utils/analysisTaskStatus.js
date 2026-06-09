export const ACTIVE_ANALYSIS_TASK_STATUSES = new Set(['starting', 'running', 'stopping'])

export function isActiveAnalysisTaskStatus(status) {
  return ACTIVE_ANALYSIS_TASK_STATUSES.has(String(status || ''))
}

export function analysisTaskModeLabel(mode) {
  return String(mode || '') === 'incremental' ? 'Update analysis' : 'Full analysis'
}

export function analysisTaskStatusLabel({ status, mode } = {}) {
  const normalizedStatus = String(status || '')
  const modeLabel = analysisTaskModeLabel(mode)
  if (normalizedStatus === 'starting') return mode === 'incremental' ? 'Starting update analysis' : 'Starting full analysis'
  if (normalizedStatus === 'running') return `${modeLabel} running`
  if (normalizedStatus === 'stopping') return 'Stopping analysis'
  if (normalizedStatus === 'completed') return 'Analysis completed'
  if (normalizedStatus === 'stopped') return 'Analysis stopped'
  if (normalizedStatus === 'failed') return 'Analysis failed'
  if (normalizedStatus === 'interrupted') return 'Analysis interrupted'
  if (normalizedStatus === 'not_started') return 'Analysis failed to start'
  return ''
}

export function analysisTaskStatusTone(status) {
  const normalizedStatus = String(status || '')
  if (['starting', 'running'].includes(normalizedStatus)) return 'running'
  if (['stopping', 'interrupted'].includes(normalizedStatus)) return 'warning'
  if (normalizedStatus === 'completed') return 'success'
  if (['failed', 'not_started'].includes(normalizedStatus)) return 'error'
  if (normalizedStatus === 'stopped') return 'muted'
  return 'muted'
}

export function selectAnalysisTaskForBadge(tasks, activeRunId = '') {
  const list = Array.isArray(tasks) ? tasks.filter((task) => task && typeof task === 'object') : []
  const runId = String(activeRunId || '').trim()
  if (runId) {
    const runTask = list.find((task) => String(task.runId || '') === runId)
    return runTask || null
  }
  return list.find((task) => isActiveAnalysisTaskStatus(task.status)) || list[0] || null
}

export function analysisTaskTooltip(task, fallbackRun = null) {
  const source = task && typeof task === 'object' ? task : {}
  const run = fallbackRun && typeof fallbackRun === 'object' ? fallbackRun : {}
  const lines = []
  const taskId = source.taskId ? String(source.taskId) : ''
  const runId = source.runId ? String(source.runId) : String(run.runId || '')
  const status = source.status ? String(source.status) : String(run.status || '')
  if (taskId) lines.push(`Task: ${taskId}`)
  if (runId) lines.push(`Run: ${runId}`)
  if (status) lines.push(`Status: ${status}`)
  if (source.latestEvent?.message) lines.push(String(source.latestEvent.message))
  if (source.error) lines.push(String(source.error))
  const timestamp = source.updatedAt || source.completedAt || source.startedAt || run.startedAt
  if (timestamp) lines.push(`Updated: ${timestamp}`)
  return lines.join('\n')
}
