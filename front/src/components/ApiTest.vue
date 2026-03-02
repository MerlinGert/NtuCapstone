<template>
    <div class="api-test-container" style="height: 100%; display: flex; flex-direction: column; padding: 10px; gap: 10px;">
        <!-- Entity Detection Controls -->
        <div style="display: flex; gap: 10px; flex-direction: column;">
            <div style="font-weight: bold;">Entity Detection</div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <label>Threshold Limit:</label>
                <input 
                    v-model.number="thresholdLimit" 
                    type="number"
                    style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 100px;"
                />
                <button 
                    @click="detectEntities" 
                    :disabled="loading"
                    style="padding: 5px 15px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer;"
                >
                    {{ loading ? 'Detecting...' : 'Detect Entities' }}
                </button>
            </div>
        </div>

        <!-- Result Display -->
        <div style="flex: 1; border: 1px solid #eee; border-radius: 4px; padding: 10px; overflow: auto; background: #f9f9f9;">
            <div v-if="error" style="color: red;">{{ error }}</div>
            <pre v-else-if="result" style="margin: 0; font-size: 12px;">{{ JSON.stringify(result, null, 2) }}</pre>
            <div v-else style="color: #999; text-align: center; margin-top: 20px;">
                Click "Detect Entities" to test the backend API.
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: "ApiTest",
    data() {
        return {
            thresholdLimit: 1000,
            result: null,
            loading: false,
            error: null
        }
    },
    methods: {
        async detectEntities() {
            this.loading = true;
            this.error = null;
            this.result = null;
            
            try {
                // Construct the payload matching the backend DetectionRequest model
                const payload = {
                    target_users: ["user_A", "user_B", "user_C"],
                    rules: [
                        {
                            rule_type: "threshold",
                            parameters: {
                                limit: this.thresholdLimit,
                                metric: "balance"
                            },
                            enabled: true
                        }
                    ]
                };

                const response = await fetch('/api/entity/detect', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                this.result = data;
            } catch (err) {
                this.error = "Error connecting to backend: " + err.message;
                console.error(err);
            } finally {
                this.loading = false;
            }
        }
    }
}
</script>
