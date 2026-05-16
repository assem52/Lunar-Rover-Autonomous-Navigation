import { useEffect, useRef, useState } from 'react'

export default function RewardChart({ rewards }) {
  const canvasRef = useRef(null)
  const chartRef = useRef(null)
  
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [minY, setMinY] = useState(-150)
  const [maxY, setMaxY] = useState(150)
  const [windowSize, setWindowSize] = useState(100)

  useEffect(() => {
    let active = true

    ;(async () => {
      const mod = await import('chart.js/auto')
      if (!active || !canvasRef.current) return
      const Chart = mod.default
      const ctx = canvasRef.current.getContext('2d')
      chartRef.current = new Chart(ctx, {
        type: 'line',
        data: { labels: [], datasets: [{ data: [], borderColor: '#00c8ff', backgroundColor: 'rgba(0,200,255,.12)', pointRadius: 0, fill: true, tension: 0.25 }] },
        options: { 
          animation: false, 
          responsive: true, 
          maintainAspectRatio: false, 
          plugins: { legend: { display: false } },
          scales: {
            y: {
              min: minY,
              max: maxY,
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { color: '#64748b', font: { size: 10 } }
            },
            x: {
              grid: { display: false },
              ticks: { display: isFullscreen, color: '#64748b', font: { size: 10 } }
            }
          }
        }
      })
    })()

    return () => {
      active = false
      chartRef.current?.destroy()
      chartRef.current = null
    }
  }, [isFullscreen]) // Re-init on fullscreen to fix size issues

  useEffect(() => {
    if (!chartRef.current) return
    
    // Update axis scales
    chartRef.current.options.scales.y.min = minY
    chartRef.current.options.scales.y.max = maxY
    
    // Slice data based on windowSize
    const displayData = rewards.slice(-windowSize)
    
    chartRef.current.data.labels = displayData.map((r) => r.episode)
    chartRef.current.data.datasets[0].data = displayData.map((r) => r.reward)
    chartRef.current.update('none')
  }, [rewards, minY, maxY, windowSize])

  return (
    <div id="chart-float" className={isFullscreen ? 'fullscreen' : ''}>
      <div id="chart-header">
        <div id="chart-title">REWARD / EPISODE</div>
        <button id="btn-expand" onClick={() => setIsFullscreen(!isFullscreen)}>
          {isFullscreen ? 'EXIT FULL' : 'FULLSCREEN'}
        </button>
      </div>
      
      <canvas ref={canvasRef} />

      <div className="chart-controls">
        <div className="chart-control-group">
          <label>Y-MIN</label>
          <input type="number" value={minY} onChange={(e) => setMinY(parseInt(e.target.value) || 0)} />
        </div>
        <div className="chart-control-group">
          <label>Y-MAX</label>
          <input type="number" value={maxY} onChange={(e) => setMaxY(parseInt(e.target.value) || 0)} />
        </div>
        <div className="chart-control-group">
          <label>X-WINDOW</label>
          <input type="number" value={windowSize} onChange={(e) => setWindowSize(parseInt(e.target.value) || 1)} />
        </div>
      </div>
    </div>
  )
}
