<template>
  <div class="layout-container" ref="container">
    <svg class="main-svg" :width="svgWidth" :height="svgHeight">
      <!-- 定义样式 -->
      <defs>
        <!-- 阴影效果 -->
        <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
          <feOffset dx="2" dy="2" result="offsetblur"/>
          <feComponentTransfer>
            <feFuncA type="linear" slope="0.2"/>
          </feComponentTransfer>
          <feMerge>
            <feMergeNode/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      <!-- 左侧大矩形 -->
      <g class="left-panel">
        <rect
          :x="layout.left.x"
          :y="layout.left.y"
          :width="layout.left.width"
          :height="layout.left.height"
          :rx="borderRadius"
          :ry="borderRadius"
          :fill="colorScheme.leftBg"
          :stroke="colorScheme.border"
          :stroke-width="strokeWidth"
          class="panel-rect"
          filter="url(#shadow)"
        />
        <!-- 左侧标题 -->
        <text
          :x="layout.left.x + 20"
          :y="layout.left.y + 35"
          class="panel-title"
          :fill="colorScheme.titleText"
        >
          左侧主视图区域
        </text>
        <!-- 左侧内容区域标记 -->
        <rect
          :x="layout.left.x + margin.inner"
          :y="layout.left.y + 60"
          :width="layout.left.width - margin.inner * 2"
          :height="layout.left.height - 80"
          :rx="borderRadius / 2"
          :ry="borderRadius / 2"
          :fill="colorScheme.contentBg"
          :stroke="colorScheme.contentBorder"
          :stroke-width="1"
          stroke-dasharray="5,5"
          opacity="0.5"
        />
        <text
          :x="layout.left.x + layout.left.width / 2"
          :y="layout.left.y + layout.left.height / 2"
          text-anchor="middle"
          dominant-baseline="middle"
          fill="#999"
          font-size="16"
        >
          主要内容区域 (2/3 高度)
        </text>
      </g>

      <!-- 右上矩形 -->
      <g class="right-top-panel">
        <rect
          :x="layout.rightTop.x"
          :y="layout.rightTop.y"
          :width="layout.rightTop.width"
          :height="layout.rightTop.height"
          :rx="borderRadius"
          :ry="borderRadius"
          :fill="colorScheme.rightTopBg"
          :stroke="colorScheme.border"
          :stroke-width="strokeWidth"
          class="panel-rect"
          filter="url(#shadow)"
        />
        <!-- 右上标题 -->
        <text
          :x="layout.rightTop.x + 20"
          :y="layout.rightTop.y + 35"
          class="panel-title"
          :fill="colorScheme.titleText"
        >
          右上视图区域
        </text>
        <!-- 右上内容区域标记 -->
        <rect
          :x="layout.rightTop.x + margin.inner"
          :y="layout.rightTop.y + 60"
          :width="layout.rightTop.width - margin.inner * 2"
          :height="layout.rightTop.height - 80"
          :rx="borderRadius / 2"
          :ry="borderRadius / 2"
          :fill="colorScheme.contentBg"
          :stroke="colorScheme.contentBorder"
          :stroke-width="1"
          stroke-dasharray="5,5"
          opacity="0.5"
        />
        <text
          :x="layout.rightTop.x + layout.rightTop.width / 2"
          :y="layout.rightTop.y + layout.rightTop.height / 2"
          text-anchor="middle"
          dominant-baseline="middle"
          fill="#999"
          font-size="14"
        >
          右上内容区域
        </text>
      </g>

      <!-- 右下矩形 -->
      <g class="right-bottom-panel">
        <rect
          :x="layout.rightBottom.x"
          :y="layout.rightBottom.y"
          :width="layout.rightBottom.width"
          :height="layout.rightBottom.height"
          :rx="borderRadius"
          :ry="borderRadius"
          :fill="colorScheme.rightBottomBg"
          :stroke="colorScheme.border"
          :stroke-width="strokeWidth"
          class="panel-rect"
          filter="url(#shadow)"
        />
        <!-- 右下标题 -->
        <text
          :x="layout.rightBottom.x + 20"
          :y="layout.rightBottom.y + 35"
          class="panel-title"
          :fill="colorScheme.titleText"
        >
          右下视图区域
        </text>
        <!-- 右下内容区域标记 -->
        <rect
          :x="layout.rightBottom.x + margin.inner"
          :y="layout.rightBottom.y + 60"
          :width="layout.rightBottom.width - margin.inner * 2"
          :height="layout.rightBottom.height - 80"
          :rx="borderRadius / 2"
          :ry="borderRadius / 2"
          :fill="colorScheme.contentBg"
          :stroke="colorScheme.contentBorder"
          :stroke-width="1"
          stroke-dasharray="5,5"
          opacity="0.5"
        />
        <text
          :x="layout.rightBottom.x + layout.rightBottom.width / 2"
          :y="layout.rightBottom.y + layout.rightBottom.height / 2"
          text-anchor="middle"
          dominant-baseline="middle"
          fill="#999"
          font-size="14"
        >
          右下内容区域
        </text>
      </g>
    </svg>

    <!-- 布局信息面板 -->
    <div class="info-panel">
      <div class="info-item">
        <span class="info-label">左侧区域:</span>
        <span class="info-value">{{ layout.left.width.toFixed(0) }} × {{ layout.left.height.toFixed(0) }} px</span>
      </div>
      <div class="info-item">
        <span class="info-label">右上区域:</span>
        <span class="info-value">{{ layout.rightTop.width.toFixed(0) }} × {{ layout.rightTop.height.toFixed(0) }} px</span>
      </div>
      <div class="info-item">
        <span class="info-label">右下区域:</span>
        <span class="info-value">{{ layout.rightBottom.width.toFixed(0) }} × {{ layout.rightBottom.height.toFixed(0) }} px</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ThreeRectLayout',
  props: {
    data: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      // SVG 尺寸
      svgWidth: 0,
      svgHeight: 0,
      
      // 边距设置
      margin: {
        outer: 20,    // 外边距
        gap: 15,      // 矩形之间的间距
        inner: 15     // 内边距
      },
      
      // 样式设置
      borderRadius: 12,   // 圆角半径
      strokeWidth: 2,     // 边框粗细
      
      // 布局配置
      leftWidthRatio: 0.65,  // 左侧宽度占比 (65%)
      leftHeightRatio: 0.67, // 左侧高度占比 (2/3)
      
      // 布局数据
      layout: {
        left: { x: 0, y: 0, width: 0, height: 0 },
        rightTop: { x: 0, y: 0, width: 0, height: 0 },
        rightBottom: { x: 0, y: 0, width: 0, height: 0 }
      },
      
      // 配色方案
      colorScheme: {
        leftBg: '#f0f4f8',
        rightTopBg: '#e6f7ff',
        rightBottomBg: '#f6ffed',
        contentBg: '#ffffff',
        border: '#4a90e2',
        contentBorder: '#cbd5e0',
        titleText: '#2d3748'
      }
    }
  },
  methods: {
    // 设置 SVG 尺寸
    setSvgSize() {
      if (this.$refs.container) {
        this.svgWidth = this.$refs.container.offsetWidth
        this.svgHeight = this.$refs.container.offsetHeight - 60 // 减去信息面板高度
        this.calculateLayout()
      }
    },
    
    // 计算布局
    calculateLayout() {
      const { outer, gap } = this.margin
      const availableWidth = this.svgWidth - outer * 2
      const availableHeight = this.svgHeight - outer * 2
      
      // 左侧大矩形
      const leftWidth = availableWidth * this.leftWidthRatio - gap / 2
      const leftHeight = availableHeight * this.leftHeightRatio
      
      this.layout.left = {
        x: outer,
        y: outer,
        width: leftWidth,
        height: leftHeight
      }
      
      // 右侧宽度
      const rightWidth = availableWidth * (1 - this.leftWidthRatio) - gap / 2
      
      // 右上矩形
      const rightTopHeight = (availableHeight - gap) / 2
      
      this.layout.rightTop = {
        x: outer + leftWidth + gap,
        y: outer,
        width: rightWidth,
        height: rightTopHeight
      }
      
      // 右下矩形
      this.layout.rightBottom = {
        x: outer + leftWidth + gap,
        y: outer + rightTopHeight + gap,
        width: rightWidth,
        height: availableHeight - rightTopHeight - gap
      }
    }
  },
  mounted() {
    window.addEventListener('resize', this.setSvgSize)
    this.$nextTick(() => {
      this.setSvgSize()
    })
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.setSvgSize)
  }
}
</script>

<style scoped>
.layout-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: #fafafa;
  display: flex;
  flex-direction: column;
}

.main-svg {
  display: block;
  flex: 1;
}

.panel-rect {
  transition: all 0.3s ease;
}

.panel-rect:hover {
  filter: url(#shadow) brightness(1.02);
}

.panel-title {
  font-family: 'Arial', sans-serif;
  font-size: 18px;
  font-weight: bold;
}

/* 信息面板样式 */
.info-panel {
  height: 60px;
  background: #ffffff;
  border-top: 2px solid #e2e8f0;
  padding: 10px 20px;
  display: flex;
  gap: 30px;
  align-items: center;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
}

.info-item {
  display: flex;
  gap: 10px;
  align-items: center;
}

.info-label {
  font-size: 14px;
  font-weight: 600;
  color: #4a5568;
}

.info-value {
  font-size: 14px;
  color: #2d3748;
  font-family: 'Courier New', monospace;
  background: #f7fafc;
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}
</style>

