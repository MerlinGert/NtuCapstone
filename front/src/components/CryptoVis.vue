<template>
<n-layout class="h-screen max-h-screen" :content-style="{ display: 'flex', flexDirection: 'column',}">
  <n-layout-header>
      <div class="techname text-light-50 text-shadow-lg font-bold" style="padding-left: 15px;" >CryptoVis</div>
</n-layout-header>
<n-layout-content class="flex-1" style="width:100%;height:100%" >
  <n-layout
        style="width:100%;height:100%"
        :content-style="{ display: 'flex', flexDirection: 'row' }"
      >

    <div style="flex: 0 0 70%; display: flex; flex-direction: column">
    <!-- <n-layout style="width:100%;height:100%" :content-style="{ display: 'flex', flexDirection: 'column'}"> -->
        <n-card 
          size="small"
          style="width:100%;height:60%;" 
          header-style="text-align:left;height:50px;font-size:1.7em"
          >
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
              <!-- 左侧文字 -->
              <span>Holder View</span>
            </div>
          </template>
        </n-card>     
        <n-card
            size="small"
            style="width:100%;height:40%;" 
            header-style="text-align:left;height:50px;font-size:1.7em"
        >
            <template #header>
                    Query Execution Panel
            </template>
        </n-card>
    </div>


    <div style="flex: 0 0 30%">
        <n-card
            size="small"
            style="width:100%;height:60%;" 
            header-style="text-align:left;height:50px;font-size:1.7em"
        >
            <template #header>
                    Result Overview
            </template>
            <div style="padding:12px;font-size:14px;">
              <div v-if="loading">加载中...</div>
              <div v-else>
                <div>已加载 {{ overview.rows }} 条记录 <span v-if="isPartial" style="color:orange">(部分数据)</span></div>
                <div>交易对（Top）：{{ overview.pairs.size }} 个</div>
                <div>日期范围：{{ overview.dateMin }} 到 {{ overview.dateMax }}</div>
              </div>
            </div>
        </n-card>
        <n-card
            size="small"
            style="width:100%;height:40%;" 
            header-style="text-align:left;height:50px;font-size:1.7em"
        >
            <template #header>
                    Result List
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

export default {
  components:{ NSelect, NCheckbox, NCard, NLayout, NSwitch, NSpace, NLayoutHeader, NLayoutFooter, NLayoutContent},
  data(){
    return {
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
