<template>
  <div class="candlestick-snapshot-container">
    <div class="header">
      <h2>K-Line Snapshot — {{ snapshotData.currentCoin }} {{ snapshotData.currentGranularity }}</h2>
      <button class="close-btn" @click="$emit('close')">×</button>
    </div>

    <!-- ezio: screenshot image + canvas overlay for annotation -->
    <div class="vis-area" ref="visArea">
      <img :src="snapshotData.imageDataUrl" class="snapshot-img" draggable="false" />
      <canvas ref="sketchCanvas" class="sketch-overlay"
          :class="'cursor-' + activeTool"></canvas>
      <SnapshotToolbar class="floating-toolbar"
          :tool="activeTool" :color="penColor"
          @update:tool="activeTool = $event"
          @update:color="penColor = $event"
          @clear="clearSketches" />
    </div>

    <!-- ezio: text input -->
    <div class="input-area">
      <input type="text" v-model="inputText" placeholder="Enter annotation text..."
        @keyup.enter="handleInput" class="text-input" />
      <button @click="handleInput" class="send-btn">Annotate</button>
    </div>
  </div>
</template>

<script>
// ezio: toolbar component
import SnapshotToolbar from './SnapshotToolbar.vue'

export default {
  name: 'CandlestickSnapshot',
  components: { SnapshotToolbar },
  props: {
    snapshotData: { type: Object, required: true }
  },
  emits: ['close', 'snapshot-input'],
  data() {
    return {
      inputText: '',
      activeTool: 'select',
      penColor: 'rgba(255,60,60,0.7)',
      sketchStrokes: [],
    }
  },
  watch: {
    activeTool() { this.redrawCanvas() }
  },
  mounted() {
    this.$nextTick(() => this.setupCanvas())
  },
  methods: {
    // ezio: init canvas to match vis-area size
    setupCanvas() {
      const canvas = this.$refs.sketchCanvas
      const container = this.$refs.visArea
      if (!canvas || !container) return
      canvas.width = container.offsetWidth
      canvas.height = container.offsetHeight
      this._setupInteraction()
    },

    redrawCanvas() {
      const canvas = this.$refs.sketchCanvas
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      this.sketchStrokes.forEach(stroke => {
        ctx.strokeStyle = stroke.color
        ctx.lineWidth = stroke.width
        ctx.lineCap = 'round'
        ctx.lineJoin = 'round'
        // ezio: dispatch on type — rect vs freehand stroke
        if (stroke.type === 'rect') {
          ctx.beginPath()
          ctx.rect(stroke.x, stroke.y, stroke.w, stroke.h)
          ctx.stroke()
        } else {
          if (stroke.points.length < 2) return
          ctx.beginPath()
          ctx.moveTo(stroke.points[0][0], stroke.points[0][1])
          for (let i = 1; i < stroke.points.length; i++) {
            ctx.lineTo(stroke.points[i][0], stroke.points[i][1])
          }
          ctx.stroke()
        }
      })
    },

    clearSketches() {
      this.sketchStrokes = []
      this.redrawCanvas()
    },

    // ezio: composite screenshot image + sketch into one image and emit
    handleInput() {
      const img = this.$refs.visArea?.querySelector('img')
      const sketchCanvas = this.$refs.sketchCanvas
      const inputText = this.inputText

      const emitResult = (dataUrl) => {
        this.$emit('snapshot-input', {
          text: inputText,
          selectedItems: [],
          sketchDataUrl: dataUrl
        })
        this.inputText = ''
        // ezio: close snapshot window after annotate
        this.$emit('close')
      }

      if (img && sketchCanvas) {
        const c = document.createElement('canvas')
        c.width = sketchCanvas.width
        c.height = sketchCanvas.height
        const ctx = c.getContext('2d')
        ctx.drawImage(img, 0, 0, c.width, c.height)
        ctx.drawImage(sketchCanvas, 0, 0)
        emitResult(c.toDataURL())
      } else {
        emitResult(sketchCanvas ? sketchCanvas.toDataURL() : null)
      }
    },

    // ezio: simple pen / eraser interaction on canvas
    _setupInteraction() {
      const canvas = this.$refs.sketchCanvas
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      const vm = this

      let isDrawing = false
      let points = []
      // ezio: rect tool drag origin
      let rectStart = null

      const ERASER_RADIUS = 10
      // ezio: hit-test for both freehand strokes and rects
      const isNearItem = (item, x, y) => {
        if (item.type === 'rect') {
          const { x: rx, y: ry, w: rw, h: rh } = item
          const nearLeft   = Math.abs(x - rx) < ERASER_RADIUS && y >= ry - ERASER_RADIUS && y <= ry + rh + ERASER_RADIUS
          const nearRight  = Math.abs(x - (rx + rw)) < ERASER_RADIUS && y >= ry - ERASER_RADIUS && y <= ry + rh + ERASER_RADIUS
          const nearTop    = Math.abs(y - ry) < ERASER_RADIUS && x >= rx - ERASER_RADIUS && x <= rx + rw + ERASER_RADIUS
          const nearBottom = Math.abs(y - (ry + rh)) < ERASER_RADIUS && x >= rx - ERASER_RADIUS && x <= rx + rw + ERASER_RADIUS
          return nearLeft || nearRight || nearTop || nearBottom
        }
        return item.points.some(([px, py]) => Math.hypot(px - x, py - y) < ERASER_RADIUS)
      }

      canvas.addEventListener('mousedown', (e) => {
        isDrawing = true
        const rect = canvas.getBoundingClientRect()
        const x = e.clientX - rect.left
        const y = e.clientY - rect.top
        points = [[x, y]]
        // ezio: rect tool records drag origin
        if (vm.activeTool === 'rect') {
          rectStart = { x, y }
        } else if (vm.activeTool === 'eraser') {
          vm.sketchStrokes = vm.sketchStrokes.filter(s => !isNearItem(s, x, y))
          vm.redrawCanvas()
        }
      })

      canvas.addEventListener('mousemove', (e) => {
        if (!isDrawing) return
        const rect = canvas.getBoundingClientRect()
        const x = e.clientX - rect.left
        const y = e.clientY - rect.top
        points.push([x, y])

        if (vm.activeTool === 'pen') {
          vm.redrawCanvas()
          if (points.length >= 2) {
            ctx.beginPath()
            ctx.moveTo(points[0][0], points[0][1])
            for (let i = 1; i < points.length; i++) ctx.lineTo(points[i][0], points[i][1])
            ctx.strokeStyle = vm.penColor
            ctx.lineWidth = 2
            ctx.lineCap = 'round'
            ctx.lineJoin = 'round'
            ctx.stroke()
          }
        } else if (vm.activeTool === 'rect' && rectStart) {
          // ezio: draw preview rectangle while dragging
          vm.redrawCanvas()
          const rx = Math.min(rectStart.x, x)
          const ry = Math.min(rectStart.y, y)
          const rw = Math.abs(x - rectStart.x)
          const rh = Math.abs(y - rectStart.y)
          ctx.beginPath()
          ctx.rect(rx, ry, rw, rh)
          ctx.strokeStyle = vm.penColor
          ctx.lineWidth = 2
          ctx.stroke()
        } else if (vm.activeTool === 'eraser') {
          vm.sketchStrokes = vm.sketchStrokes.filter(s => !isNearItem(s, x, y))
          vm.redrawCanvas()
        }
      })

      canvas.addEventListener('mouseup', (e) => {
        if (!isDrawing) return
        isDrawing = false
        if (vm.activeTool === 'pen' && points.length >= 2) {
          vm.sketchStrokes.push({ points: points.slice(), color: vm.penColor, width: 2 })
        } else if (vm.activeTool === 'rect' && rectStart) {
          // ezio: finalize rectangle
          const rect = canvas.getBoundingClientRect()
          const x = e.clientX - rect.left
          const y = e.clientY - rect.top
          const rx = Math.min(rectStart.x, x)
          const ry = Math.min(rectStart.y, y)
          const rw = Math.abs(x - rectStart.x)
          const rh = Math.abs(y - rectStart.y)
          if (rw > 2 || rh > 2) {
            vm.sketchStrokes.push({ type: 'rect', x: rx, y: ry, w: rw, h: rh, color: vm.penColor, width: 2 })
          }
          rectStart = null
        }
        vm.redrawCanvas()
        points = []
      })
    }
  }
}
</script>

<style scoped>
.candlestick-snapshot-container {
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  width: 90%;
  max-width: 1000px;
  height: 90vh;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}
.header h2 { margin: 0; font-size: 16px; }
.close-btn {
  background: none; border: none; font-size: 22px;
  cursor: pointer; color: #666; margin-left: auto;
}
.close-btn:hover { color: #000; }

.vis-area {
  flex: 1;
  min-height: 0;
  position: relative;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}
.snapshot-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}
.sketch-overlay {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  z-index: 1;
}
.sketch-overlay.cursor-select { cursor: default; }
.sketch-overlay.cursor-pen { cursor: crosshair; }
.sketch-overlay.cursor-rect { cursor: crosshair; }
.sketch-overlay.cursor-eraser { cursor: pointer; }

.floating-toolbar {
  position: absolute;
  bottom: 8px; right: 8px;
  z-index: 2;
}

.input-area {
  display: flex; gap: 8px; flex-shrink: 0;
}
.text-input {
  flex: 1; padding: 8px 12px;
  border: 1px solid #ddd; border-radius: 4px;
  font-size: 13px; outline: none;
}
.text-input:focus { border-color: #4caf50; }
.send-btn {
  padding: 8px 16px; background: #4caf50; color: white;
  border: none; border-radius: 4px; cursor: pointer;
  font-size: 13px; font-weight: bold;
}
.send-btn:hover { background: #43a047; }
</style>
