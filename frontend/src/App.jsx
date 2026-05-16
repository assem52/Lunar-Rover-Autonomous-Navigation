import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import TopBar from './components/TopBar'
import MissionMenu from './components/MissionMenu'
import FloatingControls from './components/FloatingControls'
import HudPanel from './components/HudPanel'
import RewardChart from './components/RewardChart'
import ConnectionOverlay from './components/ConnectionOverlay'
import StatusToast from './components/StatusToast'
import { usePixiRenderer } from './hooks/usePixiRenderer'
import { useSimulationSocket } from './hooks/useSimulationSocket'
import { speedLabel } from './lib/constants'

export default function App() {
  const hostRef = useRef(null)
  const rendererRef = usePixiRenderer(hostRef)

  const [showMenu, setShowMenu] = useState(true)
  const [showTrail, setShowTrail] = useState(true)
  const [mode, setMode] = useState('idle')
  const [modelName, setModelName] = useState('')
  const [models, setModels] = useState([])
  const [maps, setMaps] = useState([])
  const [rewards, setRewards] = useState([])
  const [fps, setFps] = useState('-')
  const [wsStats, setWsStats] = useState({ kb: 0, msg: 0 })
  const [state, setState] = useState({ episode: 0, trained_eps: 0, total_reward: 0, step: 0, epsilon: 1, last_outcome: '-', rover_pos: [0, 0], target_pos: [0, 0] })
  const [success, setSuccess] = useState({ total: 0, wins: 0 })
  const [speedText, setSpeedText] = useState('Normal')
  const [selectedModel, setSelectedModel] = useState('')
  const [selectedMap, setSelectedMap] = useState('')
  const [status, setStatus] = useState({ kind: 'info', message: '' })

  const trailRef = useRef([])
  const lastEpisodeRef = useRef(-1)
  const fpsRef = useRef({ frames: 0, start: performance.now() })

  const onState = useCallback((s) => {
    if (s.__event === 'saved') {
      if (s.models) setModels(s.models)
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
    if (s.model_name) {
      setModelName(s.model_name)
      setSelectedModel(s.model_name)
    }
    if (s.map_name) setSelectedMap(s.map_name)
    if (s.perf) setWsStats({ kb: s.perf.ws_kb_per_sec || 0, msg: s.perf.ws_msgs_per_sec || 0 })
    setState((prev) => ({ ...prev, ...s }))

    if (s.craters && s.rocks && rendererRef.current) {
      rendererRef.current.drawTerrain(s.craters, s.rocks)
    }

    if (s.episode !== undefined && s.episode !== lastEpisodeRef.current) {
      if (lastEpisodeRef.current >= 0 && s.total_reward !== undefined && s.episode > 0) {
        setRewards((prev) => [...prev.slice(-119), { episode: lastEpisodeRef.current, reward: s.total_reward }])
        setSuccess((prev) => ({ total: prev.total + 1, wins: prev.wins + (s.last_outcome === 'success' ? 1 : 0) }))
      }
      if (s.episode === 0) {
        setRewards([])
        setSuccess({ total: 0, wins: 0 })
      }
      trailRef.current = []
      lastEpisodeRef.current = s.episode
    }

    if (s.target_pos && s.rover_pos && rendererRef.current) {
      rendererRef.current.drawActors(s.rover_pos, s.target_pos)
      if (s.rover_pos && s.mode === 'training' && showTrail) {
        const p = rendererRef.current.toPixel(s.rover_pos)
        const lastP = trailRef.current[trailRef.current.length - 1]
        
        // Only add if position changed
        if (!lastP || Math.hypot(p.x - lastP.x, p.y - lastP.y) > 1) {
          trailRef.current = [...trailRef.current.slice(-199), p] // Increased limit to 200 for better visibility
          rendererRef.current.updateTrail(trailRef.current, s.mode, showTrail)
        }
      }
    }

    fpsRef.current.frames += 1
    const now = performance.now()
    if (now - fpsRef.current.start > 500) {
      const value = (fpsRef.current.frames * 1000) / (now - fpsRef.current.start)
      setFps(value.toFixed(1))
      fpsRef.current.frames = 0
      fpsRef.current.start = now
    }
  }, [mode, rendererRef, showTrail])

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

  const successRate = useMemo(() => {
    if (success.total === 0) return '-'
    return `${Math.round((success.wins / success.total) * 100)}%`
  }, [success])

  function start(action) {
    setShowMenu(false)
    if (action) safeSend({ action })
  }

  useEffect(() => {
    if (state.mode && state.mode !== 'idle' && showMenu) {
      setShowMenu(false)
    }
  }, [state.mode, showMenu])

  // Fix: Redraw terrain and actors when the renderer becomes ready
  useEffect(() => {
    if (rendererRef.current && state.craters && state.rocks) {
      rendererRef.current.drawTerrain(state.craters, state.rocks)
      rendererRef.current.drawActors(state.rover_pos, state.target_pos)
    }
  }, [rendererRef.current, state.craters, state.rocks, state.rover_pos, state.target_pos])

  return (
    <>
      <TopBar
        mode={mode}
        episode={state.episode ?? 0}
        trained={state.trained_eps ?? 0}
        reward={Number(state.total_reward ?? 0).toFixed(1)}
        successRate={successRate}
      />

      <div id="main">
        <div id="vp">
          <div id="pixi-host" ref={hostRef} />
          <RewardChart rewards={rewards} />
          <HudPanel
            roverPos={state.rover_pos}
            targetPos={state.target_pos}
            fps={fps}
            wsIn={`${wsStats.kb.toFixed(1)} KB/s | ${wsStats.msg.toFixed(1)} msg/s`}
          />
          <StatusToast kind={status.kind} message={status.message} />

          {!showMenu && (
            <FloatingControls
              mode={mode}
              step={state.step ?? 0}
              epsilon={Number(state.epsilon ?? 0).toFixed(3)}
              outcome={state.last_outcome || '-'}
              maps={maps}
              selectedMap={selectedMap}
              showTrail={showTrail}
              speedLabelText={speedText}
              personality={state.personality || 'explorer'}
              availablePersonalities={state.available_personalities || []}
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
              onPersonality={(name) => {
                safeSend({ action: 'set_personality', name })
              }}
              onSpeed={(v) => {
                setSpeedText(speedLabel(v))
                safeSend({ action: 'set_speed', value: v })
              }}
            />
          )}

          {showMenu && (
            <MissionMenu
              onTrain={() => start('train')}
              onRun={() => start('run')}
              onNewMap={() => {
                safeSend({ action: 'new_map' })
                start()
              }}
              onOpen={() => start()}
            />
          )}

          <ConnectionOverlay connected={connected} />
        </div>
      </div>
    </>
  )
}
