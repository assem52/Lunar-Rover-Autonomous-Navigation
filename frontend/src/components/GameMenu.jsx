export default function GameMenu({
  models,
  selectedModel,
  maps,
  selectedMap,
  onSelectModel,
  onSelectMap,
  onTrain,
  onRun,
  onNewMap,
  onOpen
}) {
  return (
    <div id="menu-screen">
      <div className="menu-card">
        <div className="menu-badge">Mission Control</div>
        <div className="menu-title">LUNAR ROVER</div>
        <div className="menu-sub">Autonomous Navigation</div>

        <div className="menu-config">
          <div className="menu-config-item">
            <label>Choose Model</label>
            <select value={selectedModel} onChange={(e) => onSelectModel(e.target.value)}>
              <option value="">-- Select Model --</option>
              {models.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div className="menu-config-item">
            <label>Choose Map</label>
            <select value={selectedMap} onChange={(e) => onSelectMap(e.target.value)}>
              <option value="">-- Select Map --</option>
              {maps.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
        </div>

        <div className="menu-actions">
          <button className="menu-btn primary" onClick={onTrain}>Start Training</button>
          <button className="menu-btn success" onClick={onRun}>Run Selected Model</button>
          <button className="menu-btn" onClick={onNewMap}>Generate New Map</button>
          <button className="menu-btn ghost" onClick={onOpen}>Open Playground</button>
        </div>
      </div>
    </div>
  )
}
