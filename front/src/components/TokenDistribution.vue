<template>
    <div style="height:100%;width:100%;background:#ffffff;display:flex;flex-direction:column">
        <!-- Controls -->
        <div style="padding: 10px; border-bottom: 1px solid #eee; display: flex; flex-direction: column; gap: 5px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold;">{{ displayTime }}</span>
                <span>Holders: {{ currentHolderCount }}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <n-button size="tiny" @click="togglePlay">
                    {{ isPlaying ? 'Pause' : 'Play' }}
                </n-button>
                <input 
                    type="range" 
                    min="0" 
                    :max="maxIndex" 
                    v-model.number="currentIndex" 
                    style="flex: 1;"
                    @input="onSliderInput"
                />
            </div>
        </div>

        <!-- Chart -->
        <div style="flex:1;position:relative;overflow:hidden;" ref="chart_container">
            <svg class="tokenDistribution"></svg>
            <div v-if="loading" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);">
                Loading data...
            </div>
        </div>
    </div>
</template>

<script>
import * as d3 from "d3"
import { NButton } from "naive-ui"

export default {
    name: "TokenDistribution",
    components: { NButton },
    data() {
        return {
            snapshots: [],
            currentIndex: 0,
            isPlaying: false,
            playInterval: null,
            loading: true,
            svgWidth: 0,
            svgHeight: 0,
            margin: { top: 10, right: 10, bottom: 10, left: 10 }
        }
    },
    computed: {
        maxIndex() {
            return Math.max(0, this.snapshots.length - 1);
        },
        currentSnapshot() {
            if (this.snapshots.length === 0) return null;
            return this.snapshots[this.currentIndex];
        },
        displayTime() {
            if (!this.currentSnapshot) return "Loading...";
            return this.currentSnapshot.time.replace(" UTC", "");
        },
        currentHolderCount() {
            if (!this.currentSnapshot) return 0;
            return Object.keys(this.currentSnapshot.balances).length;
        }
    },
    watch: {
        currentIndex() {
            this.drawChart();
        }
    },
    methods: {
        async loadData() {
            try {
                this.loading = true;
                const response = await fetch('/processed/transfers/hourly_balance_snapshots.json');
                this.snapshots = await response.json();
                this.loading = false;
                
                // Draw initial chart
                this.$nextTick(() => {
                    this.setSvg();
                });
            } catch (error) {
                console.error("Failed to load snapshots:", error);
                this.loading = false;
            }
        },
        togglePlay() {
            if (this.isPlaying) {
                this.pause();
            } else {
                this.play();
            }
        },
        play() {
            this.isPlaying = true;
            if (this.currentIndex >= this.maxIndex) {
                this.currentIndex = 0;
            }
            this.playInterval = setInterval(() => {
                if (this.currentIndex < this.maxIndex) {
                    this.currentIndex++;
                } else {
                    this.pause();
                }
            }, 200); // 200ms per frame to be smoother
        },
        pause() {
            this.isPlaying = false;
            if (this.playInterval) {
                clearInterval(this.playInterval);
                this.playInterval = null;
            }
        },
        onSliderInput() {
            this.pause(); // Pause when user drags slider
        },
        setSvg() {
            if (this.$refs.chart_container && this.$refs.chart_container.offsetHeight) {
                this.svgHeight = this.$refs.chart_container.offsetHeight;
                this.svgWidth = this.$refs.chart_container.offsetWidth;
                this.drawChart();
            }
        },
        drawChart() {
            if (!this.currentSnapshot || this.svgWidth === 0) return;

            const width = this.svgWidth;
            const height = this.svgHeight;
            const balances = this.currentSnapshot.balances;

            // Prepare hierarchical data
            const rootData = {
                name: "root",
                children: []
            };

            // Filter top N and group others
            const entries = Object.entries(balances)
                .map(([owner, balance]) => ({ owner, balance }))
                .filter(d => d.balance > 0)
                .sort((a, b) => b.balance - a.balance);

            const topN = 100; // Limit to 100 bubbles for performance
            const topHolders = entries.slice(0, topN);
            const others = entries.slice(topN);
            
            topHolders.forEach(h => {
                rootData.children.push({ name: h.owner, value: h.balance });
            });
            
            if (others.length > 0) {
                const otherSum = others.reduce((sum, h) => sum + h.balance, 0);
                rootData.children.push({ name: "Others", value: otherSum });
            }

            const root = d3.hierarchy(rootData)
                .sum(d => d.value)
                .sort((a, b) => b.value - a.value);

            const pack = d3.pack()
                .size([width - 20, height - 20])
                .padding(3);

            const nodes = pack(root).leaves();

            const svg = d3.select("svg.tokenDistribution");
            svg.attr("width", width).attr("height", height);

            // Clear previous
            svg.selectAll("*").remove();
            
            const g = svg.append("g")
                .attr("transform", `translate(10,10)`);

            const color = d3.scaleOrdinal(d3.schemeCategory10);

            const node = g.selectAll("g")
                .data(nodes)
                .enter().append("g")
                .attr("transform", d => `translate(${d.x},${d.y})`);

            node.append("circle")
                .attr("r", d => d.r)
                .style("fill", (d, i) => {
                    if (d.data.name === "Others") return "#ccc";
                    return color(i % 10);
                })
                .style("opacity", 0.7)
                .style("stroke", "#fff");

            node.append("title")
                .text(d => `${d.data.name}\n${d.data.value.toLocaleString()}`);

            // Labels for larger bubbles
            node.filter(d => d.r > 15)
                .append("text")
                .attr("dy", ".3em")
                .style("text-anchor", "middle")
                .style("font-size", d => Math.min(d.r / 2, 10) + "px")
                .text(d => d.data.name.substring(0, 4));
        }
    },
    mounted() {
        this.loadData();
        window.addEventListener("resize", this.setSvg);
    },
    unmounted() {
        this.pause();
        window.removeEventListener("resize", this.setSvg);
    }
}
</script>

<style scoped>
.tokenDistribution {
    width: 100%;
    height: 100%;
}
</style>