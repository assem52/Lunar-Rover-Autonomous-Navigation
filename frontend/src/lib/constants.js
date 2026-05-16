export const GRID_SIZE = 10
export const MODE_LABELS = {
  idle: 'IDLE',
  training: 'TRAINING',
  running: 'RUNNING'
}

export function speedLabel(v) {
  if (v < 0.04) return 'Turbo'
  if (v < 0.15) return 'Fast'
  if (v < 0.4) return 'Normal'
  return 'Slow'
}
