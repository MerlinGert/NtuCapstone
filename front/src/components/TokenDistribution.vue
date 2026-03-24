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
            <!-- ezio -->
            <button @click="openSnapshot" style="padding: 3px 6px; cursor: pointer; background-color: #4caf50; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 12px;">Snapshot</button>
        </div>

        <!-- Snapshot Modal -->
        <div v-if="showSnapshot" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; justify-content: center; align-items: center;">
            <TokenSnapshot :snapshot-data="snapshotPayload" @close="showSnapshot = false" />
        </div>

        <!-- ezio -->
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
import TokenSnapshot from "./TokenSnapshot.vue"

export default {
    name: "TokenDistribution",
    components: { TokenSnapshot },
    data() {
        return {
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
            // detectedEntities: [], // Removed local state, use prop
            // currentLinks: [], // Removed local state, use prop
            simulation: null,
            centerX: 0,
            centerY: 0,
            topPercent: 50,
            suspiciousTraders: [],
            // used by ezio
            showSnapshot: false,
            snapshotPayload: null,
        }
    },
    props: {
        snapshotData: {
            type: Object,
            default: null
        },
        entityDetectionResults: {
            type: Object,
            default: () => ({})
        },
        linkDetectionResults: {
            type: [Array, Object],
            default: () => []
        },
        manipulationDetectionResults: {
            type: [Array, Object],
            default: () => []
        }
    },
    watch: {
        snapshotData: {
            handler(newVal) {
                if (newVal) {
                    this.loading = false;
                    this.drawChart();
                } else {
                    this.loading = true;
                }
            },
            deep: true
        },
        entityDetectionResults: {
            handler(newVal) {
                console.log("TokenDistribution: entityDetectionResults changed", newVal ? newVal.length : 0);
                this.drawChart();
            },
            deep: true
        },
        linkDetectionResults: {
            handler(newVal) {
                console.log("TokenDistribution: linkDetectionResults changed", newVal ? newVal.length : 0);
                this.drawChart();
            },
            deep: true
        },
        manipulationDetectionResults: {
            handler(newVal) {
                console.log("TokenDistribution: manipulationDetectionResults changed", newVal ? newVal.length : 0);
                this.processManipulationResults();
            },
            deep: true
        }
    },
    computed: {
        displayTime() {
            if (!this.snapshotData) return "Loading...";
            return this.snapshotData.time ? this.snapshotData.time.replace(" UTC", "") : "Unknown Time";
        },
        detectedEntities() {
            return this.entityDetectionResults || [];
        },
        currentLinks() {
            return this.linkDetectionResults || [];
        }
    },
    mounted() {
        window.addEventListener('resize', this.setSvg);
        this.setSvg();
    },
    beforeUnmount() {
        window.removeEventListener('resize', this.setSvg);
    },
    methods: {
        processManipulationResults() {
            if (!this.manipulationDetectionResults || this.manipulationDetectionResults.length === 0) {
                this.suspiciousTraders = [];
                this.highlightSuspiciousTraders([]);
                return;
            }
            
            const suspiciousMap = new Map();
            this.manipulationDetectionResults.forEach(result => {
                const method = result.detection_method;
                if (result.participants && Array.isArray(result.participants)) {
                    result.participants.forEach(addr => {
                        if (!suspiciousMap.has(addr)) {
                            suspiciousMap.set(addr, { trader_id: addr, reasons: [] });
                        }
                        suspiciousMap.get(addr).reasons.push(`Detected via: ${method}`);
                    });
                }
            });
            
            this.suspiciousTraders = Array.from(suspiciousMap.values());
            this.highlightSuspiciousTraders(this.suspiciousTraders);
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
        setSvg() {
            if (this.$refs.chart_container) {
                this.svgHeight = this.$refs.chart_container.offsetHeight;
                this.svgWidth = this.$refs.chart_container.offsetWidth;
                this.drawChart();
            }
        },
        // updateLinks removed as logic moved to parent
        // async updateLinks(linkParams, silent = false) { ... }
        // added by ezio
        openSnapshot() {
            this.snapshotPayload = this.captureSnapshot();
            this.showSnapshot = true;
        },
        captureSnapshot() {
            const svg = d3.select(this.$refs.chart_container).select("svg.tokenDistribution");
            const nodes = [];

            // Capture singles — 直接读取SVG元素的fill颜色，不再重新计算
            svg.selectAll(".single").each(function(d) {
                nodes.push({
                    id: d.id, name: d.name, value: d.value, r: d.r,
                    x: d.x, y: d.y, suspicious: d.suspicious || null,
                    fill: d3.select(this).style("fill"),
                    type: 'single'
                });
            });

            // Capture groups
            svg.selectAll(".group").each(function(d) {
                const members = [];
                d3.select(this).selectAll(".member").each(function(child) {
                    members.push({
                        id: child.id, name: child.name, value: child.value, r: child.r,
                        cx: +d3.select(this).attr("cx"),
                        cy: +d3.select(this).attr("cy"),
                        suspicious: child.suspicious || null,
                        fill: d3.select(this).style("fill")
                    });
                });
                nodes.push({
                    id: d.id, isGroup: true, r: d.r, x: d.x, y: d.y,
                    children: members, type: 'group'
                });
            });

            // Capture Others ring data
            const balances = this.snapshotData ? this.snapshotData.balances : null;
            let othersBalance = 0;
            let usersBalance = 0;
            if (balances && balances.users) {
                othersBalance = balances.users['Others'] || 0;
                Object.entries(balances.users).forEach(([k, v]) => {
                    if (k !== 'Others') usersBalance += v;
                });
            }

            return {
                nodes,
                links: Array.isArray(this.currentLinks) ? this.currentLinks.map(l => ({
                    source: l.source.id || l.source,
                    target: l.target.id || l.target,
                    weight: l.weight
                })) : [],
                width: this.svgWidth,
                height: this.svgHeight,
                centerX: this.centerX,
                centerY: this.centerY,
                othersBalance,
                usersBalance,
                scaleFactor: this.scaleFactor,
                time: this.displayTime
            };
        },


        drawChart() {
            if (!this.snapshotData || this.svgWidth === 0) return;
            console.log("TokenDistribution: drawChart called with", this.entityDetectionResults, " and", this.linkDetectionResults);
            const width = this.svgWidth;
            const height = this.svgHeight;
            const balances = this.snapshotData.balances;

            // 1. Prepare base entries
            let entries = [];
            let relatedEntries = [];
            let othersBalance = 0;
            if (balances && balances.users) {
                othersBalance = balances.users['Others'] || 0;
                entries = Object.entries(balances.users)
                    .filter(([owner, balance]) => owner !== 'Others' && balance > 0)
                    .map(([owner, balance]) => ({ 
                        id: owner,
                        name: owner, 
                        value: balance,
                        r: 0, // Will be set after scale calculation
                        isRelated: false
                    }));
            }
            if (balances && balances.related_users) {
                relatedEntries = Object.entries(balances.related_users)
                    .filter(([owner, balance]) => balance > 0)
                    .map(([owner, balance]) => ({ 
                        id: owner,
                        name: owner, 
                        value: balance,
                        r: 0,
                        isRelated: true
                    }));
            }

            this.userCount = entries.length + relatedEntries.length;
            const usersBalance = entries.reduce((sum, d) => sum + d.value, 0); // Scale based on target users or both? Let's use target users for scale consistency, or both.
            const allNodesBalance = usersBalance + relatedEntries.reduce((sum, d) => sum + d.value, 0);

            // Mark suspicious traders
            if (this.suspiciousTraders && this.suspiciousTraders.length > 0) {
                const suspiciousMap = new Map();
                this.suspiciousTraders.forEach(t => suspiciousMap.set(t.trader_id, t));
                entries.forEach(d => {
                    if (suspiciousMap.has(d.id)) {
                        d.suspicious = suspiciousMap.get(d.id);
                    }
                });
                relatedEntries.forEach(d => {
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
            relatedEntries.forEach(d => {
                d.r = Math.sqrt(d.value) * radiusScale;
            });

            // 3. Handle Grouping (Hierarchical Packing)
            let simulationNodes = [];
            let finalNodes = []; // Flattened list for rendering links and interactions

            if (this.entityDetectionResults && this.entityDetectionResults.length > 0) {
                // Map user -> group
                const userGroupMap = new Map();
                // entityDetectionResults structure: [{users: [...], relations: [...]}, ...]
                // We need to assign IDs to these entities if they don't have one, or use index
                
                this.entityDetectionResults.forEach((entity, index) => {
                    const entityId = `entity_${index}`;
                    entity.id = entityId; // Assign ID for reference
                    
                    if (entity.users && entity.users.length > 1) {
                        entity.users.forEach(userId => {
                            userGroupMap.set(userId, entity);
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
                            entityId: entity.id,
                            relations: entity.relations, // Should be array of relations
                        };

                        if (!groupMap.has(entity.id)) {
                            groupMap.set(entity.id, []);
                        }
                        groupMap.get(entity.id).push(node);
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
                simulationNodes = [...entries];
                finalNodes = [...entries];
            }

            // Append related users to simulationNodes
            // We want to render them as single nodes, but keep them on the outer ring
            relatedEntries.forEach(node => {
                simulationNodes.push(node);
                finalNodes.push(node);
            });

            // 4. Setup SVG
            const svg = d3.select(this.$refs.chart_container).select("svg.tokenDistribution");
            svg.attr("width", width).attr("height", height);
            svg.selectAll("*").remove();
            
            const centerX = width / 2;
            const centerY = height / 2;
            this.centerX = centerX;
            this.centerY = centerY;
            
            const g = svg.append("g").attr("transform", `translate(${centerX},${centerY})`);
            
            // Create layer groups in specific order (bottom to top)
            const ringGroup = g.append("g").attr("class", "ring-layer");
            const linkGroup = g.append("g").attr("class", "link-layer");
            const bubbleGroup = g.append("g").attr("class", "bubble-layer");

            // Draw "Others" Ring
            let relatedRingRadius = maxGroupRadius + 20; // Default if no others balance
            if (othersBalance > 0) {
                const targetRingArea = totalBalance > 0 ? targetTotalInkArea * (othersBalance / totalBalance) : 0;
                const userGroupRadius = Math.sqrt(maxGroupRadius * maxGroupRadius - targetRingArea / Math.PI);
                relatedRingRadius = (userGroupRadius + maxGroupRadius) / 2;
                
                const arc = d3.arc()
                    .innerRadius(userGroupRadius)
                    .outerRadius(maxGroupRadius)
                    .startAngle(0)
                    .endAngle(2 * Math.PI);
                ringGroup.append("path")
                    .attr("d", arc)
                    .style("fill", "#e3f2fd")
                    .style("opacity", 0.5);
            }
            
            const allEntries = [...entries, ...relatedEntries];
            const color = d3.scaleSequential(d3.interpolateBlues).domain([0, d3.max(allEntries, d => d.value)]);

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
            relatedEntries.forEach(d => userToMemberNode.set(d.id, d));

            // Process Links from linkDetectionResults
            // Expected format: array of relations (objects)
            // But linkDetectionResults might be a dictionary with keys 'target_relations_for_links', etc.
            // Or if it's the `links` array from detection response?
            // The previous logic used `this.currentLinks` which was `data.links`.
            // Now `this.linkDetectionResults` is passed from parent.
            // Let's assume parent passes `link_generation_results` which is `detectionResults.links`.
            // Wait, `detectionResults.links` from backend is typically a dictionary of 4 types of relations?
            // Or is it a list of links?
            // In `detection_service.py`, response has `target_relations_for_links` etc inside `current_results`?
            // Or does it return a unified list?
            // Let's check `CryptoVis.vue`: `this.link_generation_results = detectionResults.links;`
            // And `detectionResults` comes from `/api/detection/run`.
            // In `detection_service.py`, `detect_all` returns `response`.
            // `response` contains `entity_results` and `current_results` (the dict of 4 maps).
            // It does NOT seem to return a simple list of links.
            // However, the user instruction says: "link根据linkresults里面的ttrelation去画"
            // So `linkDetectionResults` is likely the object containing `target_relations_for_links` (tt_relations).
            
            // Let's extract TT and TR relations
            let linksToDraw = [];
            
            // From linkDetectionResults
            if (this.linkDetectionResults) {
                // target_relations_for_links
                if (this.linkDetectionResults.target_relations_for_links) {
                     Object.entries(this.linkDetectionResults.target_relations_for_links).forEach(([key, relations]) => {
                         const parts = key.split('-');
                         if (parts.length >= 2) {
                             linksToDraw.push({
                                 source: parts[0],
                                 target: parts[1],
                                 weight: relations.length,
                                 relations: relations,
                                 type: 'link'
                             });
                         }
                     });
                } else if (Array.isArray(this.linkDetectionResults)) {
                    // Fallback
                    linksToDraw = this.linkDetectionResults.map(l => ({ ...l, type: 'link' }));
                }
                
                // target_related_relations_for_links
                if (this.linkDetectionResults.target_related_relations_for_links) {
                     Object.entries(this.linkDetectionResults.target_related_relations_for_links).forEach(([key, relations]) => {
                         const parts = key.split('-');
                         if (parts.length >= 2) {
                             linksToDraw.push({
                                 source: parts[0],
                                 target: parts[1],
                                 weight: relations.length,
                                 relations: relations,
                                 type: 'link'
                             });
                         }
                     });
                }

                // target_related_relations_for_entity
                if (this.linkDetectionResults.target_related_relations_for_entity) {
                     Object.entries(this.linkDetectionResults.target_related_relations_for_entity).forEach(([key, relations]) => {
                         const parts = key.split('-');
                         if (parts.length >= 2) {
                             linksToDraw.push({
                                 source: parts[0],
                                 target: parts[1],
                                 weight: relations.length,
                                 relations: relations,
                                 type: 'entity'
                             });
                         }
                     });
                }
            }

            if (linksToDraw.length > 0) {
                linksToDraw.forEach(link => {
                    const sourceNode = userToSimNode.get(link.source);
                    const targetNode = userToSimNode.get(link.target);
                    
                    if (sourceNode && targetNode) {
                        if (sourceNode !== targetNode) {
                            // Link between different simulation bodies (Group-Group, Group-Single, Single-Single)
                            // Create key for link aggregation (include type to separate entity vs link relations)
                            const linkType = link.type || 'link';
                            const key = `${sourceNode.id}-${targetNode.id}-${linkType}`;
                            if (!simulationLinkMap.has(key)) {
                                simulationLinkMap.set(key, { 
                                    source: sourceNode.id, 
                                    target: targetNode.id, 
                                    weight: 0,
                                    type: linkType,
                                    originalLinks: []
                                });
                            }
                            const simLink = simulationLinkMap.get(key);
                            simLink.weight += (link.weight || 1);
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
            console.log(`Simulation Links: ${simulationLinks.length} (from ${linksToDraw.length} raw links)`);

            // Draw Links
            const linkElements = linkGroup.selectAll("line")
                .data(simulationLinks)
                .join("line")
                .attr("stroke", d => d.type === 'entity' ? '#ff9800' : '#999') // Orange for entity, default #999 for links
                .style("stroke-dasharray", d => d.type === 'entity' ? '5,5' : 'none')
                .attr("stroke-opacity", 0.6)
                .attr("stroke-width", d => Math.max(1, Math.min(Math.sqrt(d.weight), 5)));
            
            linkElements.append("title")
                .text(d => {
                    let info = `Source: ${d.source.id || d.source}\nTarget: ${d.target.id || d.target}\nTotal Weight: ${d.weight}`;
                    if (d.originalLinks && d.originalLinks.length > 0) {
                        info += `\nRelations (${d.originalLinks.length}):`;
                        d.originalLinks.forEach(l => {
                            if (l.description) {
                                info += `\n- ${l.description}`;
                            } else if (l.type) {
                                info += `\n- Type: ${l.type}`;
                            }
                        });
                    }
                    return info;
                });

            // Drag Behavior
            const drag = d3.drag()
                .on("start", (event, d) => {
                    if (!event.active) this.simulation.alphaTarget(0.3).restart();
                    if (!d.isRelated) {
                        d.fx = d.x;
                        d.fy = d.y;
                    } else {
                        const angle = Math.atan2(d.y, d.x);
                        d.fx = Math.cos(angle) * relatedRingRadius;
                        d.fy = Math.sin(angle) * relatedRingRadius;
                    }
                })
                .on("drag", (event, d) => {
                    if (d.isRelated) {
                        const angle = Math.atan2(event.y, event.x);
                        d.fx = Math.cos(angle) * relatedRingRadius;
                        d.fy = Math.sin(angle) * relatedRingRadius;
                    } else {
                        d.fx = event.x;
                        d.fy = event.y;
                    }
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
                .style("fill", "none") // Add white fill
                .style("fill-opacity", 1) // Make it opaque white
                .style("stroke", "#ff9800")
                .style("stroke-width", 2)
                .style("stroke-dasharray", "5,5");

            // Draw Independent Nodes
            const singles = bubbleGroup.selectAll(".single")
                .data(simulationNodes.filter(n => !n.isGroup))
                .enter().append("circle")
                .attr("class", d => `bubble single ${d.isRelated ? 'related' : ''}`)
                .attr("transform", d => `translate(${d.x ?? 0},${d.y ?? 0})`)
                .attr("r", d => d.r)
                .style("fill", d => color(d.value)) // Use identical color encoding for related users
                .style("opacity", 0.6)
                .style("stroke", d => d.suspicious ? "#ff0000" : "#5976ba") // Same stroke color
                .style("stroke-dasharray", "none") // Same solid border
                .style("stroke-width", d => d.suspicious ? 3 : 2)
                .call(drag) // Attach drag
                .on("mouseover", (event, d) => {
                    d3.select(event.currentTarget).style("stroke", d.suspicious ? "#ff0000" : "#000");
                    const tooltip = this.$refs.tooltip;
                    let content = `Address: ${d.name.substring(0,6)}...<br>Balance: ${d.value.toLocaleString()}`;
                    if (d.isRelated) content += `<br><em>(Related User)</em>`;
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
                        if (d.detectionInfo.relations && d.detectionInfo.relations.length > 0) {
                             // Assuming relations have reasons or types
                             content += `<br>Relations: ${d.detectionInfo.relations.length}`;
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
                .force("charge", d3.forceManyBody().strength(d => d.isGroup ? -50 : (d.isRelated ? -5 : -15))) 
                .force("collide", d3.forceCollide().radius(d => d.r + 5).strength(1))
                .force("r", d3.forceRadial(d => d.isRelated ? relatedRingRadius : 0, 0, 0).strength(d => d.isRelated ? 1 : 0.15))
                .force("center", d3.forceCenter(0, 0).strength(0.1))
                .force("link", d3.forceLink(simulationLinks).id(d => d.id).distance(d => d.source.isRelated || d.target.isRelated ? relatedRingRadius * 0.5 : 20).strength(d => d.source.isRelated || d.target.isRelated ? 0.5 : 1));

            this.simulation.on("tick", () => {
                // Determine inner boundary of the related ring.
                // The ring has radius `relatedRingRadius` and stroke-width 40.
                // So the inner edge is roughly at `relatedRingRadius - 20`.
                // We add a little padding (e.g., node radius) so the node doesn't overlap the ring stroke.
                const innerBoundary = relatedRingRadius - 20;

                // Force related users to strictly stay on the relatedRingRadius
                simulationNodes.forEach(d => {
                    if (d.isRelated) {
                        const angle = Math.atan2(d.y, d.x);
                        d.x = Math.cos(angle) * relatedRingRadius;
                        d.y = Math.sin(angle) * relatedRingRadius;
                    } else {
                        // Extra safety: Keep target users strictly inside the inner boundary 
                        const dist = Math.sqrt(d.x*d.x + d.y*d.y);
                        // Ensure the entire node (including its radius) stays inside the boundary
                        const maxDist = innerBoundary - (d.r || 10) - 2; 
                        
                        if (dist > maxDist && maxDist > 0) {
                            d.x = (d.x / dist) * maxDist;
                            d.y = (d.y / dist) * maxDist;
                        }
                    }
                });

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