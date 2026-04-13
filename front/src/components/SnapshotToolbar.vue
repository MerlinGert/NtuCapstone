<!-- ezio: reusable floating toolbar for snapshot canvas interaction -->
<template>
  <div class="snapshot-toolbar">
    <!-- Select tool -->
    <button class="tb-btn" :class="{ active: tool === 'select' }"
      @click="$emit('update:tool', 'select')" title="Select / Lasso">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z"/>
        <path d="M13 13l6 6"/>
      </svg>
    </button>
    <!-- Pen tool -->
    <button class="tb-btn" :class="{ active: tool === 'pen' }"
      @click="$emit('update:tool', 'pen')" title="Pen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 19l7-7 3 3-7 7H12v-3z"/>
        <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/>
        <path d="M2 2l7.586 7.586"/>
        <circle cx="11" cy="11" r="2"/>
      </svg>
    </button>
    <!-- ezio: Box / Rect tool -->
    <button class="tb-btn" :class="{ active: tool === 'rect' }"
      @click="$emit('update:tool', 'rect')" title="Box">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
      </svg>
    </button>
    <!-- Eraser tool -->
    <button class="tb-btn" :class="{ active: tool === 'eraser' }"
      @click="$emit('update:tool', 'eraser')" title="Eraser">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 20H7L3 16c-.8-.8-.8-2 0-2.8L14.8 1.4c.8-.8 2-.8 2.8 0l4 4c.8.8.8 2 0 2.8L11 19"/>
      </svg>
    </button>

    <span class="tb-sep"></span>

    <!-- Color palette -->
    <span v-for="c in colors" :key="c.value"
      class="color-swatch" :class="{ active: color === c.value }"
      :style="{ background: c.value }"
      :title="c.label"
      @click="onColorClick(c.value)">
    </span>

    <span class="tb-sep"></span>

    <!-- Clear all -->
    <button class="tb-btn tb-danger" @click="$emit('clear')" title="Clear All">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="3 6 5 6 21 6"/>
        <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
        <path d="M10 11v6"/>
        <path d="M14 11v6"/>
        <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
      </svg>
    </button>
  </div>
</template>

<script>
// ezio: SnapshotToolbar — emits update:tool, update:color, clear
export default {
  name: 'SnapshotToolbar',
  props: {
    tool:  { type: String, default: 'select' },
    color: { type: String, default: 'rgba(255,60,60,0.7)' }
  },
  data() {
    return {
      colors: [
        { value: 'rgba(255,60,60,0.7)',   label: 'Red' },
        { value: 'rgba(33,150,243,0.7)',   label: 'Blue' },
        { value: 'rgba(76,175,80,0.7)',    label: 'Green' },
        { value: 'rgba(255,152,0,0.7)',    label: 'Orange' },
        { value: 'rgba(50,50,50,0.8)',     label: 'Black' }
      ]
    };
  },
  methods: {
    // ezio: keep rect tool active when changing color; otherwise switch to pen
    onColorClick(color) {
      this.$emit('update:color', color);
      if (this.tool !== 'rect') {
        this.$emit('update:tool', 'pen');
      }
    }
  }
};
</script>

<style scoped>
.snapshot-toolbar {
  display: flex;
  align-items: center;
  gap: 3px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  padding: 3px 5px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.10);
  user-select: none;
}

/* ── buttons ── */
.tb-btn {
  width: 28px;
  height: 28px;
  border: 1.5px solid transparent;
  border-radius: 5px;
  background: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  transition: all 0.12s;
  padding: 4px;
}
.tb-btn svg {
  width: 16px;
  height: 16px;
  display: block;
}
.tb-btn:hover              { background: #f0f0f0; color: #333; }
.tb-btn.active             { background: #e3f2fd; border-color: #4299e1; color: #4299e1; }
.tb-btn.tb-danger          { color: #999; }
.tb-btn.tb-danger:hover    { background: #ffebee; color: #d32f2f; }

/* ── separator ── */
.tb-sep {
  width: 1px;
  height: 16px;
  background: #ddd;
  margin: 0 2px;
  flex-shrink: 0;
}

/* ── color swatches ── */
.color-swatch {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.12s;
  flex-shrink: 0;
}
.color-swatch:hover  { transform: scale(1.15); }
.color-swatch.active { border-color: #333; transform: scale(1.2); }
</style>
