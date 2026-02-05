<template>
<n-layout class="h-screen max-h-screen" :content-style="{ display: 'flex', flexDirection: 'column',}">
  <n-layout-header>
      <div class="techname text-light-50 text-shadow-lg font-bold" style="padding-left: 15px;" >PrettiSmart
        <!-- <n-dropdown trigger="click" :options="options" size="small" :on-select="change_contract">
          <n-button size="tiny" color="#8c8c8c" style="position: relative;display: inline-flex;float: right;margin-right: 1%;margin-top: 3px;">Contracts</n-button>
      </n-dropdown  >
       -->
      </div>


</n-layout-header>
<n-layout-content class="flex-1" style="width:100%;height:100%" >
  <n-layout style="width:100%;height:100%" :content-style="{ display: 'flex', flexDirection: 'column'}">
 
      <n-card 
      class="custom-card"
      size="small"
      style="width:80%;height:100%;"
      header-style="text-align:left;height:50px;font-size:1.7em"
      > 
      <FunctionView
      :functionnodes="functionnodes"
      :variablenodes="variablenodes"
      :simulationData="simulationData"
      />
      </n-card>
    </n-layout>
</n-layout-content>
<n-layout-footer position="absolute" style="height: 18px">
  <div class="footer"></div>
</n-layout-footer>
</n-layout>
</template>


<script>
import { NCard,NLayout,NSwitch,NSpace,NLayoutHeader,NLayoutFooter,NLayoutContent,NDropdown,NButton } from "naive-ui"
import * as d3 from "d3"


import FunctionView from './FunctionView.vue'

//lottery
import AST from '../assets/lottery/combined_solc.json'
// // import simulationData from "../assets/lottery/lottery5.json"
// // import simulationData from "../assets/lottery/lottery.json"
import simulationData from "../assets/lottery/out.json"

// suicide watch
// import AST from '../assets/suicide/combined_solc.json'
// import simulationData from "../assets/suicide/suicide.json"

//fiveforty
// import AST from '../assets/fiveforty/combined_solc.json'
// import simulationData from "../assets/fiveforty/fiveforty.json"

//auction
// import AST from '../assets/auction/combined_solc.json'
// import simulationData from "../assets/auction/auction.json"

//ethpledge
// import AST from '../assets/ethpledge/combined_solc.json'
// import simulationData from "../assets/ethpledge/ethpledge.json"

// queue
// import AST from '../assets/queue/combined_solc.json'
// import simulationData from "../assets/queue/queue.json"

// crowdsale
// import AST from '../assets/crowdsale/combined_solc.json'
// import simulationData from "../assets/crowdsale/out.json"

export default {
  components:{ FunctionView,NCard, NLayout, NSwitch, NSpace, NLayoutHeader, NLayoutFooter, NLayoutContent, NDropdown, NButton},
  data(){
    return {
      data:JSON.parse(JSON.stringify(AST)),
      functionnodes:[],
      variablenodes:[],
      simulationData:simulationData
    }
  },
  computed:{
  },
  methods:{
    DataProcess(RawData){
      console.log(RawData['sources'][RawData['sourceList'][0]]['AST'])
      let astnodes = RawData['sources'][RawData['sourceList'][0]]['AST']['nodes']
      astnodes.forEach(node1=>{
        if(node1['contractKind']=='contract'){
          console.log(node1.name)
          console.log(node1)
          let allnodes = node1.nodes
          let functionnodes = []
          let variablenodes = []
          let eventnodes = []
          allnodes.forEach(node2=>{
            if(node2['nodeType']=='EventDefinition'){
              eventnodes.push(node2)
            }else if(node2['nodeType']=='VariableDeclaration'){
              // variablenodes.push(node2)
              let varStructure = {
                'name': node2['name'],
                'stateVariable':node2['stateVariable'],
                'type':node2['typeDescriptions']['typeString'],
                'visibility': node2['visibility']
              }
              if(node2['value']){
                varStructure['value'] = node2['value']['value']
              }else{
                varStructure['value'] = null
              }
              // console.log(varStructure)
              variablenodes.push(varStructure)

            }else if(node2['nodeType']=='FunctionDefinition'){
              // functionnodes.push(node2)
              let functionStructure = {
                'name': node2['name'],
                'isConstructor':node2['isConstructor'],
                'payable':node2['payable'],
                'stateMutability':node2['stateMutability'],
                'visibility': node2['visibility']
              }
              // console.log(functionStructure)
              functionnodes.push(functionStructure)
            }
          })
          this.functionnodes = functionnodes
          this.variablenodes = variablenodes
          console.log(variablenodes,this.functionnodes)
          // console.log({
          //   variablenodes,
          //   functionnodes
          // })
        }

      })
    }
  },
  beforeMount(){
    this.DataProcess(this.data)
  },
  mounted(){

  },
  updated(){
  }

}
</script>


<style scoped>
.custom-card {
  border:white
}
a {
  color: #42b983;
}
.techname {
  background-color:#66889e;
  color: aliceblue;
  font-size: 1.7em;
  padding-left: 10px;
  padding-top:4px; 
  height: 40px;
}
.footer {
  height: 18px;
  font-size: 0.8em;
  text-align: center;
  background-color: rgb(79, 81, 80);
    color: aliceblue;
}
</style>
