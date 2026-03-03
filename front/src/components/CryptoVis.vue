<template>
<n-layout class="h-screen max-h-screen" :content-style="{ display: 'flex', flexDirection: 'column',}">
  <n-layout-header>
      <div class="techname text-light-50 text-shadow-lg font-bold" style="padding-left: 15px;" >ManiScope</div>
</n-layout-header>
<n-layout-content class="flex-1" style="width:100%;height:100%" >
  <n-layout
        style="width:100%;height:100%"
        :content-style="{ display: 'flex', flexDirection: 'row' }"
      >
<div style="flex: 0 0 15%">
        <n-card
            size="small"
            style="width:100%;height:40%;" 
            header-style="text-align:left;height:50px;font-size:1.7em"
        >
            <template #header>
                    Control Panel
            </template>
            <ControlPanel 
                :loading="detecting"
                :lastResultCount="lastDetectionCount"
                @run-detection="handleRunDetection"
                @update-snapshot="handleUpdateSnapshot"
            />
        </n-card>
    </div>

<div style="flex: 0 0 30%; display: flex; flex-direction: column; height: 100%; overflow: hidden;">
        <n-card
            size="small"
            style="width:100%;height:60%;flex-shrink:0;"
            header-style="text-align:left;height:50px;font-size:1.7em"
            :content-style="{ padding: 0, height: 'calc(100% - 50px)', overflow: 'hidden' }"
        >
            <template #header>
                    Token Distribution
            </template>
            <TokenDistribution ref="tokenDistribution"
                @detection-complete="handleDetectionComplete"
            />
        </n-card>
        <n-card
            size="small"
            style="width:100%;height:40%;flex-shrink:0;"
            header-style="text-align:left;height:50px;font-size:1.7em"
            :content-style="{ padding: 0, height: 'calc(100% - 50px)', overflow: 'hidden' }"
        >
            <template #header>
                    Entity Details
            </template>
            <HolderView />
        </n-card>
    </div>


    <div style="flex: 0 0 55%; display: flex; flex-direction: column; height: 100%; overflow: hidden;">
        <n-card
          size="small"
          style="width:100%;height:60%;flex-shrink:0;"
          header-style="text-align:left;height:50px;font-size:1.7em"
          :content-style="{ padding: 0, height: 'calc(100% - 50px)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }"
        >
          <template #header>
            <span>Manipulation Panel</span>
          </template>
          <!-- 上 1/3：空白占位 -->
          <div style="flex:1;"></div>
          <!-- 中 1/3：K 线图 -->
          <div style="flex:1; border-top:1px solid #eef2f7; border-bottom:1px solid #eef2f7; overflow:hidden; position:relative;">
            <div style="position:absolute;top:0;left:8px;font-size:11px;font-weight:600;color:#4a5568;line-height:20px;z-index:1;">RENA K-Line</div>
            <div style="position:absolute;inset:0;padding-top:20px;">
              <CandlestickChart />
            </div>
          </div>
          <!-- 下 1/3：空白占位 -->
          <div style="flex:1;"></div>
        </n-card>
        <n-card
            size="small"
            style="width:100%;height:40%;flex-shrink:0;"
            header-style="text-align:left;height:50px;font-size:1.7em"
        >
            <template #header>
                    Insight Panel
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
              this.$refs.tokenDistribution.fetchSnapshotData(params.time, params.threshold);
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
  background-color:rgb(79, 81, 80);
  color: aliceblue;
  font-size: 2.0em;
  padding-left: 10px;
  padding-top:7px; 
  height: 50px;
}
.footer {
  height: 18px;
  font-size: 0.8em;
  text-align: center;
  background-color: rgb(79, 81, 80);
    color: aliceblue;
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
