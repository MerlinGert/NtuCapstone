<template>
    <div style="height:100%;width:100%;background:#ffffff;display:flex;flex-direction:column">
        <!-- Info Header -->
        <div style="padding: 10px; background: #f0f0f0; display: flex; align-items: center; gap: 20px; flex-wrap: wrap; border-bottom: 1px solid #ddd;">
            <span style="font-weight: bold;">{{ displayTime }}</span>
            <div style="display: flex; align-items: center; gap: 10px;">
                <label>Scale:</label>
                <input type="range" v-model.number="scaleFactor" min="0.1" max="1.5" step="0.1" @input="drawChart">
                <span>{{ scaleFactor }}</span>
            </div>
            <span>Active Users (Top 50%): {{ userCount }}</span>
        </div>

        <!-- Chart -->
        <div style="flex:1;position:relative;overflow:hidden;" ref="chart_container">
            <svg class="tokenDistribution"></svg>
            <div v-if="loading" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);">
                Loading data...
            </div>
            <div v-if="detecting" style="position:absolute;top:10px;right:10px;background:rgba(255,255,255,0.9);padding:5px;border-radius:4px;font-size:12px;border:1px solid #ddd;">
                Detecting Entities...
            </div>
            <!-- Tooltip -->
            <div ref="tooltip" style="position: absolute; opacity: 0; background: rgba(0,0,0,0.8); color: white; padding: 5px; border-radius: 4px; pointer-events: none; font-size: 12px; z-index: 10;"></div>
        </div>
    </div>
</template>

<script>
import * as d3 from "d3"
import snapshotDataFile from '../assets/processed_latest_snapshot_50.json'

export default {
    name: "TokenDistribution",
    data() {
        return {
            snapshotData: null,
            loading: true,
            detecting: false,
            svgWidth: 0,
            svgHeight: 0,
            userCount: 0,
            scaleFactor: 0.7, // Default scale parameter
            lastDetectionCount: null
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
        runEntityDetection(threshold, timeRange, ruleType) {
            console.log("TokenDistribution: runEntityDetection called with", threshold, timeRange, ruleType);
            if (!this.snapshotData || !this.snapshotData.balances) {
                 console.error("TokenDistribution: snapshotData not ready", this.snapshotData);
                 this.$emit('detection-complete', null);
                 return;
             }
            
            // Extract user list from current data
            let users = [];
            if (this.snapshotData.balances && this.snapshotData.balances.users) {
                users = Object.keys(this.snapshotData.balances.users).filter(u => u !== 'Others');
            }
            
            console.log("TokenDistribution: Found", users.length, "users");

            if (users.length === 0) {
                console.warn("TokenDistribution: No users found");
                alert("No users loaded to detect.");
                this.$emit('detection-complete', 0);
                return;
            }

            this.detecting = true;
            this.lastDetectionCount = null;
            console.log(`Sending ${users.length} users for detection...`);

            // Call backend API
            fetch('/api/entity/detect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    target_users: users,
                    time_range: timeRange,
                    rules: [
                        {
                            rule_type: ruleType,
                            parameters: {
                                threshold: threshold // Detect if > threshold transactions
                            },
                            enabled: true
                        }
                    ]
                })
            })
            .then(response => response.json())
            .then(data => {
                this.detecting = false;
                console.log("Detection Result:", data);
                if (data.detected_entities && data.detected_entities.length > 0) {
                    this.lastDetectionCount = data.detected_entities.length;
                    alert(`Detected ${data.detected_entities.length} entity groups.`);
                    this.highlightEntities(data.detected_entities);
                } else {
                    this.lastDetectionCount = 0;
                    alert("No entities detected.");
                }
                this.$emit('detection-complete', this.lastDetectionCount);
            })
            .catch(error => {
                this.detecting = false;
                console.error("Error detecting entities:", error);
                alert("Detection failed. Check console.");
                this.$emit('detection-complete', null);
            });
        },
        highlightEntities(entities) {
            // Create a set of all members in detected entities
            const memberSet = new Set();
            entities.forEach(entity => {
                if (entity.details && entity.details.members) {
                    entity.details.members.forEach(member => memberSet.add(member));
                }
            });
            
            // Highlight bubbles in D3 chart
            const bubbles = d3.selectAll(".bubble");
            
            // Update data binding
            bubbles.each(function(d) {
                d.isHighlighted = memberSet.has(d.id);
            });

            // Update visuals
            bubbles
                .style("stroke", d => d.isHighlighted ? "#ff0000" : "#fff")
                .style("stroke-width", d => d.isHighlighted ? 3 : 1);
        },
        async loadData() {
            try {
                this.loading = true;
                console.log("TokenDistribution: Loading snapshot data...", snapshotDataFile);
                this.snapshotData = snapshotDataFile;
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
                    .map(([owner, balance]) => ({ 
                        id: owner,
                        name: owner, 
                        value: balance,
                        // Initial radius based on value, will be used for collision
                        r: 0 // Will be set after scale calculation
                    }));
            }

            this.userCount = entries.length;
            const usersBalance = entries.reduce((sum, d) => sum + d.value, 0);

            // Calculate radius scale
            // We want the total area of user bubbles to be somewhat proportional to screen size
            // but ensuring they fit.
            // Let's define a maximum possible radius for the "user group" circle.
            const minDim = Math.min(width, height);
            const margin = 20;
            const maxGroupRadius = (minDim / 2) - margin;

            // Calculate total value area (sum of values)
            // We want: Area_Group = Area_Users + Area_Others (if we consider ring)
            // But for force simulation, we only care about user bubbles radius.
            // Let's first determine the 'scale' factor.
            // Total Area of Bubbles = Sum(pi * r_i^2)
            // We can relate value to area: r_i = sqrt(value) * K
            // Sum(pi * value * K^2) = Total_Bubble_Area
            // K = sqrt(Total_Bubble_Area / (pi * Sum(value)))
            
            // We need to determine Total_Bubble_Area.
            // Let's assume the user bubbles form a packed circle with radius R_users.
            // And we have an outer ring for 'Others' with radius R_outer.
            // Area_Ring = Area_Others
            // Area_Users_Circle = Area_Users (approx)
            // R_outer^2 / R_users^2 = (Balance_Total) / Balance_Users
            // R_users = R_outer * sqrt(Balance_Users / Balance_Total)
            
            const totalBalance = usersBalance + othersBalance;
            
            // "Shrink scale" logic:
             // We define a 'fillFactor' that determines how much of the total available disk area
             // is occupied by "ink" (ring area + sum of bubble areas).
             // Small fillFactor => thin ring, small bubbles, sparse layout.
             const fillFactor = this.scaleFactor; // Use user-controlled parameter 

            const totalAvailableArea = Math.PI * maxGroupRadius * maxGroupRadius;
            const targetTotalInkArea = totalAvailableArea * fillFactor;

            // Split ink area proportionally
            // Area_Ring / Area_Bubbles = Balance_Others / Balance_Users
            const targetRingArea = totalBalance > 0 
                ? targetTotalInkArea * (othersBalance / totalBalance) 
                : 0;
            const targetBubbleArea = totalBalance > 0 
                ? targetTotalInkArea * (usersBalance / totalBalance) 
                : 0;

            // Calculate geometry
            // Ring Area = pi * (R_out^2 - R_in^2)
            // R_in = sqrt(R_out^2 - Area_Ring / pi)
            const userGroupRadius = Math.sqrt(maxGroupRadius * maxGroupRadius - targetRingArea / Math.PI);
            
            // Calculate bubble radius scale k
            // Sum(pi * (k * sqrt(val))^2) = TargetBubbleArea
            // k^2 * pi * Sum(val) = TargetBubbleArea
            // k = sqrt(TargetBubbleArea / (pi * Sum(val)))
            const radiusScale = usersBalance > 0 
                ? Math.sqrt(targetBubbleArea / (Math.PI * usersBalance)) 
                : 1;

            // Assign radii to nodes
            entries.forEach(d => {
                d.r = Math.sqrt(d.value) * radiusScale;
            });

            const svg = d3.select(this.$refs.chart_container).select("svg.tokenDistribution");
            svg.attr("width", width).attr("height", height);

            // Clear previous
            svg.selectAll("*").remove();
            
            // Center group
            const centerX = width / 2;
            const centerY = height / 2;
            
            const g = svg.append("g")
                .attr("transform", `translate(${centerX},${centerY})`);

            // Draw Ring (Others)
            if (othersBalance > 0) {
                const innerRadius = userGroupRadius; // The boundary of user bubbles
                const outerRadius = maxGroupRadius;  // The boundary of the whole chart

                const arc = d3.arc()
                    .innerRadius(innerRadius)
                    .outerRadius(outerRadius)
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

            // Draw Bubbles Group
            const bubbleGroup = g.append("g");

            // Color scale
            const color = d3.scaleSequential(d3.interpolateBlues)
                .domain([0, d3.max(entries, d => d.value)]);

            // Initialize simulation
            const simulation = d3.forceSimulation(entries)
                .force("charge", d3.forceManyBody().strength(-10)) // Negative strength for repulsion (dispersion)
                .force("collide", d3.forceCollide().radius(d => d.r + 2).strength(1).iterations(2)) // Prevent overlap with padding
                .force("r", d3.forceRadial(0, 0, 0).strength(0.05)) // Weak pull to center
                .force("center", d3.forceCenter(0, 0).strength(0.05)) // Keep centered
                .stop();

            // Run simulation manually for faster rendering (static-like feel) or use tick
            // For better UX with force, we often let it settle a bit then render, or render live.
            // Since user wants "layout based on links" later, live simulation is better.
            // But for now, just to show the layout, we can let it run.
            // However, to ensure it stays "within circular range", forceRadial is key.
            
            // Let's run it for some ticks to stabilize initial positions
            for (let i = 0; i < 120; ++i) simulation.tick();

            // Render nodes
            const node = bubbleGroup.selectAll("g")
                .data(entries)
                .enter().append("g")
                .attr("transform", d => `translate(${d.x},${d.y})`);
                // Note: d.x and d.y are relative to the center because forceCenter is at (0,0) relative to the simulation,
                // but we translated 'g' to (centerX, centerY). 
                // Wait, d3.forceCenter(x,y) sets the center of mass. If we want 0,0 to be center of 'g', we should use forceCenter(0,0).
                // But forceCenter(0,0) means coordinates will be around 0.
                
            // Circles
            const circles = node.append("circle")
                .attr("class", "bubble")
                .attr("r", d => d.r)
                .style("fill", d => color(d.value))
                .style("opacity", 0.8)
                .style("stroke", d => d.isHighlighted ? "#ff0000" : "#fff")
                .style("stroke-width", d => d.isHighlighted ? 3 : 1)
                .on("mouseover", (event, d) => {
                    d3.select(event.currentTarget).style("stroke", "#000");
                    const tooltip = this.$refs.tooltip;
                    tooltip.style.opacity = 1;
                    tooltip.innerHTML = `Address: ${d.name.substring(0,6)}...<br>Balance: ${d.value.toLocaleString()}`;
                    tooltip.style.left = (event.pageX + 10) + "px";
                    tooltip.style.top = (event.pageY - 10) + "px";
                })
                .on("mousemove", (event) => {
                    const tooltip = this.$refs.tooltip;
                    tooltip.style.left = (event.pageX + 10) + "px";
                    tooltip.style.top = (event.pageY - 10) + "px";
                })
                .on("mouseout", (event, d) => {
                    d3.select(event.currentTarget)
                        .style("stroke", d.isHighlighted ? "#ff0000" : "#fff")
                        .style("stroke-width", d.isHighlighted ? 3 : 1);
                    this.$refs.tooltip.style.opacity = 0;
                });

            // Labels
            const labels = node.filter(d => d.r > 15).append("text")
                .attr("dy", ".3em")
                .style("text-anchor", "middle")
                .style("font-size", d => Math.min(d.r / 3, 10) + "px")
                .style("pointer-events", "none")
                .text(d => d.name.substring(0, 4));
            
            // Add drag behavior
            node.call(d3.drag()
                .on("start", (event, d) => {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on("drag", (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on("end", (event, d) => {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                }));

            // Restart simulation to animate
            simulation.on("tick", () => {
                // Constrain nodes to be within userGroupRadius
                // This is a hard constraint to ensure they don't go into the ring area
                entries.forEach(d => {
                    const dist = Math.sqrt(d.x * d.x + d.y * d.y);
                    const maxDist = userGroupRadius - d.r - 2; // -2 for padding
                    if (dist > maxDist) {
                        const angle = Math.atan2(d.y, d.x);
                        d.x = Math.cos(angle) * maxDist;
                        d.y = Math.sin(angle) * maxDist;
                    }
                });

                node.attr("transform", d => `translate(${d.x},${d.y})`);
            });
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