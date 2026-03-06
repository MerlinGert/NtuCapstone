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
        >
            <template #header>
                <span class="card-header-text">Control Panel</span>
            </template>
            <ControlPanel 
                :loading="detecting"
                :lastResultCount="lastDetectionCount"
                @run-detection="handleRunDetection"
                @update-snapshot="handleUpdateSnapshot"
                @update-links="handleUpdateLinks"
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
            <HolderView />
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
import HolderView from "./HolderView.vue"
import TokenDistribution from "./TokenDistribution.vue"
import ApiTest from "./ApiTest.vue"
import ControlPanel from "./ControlPanel.vue"
import CandlestickChart from "./CandlestickChart.vue"

export default {
  components:{ NSelect, NCheckbox, NCard, NLayout, NSwitch, NSpace, NLayoutHeader, NLayoutFooter, NLayoutContent, HolderView, TokenDistribution, ApiTest, ControlPanel, CandlestickChart},
  data(){
    return {
      klineGranularity: '1D',
      klineGranularities: ['1H','1D','3D','1W'],
      detecting: false,
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
      handleRunDetection(params) {
          console.log("CryptoVis: handleRunDetection called with", params);
          this.detecting = true;
          this.lastDetectionCount = null;
          // Trigger detection in TokenDistribution component
          if (this.$refs.tokenDistribution) {
              console.log("CryptoVis: calling tokenDistribution.runEntityDetection");
              this.$refs.tokenDistribution.runEntityDetection(
                  params.threshold,
                  params.timeRange,
                  params.ruleType
              );
          } else {
              console.error("CryptoVis: tokenDistribution ref not found");
          }
      },
      handleUpdateSnapshot(params) {
          console.log("CryptoVis: handleUpdateSnapshot called with", params);
          if (this.$refs.tokenDistribution) {
              this.$refs.tokenDistribution.fetchSnapshotData(
                  params.time, 
                  params.threshold,
                  params.detectionParams,
                  params.linkParams
              );
              // Clear previous detection result when data changes
              this.lastDetectionCount = null;
          } else {
              console.error("CryptoVis: tokenDistribution ref not found");
          }
      },
    handleDetectionComplete(count) {
      this.detecting = false;
      this.lastDetectionCount = count;
    },
    handleUpdateLinks(params) {
      console.log("CryptoVis: handleUpdateLinks called with", params);
      if (this.$refs.tokenDistribution) {
          this.$refs.tokenDistribution.updateLinks(
              params.threshold,
              params.timeRange
          );
      } else {
          console.error("CryptoVis: tokenDistribution ref not found");
      }
    },
    async loadCSV(){
      this.loading = true
      const overviewUrl = '/processed/overview.json'
      try{
        const res = await fetch(overviewUrl)
        const data = await res.json()
        this.overview.rows = data.rows
        this.overview.pairs = new Set(Array.from({length:data.top_pairs.length},(_,i)=>data.top_pairs[i].token_pair))
        this.overview.dateSet = new Set([...(data.date_min? [data.date_min]:[]),...(data.date_max? [data.date_max]:[])])
        this.overview.dateMin = data.date_min || ''
        this.overview.dateMax = data.date_max || ''
        this.overview.topPairs = data.top_pairs || []
        this.isPartial = true
      }catch(e){
        console.error('Failed to load overview.json:',e)
      }finally{
        this.loading = false
      }      
    }
  },
  beforeMount(){
    this.loadCSV()
  },
  mounted(){
    
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
