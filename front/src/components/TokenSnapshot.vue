<template>
    <div class="token-snapshot-container">
        <div class="header">
            <h2>Token Snapshot — {{ snapshotData.time }}</h2>
            <span v-if="selectedCount > 0" class="selection-badge">{{ selectedCount }} nodes selected</span>
            <button class="close-btn" @click="$emit('close')">×</button>
        </div>

        <!-- 可视化区域：固定高度 -->
        <div class="vis-area" ref="svgContainer">
            <svg ref="snapshotSvg"></svg>
            <canvas ref="lassoCanvas" class="lasso-overlay"></canvas>
        </div>

        <!-- 选中节点详情：可折叠 -->
        <div class="details-panel">
            <div class="details-header" @click="detailsOpen = !detailsOpen">
                <span>{{ detailsOpen ? '▼' : '▶' }} Selected Nodes Details</span>
                <span class="details-count" v-if="selectedNodes.length > 0">({{ selectedNodes.length }})</span>
            </div>
            <div v-if="detailsOpen" class="details-body">
                <div v-if="selectedNodes.length === 0" class="details-empty">
                    Use lasso to select nodes in the visualization above.
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
            <button @click="handleInput" class="send-btn">Send</button>
        </div>
    </div>
</template>

<script>
import * as d3 from "d3"

export default {
    name: "TokenSnapshot",
    props: {
        snapshotData: { type: Object, required: true }
    },
    data() {
        return {
            selectedCount: 0,
            selectedNodes: [],
            detailsOpen: true,
            inputText: ""
        };
    },
    mounted() {
        this.$nextTick(() => {
            this.renderSnapshot();
            this.setupLasso();
        });
    },
    methods: {
        handleInput() {
            if (!this.inputText.trim()) return;
            this.$emit('snapshot-input', {
                text: this.inputText,
                selectedIds: this.selectedNodes.map(n => n.id)
            });
            this.inputText = "";
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
                    if (sId && tId && sId !== tId) {
                        const key = `${sId}-${tId}`;
                        if (!aggLinks.has(key)) aggLinks.set(key, { source: sId, target: tId, weight: 0 });
                        aggLinks.get(key).weight += l.weight;
                    }
                });
                aggLinks.forEach(link => {
                    const sp = nodePositions.get(link.source);
                    const tp = nodePositions.get(link.target);
                    if (sp && tp) {
                        linkGroup.append("line")
                            .attr("x1", sp.x).attr("y1", sp.y)
                            .attr("x2", tp.x).attr("y2", tp.y)
                            .attr("stroke", "#999")
                            .attr("stroke-opacity", 0.6)
                            .attr("stroke-width", 3);
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

            canvas.addEventListener("mousedown", (e) => {
                isDrawing = true;
                hasMoved = false;
                const rect = canvas.getBoundingClientRect();
                points = [[e.clientX - rect.left, e.clientY - rect.top]];
                ctx.clearRect(0, 0, canvas.width, canvas.height);
            });

            canvas.addEventListener("mousemove", (e) => {
                if (!isDrawing) return;
                hasMoved = true;
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                points.push([x, y]);

                ctx.clearRect(0, 0, canvas.width, canvas.height);
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
            });

            canvas.addEventListener("mouseup", (e) => {
                if (!isDrawing) return;
                isDrawing = false;
                ctx.clearRect(0, 0, canvas.width, canvas.height);

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

                // Lasso 模式：选中框内所有节点（替换当前选择）
                selectedSet.clear();
                this._selectableNodes.forEach(n => {
                    if (d3.polygonContains(points, [n.screenX, n.screenY])) {
                        selectedSet.add(n.id);
                    }
                });
                updateHighlight();
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
    cursor: crosshair;
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
