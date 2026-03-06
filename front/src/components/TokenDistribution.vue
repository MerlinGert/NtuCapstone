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
            <span>Active Users (Top {{ topPercent }}%): {{ userCount }}</span>
        </div>

        <!-- Chart -->
        <div style="flex:1;position:relative;overflow:hidden;height:0;min-height:0;" ref="chart_container">
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
import localSnapshotData from '../assets/processed_latest_snapshot_50.json'

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
            scaleFactor: 0.6, // Default scale parameter
            lastDetectionCount: null,
            lastDetectionThreshold: 2,
            lastDetectionTimeRange: {},
            lastLinkThreshold: 1,
            lastLinkTimeRange: {},
            detectedEntities: [],
            nodes: [],
            currentLinks: [],
            simulation: null,
            centerX: 0,
            centerY: 0,
            topPercent: 50
        }
    },
    computed: {
        displayTime() {
            if (!this.snapshotData) return "Loading...";
            return this.snapshotData.time ? this.snapshotData.time.replace(" UTC", "") : "Unknown Time";
        }
    },
    mounted() {
        this.fetchSnapshotData(); // Default fetch
        window.addEventListener('resize', this.setSvg);
    },
    beforeUnmount() {
        window.removeEventListener('resize', this.setSvg);
    },
    methods: {
        runEntityDetection(threshold, timeRange, ruleType, silent = false) {
            console.log("TokenDistribution: runEntityDetection called with", threshold, timeRange, ruleType);
            if (!this.snapshotData || !this.snapshotData.balances) {
                 console.error("TokenDistribution: snapshotData not ready", this.snapshotData);
                 this.$emit('detection-complete', null);
                 return Promise.resolve(); // Return promise
             }
            
            // Extract user list from current data
            let users = [];
            if (this.snapshotData.balances && this.snapshotData.balances.users) {
                users = Object.keys(this.snapshotData.balances.users).filter(u => u !== 'Others');
            }
            
            console.log("TokenDistribution: Found", users.length, "users");

            if (users.length === 0) {
                console.warn("TokenDistribution: No users found");
                this.$emit('detection-complete', 0);
                return Promise.resolve();
            }

            this.detecting = true;
            this.lastDetectionCount = null;
            this.lastDetectionThreshold = threshold;
            this.lastDetectionTimeRange = timeRange;
            console.log(`Sending ${users.length} users for detection...`);

            // Call backend API
            return fetch('/api/entity/detect', {
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
                    console.log(`Detected ${data.detected_entities.length} entity groups.`);
                    // Store detected entities for grouping
                    this.detectedEntities = data.detected_entities;
                } else {
                    this.lastDetectionCount = 0;
                    this.detectedEntities = []; // Clear
                    console.log("No entities detected.");
                }
                this.$emit('detection-complete', this.lastDetectionCount);
            })
            .catch(error => {
                this.detecting = false;
                console.error("Error detecting entities:", error);
                this.$emit('detection-complete', null);
            });
        },
        // Old highlightEntities removed/deprecated as logic is now in drawChart
        highlightEntities(entities) {
            // Keep for compatibility if needed, but logic moved to drawChart
        },
        async fetchSnapshotData(time = this.selectedTime, threshold, detectionParams, linkParams) {
            console.log("TokenDistribution: fetchSnapshotData called", time, threshold, detectionParams, linkParams);
            this.loading = true;
            this.selectedTime = time;

            // Update internal state if new params provided
            if (detectionParams) {
                this.lastDetectionThreshold = detectionParams.threshold;
                this.lastDetectionTimeRange = detectionParams.timeRange || {};
            }
            if (linkParams) {
                this.lastLinkThreshold = linkParams.threshold;
                this.lastLinkTimeRange = linkParams.timeRange || {};
            }

            try {
                const response = await fetch('/api/snapshot/process', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        time: time,
                        threshold: threshold
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to fetch data: ${response.statusText}`);
                }
                
                this.snapshotData = await response.json();
                this.loading = false;
                
                // Update topPercent display based on threshold
                if (threshold !== undefined) {
                    this.topPercent = Math.round(threshold * 100);
                } else {
                     this.topPercent = 50; // default
                }
                
                // Draw chart
                this.$nextTick(async () => {
                    this.setSvg();
                    // Auto-load detection and links after initial render
                    // Run both concurrently and wait for both to finish before drawing
                    await Promise.all([
                        this.runEntityDetection(this.lastDetectionThreshold || 2, this.lastDetectionTimeRange || {}, 'transfer-network', true),
                        this.updateLinks(this.lastLinkThreshold || 1, this.lastLinkTimeRange || {}, true)
                    ]);
                    // Only draw once after both are ready
                    this.drawChart();
                });
            } catch (error) {
                console.warn("API snapshot failed, using local fallback:", error);
                // Fallback to local bundled JSON
                this.snapshotData = localSnapshotData;
                this.loading = false;
                this.$nextTick(() => {
                    this.setSvg();
                });
            }
        },
        loadData() {
            // Legacy wrapper, calls fetchSnapshotData with defaults
            this.fetchSnapshotData();
        },
        setSvg() {
            if (this.$refs.chart_container) {
                this.svgHeight = this.$refs.chart_container.offsetHeight;
                this.svgWidth = this.$refs.chart_container.offsetWidth;
                this.drawChart();
            }
        },
        async updateLinks(threshold, timeRange, silent = false) {
            console.log("TokenDistribution: updateLinks called", threshold, timeRange);
            if (!this.snapshotData || !this.snapshotData.balances) {
                console.warn("No snapshot data available.");
                return;
            }

            let users = [];
            if (this.snapshotData.balances && this.snapshotData.balances.users) {
                users = Object.keys(this.snapshotData.balances.users).filter(u => u !== 'Others');
            }

            if (users.length === 0) {
                console.warn("No users to check links for.");
                return;
            }

            this.lastLinkThreshold = threshold;
            this.lastLinkTimeRange = timeRange;

            try {
                const response = await fetch('/api/entity/links', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        target_users: users,
                        time_range: timeRange,
                        threshold: threshold
                    })
                });

                if (!response.ok) throw new Error("Failed to fetch links");
                
                const data = await response.json();
                console.log("Links received:", data.links);
                this.currentLinks = data.links || [];
                
                // If not silent (user triggered), redraw immediately. 
                // If silent (initial load), caller handles redraw.
                if (!silent) {
                     this.drawChart(); 
                }
                console.log(`Updated ${this.currentLinks.length} links.`);
                
            } catch (error) {
                console.error("Error fetching links:", error);
            }
        },
        drawChart() {
            if (!this.snapshotData || this.svgWidth === 0) return;

            const width = this.svgWidth;
            const height = this.svgHeight;
            const balances = this.snapshotData.balances;

            // 1. Prepare base entries
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
                        r: 0 // Will be set after scale calculation
                    }));
            }

            this.userCount = entries.length;
            const usersBalance = entries.reduce((sum, d) => sum + d.value, 0);

            // 2. Calculate scale for bubbles
            const minDim = Math.min(width, height);
            const margin = 20;
            const maxGroupRadius = (minDim / 2) - margin;
            const totalBalance = usersBalance + othersBalance;
            const fillFactor = this.scaleFactor; 
            const totalAvailableArea = Math.PI * maxGroupRadius * maxGroupRadius;
            const targetTotalInkArea = totalAvailableArea * fillFactor;
            const targetBubbleArea = totalBalance > 0 ? targetTotalInkArea * (usersBalance / totalBalance) : 0;
            const radiusScale = usersBalance > 0 ? Math.sqrt(targetBubbleArea / (Math.PI * usersBalance)) : 1;
            
            // Assign radii
            entries.forEach(d => {
                d.r = Math.sqrt(d.value) * radiusScale;
            });

            // 3. Handle Grouping (Hierarchical Packing)
            let simulationNodes = [];
            let finalNodes = []; // Flattened list for rendering links and interactions

            if (this.detectedEntities && this.detectedEntities.length > 0) {
                // Map user -> group
                const userGroupMap = new Map();
                this.detectedEntities.forEach(entity => {
                    if (entity.details && entity.details.members) {
                        entity.details.members.forEach(memberId => {
                            userGroupMap.set(memberId, entity);
                        });
                    }
                });

                // Separate nodes
                const groupMap = new Map(); // entityId -> [nodes]
                const independentNodes = [];

                entries.forEach(node => {
                    if (userGroupMap.has(node.id)) {
                        const entity = userGroupMap.get(node.id);
                        if (!groupMap.has(entity.entity_id)) {
                            groupMap.set(entity.entity_id, []);
                        }
                        groupMap.get(entity.entity_id).push(node);
                    } else {
                        independentNodes.push(node);
                        finalNodes.push(node);
                    }
                });

                // Process Groups
                const groupNodes = [];
                groupMap.forEach((members, entityId) => {
                    // Use d3.packSiblings to pack members tightly
                    // This adds x, y to members relative to (0,0)
                    d3.packSiblings(members);
                    
                    // Calculate enclosing circle
                    const enclose = d3.packEnclose(members);
                    
                    // Create Super Node
                    const groupNode = {
                        id: entityId,
                        isGroup: true,
                        r: enclose.r + 5, // Add padding
                        value: members.reduce((sum, m) => sum + m.value, 0),
                        children: members,
                        enclose: enclose // Store enclosure info for offset calculation
                    };
                    groupNodes.push(groupNode);
                });

                simulationNodes = [...independentNodes, ...groupNodes];
            } else {
                // No grouping
                simulationNodes = entries;
                finalNodes = entries;
            }

            // 4. Setup SVG
            const svg = d3.select(this.$refs.chart_container).select("svg.tokenDistribution");
            svg.attr("width", width).attr("height", height);
            svg.selectAll("*").remove();
            
            const centerX = width / 2;
            const centerY = height / 2;
            this.centerX = centerX;
            this.centerY = centerY;
            
            const g = svg.append("g").attr("transform", `translate(${centerX},${centerY})`);
            
            // Draw "Others" Ring
             if (othersBalance > 0) {
                const targetRingArea = totalBalance > 0 ? targetTotalInkArea * (othersBalance / totalBalance) : 0;
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

            const bubbleGroup = g.append("g");
            
            // Link group (ABOVE nodes)
            const linkGroup = g.append("g").attr("class", "links");
            
            const color = d3.scaleSequential(d3.interpolateBlues).domain([0, d3.max(entries, d => d.value)]);

            // Prepare Links for Simulation
            const simulationLinkMap = new Map();
            const userToSimNode = new Map();

            // Map independent nodes
            simulationNodes.filter(n => !n.isGroup).forEach(n => userToSimNode.set(n.id, n));

            // Map group members
            simulationNodes.filter(n => n.isGroup).forEach(g => {
                g.children.forEach(c => userToSimNode.set(c.id, g)); // Map member to GROUP
            });

            if (this.currentLinks && this.currentLinks.length > 0) {
                this.currentLinks.forEach(link => {
                    const sourceNode = userToSimNode.get(link.source);
                    const targetNode = userToSimNode.get(link.target);
                    
                    if (sourceNode && targetNode && sourceNode !== targetNode) {
                        // Link between different simulation bodies (Group-Group, Group-Single, Single-Single)
                        // Create key for link aggregation
                        const key = `${sourceNode.id}-${targetNode.id}`;
                        if (!simulationLinkMap.has(key)) {
                            simulationLinkMap.set(key, { 
                                source: sourceNode.id, 
                                target: targetNode.id, 
                                weight: 0 
                            });
                        }
                        simulationLinkMap.get(key).weight += link.weight;
                    }
                });
            }

            const simulationLinks = Array.from(simulationLinkMap.values());
            console.log(`Simulation Links: ${simulationLinks.length} (from ${this.currentLinks ? this.currentLinks.length : 0} raw links)`);

            // Draw Links
            const linkElements = linkGroup.selectAll("line")
                .data(simulationLinks)
                .join("line")
                .attr("stroke", "#999")
                .attr("stroke-opacity", 0.6)
                .attr("stroke-width", 3);
                // .attr("stroke-width", d => Math.max(1, Math.min(Math.sqrt(d.weight), 5)));
            
            linkElements.append("title")
                .text(d => `Source: ${d.source}\nTarget: ${d.target}\nWeight: ${d.weight}`);

            // Drag Behavior
            const drag = d3.drag()
                .on("start", (event, d) => {
                    if (!event.active) this.simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on("drag", (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on("end", (event, d) => {
                    if (!event.active) this.simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                });

            // Draw Group Boundaries
            const groups = bubbleGroup.selectAll(".group")
                .data(simulationNodes.filter(n => n.isGroup))
                .enter().append("g")
                .attr("class", "group")
                .attr("transform", d => `translate(${d.x},${d.y})`)
                .call(drag); // Attach drag
                
            groups.append("circle")
                .attr("r", d => d.r)
                .style("fill", "white") // Add fill to capture drag events inside
                .style("fill-opacity", 0.3)
                .style("stroke", "#ff9800")
                .style("stroke-width", 2)
                .style("stroke-dasharray", "5,5");

            // Draw Independent Nodes
            const singles = bubbleGroup.selectAll(".single")
                .data(simulationNodes.filter(n => !n.isGroup))
                .enter().append("circle")
                .attr("class", "bubble single")
                .attr("transform", d => `translate(${d.x},${d.y})`)
                .attr("r", d => d.r)
                .style("fill", d => color(d.value))
                .style("opacity", 0.6)
                .style("stroke", "#5976ba")
                .style("stroke-width", 2)
                .call(drag) // Attach drag
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
                .on("mouseout", (event) => {
                    d3.select(event.currentTarget).style("stroke", "#5976ba");
                    this.$refs.tooltip.style.opacity = 0;
                });

            // Draw Group Members
            groups.each(function(d) {
                d3.select(this).selectAll(".member")
                    .data(d.children)
                    .enter().append("circle")
                    .attr("class", "bubble member")
                    .attr("cx", child => child.x - d.enclose.x)
                    .attr("cy", child => child.y - d.enclose.y)
                    .attr("r", child => child.r)
                    .style("fill", child => color(child.value))
                    .style("opacity", 0.6)
                    .style("stroke", "#5976ba")
                    .style("stroke-width", 2);
            });
            
            // Re-bind events for members with correct scope
            const self = this;
            groups.selectAll(".member")
                 .on("mouseover", function(event, d) {
                    d3.select(this).style("stroke", "#000");
                    const tooltip = self.$refs.tooltip;
                    tooltip.style.opacity = 1;
                    tooltip.innerHTML = `Address: ${d.name.substring(0,6)}...<br>Balance: ${d.value.toLocaleString()}`;
                    tooltip.style.left = (event.pageX + 10) + "px";
                    tooltip.style.top = (event.pageY - 10) + "px";
                })
                .on("mousemove", function(event) {
                     const tooltip = self.$refs.tooltip;
                     tooltip.style.left = (event.pageX + 10) + "px";
                     tooltip.style.top = (event.pageY - 10) + "px";
                })
                .on("mouseout", function(event) {
                    d3.select(this).style("stroke", "#5976ba");
                    self.$refs.tooltip.style.opacity = 0;
                });

            // 5. Run Simulation
            if (this.simulation) this.simulation.stop();

            this.simulation = d3.forceSimulation(simulationNodes)
                .force("charge", d3.forceManyBody().strength(d => d.isGroup ? -50 : -15)) 
                .force("collide", d3.forceCollide().radius(d => d.r + 5).strength(1))
                .force("r", d3.forceRadial(0, 0, 0).strength(0.15))
                .force("center", d3.forceCenter(0, 0).strength(0.1))
                .force("link", d3.forceLink(simulationLinks).id(d => d.id).distance(20).strength(1));

            this.simulation.on("tick", () => {
                // Update Links
                linkElements
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                // Update Groups
                groups.attr("transform", d => `translate(${d.x},${d.y})`);

                // Update Singles
                singles.attr("transform", d => `translate(${d.x},${d.y})`);
            });
        },
    }
}
</script>

<style scoped>
.tokenDistribution {
    width: 100%;
    height: 100%;
}
</style>