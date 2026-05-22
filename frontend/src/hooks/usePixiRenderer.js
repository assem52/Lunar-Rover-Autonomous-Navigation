import { useEffect, useRef } from 'react'
import { GRID_SIZE, loadServerConfig } from '../lib/constants'

export function usePixiRenderer(hostRef, active = true) {
  const apiRef = useRef(null)

  useEffect(() => {
    if (!active) return
    if (!hostRef.current) return

    let disposed = false
    let cleanup = null

    ;(async () => {
      await loadServerConfig()           // fetch grid_size from server first
      const PIXI = await import('pixi.js')
      if (disposed || !hostRef.current) return

      const app = new PIXI.Application({
        background: '#5c4e40', // Exact Berkeley brown
        antialias: true,
        resolution: Math.min(window.devicePixelRatio || 1, 2),
        autoDensity: true,
      })
      hostRef.current.appendChild(app.view)

      const world = new PIXI.Container()
      const terrainLayer = new PIXI.Container()
      const trailLayer = new PIXI.Container()
      const actorLayer = new PIXI.Container()
      world.addChild(terrainLayer, trailLayer, actorLayer)
      app.stage.addChild(world)

      const targetGfx = new PIXI.Graphics()
      const targetText = new PIXI.Text('+1', { 
        fontFamily: 'Comic Sans MS, Chalkboard, Marker Felt, sans-serif', 
        fontSize: 10, 
        fill: 0xffffff,
        stroke: 0x000000,
        strokeThickness: 1
      })
      targetText.anchor.set(0.5)
      actorLayer.addChild(targetGfx, targetText)

      const roverGfx = new PIXI.Graphics()
      actorLayer.addChild(roverGfx)

      let cellSize = 24
      let offsetX = 0
      let offsetY = 0
      let roverPx = { x: 0, y: 0 }
      let roverTargetPx = { x: 0, y: 0 }

      function toPixel(pos) {
        return {
          x: offsetX + pos[0] * cellSize + cellSize * 0.5,
          y: offsetY + pos[1] * cellSize + cellSize * 0.5,
        }
      }

      function drawGrid() {
        terrainLayer.removeChildren()
        
        const g = new PIXI.Graphics()
        g.lineStyle(2, 0x111111, 0.9)
        
        for (let y = 0; y <= GRID_SIZE; y++) {
            g.moveTo(offsetX, offsetY + y * cellSize)
            g.lineTo(offsetX + GRID_SIZE * cellSize, offsetY + y * cellSize)
        }
        for (let x = 0; x <= GRID_SIZE; x++) {
            g.moveTo(offsetX + x * cellSize, offsetY)
            g.lineTo(offsetX + x * cellSize, offsetY + GRID_SIZE * cellSize)
        }
        terrainLayer.addChild(g)

        // START text
        const startText = new PIXI.Text('START', { 
            fontFamily: 'Comic Sans MS, Chalkboard, Marker Felt, sans-serif', 
            fontSize: cellSize * 0.25, 
            fill: 0x111111 
        })
        startText.x = offsetX + cellSize * 0.1
        startText.y = offsetY + (GRID_SIZE - 1) * cellSize + cellSize * 0.6
        terrainLayer.addChild(startText)
      }

      function resize() {
        if (!hostRef.current) return
        const w = hostRef.current.clientWidth
        const h = hostRef.current.clientHeight
        app.renderer.resize(w, h)
        cellSize = Math.floor(Math.min(w, h) / (GRID_SIZE + 2))
        offsetX = Math.floor((w - GRID_SIZE * cellSize) / 2)
        offsetY = Math.floor((h - GRID_SIZE * cellSize) / 2)
        drawGrid()
      }

      app.ticker.add((delta) => {
        roverPx.x += (roverTargetPx.x - roverPx.x) * 0.3
        roverPx.y += (roverTargetPx.y - roverPx.y) * 0.3
        
        roverGfx.clear()
        
        const cx = roverPx.x
        const cy = roverPx.y
        const r = cellSize * 0.3
        
        roverGfx.lineStyle(2, 0x000000, 1)

        // Arms (gray)
        roverGfx.beginFill(0x9ca3af, 1)
        roverGfx.drawCircle(cx - r * 0.85, cy, r * 0.35) // Left arm
        roverGfx.drawCircle(cx + r * 0.85, cy, r * 0.35) // Right arm
        roverGfx.endFill()
        
        // Little antennas/hands on the arms
        roverGfx.moveTo(cx - r * 0.9, cy - r * 0.3)
        roverGfx.lineTo(cx - r * 1.1, cy - r * 0.6)
        roverGfx.moveTo(cx + r * 0.9, cy - r * 0.3)
        roverGfx.lineTo(cx + r * 1.1, cy - r * 0.6)

        // Main body (white)
        roverGfx.beginFill(0xe2e8f0, 1)
        roverGfx.drawCircle(cx, cy, r)
        roverGfx.endFill()

        // Inner eye rim (light blue)
        roverGfx.beginFill(0xcceeff, 1)
        roverGfx.drawCircle(cx, cy, r * 0.65)
        roverGfx.endFill()

        // Pupil (red)
        roverGfx.beginFill(0xef4444, 1)
        roverGfx.drawCircle(cx, cy, r * 0.25)
        roverGfx.endFill()

        targetText.y = targetText.baseY
      })

      resize()
      window.addEventListener('resize', resize)

      apiRef.current = {
        drawTerrain(craters = [], rocks = []) {
          drawGrid()
          
          craters.forEach(([x, y]) => {
            const px = offsetX + x * cellSize
            const py = offsetY + y * cellSize
            const cx = px + cellSize / 2
            const cy = py + cellSize / 2
            
            const c = new PIXI.Graphics()
            
            // Background cracks radiating from center
            c.lineStyle(2, 0x3a2d20, 1)
            c.moveTo(cx, cy); c.lineTo(px + cellSize*0.1, py + cellSize*0.1)
            c.moveTo(cx, cy); c.lineTo(px + cellSize*0.9, py + cellSize*0.2)
            c.moveTo(cx, cy); c.lineTo(px + cellSize*0.2, py + cellSize*0.8)
            c.moveTo(cx, cy); c.lineTo(px + cellSize*0.8, py + cellSize*0.9)
            c.moveTo(cx, cy); c.lineTo(px, cy)
            c.moveTo(cx, cy); c.lineTo(px + cellSize, cy)
            
            // Explosion star
            c.lineStyle(2, 0xcc0000, 1) // red outline
            c.beginFill(0xff7700, 1) // orange fill
            
            // Exact jagged shape (alternating long and short spikes)
            const points = []
            const numSpikes = 12
            for (let i = 0; i < numSpikes * 2; i++) {
                const angle = (i / (numSpikes * 2)) * Math.PI * 2
                // Even index = long spike, Odd index = short indent
                let rad = (i % 2 === 0) ? cellSize * 0.45 : cellSize * 0.25
                // Add slight irregularity
                rad += (Math.random() - 0.5) * cellSize * 0.05
                points.push(cx + Math.cos(angle) * rad, cy + Math.sin(angle) * rad)
            }
            c.drawPolygon(points)
            c.endFill()

            const text = new PIXI.Text('-1', { 
                fontFamily: 'Comic Sans MS, Chalkboard, Marker Felt, sans-serif', 
                fontSize: cellSize * 0.4, 
                fill: 0xff3333, // Red text
                stroke: 0xffaa00, // Orange outline
                strokeThickness: 3,
                fontWeight: 'bold'
            })
            text.anchor.set(0.5)
            text.x = cx
            text.y = cy
            terrainLayer.addChild(c, text)
          })
          
          rocks.forEach(([x, y]) => {
            const px = offsetX + x * cellSize
            const py = offsetY + y * cellSize
            const r = new PIXI.Graphics()
            
            const pad = cellSize * 0.15
            const innerX = px + pad
            const innerY = py + pad
            const innerSize = cellSize - pad * 2
            
            // Draw 3D connection lines from corners of cell to corners of rock
            r.lineStyle(2, 0x111111, 1)
            r.moveTo(px, py); r.lineTo(innerX, innerY)
            r.moveTo(px + cellSize, py); r.lineTo(innerX + innerSize, innerY)
            r.moveTo(px, py + cellSize); r.lineTo(innerX, innerY + innerSize)
            r.moveTo(px + cellSize, py + cellSize); r.lineTo(innerX + innerSize, innerY + innerSize)

            // Rock body (gray)
            r.beginFill(0x888888, 1)
            
            // Crinkled polygon for the rock face
            const pts = [
                innerX + innerSize*0.05, innerY + innerSize*0.1,
                innerX + innerSize*0.4, innerY - innerSize*0.05,
                innerX + innerSize*0.9, innerY + innerSize*0.05,
                innerX + innerSize*0.95, innerY + innerSize*0.5,
                innerX + innerSize*0.9, innerY + innerSize*0.9,
                innerX + innerSize*0.5, innerY + innerSize*0.95,
                innerX + innerSize*0.1, innerY + innerSize*0.85,
                innerX - innerSize*0.05, innerY + innerSize*0.5
            ]
            r.drawPolygon(pts)
            r.endFill()

            // Subtle inner crack lines
            r.lineStyle(1, 0x444444, 0.8)
            r.moveTo(innerX + innerSize*0.2, innerY + innerSize*0.3)
            r.lineTo(innerX + innerSize*0.4, innerY + innerSize*0.4)
            r.moveTo(innerX + innerSize*0.7, innerY + innerSize*0.6)
            r.lineTo(innerX + innerSize*0.8, innerY + innerSize*0.8)
            
            terrainLayer.addChild(r)
          })
        },
        drawActors(roverPos, targetPos) {
          targetGfx.clear()
          const target = toPixel(targetPos)
          
          if (targetPos[0] < 0 || targetPos[1] < 0) {
              targetGfx.visible = false
              targetText.visible = false
          } else {
              targetGfx.visible = true
              targetText.visible = true
              
              const d = cellSize * 0.35
              
              targetGfx.lineStyle(2, 0x111111, 1)
              
              // Bottom right darker blue facet
              targetGfx.beginFill(0x2b57d6, 1)
              targetGfx.drawPolygon([
                target.x - d, target.y,
                target.x + d, target.y,
                target.x, target.y + d
              ])
              targetGfx.endFill()
              
              // Top left lighter blue facet
              targetGfx.beginFill(0x5282ff, 1)
              targetGfx.drawPolygon([
                target.x - d, target.y,
                target.x + d, target.y,
                target.x, target.y - d
              ])
              targetGfx.endFill()
              
              // Inner diagonal lines to give faceted look
              targetGfx.lineStyle(1, 0x111111, 0.8)
              targetGfx.moveTo(target.x - d*0.5, target.y - d*0.5)
              targetGfx.lineTo(target.x + d*0.5, target.y - d*0.5)
              targetGfx.lineTo(target.x + d*0.5, target.y + d*0.5)
              targetGfx.lineTo(target.x - d*0.5, target.y + d*0.5)
              targetGfx.lineTo(target.x - d*0.5, target.y - d*0.5)

              targetText.x = target.x
              targetText.y = target.y
              targetText.baseY = target.y
              targetText.style.fontSize = cellSize * 0.4
          }
          
          roverTargetPx = toPixel(roverPos)
          if (roverPx.x === 0 && roverPx.y === 0) roverPx = { ...roverTargetPx }
        },
        updateTrail(gridPoints, mode, showTrail) {
          trailLayer.removeChildren()
          if (!showTrail || gridPoints.length < 2) return
          
          const g = new PIXI.Graphics()
          const edges = {}
          
          for (let i = 0; i < gridPoints.length - 1; i++) {
              const p1 = toPixel(gridPoints[i])
              const p2 = toPixel(gridPoints[i+1])
              const dx = p2.x - p1.x
              const dy = p2.y - p1.y
              if (Math.hypot(dx, dy) < 1) continue

              const key1 = `${Math.round(p1.x)},${Math.round(p1.y)}->${Math.round(p2.x)},${Math.round(p2.y)}`
              const key2 = `${Math.round(p2.x)},${Math.round(p2.y)}->${Math.round(p1.x)},${Math.round(p1.y)}`
              
              if (!edges[key1] && !edges[key2]) {
                  edges[key1] = { p1, p2, bidir: false }
              } else if (edges[key2]) {
                  edges[key2].bidir = true
              }
          }
          
          for (const key in edges) {
              const { p1, p2, bidir } = edges[key]
              const dx = p2.x - p1.x
              const dy = p2.y - p1.y
              const angle = Math.atan2(dy, dx)
              const cx = (p1.x + p2.x) / 2
              const cy = (p1.y + p2.y) / 2
              
              const len = cellSize * 0.45
              const width = cellSize * 0.15
              const headLen = cellSize * 0.25
              const headWidth = cellSize * 0.4

              g.lineStyle(2, 0x004d00, 1) // Dark green outline
              g.beginFill(0x00ff00, 1) // Bright green fill
              
              const cos = Math.cos(angle)
              const sin = Math.sin(angle)
              
              let pts = []
              if (bidir) {
                  pts = [
                      -len/2 + headLen, -width/2,
                      len/2 - headLen, -width/2,
                      len/2 - headLen, -headWidth/2,
                      len/2, 0,
                      len/2 - headLen, headWidth/2,
                      len/2 - headLen, width/2,
                      -len/2 + headLen, width/2,
                      -len/2 + headLen, headWidth/2,
                      -len/2, 0,
                      -len/2 + headLen, -headWidth/2
                  ]
              } else {
                  pts = [
                    -len/2, -width/2, 
                    len/2 - headLen, -width/2, 
                    len/2 - headLen, -headWidth/2, 
                    len/2, 0, 
                    len/2 - headLen, headWidth/2, 
                    len/2 - headLen, width/2, 
                    -len/2, width/2 
                  ]
              }
              
              const transformed = []
              for (let j = 0; j < pts.length; j += 2) {
                  const px = pts[j]
                  const py = pts[j+1]
                  transformed.push(cx + px * cos - py * sin, cy + px * sin + py * cos)
              }
              
              g.drawPolygon(transformed)
              g.endFill()
          }
          
          trailLayer.addChild(g)
        },
        toPixel,
      }

      // Ensure rover is visible at START immediately on page load,
      // even before the first websocket state arrives.
      apiRef.current.drawTerrain([], [])
      apiRef.current.drawActors([0, GRID_SIZE - 1], [-1, -1])

      cleanup = () => {
        window.removeEventListener('resize', resize)
        app.destroy(true, true)
      }
    })()

    return () => {
      disposed = true
      if (cleanup) cleanup()
      apiRef.current = null
    }
  }, [hostRef, active])

  return apiRef
}
