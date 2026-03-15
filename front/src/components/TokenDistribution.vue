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
            <span>Active Users: {{ userCount }}</span>
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
            lastDetectionVolumeThreshold: 0,
            lastDetectionTimeRange: {},
            lastLinkThreshold: 1,
            lastLinkTimeRange: {},
            detectedEntities: [],
            nodes: [],
            currentLinks: [],
            simulation: null,
            centerX: 0,
            centerY: 0,
            topPercent: 50,
            suspiciousTraders: []
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
        setDetectionResults(entities, links) {
            console.log("TokenDistribution: setDetectionResults called", entities.length, links.length);
            this.detectedEntities = entities;
            this.currentLinks = links;
            this.lastDetectionCount = entities.length;
            this.drawChart();
        },
        runEntityDetection(threshold, timeRange, ruleType, checkFundingSource = false, volumeThreshold = 0, checkSameSender = false, checkSameRecipient = false, silent = false, enableTxCount = true, enableTxVolume = true, enableNetworkBased = true, enableBehaviorBased = true, behaviorTimeWindow = 1.0, enableRule3 = true, enableRule4 = true, enableRule5 = true, rule3Params = {}, rule4Params = {}, rule5Params = {}) {
            console.log("TokenDistribution: runEntityDetection called with params");
            if (!this.snapshotData || !this.snapshotData.balances) {
                 console.error("TokenDistribution: snapshotData not ready", this.snapshotData);
                 this.$emit('detection-complete', null);
                 return Promise.resolve(); // Return promise
             }
            
            // Extract user list from current data
            let users = [];
            if (this.snapshotData.balances && this.snapshotData.balances.users) {
                users = Object.entries(this.snapshotData.balances.users)
                    .filter(([u, bal]) => u !== 'Others' && bal > 0)
                    .map(([u, _]) => u);
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
            this.lastDetectionVolumeThreshold = volumeThreshold;
            this.lastDetectionTimeRange = timeRange;
            console.log(`Sending ${users.length} users for detection...`);

            // Construct rules
            const rules = [];

            // 1. Transfer Network Rule
            if (enableNetworkBased) {
                rules.push({
                    rule_type: "transfer-network",
                    parameters: {
                        threshold: threshold, // Detect if > threshold transactions
                        volume_threshold: volumeThreshold,
                        check_funding_source: checkFundingSource,
                        check_same_sender: checkSameSender,
                        check_same_recipient: checkSameRecipient,
                        enable_tx_count: enableTxCount,
                        enable_tx_volume: enableTxVolume
                    },
                    enabled: true
                });
            }

            // 2. Behavior Similarity Rule
            if (enableBehaviorBased) {
                rules.push({
                    rule_type: "behavior-similarity",
                    parameters: {
                        time_window: behaviorTimeWindow,
                        enable_rule3: enableRule3,
                        enable_rule4: enableRule4,
                        enable_rule5: enableRule5,
                        rule3_params: rule3Params,
                        rule4_params: rule4Params,
                        rule5_params: rule5Params
                    },
                    enabled: true
                });
            }

            // Call backend API
            return fetch('/api/entity/detect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    target_users: users,
                    time_range: timeRange,
                    rules: rules
                })
            })
            .then(response => response.json())
            .then(data => {
                this.detecting = false;
                console.log("Detection Result:", data);
                if (data.debug_relations) {
                    console.log("Debug Relations (Backend):", data.debug_relations);
                }
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
                return this.lastDetectionCount;
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
        highlightSuspiciousTraders(suspiciousTraders) {
            console.log("TokenDistribution: highlightSuspiciousTraders", suspiciousTraders.length);
            
            const svg = d3.select(this.$refs.chart_container).select("svg.tokenDistribution");
            const suspiciousMap = new Map();
            suspiciousTraders.forEach(t => suspiciousMap.set(t.trader_id, t));

            // Update Singles
            svg.selectAll(".single").each(function(d) {
                if (suspiciousMap.has(d.id)) {
                    d.suspicious = suspiciousMap.get(d.id);
                    d3.select(this).style("stroke", "#ff0000").style("stroke-width", 3);
                } else {
                    d.suspicious = null;
                    d3.select(this).style("stroke", "#5976ba").style("stroke-width", 2);
                }
            });

            // Update Group Members
            svg.selectAll(".member").each(function(d) {
                if (suspiciousMap.has(d.id)) {
                    d.suspicious = suspiciousMap.get(d.id);
                    d3.select(this).style("stroke", "#ff0000").style("stroke-width", 3);
                } else {
                    d.suspicious = null;
                    d3.select(this).style("stroke", "#5976ba").style("stroke-width", 2);
                }
            });
        },
        async fetchSnapshotData(time = this.selectedTime, threshold, relatedUserThreshold = 0.2, detectionParams, linkParams) {
            console.log("TokenDistribution: fetchSnapshotData called", time, threshold, relatedUserThreshold, detectionParams, linkParams);
            this.loading = true;
            this.selectedTime = time;

            // Update internal state if new params provided
            if (detectionParams) {
                this.lastDetectionThreshold = detectionParams.threshold;
                this.lastDetectionTimeRange = detectionParams.timeRange || {};
            }
            // linkParams will be handled in updateLinks

            try {
                const response = await fetch('/api/snapshot/process', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        time: time,
                        threshold: threshold,
                        related_user_threshold: relatedUserThreshold
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to fetch data: ${response.statusText}`);
                }
                
                this.snapshotData = await response.json();
                this.$emit('snapshot-loaded', this.snapshotData);
                // this.loading = false; // Wait until all detections are done
                
                // Update topPercent display based on threshold
                if (threshold !== undefined) {
                    this.topPercent = Math.round(threshold * 100);
                } else {
                     this.topPercent = 50; // default
                }
                
                // Draw chart
                this.$nextTick(async () => {
                    // Set dimensions but don't draw yet
                    if (this.$refs.chart_container) {
                        this.svgHeight = this.$refs.chart_container.offsetHeight;
                        this.svgWidth = this.$refs.chart_container.offsetWidth;
                    }
                    
                    // Auto-load detection and links after initial render
                    // Run both concurrently and wait for both to finish before drawing
                    
                    const p = detectionParams || {};
                    const thresholdToUse = p.threshold || this.lastDetectionThreshold || 2;
                    const timeRangeToUse = p.timeRange || this.lastDetectionTimeRange || {};
                    const volumeToUse = p.volumeThreshold || this.lastDetectionVolumeThreshold || 0;
                    
                    // Prepare link params
                    const linkP = linkParams || {
                        threshold: this.lastLinkThreshold || 1,
                        timeRange: this.lastLinkTimeRange || {}
                    };

                    await Promise.all([
                        this.runEntityDetection(
                            thresholdToUse, 
                            timeRangeToUse, 
                            'transfer-network', 
                            p.checkFundingSource !== undefined ? p.checkFundingSource : false,
                            volumeToUse,
                            p.checkSameSender !== undefined ? p.checkSameSender : false,
                            p.checkSameRecipient !== undefined ? p.checkSameRecipient : false,
                            true, // silent
                            p.enableTxCount !== undefined ? p.enableTxCount : true,
                            p.enableTxVolume !== undefined ? p.enableTxVolume : true,
                            p.enableNetworkBased !== undefined ? p.enableNetworkBased : true,
                            p.enableBehaviorBased !== undefined ? p.enableBehaviorBased : false,
                            p.behaviorTimeWindow !== undefined ? p.behaviorTimeWindow : 1.0,
                            p.enableRule3 !== undefined ? p.enableRule3 : true,
                            p.enableRule4 !== undefined ? p.enableRule4 : false,
                            p.enableRule5 !== undefined ? p.enableRule5 : false,
                            p.rule3Params || {},
                            p.rule4Params || {},
                            p.rule5Params || {}
                        ),
                        this.updateLinks(linkP, true),
                        // Run manipulation detection with default threshold (100) or last used
                        this.runManipulationDetection(100, true) // Pass true for isAutoRun
                    ]);
                    // Only draw once after both are ready
                    this.drawChart();
                    this.loading = false;
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
            this.fetchSnapshotData(this.selectedTime, 0.5, 0.2);
        },
        setSvg() {
            if (this.$refs.chart_container) {
                this.svgHeight = this.$refs.chart_container.offsetHeight;
                this.svgWidth = this.$refs.chart_container.offsetWidth;
                this.drawChart();
            }
        },
        async updateLinks(linkParams, silent = false) {
            console.log("TokenDistribution: updateLinks called", linkParams);

            if (!this.snapshotData || !this.snapshotData.balances) {
                console.warn("No snapshot data available.");
                return;
            }

            let users = [];
            if (this.snapshotData.balances && this.snapshotData.balances.users) {
                users = Object.entries(this.snapshotData.balances.users)
                    .filter(([u, bal]) => u !== 'Others' && bal > 0)
                    .map(([u, _]) => u);
            }

            if (users.length === 0) {
                console.warn("No users to check links for.");
                return;
            }

            // Destructure params with defaults
            const p = linkParams || {};
            const threshold = p.threshold !== undefined ? p.threshold : 1;
            const timeRange = p.timeRange || {};
            const enableNetworkBased = p.enableNetworkBased !== undefined ? p.enableNetworkBased : true;
            const enableBehaviorBased = p.enableBehaviorBased !== undefined ? p.enableBehaviorBased : true;

            this.lastLinkThreshold = threshold;
            this.lastLinkTimeRange = timeRange;

            // Construct rules
            const rules = [];

            // 1. Transfer Network Rule
            if (enableNetworkBased) {
                rules.push({
                    rule_type: "transfer-network",
                    parameters: {
                        threshold: threshold,
                        volume_threshold: p.volumeThreshold || 0,
                        check_funding_source: p.checkFundingSource || false,
                        check_same_sender: p.checkSameSender || false,
                        check_same_recipient: p.checkSameRecipient || false,
                        enable_tx_count: p.enableTxCount !== undefined ? p.enableTxCount : true,
                        enable_tx_volume: p.enableTxVolume !== undefined ? p.enableTxVolume : true
                    },
                    enabled: true
                });
            }

            // 2. Behavior Similarity Rule
            if (enableBehaviorBased) {
                rules.push({
                    rule_type: "behavior-similarity",
                    parameters: {
                        time_window: p.behaviorTimeWindow || 1.0,
                        enable_rule3: p.enableRule3 !== undefined ? p.enableRule3 : true,
                        enable_rule4: p.enableRule4 !== undefined ? p.enableRule4 : false,
                        enable_rule5: p.enableRule5 !== undefined ? p.enableRule5 : false,
                        rule3_params: p.rule3Params || {},
                        rule4_params: p.rule4Params || {},
                        rule5_params: p.rule5Params || {}
                    },
                    enabled: true
                });
            }

            try {
                console.log("TokenDistribution: Sending link request with rules:", JSON.stringify(rules, null, 2));
                const response = await fetch('/api/entity/links', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        target_users: users,
                        time_range: timeRange,
                        rules: rules
                    })
                });

                if (!response.ok) throw new Error("Failed to fetch links");
                
                const data = await response.json();
                console.log("Links received:", data.links ? data.links.length : 0);
                if (data.links && data.links.length > 0) {
                     const behaviorLinks = data.links.filter(l => l.reasons && l.reasons.some(r => r.includes("Behavior") || r.includes("Sequence")));
                     console.log(`Behavior-based links count: ${behaviorLinks.length}`);
                }
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

            // Mark suspicious traders
            if (this.suspiciousTraders && this.suspiciousTraders.length > 0) {
                const suspiciousMap = new Map();
                this.suspiciousTraders.forEach(t => suspiciousMap.set(t.trader_id, t));
                entries.forEach(d => {
                    if (suspiciousMap.has(d.id)) {
                        d.suspicious = suspiciousMap.get(d.id);
                    }
                });
            }

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
                    if (entity.details && entity.details.members && entity.details.members.length > 1) {
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
                        
                        // Attach detection info to the node
                        node.detectionInfo = {
                            entityId: entity.entity_id,
                            reason: entity.reason, // List[str]
                            confidence: entity.confidence
                        };

                        if (!groupMap.has(entity.entity_id)) {
                            groupMap.set(entity.entity_id, []);
                        }
                        groupMap.get(entity.entity_id).push(node);
                    } else {
                        independentNodes.push(node);
                        finalNodes.push(node);
                    }
                });

                // Post-process groups: Dismantle groups with < 2 members
                const finalGroupNodes = [];
                groupMap.forEach((members, entityId) => {
                    if (members.length > 1) {
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
                        finalGroupNodes.push(groupNode);
                    } else {
                        // Dismantle single-node groups
                        members.forEach(m => {
                            m.detectionInfo = null; // Clear detection info as it's not shown as group
                            independentNodes.push(m);
                            finalNodes.push(m);
                        });
                    }
                });

                simulationNodes = [...independentNodes, ...finalGroupNodes];
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

            // Map user ID to member node for internal links
            const userToMemberNode = new Map();
            entries.forEach(d => userToMemberNode.set(d.id, d));

            if (this.currentLinks && this.currentLinks.length > 0) {
                this.currentLinks.forEach(link => {
                    const sourceNode = userToSimNode.get(link.source);
                    const targetNode = userToSimNode.get(link.target);
                    
                    if (sourceNode && targetNode) {
                        if (sourceNode !== targetNode) {
                            // Link between different simulation bodies (Group-Group, Group-Single, Single-Single)
                            // Create key for link aggregation
                            const key = `${sourceNode.id}-${targetNode.id}`;
                            if (!simulationLinkMap.has(key)) {
                                simulationLinkMap.set(key, { 
                                    source: sourceNode.id, 
                                    target: targetNode.id, 
                                    weight: 0,
                                    originalLinks: []
                                });
                            }
                            const simLink = simulationLinkMap.get(key);
                            simLink.weight += link.weight;
                            simLink.originalLinks.push(link);
                        } else if (sourceNode.isGroup) {
                            // Internal link within a group
                            if (!sourceNode.internalLinks) {
                                sourceNode.internalLinks = [];
                            }
                            sourceNode.internalLinks.push({
                                source: userToMemberNode.get(link.source),
                                target: userToMemberNode.get(link.target),
                                ...link
                            });
                        }
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
                .text(d => {
                    let info = `Source: ${d.source}\nTarget: ${d.target}\nTotal Weight: ${d.weight}`;
                    if (d.originalLinks && d.originalLinks.length > 0) {
                        const reasons = new Set();
                        d.originalLinks.forEach(l => {
                            if (l.reasons) l.reasons.forEach(r => reasons.add(r));
                        });
                        if (reasons.size > 0) {
                            info += `\nReasons:\n- ${Array.from(reasons).join('\n- ')}`;
                        }
                        info += `\nOriginal Links: ${d.originalLinks.length}`;
                    }
                    return info;
                });

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
                .attr("transform", d => `translate(${d.x ?? 0},${d.y ?? 0})`)
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
                .attr("transform", d => `translate(${d.x ?? 0},${d.y ?? 0})`)
                .attr("r", d => d.r)
                .style("fill", d => color(d.value))
                .style("opacity", 0.6)
                .style("stroke", d => d.suspicious ? "#ff0000" : "#5976ba")
                .style("stroke-width", d => d.suspicious ? 3 : 2)
                .call(drag) // Attach drag
                .on("mouseover", (event, d) => {
                    d3.select(event.currentTarget).style("stroke", d.suspicious ? "#ff0000" : "#000");
                    const tooltip = this.$refs.tooltip;
                    let content = `Address: ${d.name.substring(0,6)}...<br>Balance: ${d.value.toLocaleString()}`;
                    if (d.suspicious) {
                        content += `<br><strong style="color:red">Suspicious Activity Detected!</strong>`;
                        if (d.suspicious.reasons && d.suspicious.reasons.length > 0) {
                             content += `<ul style="margin: 5px 0; padding-left: 15px; text-align: left;">`;
                             d.suspicious.reasons.forEach(r => {
                                 content += `<li style="font-size: 10px;">${r}</li>`;
                             });
                             content += `</ul>`;
                        } else {
                             content += `<br>Diff: ${d.suspicious.diff.toFixed(2)}`;
                        }
                    }

                    if (d.detectionInfo) {
                        content += `<br><strong style="color:orange">Entity Group Detected</strong>`;
                        if (d.detectionInfo.reason && d.detectionInfo.reason.length > 0) {
                             content += `<ul style="margin: 5px 0; padding-left: 15px; text-align: left;">`;
                             d.detectionInfo.reason.forEach(r => {
                                 content += `<li style="font-size: 10px;">${r}</li>`;
                             });
                             content += `</ul>`;
                        }
                    }

                    tooltip.innerHTML = content;
                    tooltip.style.display = "block";
                    tooltip.style.opacity = 1;
                    const [x, y] = d3.pointer(event, this.$refs.chart_container);
                    tooltip.style.left = (x + 10) + "px";
                    tooltip.style.top = (y - 10) + "px";
                })
                .on("mousemove", (event) => {
                    const tooltip = this.$refs.tooltip;
                    const [x, y] = d3.pointer(event, this.$refs.chart_container);
                    tooltip.style.left = (x + 10) + "px";
                    tooltip.style.top = (y - 10) + "px";
                })
                .on("mouseout", (event, d) => {
                    d3.select(event.currentTarget).style("stroke", d.suspicious ? "#ff0000" : "#5976ba");
                    this.$refs.tooltip.style.opacity = 0;
                });

            // Draw Group Members
            groups.each(function(d) {
                const groupG = d3.select(this);

                // Draw Members first (so links are on top)
                groupG.selectAll(".member")
                    .data(d.children)
                    .enter().append("circle")
                    .attr("class", "bubble member")
                    .attr("cx", child => child.x - d.enclose.x)
                    .attr("cy", child => child.y - d.enclose.y)
                    .attr("r", child => child.r)
                    .style("fill", child => color(child.value))
                    .style("opacity", 0.6)
                    .style("stroke", child => child.suspicious ? "#ff0000" : "#5976ba")
                    .style("stroke-width", child => child.suspicious ? 3 : 2);

                // Draw Internal Links on top
                if (d.internalLinks && d.internalLinks.length > 0) {
                    console.log(`Group ${d.id} has ${d.internalLinks.length} internal links.`);
                    groupG.selectAll(".internal-link")
                        .data(d.internalLinks)
                        .enter().append("line")
                        .attr("class", "internal-link")
                        .attr("x1", l => l.source.x - d.enclose.x)
                        .attr("y1", l => l.source.y - d.enclose.y)
                        .attr("x2", l => l.target.x - d.enclose.x)
                        .attr("y2", l => l.target.y - d.enclose.y)
                        .attr("stroke", "#555") 
                        .attr("stroke-width", 1.5)
                        .attr("stroke-opacity", 0.6)
                        // .style("pointer-events", "none") // Let clicks pass through to bubbles
                        .append("title")
                        .text(l => {
                            let info = `Internal Link\nSource: ${l.source.name}\nTarget: ${l.target.name}`;
                            if (l.reasons && l.reasons.length > 0) {
                                info += `\nReasons:\n- ${l.reasons.join('\n- ')}`;
                            }
                            return info;
                        });
                }
            });
            
            // Re-bind events for members with correct scope
            const self = this;
            groups.selectAll(".member")
                 .on("mouseover", function(event, d) {
                    d3.select(this).style("stroke", d.suspicious ? "#ff0000" : "#000");
                    const tooltip = self.$refs.tooltip;
                    let content = `Address: ${d.name.substring(0,6)}...<br>Balance: ${d.value.toLocaleString()}`;
                    if (d.suspicious) {
                            content += `<br><strong style="color:red">Suspicious Activity Detected!</strong>`;
                            if (d.suspicious.reasons && d.suspicious.reasons.length > 0) {
                                 content += `<ul style="margin: 5px 0; padding-left: 15px; text-align: left;">`;
                                 d.suspicious.reasons.forEach(r => {
                                     content += `<li style="font-size: 10px;">${r}</li>`;
                                 });
                                 content += `</ul>`;
                            } else {
                                 content += `<br>Diff: ${d.suspicious.diff.toFixed(2)}`;
                            }
                        }

                        if (d.detectionInfo) {
                            content += `<br><strong style="color:orange">Entity Group Detected</strong>`;
                            if (d.detectionInfo.reason && d.detectionInfo.reason.length > 0) {
                                 content += `<ul style="margin: 5px 0; padding-left: 15px; text-align: left;">`;
                                 d.detectionInfo.reason.forEach(r => {
                                     content += `<li style="font-size: 10px;">${r}</li>`;
                                 });
                                 content += `</ul>`;
                            }
                        }

                        tooltip.innerHTML = content;
                    tooltip.style.display = "block";
                    tooltip.style.opacity = 1;
                    const [x, y] = d3.pointer(event, self.$refs.chart_container);
                    tooltip.style.left = (x + 10) + "px";
                    tooltip.style.top = (y - 10) + "px";
                })
                .on("mousemove", function(event) {
                     const tooltip = self.$refs.tooltip;
                     const [x, y] = d3.pointer(event, self.$refs.chart_container);
                     tooltip.style.left = (x + 10) + "px";
                     tooltip.style.top = (y - 10) + "px";
                })
                .on("mouseout", function(event, d) {
                    d3.select(this).style("stroke", d.suspicious ? "#ff0000" : "#5976ba");
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
        async runManipulationDetection(threshold, timeWindow, checkEntityBased, isAutoRun = false) {
            console.log("TokenDistribution: runManipulationDetection called with", threshold, timeWindow, checkEntityBased, isAutoRun);
            
            // Get current users from snapshot data
            let users = [];
            if (this.snapshotData && this.snapshotData.balances && this.snapshotData.balances.users) {
                users = Object.keys(this.snapshotData.balances.users).filter(u => u !== 'Others');
            }

            if (users.length === 0) {
                console.warn("TokenDistribution: No users to detect manipulation for.");
                return;
            }

            // Prepare entities if checkEntityBased is true
            let entities = [];
            if (checkEntityBased && this.detectedEntities && this.detectedEntities.length > 0) {
                entities = this.detectedEntities.map(e => e.details.members);
            }
            
            try {
                const response = await fetch('/api/manipulation/detect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        threshold: threshold,
                        limit_traders: users,
                        time_window: timeWindow,
                        check_entity_based: checkEntityBased,
                        entities: entities
                    })
                });
                
                if (!response.ok) throw new Error("Detection failed");
                
                const data = await response.json();
                console.log("Manipulation detection result:", data);
                
                // Store results
                this.suspiciousTraders = data.suspicious_traders || [];
                
                // If not auto-run (meaning triggered by user update), we might need to re-highlight or re-draw
                // But since we are likely in a flow where drawChart handles it, we just update data.
                // If the chart is already drawn, we can call highlightSuspiciousTraders to update it without full redraw?
                // Or just call drawChart again? calling drawChart is safer but might restart simulation.
                // Let's stick to updating data. If this is called standalone, we might want to trigger update.
                
                if (!isAutoRun) {
                    this.highlightSuspiciousTraders(this.suspiciousTraders);
                }
                
                // Emit result up
                this.$emit('manipulation-detected', { ...data, isAutoRun });
                
            } catch (error) {
                console.error("TokenDistribution: Manipulation detection error:", error);
            }
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