import { useEffect, useRef, useState } from 'react'
import Chart from 'chart.js/auto'

export default function RewardChart({ rewards }) {
  const canvasRef = useRef(null)
  const chartRef = useRef(null)
  
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [windowSize, setWindowSize] = useState(200)
  const [autoScale, setAutoScale] = useState(true)

  useEffect(() => {
    if (!canvasRef.current) return
    const ctx = canvasRef.current.getContext('2d')
    
    // Sci-fi gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 300)
    gradient.addColorStop(0, 'rgba(0, 212, 255, 0.4)')
    gradient.addColorStop(1, 'rgba(0, 212, 255, 0.0)')

    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: { 
        labels: [], 
        datasets: [{ 
          label: 'Reward',
          data: [], 
          borderColor: '#00d4ff', 
          backgroundColor: gradient, 
          borderWidth: 2,
          pointRadius: 0, 
          pointHitRadius: 10,
          fill: true, 
          tension: 0.3 
        }] 
      },
      options: { 
        animation: false, 
        responsive: true, 
        maintainAspectRatio: false, 
        interaction: { intersect: false, mode: 'index' },
        plugins: { 
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(17, 24, 34, 0.9)',
            titleColor: '#00d4ff',
            bodyColor: '#e2e8f0',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1,
            padding: 10,
            displayColors: false,
          }
        },
        scales: {
          y: {
            grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
            ticks: { color: '#64748b', font: { family: "'Orbitron', sans-serif", size: 10 } }
          },
          x: {
            grid: { display: false, drawBorder: false },
            ticks: { display: isFullscreen, color: '#64748b', font: { family: "'Orbitron', sans-serif", size: 10 }, maxTicksLimit: 8 }
          }
        }
      }
    })

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy()
        chartRef.current = null
      }
    }
  }, [isFullscreen])

  useEffect(() => {
    if (!chartRef.current) return
    
    const displayData = rewards.slice(-windowSize)
    
    if (autoScale) {
      chartRef.current.options.scales.y.min = undefined
      chartRef.current.options.scales.y.max = undefined
    } else {
      chartRef.current.options.scales.y.min = -250
      chartRef.current.options.scales.y.max = 250
    }

    chartRef.current.data.labels = displayData.map((r) => `Ep ${r.episode}`)
    chartRef.current.data.datasets[0].data = displayData.map((r) => r.reward)
    chartRef.current.update('none')
  }, [rewards, windowSize, autoScale])

  return (
    <div id="chart-float" className={isFullscreen ? 'fullscreen' : ''}>
      <div id="chart-header">
        <div id="chart-title" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: '#00d4ff' }}>
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
          </svg>
          REWARD HISTORY
        </div>
        <button id="btn-expand" onClick={() => setIsFullscreen(!isFullscreen)}>
          {isFullscreen ? 'EXIT FULL' : 'FULLSCREEN'}
        </button>
      </div>
      
      <div className="chart-canvas-container" style={{ flex: 1, position: 'relative', minHeight: 0 }}>
        <canvas ref={canvasRef} />
      </div>

      <div className="chart-controls">
        <div className="chart-control-group">
          <label>X-WINDOW</label>
          <select value={windowSize} onChange={(e) => setWindowSize(Number(e.target.value))}>
            <option value={50}>50 EPS</option>
            <option value={100}>100 EPS</option>
            <option value={200}>200 EPS</option>
            <option value={500}>500 EPS</option>
            <option value={999999}>ALL</option>
          </select>
        </div>
        <div className="chart-control-group" style={{ marginLeft: 'auto' }}>
          <label style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <input 
              type="checkbox" 
              checked={autoScale} 
              onChange={(e) => setAutoScale(e.target.checked)} 
              style={{ width: '14px', height: '14px', margin: 0, cursor: 'pointer' }}
            />
            AUTO-SCALE Y
          </label>
        </div>
      </div>
    </div>
  )
}
