<template>
    <div class="token-snapshot-container">
        <div class="header">
            <h2>Token Snapshot — {{ snapshotData.time }}</h2>
            <span v-if="selectedCount > 0" class="selection-badge">{{ selectedCount }} nodes selected</span>
            <button class="close-btn" @click="$emit('close')">×</button>
        </div>

        <!-- ezio: 可视化区域 + 浮动工具栏 -->
        <div class="vis-area" ref="svgContainer">
            <svg ref="snapshotSvg"></svg>
            <!-- ezio: preserved hover tooltip from snapshot — matches original tooltip per node type -->
            <div v-if="snapshotData.hoveredNode" ref="hoverTooltip" class="snapshot-tooltip" :style="tooltipStyle" v-html="hoveredTooltipHtml"></div>
            <canvas ref="lassoCanvas" class="lasso-overlay"
                :class="'cursor-' + activeTool"></canvas>
            <!-- ezio: toolbar component -->
            <SnapshotToolbar class="floating-toolbar"
                :tool="activeTool" :color="penColor"
                @update:tool="activeTool = $event"
                @update:color="penColor = $event"
                @clear="clearSketches" />
        </div>

        <!-- 选中节点详情：可折叠 -->
        <div class="details-panel">
            <div class="details-header" @click="detailsOpen = !detailsOpen">
                <span>{{ detailsOpen ? '▼' : '▶' }} Selected Nodes Details</span>
                <span class="details-count" v-if="selectedNodes.length > 0">({{ selectedNodes.length }})</span>
            </div>
            <div v-if="detailsOpen" class="details-body">
                <!-- ezio: mode-aware help text -->
                <div v-if="selectedNodes.length === 0" class="details-empty">
                    Use lasso or click to select nodes in the visualization above.
                </div>
                <table v-else class="details-table">
                    <thead>
                        <tr>
                            <th>Address</th>
                            <th>Balance</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="node in selectedNodes" :key="node.id">
                            <td class="addr">{{ node.id.substring(0, 8) }}...{{ node.id.substring(node.id.length - 6) }}</td>
                            <td>{{ node.value.toLocaleString() }}</td>
                            <td>
                                <span v-if="node.suspicious" class="suspicious-tag">Suspicious</span>
                                <span v-else class="normal-tag">Normal</span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 文本输入区域 -->
        <div class="input-area">
            <input
                type="text"
                v-model="inputText"
                placeholder="Enter text here..."
                @keyup.enter="handleInput"
                class="text-input"
            />
            <button @click="handleInput" class="send-btn">Annotate</button>
        </div>
    </div>
</template>

<script>
import * as d3 from "d3"
// ezio: toolbar component
import SnapshotToolbar from "./SnapshotToolbar.vue"

export default {
    name: "TokenSnapshot",
    components: { SnapshotToolbar },
    props: {
        snapshotData: { type: Object, required: true }
    },
    data() {
        return {
            selectedCount: 0,
            selectedNodes: [],
            detailsOpen: true,
            inputText: "",
            // ezio: toolbar state
            activeTool: 'select',    // 'select' | 'pen' | 'eraser'
            penColor: 'rgba(255,60,60,0.7)',
            sketchStrokes: [],       // [{points, color, width}, ...]
            // ezio: hovered node screen position for tooltip
            hoveredNodeScreenX: null,
            hoveredNodeScreenY: null,
            tooltipLeft: 0,
            tooltipTop: 0,
        };
    },
    // ezio: redraw canvas when switching modes
    watch: {
        activeTool() {
            this.redrawCanvas();
        }
    },
    // ezio: computed tooltip for hovered node — mirrors original TokenDistribution tooltip per type
    computed: {
        tooltipStyle() {
            if (this.hoveredNodeScreenX == null) return { display: 'none' };
            return {
                left: this.tooltipLeft + 'px',
                top: this.tooltipTop + 'px',
            };
        },
        hoveredTooltipHtml() {
            const hn = this.snapshotData && this.snapshotData.hoveredNode;
            if (!hn) return '';
            if (hn.type === 'single') {
                // ezio: matches single-node tooltip in TokenDistribution
                let html = `<strong>Address:</strong> ${hn.id}<br/>`;
                html += `<strong>Balance:</strong> ${hn.value.toFixed(2)}<br/>`;
                if (hn.isRelated) html += '<strong>Type:</strong> Related User<br/>';
                if (hn.suspicious) {
                    html += `<br><strong style="color:red">Suspicious Activity Detected!</strong>`;
                    if (hn.suspicious.reasons && hn.suspicious.reasons.length > 0) {
                        html += `<ul style="margin: 5px 0; padding-left: 15px; text-align: left;">`;
                        hn.suspicious.reasons.forEach(r => { html += `<li style="font-size: 10px;">${r}</li>`; });
                        html += `</ul>`;
                    }
                }
                if (hn.detectionInfo) html += `<br><strong>Entity ID:</strong> ${hn.detectionInfo.entityId}<br/>`;
                return html;
            } else {
                // ezio: matches group-member tooltip in TokenDistribution
                let html = `Address: ${(hn.name || hn.id).substring(0, 6)}...<br>Balance: ${hn.value.toLocaleString()}`;
                if (hn.suspicious) {
                    html += `<br><strong style="color:red">Suspicious Activity Detected!</strong>`;
                    if (hn.suspicious.reasons && hn.suspicious.reasons.length > 0) {
                        html += `<ul style="margin: 5px 0; padding-left: 15px; text-align: left;">`;
                        hn.suspicious.reasons.forEach(r => { html += `<li style="font-size: 10px;">${r}</li>`; });
                        html += '</ul>';
                    } else {
                        html += `<br>Diff: ${hn.suspicious.diff.toFixed(2)}`;
                    }
                }
                if (hn.detectionInfo) {
                    html += `<br><strong style="color:orange">Entity Group Detected</strong>`;
                    if (hn.detectionInfo.reason && hn.detectionInfo.reason.length > 0) {
                        html += `<ul style="margin: 5px 0; padding-left: 15px; text-align: left;">`;
                        hn.detectionInfo.reason.forEach(r => { html += `<li style="font-size: 10px;">${r}</li>`; });
                        html += '</ul>';
                    }
                }
                return html;
            }
        },
    },
    mounted() {
        this.$nextTick(() => {
            this.renderSnapshot();
            this.setupLasso();
        });
    },
    methods: {
        // ezio: allow empty text; capture full screenshot (SVG + sketch canvas composited)
        handleInput() {
            const svgEl = this.$refs.snapshotSvg;
            const sketchCanvas = this.$refs.lassoCanvas;
            const container = this.$refs.svgContainer;
            const w = container ? container.offsetWidth : 800;
            const h = container ? container.offsetHeight : 400;
            const inputText = this.inputText;
            const selectedIds = this.selectedNodes.map(n => n.id);

            // ezio: helper to emit and reset
            const emitResult = (dataUrl) => {
                this.$emit('snapshot-input', {
                    text: inputText,
                    selectedIds,
                    sketchDataUrl: dataUrl
                });
                this.inputText = '';
                // ezio: close snapshot window after annotate
                this.$emit('close');
            };

            // ezio: composite SVG + sketch canvas into one image
            if (svgEl) {
                const svgData = new XMLSerializer().serializeToString(svgEl);
                const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
                const url = URL.createObjectURL(svgBlob);
                const img = new Image();
                img.onload = () => {
                    const c = document.createElement('canvas');
                    c.width = w;
                    c.height = h;
                    const ctx = c.getContext('2d');
                    ctx.fillStyle = '#ffffff';
                    ctx.fillRect(0, 0, w, h);
                    ctx.drawImage(img, 0, 0, w, h);
                    URL.revokeObjectURL(url);
                    if (sketchCanvas) ctx.drawImage(sketchCanvas, 0, 0);
                    emitResult(c.toDataURL());
                };
                img.onerror = () => {
                    URL.revokeObjectURL(url);
                    emitResult(sketchCanvas ? sketchCanvas.toDataURL() : null);
                };
                img.src = url;
            } else {
                emitResult(sketchCanvas ? sketchCanvas.toDataURL() : null);
            }
        },

        renderSnapshot() {
            const data = this.snapshotData;
            if (!data) return;

            const container = this.$refs.svgContainer;
            const width = container.offsetWidth;
            const height = container.offsetHeight;
            const centerX = width / 2;
            const centerY = height / 2;

            const scaleX = width / data.width;
            const scaleY = height / data.height;
            const scale = Math.min(scaleX, scaleY, 1);

            this._width = width;
            this._height = height;
            this._centerX = centerX;
            this._centerY = centerY;
            this._scale = scale;

            const svg = d3.select(this.$refs.snapshotSvg)
                .attr("width", width)
                .attr("height", height);

            svg.selectAll("*").remove();

            const g = svg.append("g")
                .attr("transform", `translate(${centerX},${centerY}) scale(${scale})`);

            // Draw "Others" ring
            if (data.othersBalance > 0) {
                const totalBalance = data.usersBalance + data.othersBalance;
                const minDim = Math.min(data.width, data.height);
                const margin = 20;
                const maxGroupRadius = (minDim / 2) - margin;
                const totalAvailableArea = Math.PI * maxGroupRadius * maxGroupRadius;
                const targetTotalInkArea = totalAvailableArea * data.scaleFactor;
                const targetRingArea = totalBalance > 0 ? targetTotalInkArea * (data.othersBalance / totalBalance) : 0;
                const userGroupRadius = Math.sqrt(maxGroupRadius * maxGroupRadius - targetRingArea / Math.PI);
                const arc = d3.arc()
                    .innerRadius(userGroupRadius)
                    .outerRadius(maxGroupRadius)
                    .startAngle(0)
                    .endAngle(2 * Math.PI);
                g.append("path")
                    .attr("d", arc)
                    .style("fill", "#e3f2fd")
                    .style("opacity", 0.5);
            }

            // Build node position lookup for links
            const nodePositions = new Map();
            data.nodes.forEach(n => {
                nodePositions.set(n.id, { x: n.x, y: n.y });
                if (n.type === 'group' && n.children) {
                    n.children.forEach(c => {
                        nodePositions.set(c.id, { x: n.x + c.cx, y: n.y + c.cy });
                    });
                }
            });

            const userToNodeId = new Map();
            data.nodes.forEach(n => {
                if (n.type === 'single') {
                    userToNodeId.set(n.id, n.id);
                } else if (n.type === 'group' && n.children) {
                    n.children.forEach(c => userToNodeId.set(c.id, n.id));
                }
            });

            // Draw links
            if (data.links && data.links.length > 0) {
                const linkGroup = g.append("g").attr("class", "links");
                const aggLinks = new Map();
                data.links.forEach(l => {
                    const sId = userToNodeId.get(l.source);
                    const tId = userToNodeId.get(l.target);
                    const linkType = l.type || 'link';
                    if (sId && tId && sId !== tId) {
                        const key = `${sId}-${tId}-${linkType}`;
                        if (!aggLinks.has(key)) aggLinks.set(key, { source: sId, target: tId, weight: 0, type: linkType });
                        aggLinks.get(key).weight += l.weight;
                    }
                });
                aggLinks.forEach(link => {
                    const sp = nodePositions.get(link.source);
                    const tp = nodePositions.get(link.target);
                    if (sp && tp) {
                        linkGroup.append("line")
                            .datum(link)
                            .attr("class", "snapshot-link")
                            .attr("x1", sp.x).attr("y1", sp.y)
                            .attr("x2", tp.x).attr("y2", tp.y)
                            .attr("stroke", link.type === 'entity' ? '#ff9800' : '#999')
                            .style("stroke-dasharray", link.type === 'entity' ? '5,5' : 'none')
                            .attr("stroke-opacity", 0.6)
                            .attr("stroke-width", Math.max(1, Math.min(Math.sqrt(link.weight), 5)));
                    }
                });
            }

            const bubbleGroup = g.append("g");

            // Draw groups
            data.nodes.filter(n => n.type === 'group').forEach(groupNode => {
                const gg = bubbleGroup.append("g")
                    .attr("class", "group")
                    .attr("transform", `translate(${groupNode.x},${groupNode.y})`);

                gg.append("circle")
                    .attr("r", groupNode.r)
                    .style("fill", "white")
                    .style("fill-opacity", 0.3)
                    .style("stroke", "#ff9800")
                    .style("stroke-width", 2)
                    .style("stroke-dasharray", "5,5");

                if (groupNode.children) {
                    groupNode.children.forEach(child => {
                        gg.append("circle")
                            .attr("class", "bubble member")
                            .attr("cx", child.cx)
                            .attr("cy", child.cy)
                            .attr("r", child.r)
                            .style("fill", child.fill)
                            .style("opacity", 0.6)
                            .style("stroke", child.suspicious ? "#ff0000" : "#5976ba")
                            .style("stroke-width", child.suspicious ? 3 : 2)
                            .datum(child);
                    });
                }
            });

            // Draw singles
            data.nodes.filter(n => n.type === 'single').forEach(node => {
                bubbleGroup.append("circle")
                    .attr("class", "bubble single")
                    .attr("cx", node.x)
                    .attr("cy", node.y)
                    .attr("r", node.r)
                    .style("fill", node.fill)
                    .style("opacity", 0.6)
                    .style("stroke", node.suspicious ? "#ff0000" : "#5976ba")
                    .style("stroke-width", node.suspicious ? 3 : 2)
                    .datum(node);
            });

            // 预计算所有可选节点的屏幕坐标 + 保存完整数据用于详情面板
            this._selectableNodes = [];
            data.nodes.forEach(n => {
                if (n.type === 'single') {
                    this._selectableNodes.push({
                        id: n.id, value: n.value, suspicious: n.suspicious,
                        screenX: centerX + n.x * scale,
                        screenY: centerY + n.y * scale
                    });
                } else if (n.type === 'group' && n.children) {
                    n.children.forEach(c => {
                        this._selectableNodes.push({
                            id: c.id, value: c.value, suspicious: c.suspicious,
                            screenX: centerX + (n.x + c.cx) * scale,
                            screenY: centerY + (n.y + c.cy) * scale
                        });
                    });
                }
            });

            // ezio: highlight hovered node and compute tooltip position (clamped to container)
            if (data.hoveredNode) {
                const hn = data.hoveredNode;
                const matchNode = this._selectableNodes.find(n => n.id === hn.id);
                if (matchNode) {
                    // set raw position first so tooltip renders, then clamp in $nextTick
                    this.hoveredNodeScreenX = matchNode.screenX;
                    this.hoveredNodeScreenY = matchNode.screenY;
                    this.tooltipLeft = matchNode.screenX + 15;
                    this.tooltipTop = matchNode.screenY - 10;

                    this.$nextTick(() => {
                        const tip = this.$refs.hoverTooltip;
                        const box = this.$refs.svgContainer;
                        if (tip && box) {
                            const tw = tip.offsetWidth;
                            const th = tip.offsetHeight;
                            const bw = box.offsetWidth;
                            const bh = box.offsetHeight;
                            let lx = matchNode.screenX + 15;
                            let ly = matchNode.screenY - 10;
                            // flip left if overflows right
                            if (lx + tw > bw) lx = matchNode.screenX - tw - 10;
                            // flip up if overflows bottom (reserve 50px for toolbar)
                            if (ly + th > bh - 50) ly = bh - th - 50;
                            // clamp to top/left edges
                            if (lx < 5) lx = 5;
                            if (ly < 5) ly = 5;
                            this.tooltipLeft = lx;
                            this.tooltipTop = ly;
                        }
                    });

                    // find node radius for highlight ring
                    let hx, hy, hr;
                    for (const n of data.nodes) {
                        if (n.type === 'single' && n.id === hn.id) {
                            hx = n.x; hy = n.y; hr = n.r;
                            break;
                        }
                        if (n.type === 'group' && n.children) {
                            const child = n.children.find(c => c.id === hn.id);
                            if (child) {
                                hx = n.x + child.cx; hy = n.y + child.cy; hr = child.r;
                                break;
                            }
                        }
                    }
                    if (hr != null) {
                        bubbleGroup.append("circle")
                            .attr("cx", hx).attr("cy", hy)
                            .attr("r", hr + 3)
                            .style("fill", "none")
                            .style("stroke", "#fdd835")
                            .style("stroke-width", 3)
                            .style("stroke-dasharray", "4,2");
                    }
                }
            }
        },

        // ezio: clear all sketch strokes
        clearSketches() {
            this.sketchStrokes = [];
            this.redrawCanvas();
        },

        // ezio: redraw persistent sketch strokes and rects on canvas
        redrawCanvas() {
            const canvas = this.$refs.lassoCanvas;
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            this.sketchStrokes.forEach(stroke => {
                ctx.strokeStyle = stroke.color;
                ctx.lineWidth = stroke.width;
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';
                ctx.setLineDash([]);
                // ezio: dispatch on type — rect vs freehand stroke
                if (stroke.type === 'rect') {
                    ctx.beginPath();
                    ctx.rect(stroke.x, stroke.y, stroke.w, stroke.h);
                    ctx.stroke();
                } else {
                    if (stroke.points.length < 2) return;
                    ctx.beginPath();
                    ctx.moveTo(stroke.points[0][0], stroke.points[0][1]);
                    for (let i = 1; i < stroke.points.length; i++) {
                        ctx.lineTo(stroke.points[i][0], stroke.points[i][1]);
                    }
                    ctx.stroke();
                }
            });
        },

        setupLasso() {
            const canvas = this.$refs.lassoCanvas;
            const container = this.$refs.svgContainer;
            canvas.width = container.offsetWidth;
            canvas.height = container.offsetHeight;
            const ctx = canvas.getContext("2d");

            let isDrawing = false;
            let hasMoved = false; // 区分点击 vs 拖拽
            let points = [];

            // 维护当前选中集合（用于点击 toggle）
            const selectedSet = new Set();

            // 更新 SVG 高亮（根据 selectedSet）
            const updateHighlight = () => {
                const svg = d3.select(this.$refs.snapshotSvg);
                if (selectedSet.size > 0) {
                    svg.selectAll(".bubble").each(function(d) {
                        if (!d) return;
                        if (selectedSet.has(d.id)) {
                            d3.select(this)
                                .style("opacity", 1.0)
                                .style("stroke", "#fdd835")
                                .style("stroke-width", 4);
                        } else {
                            d3.select(this)
                                .style("opacity", 0.15)
                                .style("stroke", d.suspicious ? "#ff0000" : "#5976ba")
                                .style("stroke-width", d.suspicious ? 3 : 2);
                        }
                    });
                    // Links: highlight if both endpoints are selected, dim otherwise
                    svg.selectAll(".snapshot-link").each(function(d) {
                        if (!d) return;
                        if (selectedSet.has(d.source) && selectedSet.has(d.target)) {
                            d3.select(this).attr("stroke-opacity", 1.0);
                        } else {
                            d3.select(this).attr("stroke-opacity", 0.15);
                        }
                    });
                } else {
                    // 没有选中节点时恢复默认样式
                    svg.selectAll(".bubble")
                        .style("opacity", 0.6)
                        .each(function(d) {
                            if (d) {
                                d3.select(this)
                                    .style("stroke", d.suspicious ? "#ff0000" : "#5976ba")
                                    .style("stroke-width", d.suspicious ? 3 : 2);
                            }
                        });
                    svg.selectAll(".snapshot-link")
                        .attr("stroke-opacity", 0.6);
                }
                // 同步 Vue 状态
                this.selectedNodes = this._selectableNodes.filter(n => selectedSet.has(n.id));
                this.selectedCount = this.selectedNodes.length;
                this.$emit('lasso-select', Array.from(selectedSet));
            };

            // 找到点击位置最近的节点（在半径范围内）
            const findClickedNode = (x, y) => {
                let closest = null;
                let minDist = Infinity;
                this._selectableNodes.forEach(n => {
                    const dx = x - n.screenX, dy = y - n.screenY;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    // 用节点半径作为点击判定范围（乘以 scale）
                    if (dist < minDist) {
                        minDist = dist;
                        closest = n;
                    }
                });
                // 允许一定的点击容差（30px）
                return (closest && minDist < 30) ? closest : null;
            };

            // ezio: capture vm for use in event listeners
            const vm = this;
            // ezio: rect tool drag origin
            let rectStart = null;

            // ezio: hit-test helper for both freehand strokes and rects
            const ERASER_RADIUS = 10;
            const isNearItem = (item, x, y) => {
                if (item.type === 'rect') {
                    const { x: rx, y: ry, w: rw, h: rh } = item;
                    const nearLeft   = Math.abs(x - rx) < ERASER_RADIUS && y >= ry - ERASER_RADIUS && y <= ry + rh + ERASER_RADIUS;
                    const nearRight  = Math.abs(x - (rx + rw)) < ERASER_RADIUS && y >= ry - ERASER_RADIUS && y <= ry + rh + ERASER_RADIUS;
                    const nearTop    = Math.abs(y - ry) < ERASER_RADIUS && x >= rx - ERASER_RADIUS && x <= rx + rw + ERASER_RADIUS;
                    const nearBottom = Math.abs(y - (ry + rh)) < ERASER_RADIUS && x >= rx - ERASER_RADIUS && x <= rx + rw + ERASER_RADIUS;
                    return nearLeft || nearRight || nearTop || nearBottom;
                }
                return item.points.some(([px, py]) => Math.hypot(px - x, py - y) < ERASER_RADIUS);
            };

            canvas.addEventListener("mousedown", (e) => {
                isDrawing = true;
                hasMoved = false;
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                points = [[x, y]];

                // ezio: rect tool records drag origin
                if (vm.activeTool === 'rect') {
                    rectStart = { x, y };
                } else if (vm.activeTool === 'eraser') {
                    // ezio: eraser immediately erases on mousedown
                    vm.sketchStrokes = vm.sketchStrokes.filter(s => !isNearItem(s, x, y));
                }
                vm.redrawCanvas();
            });

            canvas.addEventListener("mousemove", (e) => {
                if (!isDrawing) return;
                hasMoved = true;
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                points.push([x, y]);

                // ezio: branch on active tool
                if (vm.activeTool === 'pen') {
                    vm.redrawCanvas();
                    if (points.length >= 2) {
                        ctx.beginPath();
                        ctx.moveTo(points[0][0], points[0][1]);
                        for (let i = 1; i < points.length; i++) {
                            ctx.lineTo(points[i][0], points[i][1]);
                        }
                        ctx.strokeStyle = vm.penColor;
                        ctx.lineWidth = 2;
                        ctx.lineCap = 'round';
                        ctx.lineJoin = 'round';
                        ctx.setLineDash([]);
                        ctx.stroke();
                    }
                } else if (vm.activeTool === 'rect' && rectStart) {
                    // ezio: draw preview rectangle while dragging
                    vm.redrawCanvas();
                    const rx = Math.min(rectStart.x, x);
                    const ry = Math.min(rectStart.y, y);
                    const rw = Math.abs(x - rectStart.x);
                    const rh = Math.abs(y - rectStart.y);
                    ctx.beginPath();
                    ctx.rect(rx, ry, rw, rh);
                    ctx.strokeStyle = vm.penColor;
                    ctx.lineWidth = 2;
                    ctx.setLineDash([]);
                    ctx.stroke();
                } else if (vm.activeTool === 'eraser') {
                    // ezio: erase strokes touched by the eraser path
                    vm.sketchStrokes = vm.sketchStrokes.filter(s => !isNearItem(s, x, y));
                    vm.redrawCanvas();
                } else {
                    // select mode: draw lasso polygon
                    vm.redrawCanvas();
                    ctx.beginPath();
                    ctx.moveTo(points[0][0], points[0][1]);
                    for (let i = 1; i < points.length; i++) {
                        ctx.lineTo(points[i][0], points[i][1]);
                    }
                    ctx.closePath();
                    ctx.fillStyle = "rgba(255, 235, 59, 0.2)";
                    ctx.fill();
                    ctx.strokeStyle = "#fbc02d";
                    ctx.lineWidth = 2;
                    ctx.setLineDash([4, 4]);
                    ctx.stroke();
                }
            });

            canvas.addEventListener("mouseup", (e) => {
                if (!isDrawing) return;
                isDrawing = false;

                // ezio: branch on active tool
                if (vm.activeTool === 'pen') {
                    if (hasMoved && points.length >= 2) {
                        vm.sketchStrokes.push({
                            points: points.slice(),
                            color: vm.penColor,
                            width: 2
                        });
                    }
                    vm.redrawCanvas();
                } else if (vm.activeTool === 'rect' && rectStart) {
                    // ezio: finalize rectangle
                    const rect = canvas.getBoundingClientRect();
                    const fx = e.clientX - rect.left;
                    const fy = e.clientY - rect.top;
                    const rx = Math.min(rectStart.x, fx);
                    const ry = Math.min(rectStart.y, fy);
                    const rw = Math.abs(fx - rectStart.x);
                    const rh = Math.abs(fy - rectStart.y);
                    if (rw > 2 || rh > 2) {
                        vm.sketchStrokes.push({ type: 'rect', x: rx, y: ry, w: rw, h: rh, color: vm.penColor, width: 2 });
                    }
                    rectStart = null;
                    vm.redrawCanvas();
                } else if (vm.activeTool === 'eraser') {
                    vm.redrawCanvas();
                } else {
                    // select mode
                    vm.redrawCanvas();

                    if (!hasMoved || points.length < 3) {
                        // 点击模式：toggle 最近的节点
                        const rect = canvas.getBoundingClientRect();
                        const cx = e.clientX - rect.left;
                        const cy = e.clientY - rect.top;
                        const node = findClickedNode(cx, cy);
                        if (node) {
                            if (selectedSet.has(node.id)) {
                                selectedSet.delete(node.id);
                            } else {
                                selectedSet.add(node.id);
                            }
                            updateHighlight();
                        }
                        return;
                    }

                    // ezio: Lasso 模式：选中框内所有节点（追加到当前选择）
                    vm._selectableNodes.forEach(n => {
                        if (d3.polygonContains(points, [n.screenX, n.screenY])) {
                            selectedSet.add(n.id);
                        }
                    });
                    updateHighlight();
                }
                points = [];
            });
        }
    }
}
</script>

<style scoped>
.token-snapshot-container {
    background: white;
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    width: 90%;
    max-width: 600px;
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

.header h2 {
    margin: 0;
    font-size: 16px;
}

.selection-badge {
    background: #fdd835;
    color: #333;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: bold;
}

.close-btn {
    background: none;
    border: none;
    font-size: 22px;
    cursor: pointer;
    color: #666;
    margin-left: auto;
}

.close-btn:hover {
    color: #000;
}

/* ezio: preserved hover tooltip — boundary-aware positioning */
.snapshot-tooltip {
    position: absolute;
    background: rgba(0, 0, 0, 0.85);
    color: white;
    padding: 8px 10px;
    border-radius: 4px;
    font-size: 12px;
    z-index: 3;
    pointer-events: none;
    max-width: 280px;
    max-height: 300px;
    overflow-y: auto;
    white-space: normal;
    word-break: break-word;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

/* ezio: floating toolbar positioning */
.floating-toolbar {
    position: absolute;
    bottom: 8px;
    right: 8px;
    z-index: 2;
}

/* ezio: cursor per tool */
.lasso-overlay.cursor-select { cursor: crosshair; }
.lasso-overlay.cursor-pen    { cursor: crosshair; }
.lasso-overlay.cursor-rect    { cursor: crosshair; }
.lasso-overlay.cursor-eraser { cursor: pointer; }

/* 可视化区域：固定高度 */
.vis-area {
    height: 400px;
    flex-shrink: 0;
    position: relative;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
}

.vis-area svg {
    width: 100%;
    height: 100%;
    position: absolute;
    top: 0;
    left: 0;
}

.lasso-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1;
}

/* 详情面板：可折叠，占剩余空间 */
.details-panel {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
}

.details-header {
    padding: 8px 12px;
    background: #f5f5f5;
    cursor: pointer;
    font-size: 13px;
    font-weight: bold;
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
    user-select: none;
}

.details-count {
    color: #666;
    font-weight: normal;
}

.details-body {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
}

.details-empty {
    padding: 20px;
    text-align: center;
    color: #999;
    font-size: 13px;
}

.details-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}

.details-table th {
    background: #fafafa;
    padding: 6px 10px;
    text-align: left;
    border-bottom: 1px solid #e0e0e0;
    position: sticky;
    top: 0;
}

.details-table td {
    padding: 5px 10px;
    border-bottom: 1px solid #f0f0f0;
}

.details-table tr:hover {
    background: #f8f8f8;
}

.addr {
    font-family: monospace;
    font-size: 11px;
}

.suspicious-tag {
    color: #d32f2f;
    font-weight: bold;
    font-size: 11px;
}

.normal-tag {
    color: #388e3c;
    font-size: 11px;
}

/* 输入区域 */
.input-area {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
}

.text-input {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
}

.text-input:focus {
    border-color: #4caf50;
}

.send-btn {
    padding: 8px 16px;
    background: #4caf50;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    font-weight: bold;
}

.send-btn:hover {
    background: #43a047;
}
</style>
