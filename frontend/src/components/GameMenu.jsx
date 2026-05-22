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

  return (
    <div id="menu-screen">
      <div className="menu-card">
        <div className="menu-badge">Mission Control</div>
        <div className="menu-title">LUNAR ROVER</div>
        <div className="menu-sub">Autonomous Navigation</div>

        <div className="menu-actions">
          <button className="menu-btn primary" onClick={onTrain}>Train Model</button>
          <button className="menu-btn success" onClick={() => setShowRunList(true)}>Run Trained Models</button>
        </div>
      </div>
    </div>
  )
}
