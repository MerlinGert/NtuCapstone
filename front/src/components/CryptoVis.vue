<template>
<n-layout class="h-screen max-h-screen" :content-style="{ display: 'flex', flexDirection: 'column'}">
  <n-layout-header>
      <div class="techname font-bold" style="padding-left: 20px;" >ManiScope</div>
</n-layout-header>
<n-layout-content class="flex-1" style="width:100%;height:100%" >
  <n-layout
        style="width:100%;height:100%;overflow:hidden"
        :content-style="{ display: 'flex', flexDirection: 'row', overflow: 'hidden', width: '100%', height: '100%', boxSizing: 'border-box' }"
      >
<div style="flex: 4; min-width:0; overflow:hidden;">
        <n-card
            size="small"
            style="width:100%;height:100%;"
            class="panel-card"
            header-style="text-align:left;height:50px;font-size:1.4em;"
            :content-style="{ padding: 0, height: 'calc(100% - 50px)', overflow: 'hidden' }"
        >
            <template #header>
                <span class="card-header-text">Control Panel</span>
            </template>
            <ControlPanel 
                :loading="detecting"
                :loadingLinks="detectingLinks"
                :loadingManipulation="detectingManipulation"
                :lastResultCount="lastDetectionCount"
                :snapshotConfig="snapshot_configuration"
                :snapshotTimes="snapshotTimes"
                :entityConfig="entity_detection_configuration"
                :linkConfig="link_detection_configuration"
                :manipulationConfig="manipulation_detection_configuration"
              />
        </n-card>
    </div>

<div style="flex: 6; min-width:0; display: flex; flex-direction: column; height: 100%; overflow: hidden;">
        <n-card
            size="small"
            class="panel-card"
            style="width:100%;height:60%;flex-shrink:0;"
            header-style="text-align:left;height:50px;font-size:1.4em;"
            :content-style="{ padding: 0, height: 'calc(100% - 50px)', overflow: 'hidden' }"
        >
            <template #header>
                <span class="card-header-text">Token Distribution</span>
            </template>
            <TokenDistribution ref="tokenDistribution"
                :snapshot-data="snapshot_data"
                :entity-detection-results="entity_detection_results"
                :link-detection-results="link_generation_results"
                @detection-complete="handleDetectionComplete"
            />
        </n-card>
        <n-card
            size="small"
            class="panel-card"
            style="width:100%;height:40%;flex-shrink:0;"
            header-style="text-align:left;height:50px;font-size:1.4em;"
            :content-style="{ padding: 0, height: 'calc(100% - 50px)', overflow: 'hidden' }"
        >
            <template #header>
                <span class="card-header-text">Entity Details</span>
            </template>

        </n-card>
    </div>


    <div style="flex: 9; min-width:0; display: flex; flex-direction: column; height: 100%; overflow: hidden;">
        <n-card
          size="small"
          class="panel-card"
          style="width:100%;height:60%;flex-shrink:0;"
          header-style="text-align:left;height:50px;font-size:1.4em;"
          :content-style="{ padding: 0, height: 'calc(100% - 50px)', display: 'flex', flexDirection: 'column', overflow: 'visible' }"
        >
          <template #header>
            <span class="card-header-text">Manipulation Panel</span>
          </template>
          <!-- 上 1/3：空白占位 -->
          <div style="flex:1;"></div>
          <!-- 中 1/3：K 线图 -->
          <div style="flex:1; border-top:1px solid #eef2f7; border-bottom:1px solid #eef2f7; display:flex; flex-direction:row; overflow:hidden;">
            <div style="flex:1; min-width:0; display:flex; flex-direction:column; overflow:hidden; background:#fff;">
              <div style="flex-shrink:0;height:18px;padding-left:8px;font-size:11px;font-weight:600;color:#4a5568;line-height:18px;">ACT K-Line</div>
              <div style="flex:1; min-height:0; overflow:hidden;">
                <CandlestickChart :granularity="klineGranularity" style="width:100%;height:100%;" />
              </div>
            </div>
            <div class="granularity-panel">
              <div class="gran-title">Granularity</div>
              <button v-for="g in klineGranularities" :key="g"
                :class="['gran-btn', klineGranularity===g ? 'gran-btn--active' : '']"
                @click="klineGranularity=g"
              >{{ g }}</button>
            </div>
          </div>
          <!-- 下 1/3：空白占位 -->
          <div style="flex:1;"></div>
        </n-card>
        <n-card
            size="small"
            class="panel-card"
            style="width:100%;height:40%;flex-shrink:0;"
            header-style="text-align:left;height:50px;font-size:1.4em;"
        >
            <template #header>
                <span class="card-header-text">Insight Panel</span>
            </template>
        </n-card>
    </div>
      <!-- </n-layout> -->
  </n-layout>

</n-layout-content>
<n-layout-footer position="absolute" style="height: 18px">
  <div class="footer"></div>
</n-layout-footer>
</n-layout>
</template>


<!-- scripts -->
<script>
import { NSelect,NCheckbox,NCard,NLayout,NSwitch,NSpace,NLayoutHeader,NLayoutFooter,NLayoutContent} from "naive-ui"
import * as d3 from "d3"
import TokenDistribution from "./TokenDistribution.vue"
import ControlPanel from "./ControlPanel.vue"
import CandlestickChart from "./CandlestickChart.vue"

export default {
  components:{ NSelect, NCheckbox, NCard, NLayout, NSwitch, NSpace, NLayoutHeader, NLayoutFooter, NLayoutContent, TokenDistribution, ControlPanel, CandlestickChart},
  data(){
    return {
      //new params
      //snapshot configuration
      snapshot_configuration:{
        time: "2024-11-09 23:00:00 UTC", //current snapshot time
        top_holder_threshold: 0.3,  //current top holder threshold
        related_user_threshold: 0.2, //current related user threshold
      },
      snapshotTimes: [],
      snapshot_data:{}, //current snapshot data

      //entity detection configuration
      entity_detection_configuration: {
        enable_network_based: false,
        transfer_network_based_params: {
           enable_direct_transfer: true,
           direct_transfer_params: {
             enable_min_count: true,
             min_tx_count: 3,
             enable_min_volume: false,
             min_tx_volume: 0,
           },
           enable_funding_relationship: true, //direct fund or co funder
           enable_same_sender: false,
           enable_same_recipient: false,
        },
        enable_similarity_based: true,
        similarity_based_params: {
          enable_trading_action_sequence: false,
          trading_action_sequence_params: {
            type: "action_amount_price", //action_only, action_amount, action_price, action_amount_price
            min_seq_length: 3, //min matching sequence length
            max_time_diff: 20, //max time difference between the first and last matching actions in the sequence
            amount_similarity: 0.7, //0.5-1.0
            price_similarity: 0.7, //0.5-1.0
          },
          enable_balance_sequence: true,
          balance_sequence_params: {
            balance_granularity: '1h', //1min, 1h, 1d
            balance_similarity_threshold: 0.6, //0.5-1.0
          },
          enable_earning_sequence: false,
          earning_sequence_params: {
            earning_granularity: '1d', //1min, 1h, 1d
            earning_similarity_threshold: 0.8, //0.5-1.0
          },
        },
        enable_manipulation_based: false,
        manipulation_based_params: {
          max_manipulation_time_diff: 2, //max time difference between the first and last manipulation actions in the sequence
        },
      },
      entity_detection_results: {}, //current entity detection results

      // link detection configuration
      link_detection_configuration: {
        enable_network_based: false,
        transfer_network_based_params: {
           enable_direct_transfer: true,
           direct_transfer_params: {
             enable_min_count: true,
             min_tx_count: 1,
             enable_min_volume: false,
             min_tx_volume: 0,
           },
           enable_funding_relationship: false, //direct fund or co funder
           enable_same_sender: false,
           enable_same_recipient: false,
        },
        enable_similarity_based: true,
        similarity_based_params: {
          enable_trading_action_sequence: true,
          trading_action_sequence_params: {
            type: "action_only", //action_only, action_amount, action_price, action_amount_price
            min_seq_length: 3, //min matching sequence length
            max_time_diff: 120, //max time difference between the first and last matching actions in the sequence
            amount_similarity: 0.7, //0.5-1.0
            price_similarity: 0.7, //0.5-1.0
          },
          enable_balance_sequence: false,
          balance_sequence_params: {
            balance_granularity: '1h', //1min, 1h, 1d
            balance_similarity_threshold: 0.7, //0.5-1.0
          },
          enable_earning_sequence: false,
          earning_sequence_params: {
            earning_granularity: '1d', //1min, 1h, 1d
            earning_similarity_threshold: 0.7, //0.5-1.0
          },
        },
        enable_manipulation_based: false,
        manipulation_based_params: {
          max_manipulation_time_diff: 2, //max time difference between the first and last manipulation actions in the sequence
        },
      },
      link_generation_results: {}, //current link detection results

      //manipulation detection configuration
      manipulation_detection_configuration: {
        enable_round_trip_detection: true, //whether to enable round trip detection
        round_trip_params: {
          max_time_diff: 120, //max time difference between the first and last round trip actions in the sequence
          max_position_diff: 100, //max position difference between the first and last round trip actions in the sequence
          max_earning: 1000, //max earning usd for this round trip
          enable_entity_based: true, //whether to enable entity based round trip detection
        },
        enable_same_direction_detection: true, //whether to enable same direction detection
        same_direction_params: {
          max_time_diff: 10, //max time (min) difference between the first and last same direction actions in the sequence
          min_seq_length: 5, //min same direction sequence length
          max_diff_direction: 0, //max direction difference between the first and last same direction actions in the sequence
          enable_entity_based: true, //whether to enable entity based same direction detection
        },
      },
      manipulation_detection_results: {}, //current manipulation detection results

      //old params
      klineGranularity: '1D',
      klineGranularities: ['1H','1D','3D','1W'],
      detecting: false,
      detectingLinks: false,
      detectingManipulation: false,
      lastDetectionCount: null,
      overview:{
        rows:0,
        pairs:new Set(),
        dateSet:new Set(),
        dateMin:'',
        dateMax:'',
        topPairs:[]
      },
      loading: false,
      isPartial: false
    }
  },  
  watch:{
  },
  methods:{
      handleRunDetection() {
      },
      handleUpdateSnapshot() {
          
      },
    handleDetectionComplete(count) {
      this.detecting = false;
      this.lastDetectionCount = count;
    },
    async handleUpdateLinks() {
    },
    async fetchInitialSnapshotData() { 
        console.log("CryptoVis: Fetching initial snapshot data...");
        try {
            const response = await fetch('/api/snapshot/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    time: this.snapshot_configuration.time,
                    threshold: this.snapshot_configuration.top_holder_threshold
                })
            });
            if (!response.ok) throw new Error("Failed to fetch snapshot data");
            const data = await response.json();
            this.snapshot_data = data;
            this.snapshotTimes = data.all_times;
            console.log("CryptoVis: Initial snapshot data loaded:", this.snapshot_data);

            // Run unified detection
            const balances = this.snapshot_data.balances || {};
            const processedUsers = { ...balances.users };
            delete processedUsers['Others'];
            const relatedUsers = balances.related_users || {};

            const detectionRequest = {
                target_users: processedUsers,
                related_users: relatedUsers,
                entity_detection_config: this.entity_detection_configuration,
                link_detection_config: this.link_detection_configuration,
                snapshot_time: this.snapshot_configuration.time,
                detect_entity: true,
                detect_link: true
            };

            console.log("CryptoVis: Running unified detection...", detectionRequest);

            const detectionResponse = await fetch('/api/detection/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(detectionRequest)
            });

            if (!detectionResponse.ok) throw new Error("Failed to run detection");

            const detectionResults = await detectionResponse.json();
            console.log("CryptoVis: Detection results received:", detectionResults);

            this.entity_detection_results = detectionResults.entity_results;
            this.link_generation_results = detectionResults.relations;

            // Run manipulation detection
            console.log("CryptoVis: Running manipulation detection...");
            const manipulationRequest = {
                target_users: processedUsers,
                related_users: relatedUsers,
                entity_results: this.entity_detection_results,
                manipulation_config: this.manipulation_detection_configuration
            };

            try {
                const manipulationResponse = await fetch('/api/manipulation_service/detect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(manipulationRequest)
                });

                if (manipulationResponse.ok) {
                    const manipulationResults = await manipulationResponse.json();
                    this.manipulation_detection_results = manipulationResults.results;
                    console.log("CryptoVis: Manipulation detection results received:", this.manipulation_detection_results);
                } else {
                    console.error("CryptoVis: Failed to run manipulation detection", manipulationResponse.statusText);
                }
            } catch (manError) {
                console.error("CryptoVis: Error running manipulation detection:", manError);
            }

            // Update TokenDistribution if available
            if (this.$refs.tokenDistribution) {
                // Ensure data is set before drawing
                // We don't need setDetectionResults anymore as props are reactive
                // But we need to call drawChart() explicitly as requested
                // "把drawchart函数暴露给cryptovis，在第一次fetchinitial计算出结果调用一次"
                
                // Wait for Vue to update props
                this.$nextTick(() => {
                    if (this.$refs.tokenDistribution.drawChart) {
                        console.log("CryptoVis: Calling tokenDistribution.drawChart() after initial detection");
                        this.$refs.tokenDistribution.drawChart();
                    } else {
                        console.warn("CryptoVis: tokenDistribution.drawChart method not found");
                    }
                });
            } else {
                console.warn("CryptoVis: tokenDistribution ref not found when updating detection results");
            }

        } catch (error) {
            console.error("CryptoVis: Error fetching initial snapshot data:", error);
        }
    }
  },
  mounted(){
    this.fetchInitialSnapshotData();
  },
  updated(){
  }

}
</script>

<style scoped>
a {
  color: #42b983;
}
.techname {
  background: #ffffff;
  color: #2d3748;
  font-size: 2.0em;
  padding-left: 20px;
  padding-top: 7px;
  height: 50px;
  letter-spacing: 2px;
  border-bottom: 2px solid #e2e8f0;
}
.footer {
  height: 18px;
  font-size: 0.8em;
  text-align: center;
  background: #f7f8fa;
  color: #a0aec0;
  border-top: 1px solid #e2e8f0;
}
.card-header-text {
  font-weight: 700;
  font-size: 1em;
  color: #2d3748;
  letter-spacing: 0.5px;
}
.panel-card {
  border: none !important;
  box-shadow: 0 1px 8px rgba(0,0,0,0.12) !important;
}
/* 粒度按钮面板 */
.granularity-panel {
  flex: 0 0 62px;
  border-left: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  gap: 4px;
  padding: 6px 6px;
  overflow: hidden;
}
.gran-title {
  font-size: 9px;
  color: #a0aec0;
  text-align: center;
  letter-spacing: 1px;
  margin-bottom: 2px;
  font-weight: 600;
  text-transform: uppercase;
}
.gran-btn {
  display: block;
  width: 100%;
  padding: 4px 0;
  border: 1px solid #e8edf3;
  border-radius: 6px;
  background: #fff;
  color: #90a0b7;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  text-align: center;
  white-space: nowrap;
  transition: all 0.18s ease;
  letter-spacing: 0.5px;
  box-shadow: none;
}
.gran-btn:hover {
  background: #f4f7fd;
  color: #7090b8;
  border-color: #d0ddef;
}
.gran-btn--active {
  background: #edf3ff !important;
  color: #7090c8 !important;
  border-color: #d2e0f8 !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}
.checkbox{
  --n-color-checked: #728efd !important;
  --n-border-checked:  #728efd !important;
  --n-border-focus:  #728efd !important;
}
.dataset_label{
  font-size: 15px;
  margin-left: 15%;
}
</style>
