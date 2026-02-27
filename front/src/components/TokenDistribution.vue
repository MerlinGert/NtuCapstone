<template>
    <div style="height:100%;width:100%;background:#ffffff;display:flex;flex-direction:column">
        <!-- Info Header -->
        <div style="padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: bold;">{{ displayTime }}</span>
            <span>Active Users (Top 50%): {{ userCount }}</span>
        </div>

        <!-- Chart -->
        <div style="flex:1;position:relative;overflow:hidden;" ref="chart_container">
            <svg class="tokenDistribution"></svg>
            <div v-if="loading" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);">
                Loading data...
            </div>
            <!-- Tooltip -->
            <div ref="tooltip" style="position: absolute; opacity: 0; background: rgba(0,0,0,0.8); color: white; padding: 5px; border-radius: 4px; pointer-events: none; font-size: 12px; z-index: 10;"></div>
        </div>
    </div>
</template>

<script>
import * as d3 from "d3"

export default {
    name: "TokenDistribution",
    data() {
        return {
            snapshotData: null,
            loading: true,
            svgWidth: 0,
            svgHeight: 0,
            userCount: 0
        }
    },
    computed: {
        displayTime() {
            if (!this.snapshotData) return "Loading...";
            return this.snapshotData.time ? this.snapshotData.time.replace(" UTC", "") : "Unknown Time";
        }
    },
    mounted() {
        this.loadData();
        window.addEventListener('resize', this.setSvg);
    },
    beforeUnmount() {
        window.removeEventListener('resize', this.setSvg);
    },
    methods: {
        async loadData() {
            try {
                this.loading = true;
                const response = await fetch('/processed/transfers/processed_latest_snapshot_50.json');
                this.snapshotData = await response.json();
                this.loading = false;
                
                // Draw chart
                this.$nextTick(() => {
                    this.setSvg();
                });
            } catch (error) {
                console.error("Failed to load snapshot:", error);
                this.loading = false;
            }
        },
        setSvg() {
            if (this.$refs.chart_container) {
                this.svgHeight = this.$refs.chart_container.offsetHeight;
                this.svgWidth = this.$refs.chart_container.offsetWidth;
                this.drawChart();
            }
        },
        drawChart() {
            if (!this.snapshotData || this.svgWidth === 0) return;

            const width = this.svgWidth;
            const height = this.svgHeight;
            const balances = this.snapshotData.balances;

            // Prepare data: Only users, exclude 'Others'
            let entries = [];
            let othersBalance = 0;
            if (balances && balances.users) {
                othersBalance = balances.users['Others'] || 0;
                entries = Object.entries(balances.users)
                    .filter(([owner, balance]) => owner !== 'Others' && balance > 0)
                    .map(([owner, balance]) => ({ owner, balance, type: 'user' }));
            }

            this.userCount = entries.length;
            const usersBalance = entries.reduce((sum, d) => sum + d.balance, 0);

            // 1. Pack bubbles first to find their layout area
            // We use an arbitrary large size for high precision layout, then scale down
            const packSize = 1000;
            const rootData = {
                name: "root",
                children: entries.map(d => ({ name: d.owner, value: d.balance }))
            };

            const root = d3.hierarchy(rootData)
                .sum(d => d.value)
                .sort((a, b) => b.value - a.value);

            const pack = d3.pack()
                .size([packSize, packSize])
                .padding(3);

            const nodes = pack(root).leaves();

            // Calculate actual sum of bubble areas
            const totalBubbleArea = nodes.reduce((sum, d) => sum + Math.PI * d.r * d.r, 0);

            // Calculate required ring area based on proportion
            // Area_Ring / Area_Bubbles = Balance_Others / Balance_Users
            const ringArea = usersBalance > 0 ? totalBubbleArea * (othersBalance / usersBalance) : 0;

            // The pack is centered at (packSize/2, packSize/2) with radius packSize/2
            // Let's assume the enclosing circle of the pack is effectively the pack radius (packSize/2)
            // But strictly, d3.pack fits into the box.
            const packRadius = packSize / 2;

            // Calculate outer radius of the ring
            // Area_Ring = pi * (R_out^2 - R_in^2)
            // where R_in = packRadius
            const outerRadius = Math.sqrt(packRadius * packRadius + ringArea / Math.PI);

            // Now we need to fit everything (pack + ring) into the SVG view
            const viewMinDim = Math.min(width, height);
            const margin = 20;
            const maxViewRadius = (viewMinDim / 2) - margin;
            
            const scale = maxViewRadius / outerRadius;

            const svg = d3.select(this.$refs.chart_container).select("svg.tokenDistribution");
            svg.attr("width", width).attr("height", height);

            // Clear previous
            svg.selectAll("*").remove();
            
            // Center group
            const g = svg.append("g")
                .attr("transform", `translate(${width/2},${height/2})`);

            // Draw Ring (Others)
            if (ringArea > 0) {
                const arc = d3.arc()
                    .innerRadius(packRadius * scale)
                    .outerRadius(outerRadius * scale)
                    .startAngle(0)
                    .endAngle(2 * Math.PI);

                g.append("path")
                    .attr("d", arc)
                    .style("fill", "#e3f2fd") // Light blue
                    .style("opacity", 0.5)
                    .on("mouseover", (event) => {
                        const tooltip = this.$refs.tooltip;
                        tooltip.style.opacity = 1;
                        tooltip.innerHTML = `Category: Others<br>Balance: ${othersBalance.toLocaleString()}`;
                        tooltip.style.left = (event.pageX + 10) + "px";
                        tooltip.style.top = (event.pageY - 10) + "px";
                    })
                    .on("mousemove", (event) => {
                        const tooltip = this.$refs.tooltip;
                        tooltip.style.left = (event.pageX + 10) + "px";
                        tooltip.style.top = (event.pageY - 10) + "px";
                    })
                    .on("mouseout", () => {
                        this.$refs.tooltip.style.opacity = 0;
                    });
            }

            // Draw Bubbles
            // Shift bubbles to center (they are currently in [0, packSize] coordinates)
            const bubbleGroup = g.append("g")
                .attr("transform", `translate(${-packSize/2 * scale}, ${-packSize/2 * scale})`);

            // Color scale
            const color = d3.scaleSequential(d3.interpolateBlues)
                .domain([0, d3.max(entries, d => d.balance)]);

            const node = bubbleGroup.selectAll("g")
                .data(nodes)
                .enter().append("g")
                .attr("transform", d => `translate(${d.x * scale},${d.y * scale})`);

            // Circles
            node.append("circle")
                .attr("r", d => d.r * scale)
                .style("fill", d => color(d.value))
                .style("opacity", 0.8)
                .style("stroke", "#fff")
                .style("stroke-width", 1)
                .on("mouseover", (event, d) => {
                    d3.select(event.currentTarget).style("stroke", "#000");
                    const tooltip = this.$refs.tooltip;
                    tooltip.style.opacity = 1;
                    tooltip.innerHTML = `Address: ${d.data.name.substring(0,6)}...<br>Balance: ${d.value.toLocaleString()}`;
                    tooltip.style.left = (event.pageX + 10) + "px";
                    tooltip.style.top = (event.pageY - 10) + "px";
                })
                .on("mousemove", (event) => {
                    const tooltip = this.$refs.tooltip;
                    tooltip.style.left = (event.pageX + 10) + "px";
                    tooltip.style.top = (event.pageY - 10) + "px";
                })
                .on("mouseout", (event) => {
                    d3.select(event.currentTarget).style("stroke", "#fff");
                    this.$refs.tooltip.style.opacity = 0;
                });

            // Labels (only if big enough)
            node.filter(d => (d.r * scale) > 15).append("text")
                .attr("dy", ".3em")
                .style("text-anchor", "middle")
                .style("font-size", d => Math.min((d.r * scale) / 3, 10) + "px")
                .style("pointer-events", "none")
                .text(d => d.data.name.substring(0, 4));
        }
    }
}
</script>

<style scoped>
.tokenDistribution {
    width: 100%;
    height: 100%;
}
</style>