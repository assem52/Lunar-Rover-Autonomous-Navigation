import FloatingControls from '../components/FloatingControls'
import StatusToast from '../components/StatusToast'
import ConnectionOverlay from '../components/ConnectionOverlay'

export default function GamePage({
  hostRef,
  status,
  mode,
  showTrail,
  speedText,
  onMenu,
  onTrain,
  onRun,
  onStop,
  onPause,
  onResume,
  onToggleTrail,
  onSpeed,
  connected
}) {
  return (
    <div id="main">
      <div id="vp">
        <div id="pixi-host" ref={hostRef} />
        <StatusToast kind={status.kind} message={status.message} />
        <FloatingControls
          mode={mode}
          showTrail={showTrail}
          speedLabelText={speedText}
          onMenu={onMenu}
          onTrain={onTrain}
          onRun={onRun}
          onStop={onStop}
          onPause={onPause}
          onResume={onResume}
          onToggleTrail={onToggleTrail}
          onSpeed={onSpeed}
        />
        <ConnectionOverlay connected={connected} />
      </div>
    </div>
  )
}
