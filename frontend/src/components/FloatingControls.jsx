import { MODE_LABELS } from '../lib/constants'

export default function FloatingControls({
  mode,
  maps, selectedMap,
  showTrail, speedLabelText,
  onTrain, onRun, onStop, onPause, onResume, onNewMap, onToggleTrail, onMenu,
  onLoadMap,
  onSpeed
}) {
  return (
    <div id="floating-controls">
      <div className="row">
        {(mode === 'idle') ? (
          <>
            <button id="btn-train" onClick={onTrain}>TRAIN</button>
            <button id="btn-run" onClick={onRun}>RUN</button>
          </>
        ) : (mode === 'paused_training' || mode === 'paused_running') ? (
          <>
            <button id="btn-resume" style={{ backgroundColor: '#10b981' }} onClick={onResume}>RESUME</button>
            <button id="btn-end" style={{ backgroundColor: '#ef4444' }} onClick={onStop}>END</button>
          </>
        ) : (
          <>
            <button id="btn-pause" style={{ backgroundColor: '#f59e0b' }} onClick={onPause}>PAUSE</button>
            <button id="btn-end" style={{ backgroundColor: '#ef4444' }} onClick={onStop}>END</button>
          </>
        )}
      </div>
      <div className="row">
        <button style={{ flex: 1 }} onClick={onNewMap}>NEW MAP</button>
        <button onClick={onToggleTrail}>{`PATH: ${showTrail ? 'ON' : 'OFF'}`}</button>
      </div>

      <select value={selectedMap} onChange={(e) => e.target.value && onLoadMap(e.target.value)}>
        <option value="">-- Select Map --</option>
        {maps.map((m) => <option key={m} value={m}>{m}</option>)}
      </select>
      <div className="row"><span className="label">MODE</span><span style={{ marginLeft: 'auto' }}>{MODE_LABELS[mode] || mode.toUpperCase()}</span></div>
      <div className="row"><span className="label">SPEED</span><span style={{ marginLeft: 'auto' }}>{speedLabelText}</span></div>
      <input type="range" min="0" max="0.9" step="0.01" defaultValue="0.12" dir="rtl" onChange={(e) => onSpeed(parseFloat(e.target.value))} />
      <button onClick={onMenu}>BACK TO MENU</button>
    </div>
  )
}
