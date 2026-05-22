import { useState } from 'react'

function MiniMapPreview({ mapData }) {
  const grid = mapData?.grid || []
  const size = grid.length || 0
  const target = mapData?.target || [-1, -1]
  const start = mapData?.start || [0, size - 1]

  return (
    <div className="mini-map-grid" style={{ gridTemplateColumns: `repeat(${size || 1}, 1fr)` }}>
      {grid.flatMap((row, y) => row.map((cell, x) => {
        let cls = 'mini-cell'
        if (x === start[0] && y === start[1]) cls += ' start'
        else if (x === target[0] && y === target[1]) cls += ' target'
        else if (cell === 1) cls += ' crater'
        else if (cell === 2) cls += ' rock'
        return <div key={`${x}-${y}`} className={cls} />
      }))}
    </div>
  )
}

export default function GameMenu({ trainedModels, trainedModelPreviews, onTrain, onRunTrainedModel }) {
  const [showRunList, setShowRunList] = useState(false)
  const [showTrainForm, setShowTrainForm] = useState(false)
  const [exploration, setExploration] = useState(0.3)
  const MIN_EXPLORATION = 0
  const MAX_EXPLORATION = 1

  const handleExplorationInput = (value) => {
    const parsed = Number.parseFloat(value)
    if (Number.isNaN(parsed)) return
    const normalized = Math.min(MAX_EXPLORATION, Math.max(MIN_EXPLORATION, parsed / 100))
    setExploration(normalized)
  }

  const handleExploitationInput = (value) => {
    const parsed = Number.parseFloat(value)
    if (Number.isNaN(parsed)) return
    const normalizedExploitation = Math.min(MAX_EXPLORATION, Math.max(MIN_EXPLORATION, parsed / 100))
    setExploration(1 - normalizedExploitation)
  }

  if (showRunList) {
    return (
      <div id="menu-screen">
        <div className="menu-card">
          <div className="menu-badge">Run Trained Models</div>
          <div className="menu-title">Select Model</div>
          <div className="menu-sub">Choose a saved model name to auto-load and run</div>

          <div className="trained-list">
            {trainedModels.length === 0 && (
              <div className="trained-empty">No trained models yet. Train and save a model first.</div>
            )}
            <div className="trained-grid">
              {trainedModels.map((name) => (
                <button key={name} className="trained-card" onClick={() => onRunTrainedModel(name)}>
                  <MiniMapPreview mapData={trainedModelPreviews?.[name]} />
                  <span>{name}</span>
                </button>
              ))}
            </div>
          </div>

          <button className="menu-btn ghost" onClick={() => setShowRunList(false)}>Back</button>
        </div>
      </div>
    )
  }

  if (showTrainForm) {
    const exploitation = 1 - exploration
    return (
      <div id="menu-screen">
        <div className="menu-card">
          <div className="menu-badge">Train Configuration</div>
          <div className="menu-title">Model Balance</div>
          <div className="menu-sub">Set how much the model explores vs exploits</div>

          <div className="train-form">
            <div className="train-row">
              <span>Exploration</span>
              <input
                type="number"
                min="0"
                max="100"
                step="1"
                value={Math.round(exploration * 100)}
                onChange={(e) => handleExplorationInput(e.target.value)}
              />
            </div>
            <div className="train-row">
              <span>Exploitation</span>
              <input
                type="number"
                min="0"
                max="100"
                step="1"
                value={Math.round(exploitation * 100)}
                onChange={(e) => handleExploitationInput(e.target.value)}
              />
            </div>
          </div>

          <div className="menu-actions">
            <button className="menu-btn primary" onClick={() => onTrain({ exploration, exploitation })}>Start Training</button>
            <button className="menu-btn ghost" onClick={() => setShowTrainForm(false)}>Back</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div id="menu-screen">
      <div className="menu-card">
        <div className="menu-badge">Mission Control</div>
        <div className="menu-title">LUNAR ROVER</div>
        <div className="menu-sub">Autonomous Navigation</div>

        <div className="menu-actions">
          <button className="menu-btn primary" onClick={() => setShowTrainForm(true)}>Train Model</button>
          <button className="menu-btn success" onClick={() => setShowRunList(true)}>Run Trained Models</button>
        </div>
      </div>
    </div>
  )
}
