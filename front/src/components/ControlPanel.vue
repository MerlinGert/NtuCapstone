<template>
    <div style="padding: 15px; height: 100%; display: flex; flex-direction: column; gap: 10px;">
        <div style="font-weight: bold; border-bottom: 1px solid #eee; padding-bottom: 5px;">Rule Configuration</div>
        
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
            endTime: ""
        }
    },
    methods: {
        triggerDetection() {
            console.log("ControlPanel: triggerDetection called");
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
    }
}
</script>

<style scoped>
</style>
