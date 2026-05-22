import { useCallback, useEffect, useRef, useState } from 'react'
import ConnectionOverlay from './components/ConnectionOverlay'
import GameMenuPage from './pages/GameMenuPage'
import GamePage from './pages/GamePage'
import { usePixiRenderer } from './hooks/usePixiRenderer'
import { useSimulationSocket } from './hooks/useSimulationSocket'
import { GRID_SIZE, speedLabel } from './lib/constants'

export default function App() {
  const hostRef = useRef(null)
  const resolvePageFromPath = useCallback(() => {
    const raw = window.location.pathname.replace(/^\/+/, '')
    const normalized = raw.endsWith('/') ? raw : `${raw}/`
    return normalized === 'Ai/' ? 'game' : 'menu'
  }, [])
  const [page, setPage] = useState(resolvePageFromPath)
  const rendererRef = usePixiRenderer(hostRef, page === 'game')

  const [showTrail, setShowTrail] = useState(true)
  const [mode, setMode] = useState('idle')
  const [models, setModels] = useState([])
  const [maps, setMaps] = useState([])
  const [state, setState] = useState({ rover_pos: [0, GRID_SIZE - 1], target_pos: [-1, -1] })
  const [speedText, setSpeedText] = useState('Normal')
  const [selectedModel, setSelectedModel] = useState('')
  const [selectedMap, setSelectedMap] = useState('')
  const [status, setStatus] = useState({ kind: 'info', message: '' })

  const trailRef = useRef([])
  const speedTimeoutRef = useRef(null)

  useEffect(() => {
    const onPathChange = () => setPage(resolvePageFromPath())
    window.addEventListener('popstate', onPathChange)
    return () => window.removeEventListener('popstate', onPathChange)
  }, [resolvePageFromPath])

  const navigateTo = useCallback((nextPage) => {
    const nextPath = nextPage === 'game' ? '/Ai/' : '/AiMenu/'
    if (window.location.pathname !== nextPath) {
      window.history.pushState({}, '', nextPath)
    }
    setPage(nextPage)
  }, [])

  const onState = useCallback((s) => {
    if (s.__event === 'saved') {
      setStatus({ kind: 'info', message: `Model saved: ${s.model_name || ''}` })
      return
    }
    if (s.__event === 'error') {
      setStatus({ kind: 'error', message: s.message || 'Operation failed.' })
      return
    }
    if (s.__event === 'info') {
      setStatus({ kind: 'info', message: s.message || '' })
      return
    }
    if (s.__event === 'stopped') {
      setMode('idle')
      trailRef.current = []
      if (rendererRef.current) rendererRef.current.updateTrail([], 'idle', showTrail)
      return
    }

    if (s.mode) {
      setMode(s.mode)
      if (s.mode === 'idle') {
        trailRef.current = []
        if (rendererRef.current) rendererRef.current.updateTrail([], 'idle', showTrail)
      }
    }
    if (s.models) setModels(s.models)
    if (s.maps) setMaps(s.maps)
    if (s.model_name) setSelectedModel(s.model_name)
    if (s.map_name) setSelectedMap(s.map_name)
    setState((prev) => ({ ...prev, ...s }))

    if (s.craters && s.rocks && rendererRef.current) {
      rendererRef.current.drawTerrain(s.craters, s.rocks)
    }

    if (s.step === 0) {
      trailRef.current = []
      if (rendererRef.current) rendererRef.current.updateTrail([], s.mode, showTrail)
    }

    if (s.target_pos && s.rover_pos && rendererRef.current) {
      rendererRef.current.drawActors(s.rover_pos, s.target_pos)
      if (s.rover_pos && s.mode === 'training' && showTrail) {
        const pGrid = s.rover_pos
        const lastPGrid = trailRef.current[trailRef.current.length - 1]
        
        // Only add if position changed
        if (!lastPGrid || pGrid[0] !== lastPGrid[0] || pGrid[1] !== lastPGrid[1]) {
          trailRef.current = [...trailRef.current.slice(-199), pGrid]
          rendererRef.current.updateTrail(trailRef.current, s.mode, showTrail)
        }
      }
    }
  }, [rendererRef, showTrail])

  const { connected, send } = useSimulationSocket(onState)

  useEffect(() => {
    if (!status.message) return
    const id = setTimeout(() => setStatus((prev) => ({ ...prev, message: '' })), 2200)
    return () => clearTimeout(id)
  }, [status.message])

  const safeSend = useCallback((payload, failMessage = 'Server not connected yet.') => {
    const ok = send(payload)
    if (!ok) setStatus({ kind: 'error', message: failMessage })
    return ok
  }, [send])

  function start(action) {
    navigateTo('game')
    if (action) safeSend({ action })
  }

  // Ensure terrain/actors are visible when entering the game page.
  useEffect(() => {
    if (page !== 'game' || !rendererRef.current) return
    rendererRef.current.drawTerrain(state.craters || [], state.rocks || [])
    if (state.rover_pos && state.target_pos) {
      rendererRef.current.drawActors(state.rover_pos, state.target_pos)
    }
  }, [page, rendererRef, state.craters, state.rocks, state.rover_pos, state.target_pos])

  if (page === 'menu') {
    return (
      <>
        <GameMenuPage
          models={models}
          selectedModel={selectedModel}
          maps={maps}
          selectedMap={selectedMap}
          onSelectModel={(name) => {
            setSelectedModel(name)
            if (name) safeSend({ action: 'load_model', name })
          }}
          onSelectMap={(name) => {
            setSelectedMap(name)
            if (name) safeSend({ action: 'load_map', name })
          }}
          onTrain={() => start('train')}
          onRun={() => start('run')}
          onNewMap={() => {
            safeSend({ action: 'new_map' })
            start()
          }}
          onOpen={() => start()}
        />
        <ConnectionOverlay connected={connected} />
      </>
    )
  }

  return (
    <GamePage
      hostRef={hostRef}
      status={status}
      mode={mode}
      maps={maps}
      selectedMap={selectedMap}
      showTrail={showTrail}
      speedText={speedText}
      onMenu={() => {
        safeSend({ action: 'stop' })
        navigateTo('menu')
      }}
      onTrain={() => safeSend({ action: 'train' })}
      onRun={() => safeSend({ action: 'run' })}
      onStop={() => safeSend({ action: 'stop' })}
      onPause={() => safeSend({ action: 'pause' })}
      onResume={() => safeSend({ action: 'resume' })}
      onNewMap={() => safeSend({ action: 'new_map' })}
      onToggleTrail={() => {
        const next = !showTrail
        setShowTrail(next)
        if (rendererRef.current) rendererRef.current.updateTrail(trailRef.current, mode, next)
      }}
      onLoadMap={(name) => {
        setSelectedMap(name)
        safeSend({ action: 'load_map', name })
      }}
      onSpeed={(v) => {
        setSpeedText(speedLabel(v))
        if (speedTimeoutRef.current) clearTimeout(speedTimeoutRef.current)
        speedTimeoutRef.current = setTimeout(() => {
          safeSend({ action: 'set_speed', value: v })
        }, 100)
      }}
      connected={connected}
    />
  )
}
