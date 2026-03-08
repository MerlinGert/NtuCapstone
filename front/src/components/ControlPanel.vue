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

        <!-- Entity Detection Configuration -->
        <div style="border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;">
            <div style="font-weight: bold;">Entity Detection</div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <button @click="triggerDetection" :disabled="loading" style="padding: 5px 15px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 12px;">
                    {{ loading ? 'Detecting...' : 'Run Detection' }}
                </button>
                <span v-if="lastResultCount !== null" style="color: #666; font-size: 12px;">
                    Last Result: {{ lastResultCount }} groups
                </span>
            </div>
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
                    <div style="display: flex; align-items: center;">
                        <label style="display: flex; align-items: center; gap: 5px; font-size: 12px; cursor: pointer;">
                            <input type="checkbox" v-model="checkFundingSource">
                            <span>Check Same Funding Source</span>
                        </label>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 5px;">
                        <label style="font-size: 12px; font-weight: bold;">Time Range (Empty = Full Range)</label>
                        <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                            <input type="datetime-local" v-model="startTime" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                            <span>to</span>
                            <input type="datetime-local" v-model="endTime" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Behavior Similarity Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleSection('behavior')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>Behavior Similarity Based</span>
                    <span>{{ activeSection === 'behavior' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeSection === 'behavior'" style="padding: 10px;">
                    <span style="color: #999; font-size: 12px;">Configuration not yet available.</span>
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
                </div>
            </div>
        </div>

        <!-- Manipulation Detection Configuration -->
        <div style="border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;">
            <div style="font-weight: bold;">Manipulation Detection</div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <button @click="triggerManipulationDetection" :disabled="loadingManipulation" style="padding: 5px 15px; background: #FF9800; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 12px;">
                    {{ loadingManipulation ? 'Detecting...' : 'Run Detection' }}
                </button>
            </div>
        </div>
        
        <div style="display: flex; flex-direction: column; gap: 5px;">
            <!-- Self Trading -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleManipulationSection('self_trading')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>Self Trading (Wash Trading)</span>
                    <span>{{ activeManipulationSection === 'self_trading' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeManipulationSection === 'self_trading'" style="padding: 10px; display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; flex-direction: column; gap: 5px;">
                        <label style="font-size: 12px; font-weight: bold;">Volume Difference Threshold</label>
                        <input type="number" v-model.number="selfTradingThreshold" min="0" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 150px;">
                        <span style="font-size: 10px; color: #666;">Max difference between buy/sell amounts.</span>
                    </div>
                </div>
            </div>

            <!-- Network Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleManipulationSection('network')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>Network Based</span>
                    <span>{{ activeManipulationSection === 'network' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeManipulationSection === 'network'" style="padding: 10px;">
                    <span style="color: #999; font-size: 12px;">Configuration not yet available.</span>
                </div>
            </div>

            <!-- Behavior Similarity Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleManipulationSection('behavior_sim')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>Behavior Similarity Based</span>
                    <span>{{ activeManipulationSection === 'behavior_sim' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeManipulationSection === 'behavior_sim'" style="padding: 10px;">
                    <span style="color: #999; font-size: 12px;">Configuration not yet available.</span>
                </div>
            </div>
        </div>

        <!-- Link Configuration -->
        <div style="border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;">
            <div style="font-weight: bold;">Link Configuration</div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <button @click="updateLinks" :disabled="loadingLinks" style="padding: 5px 15px; background: #9C27B0; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 12px;">
                    {{ loadingLinks ? 'Updating...' : 'Update Links' }}
                </button>
            </div>
        </div>
        
        <div style="display: flex; flex-direction: column; gap: 5px;">
            <!-- Network Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleLinkSection('network')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>Network Based</span>
                    <span>{{ activeLinkSection === 'network' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeLinkSection === 'network'" style="padding: 10px; display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; flex-direction: column; gap: 5px;">
                        <label style="font-size: 12px; font-weight: bold;">Link Threshold (Min Tx)</label>
                        <input type="number" v-model.number="linkThreshold" min="1" max="50" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 150px;">
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 5px;">
                        <label style="font-size: 12px; font-weight: bold;">Time Range (Empty = Full Range)</label>
                        <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                            <input type="datetime-local" v-model="linkStartTime" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                            <span>to</span>
                            <input type="datetime-local" v-model="linkEndTime" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px;">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Behavior Similarity Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleLinkSection('behavior_sim')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>Behavior Similarity Based</span>
                    <span>{{ activeLinkSection === 'behavior_sim' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeLinkSection === 'behavior_sim'" style="padding: 10px;">
                    <span style="color: #999; font-size: 12px;">Configuration not yet available.</span>
                </div>
            </div>

            <!-- Manipulation History Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleLinkSection('history')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <span>Manipulation History Based</span>
                    <span>{{ activeLinkSection === 'history' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeLinkSection === 'history'" style="padding: 10px;">
                    <span style="color: #999; font-size: 12px;">Configuration not yet available.</span>
                </div>
            </div>
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
        loadingManipulation: {
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
            detectionThreshold: 2,
            checkFundingSource: true,
            // Default to empty strings which means "Full Range" in our logic
            startTime: "",
            endTime: "",
            
            // Snapshot Data
            snapshotTimes: [],
            selectedSnapshotTime: "",
            snapshotThreshold: 30,
            loadingSnapshot: false,

            // UI State
            activeSection: 'transfer', // 'transfer', 'behavior', 'history'
            activeManipulationSection: 'self_trading', // 'network', 'behavior_sim', 'self_trading'
            // loadingManipulation: false, // Moved to props
            activeLinkSection: 'network', // 'network', 'behavior_sim', 'history'
            loadingLinks: false,
            
            selfTradingThreshold: 100,
            
            // Link Config
            linkThreshold: 1,
            linkStartTime: "",
            linkEndTime: ""
        }
    },
    mounted() {
        this.fetchSnapshotTimes();
    },
    methods: {
        toggleSection(section) {
            if (this.activeSection === section) {
                this.activeSection = null;
            } else {
                this.activeSection = section;
            }
        },
        toggleManipulationSection(section) {
            if (this.activeManipulationSection === section) {
                this.activeManipulationSection = null;
            } else {
                this.activeManipulationSection = section;
            }
        },
        toggleLinkSection(section) {
            if (this.activeLinkSection === section) {
                this.activeLinkSection = null;
            } else {
                this.activeLinkSection = section;
            }
        },
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
        getDetectionParams() {
            const timeRange = {};
            if (this.startTime) timeRange.start = this.startTime.replace('T', ' ');
            if (this.endTime) timeRange.end = this.endTime.replace('T', ' ');
            return {
                threshold: this.detectionThreshold,
                checkFundingSource: this.checkFundingSource,
                timeRange: Object.keys(timeRange).length > 0 ? timeRange : undefined,
                ruleType: "transfer-network"
            };
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
        updateSnapshot() {
            this.loadingSnapshot = true;
            this.$emit('update-snapshot', {
                time: this.selectedSnapshotTime,
                threshold: this.snapshotThreshold / 100, // Convert percentage to 0-1
                detectionParams: this.getDetectionParams(),
                linkParams: this.getLinkParams()
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
            const params = this.getDetectionParams();
            
            console.log("ControlPanel: emitting run-detection", params);

            this.$emit('run-detection', params);
        },
        async triggerManipulationDetection() {
            // this.loadingManipulation = true; // Controlled by prop now
            console.log("ControlPanel: emitting request-manipulation-detection");
            
            this.$emit('request-manipulation-detection', {
                threshold: this.selfTradingThreshold
            });
        },
        updateLinks() {
            console.log("ControlPanel: updateLinks called");
            const params = this.getLinkParams();
            
            console.log("ControlPanel: emitting update-links", params);
            
            this.$emit('update-links', params);
        },
    }
}
</script>

<style scoped>
</style>
