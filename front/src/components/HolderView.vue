<template>
    <div style="height:100%;width:100%;background:#ffffff" ref="holder_container" class="display-flex">
        <svg class="holderView" :height="this.svgHeight" :width="this.svgWidth"></svg>             
    </div>
</template>

<script>
import * as d3 from "d3"



export default {
    name:"holderView",
    props:['data','functionnodes','variablenodes','simulationData'],
    data(){
        return {
            svgHeight:'0',
            svgWidth:'0',
            margin:{left:60,right:50,top:10,bottom:10},
        }
    },
    computed:{
    },
    methods:{
        setSvg(){
            if(this.$refs.holder_container.offsetHeight){
                this.svgHeight = this.$refs.holder_container.offsetHeight;                
            }
            if(this.$refs.func_container.offsetWidth){
                this.svgWidth = this.$refs.func_container.offsetWidth;            
            }
            console.log("this.svg",this.$refs.holder_container.offsetHeight,this.svgHeight,this.svgWidth)
            this.drawInit()
        },
        drawInit(){
            let that = this
            //get the svg
            let svg = d3.select("svg.holderView")
                    .attr("width",that.svgWidth)
                    .attr("height",that.svgHeight)
        },

    },
    created(){
    },
    beforeMount(){
        this.dataInit()
    },
    mounted(){
        this.setSvg()

    },
    updated(){
    },
    unmounted(){
        window.removeEventListener("resize",this.setSvg)
    }
}
</script>

<style>
.lil_title {
    font-size: 1.6em;
    /* font-weight: bolder; */
    /* font-family: 'Metropolis'; */
}
</style>