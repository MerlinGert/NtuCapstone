<template>
    <div style="padding: 15px; height: 100%; display: flex; flex-direction: column; gap: 10px; overflow-y: auto;">
        <!-- Snapshot Configuration -->
        <div style="font-weight: bold; border-bottom: 1px solid #eee; padding-bottom: 5px;">Snapshot Configuration</div>
        <div style="display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-end;">
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <label style="font-size: 12px; font-weight: bold;">Snapshot Time</label>
                <select v-model="selectedSnapshotTime" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; min-width: 200px;">
                    <option v-for="time in snapshotTimes" :key="time" :value="time">{{ time }}</option>
                </select>
            </div>
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <label style="font-size: 12px; font-weight: bold;">Top Holders Threshold (%)</label>
                <input type="number" v-model.number="snapshotThreshold" min="1" max="100" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 80px;">
            </div>
            <button @click="updateSnapshot" :disabled="loadingSnapshot" style="padding: 8px 15px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; height: 36px;">
                {{ loadingSnapshot ? 'Loading...' : 'Update View' }}
            </button>
        </div>

<<<<<<< Updated upstream
        <!-- Rule Configuration -->
        <div style="font-weight: bold; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 10px;">Entity Detection Configuration</div>
        
        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <!-- Rule Type -->
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <label style="font-size: 12px; font-weight: bold;">Rule Type</label>
                <select style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                    <option value="transfer-network">Transfer Network Based</option>
                </select>
            </div>

            <!-- Threshold -->
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <label style="font-size: 12px; font-weight: bold;">Threshold (Min Tx Count)</label>
                <input type="number" v-model.number="detectionThreshold" min="1" max="50" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 150px;">
            </div>

            <!-- Time Range -->
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <label style="font-size: 12px; font-weight: bold;">Time Range (Empty = Full Range)</label>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <input type="datetime-local" v-model="startTime" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                    <span>to</span>
                    <input type="datetime-local" v-model="endTime" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
=======
        <!-- Entity Detection Configuration -->
        <div style="border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;">
            <div style="font-weight: bold;">Entity Detection</div>
            <span v-if="lastResultCount !== null" style="color: #666; font-size: 12px;">
                Last Result: {{ lastResultCount }} groups
            </span>
        </div>
        
        <div style="display: flex; flex-direction: column; gap: 5px;">
            <!-- Transfer Network Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleSection('transfer')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>Network Based</span>
                    <span>{{ activeSection === 'transfer' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeSection === 'transfer'" style="padding: 10px; display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; flex-direction: column; gap: 5px;">
                        <label style="font-size: 12px; font-weight: bold;">Threshold (Min Tx Count)</label>
                        <input type="number" v-model.number="detectionThreshold" min="1" max="50" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 150px;">
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 5px;">
                        <label style="font-size: 12px; font-weight: bold;">Time Range (Empty = Full Range)</label>
                        <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                            <input type="datetime-local" v-model="startTime" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                            <span>to</span>
                            <input type="datetime-local" v-model="endTime" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                        </div>
                    </div>
                    <button @click="triggerDetectionSection('transfer')" :disabled="loading" style="padding: 6px 14px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 12px; align-self: flex-start;">
                        {{ loading ? 'Detecting...' : 'Run Detection' }}
                    </button>
                </div>
            </div>

            <!-- Behavior Similarity Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleSection('behavior')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>Behavior Similarity Based</span>
                    <span>{{ activeSection === 'behavior' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeSection === 'behavior'" style="padding: 10px; display: flex; flex-direction: column; gap: 10px;">
                    <!-- Sub-rule selector -->
                    <div style="display: flex; flex-direction: column; gap: 5px;">
                        <label style="font-size: 12px; font-weight: bold;">Similarity Rule</label>
                        <select v-model="similarityRuleType" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                            <option value="similar_trading_sequence">Similar Trading Sequence</option>
                            <option value="similar_balance_sequence">Similar Balance Sequence</option>
                            <option value="similar_earning_sequence">Similar Earning Sequence</option>
                        </select>
                    </div>

                    <!-- Rule3: Similar Trading Sequence -->
                    <template v-if="similarityRuleType === 'similar_trading_sequence'">
                        <div style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Direction Mode</label>
                            <select v-model="simTradingParams.direction_mode" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                                <option value="same_side_only">Same Side Only</option>
                                <option value="mixed_allowed">Mixed Allowed</option>
                            </select>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Sequence Representation</label>
                            <select v-model="simTradingParams.sequence_representation" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                                <option value="action_only">Action Only</option>
                                <option value="action+amount">Action + Amount</option>
                                <option value="action+price">Action + Price</option>
                                <option value="action+amount+price">Action + Amount + Price</option>
                            </select>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Min Contiguous Length</label>
                            <input type="number" v-model.number="simTradingParams.min_contiguous_length" min="1" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 80px;">
                        </div>
                        <div v-if="simTradingParams.sequence_representation.includes('amount')" style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Amount Similarity (0-1)</label>
                            <input type="number" v-model.number="simTradingParams.amount_similarity" min="0" max="1" step="0.05" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 80px;">
                        </div>
                        <div v-if="simTradingParams.sequence_representation.includes('price')" style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Price Similarity (0-1)</label>
                            <input type="number" v-model.number="simTradingParams.price_similarity" min="0" max="1" step="0.05" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 80px;">
                        </div>
                    </template>

                    <!-- Rule4: Similar Balance Sequence -->
                    <template v-if="similarityRuleType === 'similar_balance_sequence'">
                        <div style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Balance Axis</label>
                            <select v-model="simBalanceParams.balance_axis" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                                <option value="time_grid">Time Grid</option>
                                <option value="tx_step">Transaction Step</option>
                            </select>
                        </div>
                        <div v-if="simBalanceParams.balance_axis === 'tx_step'" style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Tx Step</label>
                            <input type="number" v-model.number="simBalanceParams.tx_step" min="2" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 80px;">
                        </div>
                        <div v-if="simBalanceParams.balance_axis === 'time_grid'" style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Time Bin</label>
                            <select v-model="simBalanceParams.time_bin" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                                <option value="1h">1 Hour</option>
                                <option value="1d">1 Day</option>
                            </select>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Similarity Threshold (0-1)</label>
                            <input type="number" v-model.number="simBalanceParams.similarity" min="0" max="1" step="0.05" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 80px;">
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">TopK Neighbors</label>
                            <input type="number" v-model.number="simBalanceParams.topk_neighbors" min="1" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 80px;">
                        </div>
                    </template>

                    <!-- Rule5: Similar Earning Sequence -->
                    <template v-if="similarityRuleType === 'similar_earning_sequence'">
                        <div style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Earning Axis</label>
                            <select v-model="simEarningParams.earning_axis" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                                <option value="time_grid">Time Grid</option>
                                <option value="tx_step">Transaction Step</option>
                            </select>
                        </div>
                        <div v-if="simEarningParams.earning_axis === 'tx_step'" style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Tx Step</label>
                            <input type="number" v-model.number="simEarningParams.tx_step" min="2" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 80px;">
                        </div>
                        <div v-if="simEarningParams.earning_axis === 'time_grid'" style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Time Bin</label>
                            <select v-model="simEarningParams.time_bin" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                                <option value="1h">1 Hour</option>
                                <option value="1d">1 Day</option>
                            </select>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">Similarity Threshold (0-1)</label>
                            <input type="number" v-model.number="simEarningParams.similarity" min="0" max="1" step="0.05" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 80px;">
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; font-weight: bold;">TopK Neighbors</label>
                            <input type="number" v-model.number="simEarningParams.topk_neighbors" min="1" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 80px;">
                        </div>
                    </template>

                    <!-- Time Range for Similarity -->
                    <div style="display: flex; flex-direction: column; gap: 5px;">
                        <label style="font-size: 12px; font-weight: bold;">Time Range (Empty = Full Range)</label>
                        <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                            <input type="datetime-local" v-model="simStartTime" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                            <span>to</span>
                            <input type="datetime-local" v-model="simEndTime" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                        </div>
                    </div>
                    <button @click="triggerDetectionSection('behavior')" :disabled="loading" style="padding: 6px 14px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 12px; align-self: flex-start;">
                        {{ loading ? 'Detecting...' : 'Run Detection' }}
                    </button>
                </div>
            </div>

            <!-- Manipulation History Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleSection('history')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>Manipulation History Based</span>
                    <span>{{ activeSection === 'history' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeSection === 'history'" style="padding: 10px;">
                    <span style="color: #999; font-size: 12px;">Configuration not yet available.</span>
                    <br><br>
                    <button disabled style="padding: 6px 14px; background: #ccc; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 12px; cursor: not-allowed;">Run Detection</button>
>>>>>>> Stashed changes
                </div>
            </div>
        </div>

        <div style="margin-top: 5px;">
            <button @click="triggerDetection" :disabled="loading" style="padding: 8px 15px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">
                {{ loading ? 'Detecting...' : 'Run Detection' }}
            </button>
            <span v-if="lastResultCount !== null" style="margin-left: 10px; color: #666; font-size: 13px;">
                Last Result: Found {{ lastResultCount }} entity groups
            </span>
        </div>
    </div>
</template>

<script>
export default {
    name: "ControlPanel",
    props: {
        loading: {
            type: Boolean,
            default: false
        },
        lastResultCount: {
            type: Number,
            default: null
        }
    },
    data() {
        return {
            detectionThreshold: 1,
            // Default to empty strings which means "Full Range" in our logic
            startTime: "",
            endTime: "",
            
            // Snapshot Data
            snapshotTimes: [],
            selectedSnapshotTime: "",
<<<<<<< Updated upstream
            snapshotThreshold: 50,
            loadingSnapshot: false
=======
            snapshotThreshold: 30,
            loadingSnapshot: false,

            // UI State
            activeSection: 'transfer', // 'transfer', 'behavior', 'history'
            activeManipulationSection: 'network', // 'network', 'behavior_sim'
            loadingManipulation: false,
            activeLinkSection: 'network', // 'network', 'behavior_sim', 'history'
            loadingLinks: false,
            
            // Link Config
            linkThreshold: 1,
            linkStartTime: "",
            linkEndTime: "",

            // Similarity Detection Config
            similarityRuleType: "similar_trading_sequence",
            simStartTime: "",
            simEndTime: "",
            simTradingParams: {
                direction_mode: "same_side_only",
                sequence_representation: "action_only",
                min_contiguous_length: 3,
                amount_similarity: 0.8,
                price_similarity: 0.8,
            },
            simBalanceParams: {
                balance_axis: "time_grid",
                tx_step: 5,
                time_bin: "1h",
                similarity: 0.8,
                topk_neighbors: 5,
            },
            simEarningParams: {
                earning_axis: "time_grid",
                tx_step: 5,
                time_bin: "1h",
                similarity: 0.8,
                topk_neighbors: 5,
            },
>>>>>>> Stashed changes
        }
    },
    mounted() {
        this.fetchSnapshotTimes();
    },
    methods: {
        async fetchSnapshotTimes() {
            try {
                const response = await fetch('/api/snapshot/times');
                const data = await response.json();
                if (data.times && data.times.length > 0) {
                    this.snapshotTimes = data.times;
                    this.selectedSnapshotTime = data.times[data.times.length - 1]; // Default to last
                    // Trigger initial load
                    this.updateSnapshot();
                }
            } catch (error) {
                console.error("ControlPanel: Failed to fetch snapshot times", error);
            }
        },
<<<<<<< Updated upstream
=======
        triggerDetectionSection(section) {
            const params = this.getDetectionParams(section);
            this.$emit('run-detection', params);
        },
        getDetectionParams(section) {
            const resolvedSection = section !== undefined ? section : this.activeSection;
            const timeRange = {};
            if (this.startTime) timeRange.start = this.startTime.replace('T', ' ');
            if (this.endTime) timeRange.end = this.endTime.replace('T', ' ');

            if (resolvedSection === 'behavior') {
                // Similarity-based detection
                const simTimeRange = {};
                if (this.simStartTime) simTimeRange.start = this.simStartTime.replace('T', ' ');
                if (this.simEndTime) simTimeRange.end = this.simEndTime.replace('T', ' ');

                let parameters = {};
                if (this.similarityRuleType === 'similar_trading_sequence') {
                    parameters = { ...this.simTradingParams };
                } else if (this.similarityRuleType === 'similar_balance_sequence') {
                    parameters = { ...this.simBalanceParams };
                } else if (this.similarityRuleType === 'similar_earning_sequence') {
                    parameters = { ...this.simEarningParams };
                }

                return {
                    threshold: this.detectionThreshold,
                    timeRange: Object.keys(simTimeRange).length > 0 ? simTimeRange : undefined,
                    ruleType: this.similarityRuleType,
                    parameters: parameters,
                };
            }

            return {
                threshold: this.detectionThreshold,
                timeRange: Object.keys(timeRange).length > 0 ? timeRange : undefined,
                ruleType: "transfer-network"
            };
        },
        // Keep old method for backward compat (used by updateSnapshot)
        getDetectionParamsLegacy() {
            return this.getDetectionParams();
        },
        getLinkParams() {
            const timeRange = {};
            if (this.linkStartTime) timeRange.start = this.linkStartTime.replace('T', ' ');
            if (this.linkEndTime) timeRange.end = this.linkEndTime.replace('T', ' ');
            return {
                threshold: this.linkThreshold,
                timeRange: Object.keys(timeRange).length > 0 ? timeRange : undefined,
                ruleType: "transfer-network"
            };
        },
>>>>>>> Stashed changes
        updateSnapshot() {
            this.loadingSnapshot = true;
            this.$emit('update-snapshot', {
                time: this.selectedSnapshotTime,
                threshold: this.snapshotThreshold / 100 // Convert percentage to 0-1
            });
            // Simulate loading done after emit (actual data loading is in parent/sibling)
            // But we can just set it to false after a timeout or let parent handle it?
            // For now, let's just reset it after a short delay or rely on parent.
            // Actually, we don't know when parent is done. Let's just set it false after 500ms.
            setTimeout(() => {
                this.loadingSnapshot = false;
            }, 500);
        },
        triggerDetection() {
            console.log("ControlPanel: triggerDetection called");
<<<<<<< Updated upstream
            // Prepare time range object
            const timeRange = {};
            if (this.startTime) timeRange.start = this.startTime.replace('T', ' ');
            if (this.endTime) timeRange.end = this.endTime.replace('T', ' ');
            
            console.log("ControlPanel: emitting run-detection", {
                threshold: this.detectionThreshold,
                timeRange: Object.keys(timeRange).length > 0 ? timeRange : undefined,
                ruleType: "transfer-network"
            });

            this.$emit('run-detection', {
                threshold: this.detectionThreshold,
                timeRange: Object.keys(timeRange).length > 0 ? timeRange : undefined,
                ruleType: "transfer-network"
            });
        }
=======
            const params = this.getDetectionParams();
            console.log("ControlPanel: emitting run-detection", params);
            this.$emit('run-detection', params);
        },
        triggerManipulationDetection() {
            this.loadingManipulation = true;
            // TODO: Implement actual detection logic
            console.log("ControlPanel: triggerManipulationDetection called");
            setTimeout(() => {
                this.loadingManipulation = false;
                alert("Manipulation detection not yet implemented.");
            }, 1000);
        },
        updateLinks() {
            console.log("ControlPanel: updateLinks called");
            const params = this.getLinkParams();
            
            console.log("ControlPanel: emitting update-links", params);
            
            this.$emit('update-links', params);
        },
>>>>>>> Stashed changes
    }
}
</script>

<style scoped>
</style>
