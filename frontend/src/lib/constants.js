// GRID_SIZE is fetched from the server at startup (see usePixiRenderer).
// This module re-exports whatever the server returns, so there is a single
// source of truth and no need to keep Python + JS in sync manually.
export let GRID_SIZE = 10  // default until the server responds

export async function loadServerConfig() {
  try {
    const res = await fetch('/api/config')
    if (res.ok) {
      const cfg = await res.json()
      if (typeof cfg.grid_size === 'number') GRID_SIZE = cfg.grid_size
    }
  } catch {
    // Server not reachable yet — keep the default value
  }
}

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
