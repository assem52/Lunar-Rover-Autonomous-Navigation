import { MODE_LABELS } from '../lib/constants'

export default function FloatingControls({
  mode, step, epsilon, outcome,
  maps, selectedMap,
  showTrail, speedLabelText,
  onTrain, onRun, onStop, onPause, onResume, onNewMap, onToggleTrail,
  onLoadMap,
  onSpeed,
  personality, availablePersonalities, onPersonality
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

      <div className="label">ROVER PERSONALITY</div>
      <select value={personality} onChange={(e) => e.target.value && onPersonality(e.target.value)}>
        {availablePersonalities.map((p) => (
          <option key={p} value={p}>{p.toUpperCase()}</option>
        ))}
      </select>

      <select value={selectedMap} onChange={(e) => e.target.value && onLoadMap(e.target.value)}>
        <option value="">-- Select Map --</option>
        {maps.map((m) => <option key={m} value={m}>{m}</option>)}
      </select>
      <div className="row"><span className="label">STEP</span><span>{step}</span><span className="label" style={{ marginLeft: 'auto' }}>EPS</span><span>{epsilon}</span></div>
      <div className="row"><span className="label">OUTCOME</span><span>{outcome}</span><span className="label" style={{ marginLeft: 'auto' }}>MODE</span><span>{MODE_LABELS[mode] || mode.toUpperCase()}</span></div>
      <div className="row"><span className="label">SPEED</span><span style={{ marginLeft: 'auto' }}>{speedLabelText}</span></div>
      <input type="range" min="0" max="0.9" step="0.01" defaultValue="0.12" dir="rtl" onInput={(e) => onSpeed(parseFloat(e.target.value))} />
    </div>
  )
}
