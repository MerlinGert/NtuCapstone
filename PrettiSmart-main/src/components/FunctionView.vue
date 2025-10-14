<template>
    <div style="height:100%;width:100%;background:#ffffff" ref="func_container" class="display-flex">
        <svg class="function" :height="this.svgHeight" :width="this.svgWidth"></svg>             
    </div>
</template>

<script>
import * as d3 from "d3"



export default {
    name:"netView",
    props:['data','functionnodes','variablenodes','simulationData'],
    data(){
        return {
            svgHeight:'0',
            svgWidth:'0',
            margin:{left:60,right:50,top:10,bottom:10},
            AllSimuD: JSON.parse(JSON.stringify(this.simulationData)),
            owner:"0x0000000000000000000000000000000000010000",
            // owner:"0x0000000000000000000000000000000000030000",
            func_list:[],
            r:9,
            text_size:14,
            colorScheme:{
                var:'#95b2a0',
                varback:'#e3eae6',
                addrline:'#dee2e6',
                contline:'#868e96',
                back:'#f8f9fa',
                // back:'white',
                payable:'#b49b7f',
                nonpayable:"#dfceb4",
                balance_p:'#aab5d7',
                balance_n:'#da99b1',
                p:'#7d93d7',
                n:'#da749a',
                // tran_in:'#aab5d7',
                // tran_out:'#da99b1',
                tran_in:'#aab5d7',                 
                tran_out:'#e1adc1',
                f_link:'#ced4da',
                // f_link:'#8a8886',
                s_legend_text:'#495057'
            },
            current_simu:0,
            simu_objs:[],
        }
    },
    computed:{
    },
    methods:{
        setSvg(){
            if(this.$refs.func_container.offsetHeight){
                this.svgHeight = this.$refs.func_container.offsetHeight;                
            }
            if(this.$refs.func_container.offsetWidth){
                this.svgWidth = this.$refs.func_container.offsetWidth;            
            }
            console.log("this.svg",this.$refs.func_container.offsetHeight,this.svgHeight,this.svgWidth)
            this.drawInit()
        },
        drawInit(){
            let that = this
            //get the svg
            let svg = d3.select("svg.function")
                    .attr("width",that.svgWidth)
                    .attr("height",that.svgHeight)


            //simulation
            let simu_view = {
                left:that.margin.left,
                right:that.svgWidth-that.margin.right,
                top:that.margin.top,
                bottom:that.svgHeight*0.2
            }
            //function summary
            let func_overview ={
                left:that.margin.left,
                right:that.svgWidth-that.margin.right,
                top:simu_view.bottom,
                bottom:that.svgHeight*0.32
            }
            //background
            let back_view = {
                left:that.margin.left,
                right:that.svgWidth-that.margin.right,
                top:func_overview.bottom,
                bottom:that.svgHeight*0.9
            }
            //function view
            let func_view = {
                left:that.margin.left,
                right:that.svgWidth-that.margin.right,
                top:func_overview.bottom,
                bottom:that.svgHeight*0.75
            }
            //state view
            let state_view = {
                left:that.margin.left,
                right:that.svgWidth-that.margin.right,
                top:func_view.bottom+that.svgHeight*0.08,
                bottom:back_view.bottom
            }

            //draw border
            d3.select('g.border').remove()
            let b_G = svg.append('g').classed('border',true)
            let b1_d = `M${0.5} ${simu_view.bottom} V${back_view.bottom}`
            b_G.append('path')
                .attr('d',b1_d).attr('stroke',that.colorScheme.addrline)
            let b2_d = `M${func_view.right+20} ${simu_view.bottom} V${back_view.bottom}`
            b_G.append('path')
                .attr('d',b2_d).attr('stroke',that.colorScheme.addrline)
            // //draw title\
            // d3.select('g.title').remove()
            // let title_G = svg.append('g').classed('title',true)
            // let w = 22
            // let start_x = 1
            // let font_size = 14
            // title_G.append('rect')
            //     .attr('x',start_x).attr('y',simu_view.top-10)
            //     .attr('height',simu_view.bottom-simu_view.top-40).attr('width',w)
            //     .attr('fill',that.colorScheme.contline)
            //     .attr('ry',3)
            // title_G.append('text')
            //             .attr(`transform`,`rotate(-90)`)
            //             .attr('x',-(simu_view.bottom+simu_view.top)/2+30).attr('y',start_x+12)
            //             .attr('fill','black')
            //             .attr('text-anchor','middle').attr('dominant-baseline','middle')
            //                 .attr('font-family','Arial').attr('font-weight','bold')
            //                 .attr('font-size',font_size)
            //                 .attr('fill','white')
            //         .text(`Simulations`)

            // title_G.append('rect')
            //     .attr('x',start_x).attr('y',func_overview.top-10)
            //     .attr('height',func_overview.bottom-func_overview.top+7).attr('width',w)
            //     .attr('fill',that.colorScheme.contline)
            //     .attr('ry',3)
            // title_G.append('text')
            //             .attr(`transform`,`rotate(-90)`)
            //             .attr('x',-(func_overview.bottom+func_overview.top)/2+10).attr('y',start_x+12)
            //             .attr('fill','black')
            //             .attr('text-anchor','middle').attr('dominant-baseline','middle')
            //                 .attr('font-family','Arial').attr('font-weight','bold')
            //                 .attr('font-size',font_size)
            //                 .attr('fill','white')
            //         .text(`Functions`)

            // title_G.append('rect')
            //     .attr('x',start_x).attr('y',func_view.top)
            //     .attr('height',func_view.bottom-func_view.top+5).attr('width',w)
            //     .attr('fill',that.colorScheme.contline)
            //     .attr('ry',3)
            // title_G.append('text')
            //             .attr(`transform`,`rotate(-90)`)
            //             .attr('x',-(func_view.bottom+func_view.top)/2).attr('y',start_x+12)
            //             .attr('fill','black')
            //             .attr('text-anchor','middle').attr('dominant-baseline','middle')
            //                 .attr('font-family','Arial').attr('font-weight','bold')
            //                 .attr('font-size',font_size)
            //                 .attr('fill','white')
            //         .text(`Function Call`)



            // title_G.append('rect')
            //     .attr('x',start_x).attr('y',state_view.top-10)
            //     .attr('height',state_view.bottom-state_view.top).attr('width',w)
            //     .attr('fill',that.colorScheme.contline)
            //     .attr('ry',3)
            // title_G.append('text')
            //             .attr(`transform`,`rotate(-90)`)
            //             .attr('x',-(state_view.bottom+state_view.top)/2).attr('y',start_x+12)
            //             .attr('fill','black')
            //             .attr('text-anchor','middle').attr('dominant-baseline','middle')
            //                 .attr('font-family','Arial').attr('font-weight','bold')
            //                 .attr('font-size',font_size)
            //                 .attr('fill','white')
            //         .text(`State`)




            that.drawBack(svg,back_view,func_view,state_view)
            that.drawState(svg,state_view)
            that.drawFunc(svg,func_view)
            that.drawFuncOverview(svg,func_overview,back_view.bottom-func_view.top)
            that.drawSimu(svg,simu_view)

            that.draw_state_legend(svg,state_view)
        },
        draw_state_legend(svg,state_view){
            //draw legend state\
            d3.select('g.legend').remove()

            let that = this
            let legend_G = svg.append('g').classed('legend',true)
            let l_h = this.r*1.3
            let l_x = state_view.left+50
            let l_y = state_view.top-l_h -2
            let r = this.r
            let text_size = this.text_size
            let l_color = '#868e96'
            legend_G.append('text')
                    .attr('x',l_x).attr('y',l_y)
                    .attr('fill','black')
                    .attr('text-anchor','start').attr('dominant-baseline','middle')
                        .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-style','italic')
                        .attr('font-size',text_size)
                .text(`Numerical:`)
            l_x += text_size*6
            legend_G.append('circle').classed('state',true)
                .attr('cx',l_x)
                .attr('cy',l_y-1)
                .attr('r',r)
                .attr('fill',that.colorScheme['var'])
            l_x += 4.5*r
            legend_G.append('text')
                    .attr('x',l_x-r).attr('y',l_y)
                    .attr('fill','black')
                    .attr('text-anchor','end').attr('dominant-baseline','middle')
                        .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-size',text_size*0.9).attr('fill',that.colorScheme.s_legend_text)
                .text(`| 0`)
            legend_G.append('circle').classed('state',true)
                .attr('cx',l_x)
                .attr('cy',l_y-1)
                .attr('r',0.2*r)
                .attr('fill',that.colorScheme['var'])
            l_x += 2*r
            legend_G.append('circle').classed('state',true)
                .attr('cx',l_x)
                .attr('cy',l_y-1)
                .attr('r',0.4*r)
                .attr('fill',that.colorScheme['var'])
            l_x += 2*r
            legend_G.append('circle').classed('state',true)
                .attr('cx',l_x)
                .attr('cy',l_y-1)
                .attr('r',0.6*r)
                .attr('fill',that.colorScheme['var'])
            l_x += 2*r
            legend_G.append('circle').classed('state',true)
                .attr('cx',l_x)
                .attr('cy',l_y-1)
                .attr('r',0.8*r)
                .attr('fill',that.colorScheme['var'])
            l_x += 2.5*r
            legend_G.append('circle').classed('state',true)
                .attr('cx',l_x)
                .attr('cy',l_y-1)
                .attr('r',r)
                .attr('fill',that.colorScheme['var'])
            l_x += 3*r
            legend_G.append('text')
                    .attr('x',l_x-r).attr('y',l_y)
                    .attr('fill','black')
                    .attr('text-anchor','start').attr('dominant-baseline','middle')
                        .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-size',text_size*0.9)
                        .attr('fill',that.colorScheme.s_legend_text)
                .text(`max  |`)
            l_x += 5*r
            legend_G.append('circle').classed('state',true)
                                .attr('cx',l_x)
                                .attr('cy',l_y-1)
                                .attr('r',r)
                                .attr('fill','white')
                                .attr('stroke',that.colorScheme.p)  
                                .attr('stroke-width',2)
            l_x += 3*r
            legend_G.append('text')
                    .attr('x',l_x-r).attr('y',l_y)
                    .attr('fill','black')
                    .attr('text-anchor','start').attr('dominant-baseline','middle')
                        .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-size',text_size*0.9)
                        .attr('fill',that.colorScheme.s_legend_text)
                .text(`increase`)
            l_x += 7.5*r
            legend_G.append('circle').classed('state',true)
                                .attr('cx',l_x)
                                .attr('cy',l_y-1)
                                .attr('r',r)
                                .attr('fill','white')
                                .attr('stroke',that.colorScheme.n)  
                                .attr('stroke-width',2)
            l_x += 3*r
            legend_G.append('text')
                    .attr('x',l_x-r).attr('y',l_y)
                    .attr('fill','black')
                    .attr('text-anchor','start').attr('dominant-baseline','middle')
                    .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-size',text_size*0.9)
                        .attr('fill',that.colorScheme.s_legend_text)
                .text(`decrease`)
            l_x += 8*r
            legend_G.append('circle').classed('state',true)
                                .attr('cx',l_x)
                                .attr('cy',l_y-1)
                                .attr('r',r)
                                .attr('fill','white')
                                .attr('stroke',that.colorScheme.var)  
                                .attr('stroke-width',2)
            l_x += 3*r
            legend_G.append('text')
                    .attr('x',l_x-r).attr('y',l_y)
                    .attr('fill','black')
                    .attr('text-anchor','start').attr('dominant-baseline','middle')
                    .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-size',text_size*0.9)
                        .attr('fill',that.colorScheme.s_legend_text)
                .text(`same`)
            //address or string
            l_x += 4*r
            legend_G.append('text')
                    .attr('x',l_x).attr('y',l_y)
                    .attr('fill','black')
                    .attr('text-anchor','start').attr('dominant-baseline','middle')
                    .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-style','italic')
                        .attr('font-size',text_size)
                .text(`| Address:`)
            l_x += 9*r
            let h = 2.5*r
            let tri_d = `M${l_x+0.5*h} ${l_y-1-0.5*h} l${-0.5*h} ${h} h${h} z`
            legend_G.append('path').classed('state',true)
                                .attr('d',tri_d)
                                .attr('fill',that.colorScheme['var'])
                                // .attr('stroke','black')
                                .attr('stroke-width',0.4)      
            legend_G.append('text')
                        .attr('x',l_x+r*1.2).attr('y',l_y+r*0.4)
                        .attr('fill','black')
                        .attr('text-anchor','middle').attr('dominant-baseline','middle')
                            .attr('font-family','Arial').attr('font-weight','bold')
                            .attr('font-size',r*1.3)
                        .text(`#`)
            l_x += 4*r
            legend_G.append('text')
                    .attr('x',l_x-r).attr('y',l_y)
                    .attr('fill','black')
                    .attr('text-anchor','start').attr('dominant-baseline','middle')
                        .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-size',text_size*0.9)
                        .attr('fill',that.colorScheme.s_legend_text)
                .text(`participants`)
            l_x += 9*r
            tri_d = `M${l_x+0.5*h} ${l_y-1-0.5*h} l${-0.5*h} ${h} h${h} z`
            legend_G.append('path').classed('state',true)
                                .attr('d',tri_d)
                                .attr('fill',that.colorScheme['var'])
                                // .attr('stroke','black')
                                .attr('stroke-width',0.4)      
            legend_G.append('text')
                        .attr('x',l_x+r*1.2).attr('y',l_y+r*0.4)
                        .attr('fill','black')
                        .attr('text-anchor','middle').attr('dominant-baseline','middle')
                            .attr('font-family','Arial').attr('font-weight','bold')
                            .attr('font-size',r*1.3)
                        .text(`O`)
            l_x += 4*r
            legend_G.append('text')
                    .attr('x',l_x-r).attr('y',l_y)
                    .attr('fill','black')
                    .attr('text-anchor','start').attr('dominant-baseline','middle')
                        .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-size',text_size*0.9)
                        .attr('fill',that.colorScheme.s_legend_text)
                .text(`others`)
            l_x += 5*r
            tri_d = `M${l_x+0.5*h} ${l_y-1-0.5*h} l${-0.5*h} ${h} h${h} z`
            legend_G.append('path').classed('state',true)
                                .attr('d',tri_d)
                                .attr('stroke',that.colorScheme['var'])
                                .attr('fill','none')
                                .attr('stroke-width',1)      
            legend_G.append('text')
            .attr('x',l_x+r*1.2).attr('y',l_y+r*0.4)
                        .attr('fill','black')
                        .attr('text-anchor','middle').attr('dominant-baseline','middle')
                            .attr('font-family','Arial').attr('font-weight','bold')
                            .attr('font-size',r*1.3)
                        .text(`#`)
            l_x += 4*r
            legend_G.append('text')
                    .attr('x',l_x-r).attr('y',l_y)
                    .attr('fill','black')
                    .attr('text-anchor','start').attr('dominant-baseline','middle')
                        .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-size',text_size*0.9)
                        .attr('fill',that.colorScheme.s_legend_text)
                .text(`same`)
                // l_x += 4*r
            // legend_G.append('text')
            //         .attr('x',l_x).attr('y',l_y)
            //         .attr('fill','black')
            //         .attr('text-anchor','start').attr('dominant-baseline','middle')
            //         .attr('font-family','Arial').attr('font-weight','bold')
            //             .attr('font-style','italic')
            //             .attr('font-size',text_size)
            //     .text(`| String:`)
            // l_x += 7*r
            // tri_d = `M${l_x+0.5*h} ${l_y-1-0.5*h} l${-0.5*h} ${h} h${h} z`
            // legend_G.append('path').classed('state',true)
            //                     .attr('d',tri_d)
            //                     .attr('fill',that.colorScheme['var'])
            //                     // .attr('stroke','black')
            //                     .attr('stroke-width',0.4)      
            // l_x += 3*r
            // tri_d = `M${l_x+0.5*h} ${l_y-1-0.5*h} l${-0.5*h} ${h} h${h} z`
            // legend_G.append('path').classed('state',true)
            //                     .attr('d',tri_d)
            //                     .attr('stroke',that.colorScheme['var'])
            //                     .attr('fill','none')
            //                     .attr('stroke-width',1)      
            // l_x += 4*r
            // legend_G.append('text')
            //         .attr('x',l_x-r).attr('y',l_y)
            //         .attr('fill','black')
            //         .attr('text-anchor','start').attr('dominant-baseline','middle')
            //         .attr('font-family','Arial').attr('font-weight','bold')
            //             .attr('font-size',text_size*0.9)
            //             .attr('fill',that.colorScheme.s_legend_text)
            //     .text(`same`)
            //     l_x += 4*r
            // legend_G.append('text')
            //         .attr('x',l_x).attr('y',l_y)
            //         .attr('fill','black')
            //         .attr('text-anchor','start').attr('dominant-baseline','middle')
            //         .attr('font-family','Arial').attr('font-weight','bold')
            //             .attr('font-style','italic')
            //             .attr('font-size',text_size)
            //     .text(`| Mapping and Array:`)
            // l_x += 19*r
            // legend_G.append('rect').classed('state',true)
            //         .attr('x',l_x-r)
            //         .attr('y',l_y-1-r)
            //         .attr('width',r*2).attr('height',r*2)
            //         .attr('fill',that.colorScheme['var'])
            l_x += 4*r
            legend_G.append('text')
                    .attr('x',l_x).attr('y',l_y)
                    .attr('fill','black')
                    .attr('text-anchor','start').attr('dominant-baseline','middle')
                    .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-style','italic')
                        .attr('font-size',text_size)
                .text(`| Updated:`)            
            l_x += 10*r
            legend_G.append('rect').classed('state',true)
                        .attr('x',l_x-r)
                        .attr('y',l_y-1-r)
                        .attr('width',r*5).attr('height',r*2)
                        .attr('fill',that.colorScheme.varback)    
                        .attr('rx',5)
            l_x += 5*r
            legend_G.append('text')
                    .attr('x',l_x).attr('y',l_y)
                    .attr('fill','black')
                    .attr('text-anchor','start').attr('dominant-baseline','middle')
                    .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-style','italic')
                        .attr('font-size',text_size)
                .text(`| Not Change:`)            
            l_x += 12*r
            let same_d = `M${l_x} ${l_y} h${r*6} `
            legend_G.append('path').classed('state',true)
                .attr('d',same_d)
                .attr('fill',that.colorScheme['var'])
                .attr('stroke','black')
                .attr('stroke-width',1.5)
                .attr('stroke-dasharray','3,2')
        },
        drawFuncOverview(svg,func_overview,cover_len){
            d3.select('g.funcO').remove()

            let that = this
            let funcO_G = svg.append('g').classed('funcO',true)
            let x1 = func_overview.left +50 
            let x2 = func_overview.right - 50
            let y1 = func_overview.top + 25
            let y2 = func_overview.bottom

            let simu_obj = that.simu_objs[this.current_simu]
            let calls = simu_obj.calls
            let callLen = simu_obj.callLen
            let funcNodes = this.functionnodes

            let called_functions = [...new Set([...calls.map(item=>item['function'])])]
            let funcLen = Math.max(called_functions.length,6)
            // console.log(calls,called_functions)
            let x_scale = d3.scaleLinear().domain([0,funcLen]).range([x1,x2])
            let x_gap = x_scale(1)-x_scale(0)
            let func_list = simu_obj.func_list

            // draw legends
            let text_size = this.text_size
            let r = this.r*0.9
            let l_y = y1
            let l_x = func_overview.right - r*35
            funcO_G.append('text')
                            .attr('x',l_x-r*3).attr('y',l_y)
                            .attr('fill','black')
                            .attr('text-anchor','end').attr('dominant-baseline','middle')
                                .attr('font-family','Arial').attr('font-weight','bold')
                                .attr('font-size',text_size)
                                .attr('fill',that.colorScheme.s_legend_text)
                        .text(`Payable Functions:`)
            funcO_G.append('rect')
                .attr('x',l_x-r*2.5).attr('y',l_y-r)
                .attr('width',r*2).attr('height',r*2)
                .attr('fill',that.colorScheme['payable'])     
            l_y+= 3*r     
            funcO_G.append('text')
                            .attr('x',l_x-r*3).attr('y',l_y)
                            .attr('fill','black')
                            .attr('text-anchor','end').attr('dominant-baseline','middle')
                            .attr('font-family','Arial').attr('font-weight','bold')
                                .attr('font-size',text_size)
                                .attr('fill',that.colorScheme.s_legend_text)
                        .text(`NonPayable Functions:`)
            funcO_G.append('rect')
                .attr('x',l_x-r*2.5).attr('y',l_y-r)
                .attr('width',r*2).attr('height',r*2)
                .attr('fill',that.colorScheme['nonpayable'])  
            
            l_x+= 15*r
            l_y-= 3*r  
            funcO_G.append('text')
                            .attr('x',l_x-r*3).attr('y',l_y)
                            .attr('fill','black')
                            .attr('text-anchor','end').attr('dominant-baseline','middle')
                            .attr('font-family','Arial').attr('font-weight','bold')
                                .attr('font-size',text_size)
                                .attr('fill',that.colorScheme.s_legend_text)
                        .text(`Money Out:`)
            funcO_G.append('text')
                .attr('x',l_x-r*3).attr('y',l_y+3*r)
                .attr('fill','black')
                .attr('text-anchor','end').attr('dominant-baseline','middle')
                .attr('font-family','Arial').attr('font-weight','bold')
                                .attr('font-size',text_size)
                                .attr('fill',that.colorScheme.s_legend_text)
            .text(`Money In:`)
            l_x-=1.5*r
            let l_tri_width = 1.3*r
            let l_tri_d = `M${l_x} ${l_y-l_tri_width*0.6} l${-0.5*l_tri_width} ${l_tri_width} h${l_tri_width} z`
            funcO_G.append('path')
                    .attr('d',l_tri_d)
                    .attr('fill','black')
            l_tri_d = `M${l_x} ${l_y+r*3.5} l${-0.5*l_tri_width} ${-l_tri_width} h${l_tri_width} z`
            funcO_G.append('path')
                    .attr('d',l_tri_d)
                    .attr('fill','black')
            l_x+= 2*r
            let path_d = `M${l_x} ${l_y+r*1.2} 
                    C${l_x+r} ${l_y+r*1.2}, ${l_x+r} ${l_y-r*1.2}, ${l_x+r*2} ${l_y-r*1.2}`
            funcO_G.append('path')
                .attr("d",path_d)
                .attr('fill','none')
                .attr('stroke',that.colorScheme.tran_out)
                .attr('stroke-width',1)
            l_y+= 3*r
            path_d = `M${l_x} ${l_y-r*1.2} 
                C${l_x+r} ${l_y-r*1.2}, ${l_x+r} ${l_y+r*1.2}, ${l_x+r*2} ${l_y+r*1.2}`
            funcO_G.append('path')
                .attr("d",path_d)
                .attr('fill','none')
                .attr('stroke',that.colorScheme.tran_in)
                .attr('stroke-width',1)
            l_y-= r*3
            l_x+= 2*r
            path_d = `M${l_x} ${l_y+r*1.2} 
                    C${l_x+r} ${l_y+r*1.2}, ${l_x+r} ${l_y-r*1.2}, ${l_x+r*2} ${l_y-r*1.2}`
            funcO_G.append('path')
                .attr("d",path_d)
                .attr('fill','none')
                .attr('stroke',that.colorScheme.tran_out)
                .attr('stroke-width',2)
                l_y+= 3*r
            path_d = `M${l_x} ${l_y-r*1.2} 
                C${l_x+r} ${l_y-r*1.2}, ${l_x+r} ${l_y+r*1.2}, ${l_x+r*2} ${l_y+r*1.2}`
            funcO_G.append('path')
                .attr("d",path_d)
                .attr('fill','none')
                .attr('stroke',that.colorScheme.tran_in)
                .attr('stroke-width',2)
            l_y-= r*3
            l_x+= 2*r
            path_d = `M${l_x} ${l_y+r*1.2} 
                    C${l_x+r} ${l_y+r*1.2}, ${l_x+r} ${l_y-r*1.2}, ${l_x+r*2} ${l_y-r*1.2}`
            funcO_G.append('path')
                .attr("d",path_d)
                .attr('fill','none')
                .attr('stroke',that.colorScheme.tran_out)
                .attr('stroke-width',3)
            l_y+= 3*r
            path_d = `M${l_x} ${l_y-r*1.2} 
                C${l_x+r} ${l_y-r*1.2}, ${l_x+r} ${l_y+r*1.2}, ${l_x+r*2} ${l_y+r*1.2}`
            funcO_G.append('path')
                .attr("d",path_d)
                .attr('fill','none')
                .attr('stroke',that.colorScheme.tran_in)
                .attr('stroke-width',3)
            l_y-= r*3
            l_x+= 15*r
            funcO_G.append('text')
                .attr('x',l_x-r*3).attr('y',l_y)
                .attr('fill','black')
                .attr('text-anchor','end').attr('dominant-baseline','middle')
                .attr('font-family','Arial').attr('font-weight','bold')
                                .attr('font-size',text_size)
                                .attr('fill',that.colorScheme.s_legend_text)
            .text(`Negative:`)
            funcO_G.append('text')
                .attr('x',l_x-r*3).attr('y',l_y+3*r)
                .attr('fill','black')
                .attr('text-anchor','end').attr('dominant-baseline','middle')
                .attr('font-family','Arial').attr('font-weight','bold')
                                .attr('font-size',text_size)
                                .attr('fill',that.colorScheme.s_legend_text)
            .text(`Positive:`)
            funcO_G.append('rect')
                .attr('x',l_x-r*2.5).attr('y',l_y-r)
                .attr('width',r*2).attr('height',r*2)
                .attr('fill',that.colorScheme.balance_n) 
            funcO_G.append('rect')
                .attr('x',l_x-r*2.5).attr('y',l_y+r*2)
                .attr('width',r*2).attr('height',r*2)
                .attr('fill',that.colorScheme.balance_p) 
            //draw function=============================================================================
            let width = Math.max(x_gap*0.1,(y2-y1)*0.4)
            let height = width
            let tri_scale = width*0.3
            funcO_G.append('text')
                            .attr('x',func_overview.left+30).attr('y',y1+height*0.5)
                            .attr('fill','black')
                            .attr('text-anchor','end').attr('dominant-baseline','middle')
                                .attr('font-family','Arial').attr('font-weight','bold')
                                .attr('font-style','italic')
                                .attr('font-size',text_size*1.1)
                        .text(`Functions:`)
            func_list.forEach((func,fid)=>{
                    let f_g = funcO_G.append('g').classed(`f${fid}`,true)
                    // drawtext
                    f_g.append('text')
                            .attr('x',x_scale(fid)).attr('y',y1-10)
                            .attr('fill','black')
                            .attr('text-anchor','start').attr('dominant-baseline','middle')
                                .attr('font-family','Arial').attr('font-weight','bold')
                                .attr('font-size',text_size*0.9)
                        .text(`F${fid}: ${func[0]}`)
                    //draw glyph
                    f_g.append('rect')
                        .attr('x',x_scale(fid)).attr('y',y1)
                        .attr('width',width-1).attr('height',height)
                        .attr('fill',that.colorScheme[func[4]?'payable':'nonpayable'])
                    let bar_rate = 0.8
                    let call_scale = d3.scaleLinear().domain([0,callLen]).range([5,bar_rate*x_gap])
                    //draw triangle

                    if(func[2]>0){
                        let tri_d = `M${x_scale(fid)+0.5*width} ${y1+0.1*width} l${-0.5*tri_scale} ${tri_scale} h${tri_scale}`
                        f_g.append('path')
                                .attr('d',tri_d)
                                .attr('fill','black')
                    }
                    if(func[5]>0){
                        let tri_d = `M${x_scale(fid)+0.5*width} ${y1+0.9*width} l${-0.5*tri_scale} ${-tri_scale} h${tri_scale}`
                        f_g.append('path')
                                .attr('d',tri_d)
                                .attr('fill','black')
                    }
                    if(func[6]>0){
                        let tri_d = `M${x_scale(fid)+0.5*width} ${y1+1.4*width} l${-0.5*tri_scale} ${-tri_scale} h${tri_scale}`
                        f_g.append('path')
                                .attr('d',tri_d)
                                .attr('fill','black')
                    }
                    //draw bar chart

                    f_g.append('rect')
                        .attr('x',x_scale(fid)+width).attr('y',y1+1)
                        .attr('width',call_scale(func[1])).attr('height',height/3-2)
                        .attr('stroke',that.colorScheme['contline'])
                        .attr('fill','white')
                    f_g.append('rect')
                        .attr('x',x_scale(fid)+width).attr('y',y1+1)
                        .attr('width',call_scale(func[1])).attr('height',height/3-2)
                        .attr('fill',that.colorScheme['contline'])
                    f_g.append('rect')
                        .attr('x',x_scale(fid)+width).attr('y',y1+height/3+1)
                        .attr('width',call_scale(func[1])).attr('height',height/3-2)
                        .attr('stroke',that.colorScheme['tran_out'])
                        .attr('fill','white')
                    f_g.append('rect')
                        .attr('x',x_scale(fid)+width).attr('y',y1+height/3+1)
                        .attr('width',func[2]>0?call_scale(func[2]):0).attr('height',height/3-2)
                        .attr('fill',that.colorScheme['tran_out'])
                    f_g.append('rect')
                        .attr('x',x_scale(fid)+width).attr('y',y1+height*2/3+1)
                        .attr('width',call_scale(func[1])).attr('height',height/3-2)
                        .attr('stroke',that.colorScheme['tran_in'])
                        .attr('fill','white')
                    f_g.append('rect')
                        .attr('x',x_scale(fid)+width).attr('y',y1+height*2/3+1)
                        .attr('width',func[3]>0?call_scale(func[3]):0).attr('height',height/3-2)
                        .attr('fill',that.colorScheme['tran_in'])

                    // add interactions 
                    let call_x_scale = d3.scaleLinear().domain([-1,callLen]).range([func_overview.left+20,func_overview.right])
                    f_g.on('mouseover', function(_event){
                        let count = 0
                        func[7].forEach((cid,idx)=>{
                            if(cid>=0){
                                let s_x = x_scale(fid)+width +count*0.2
                                let control_y1 = (y1+y2+height+5)/2
                                let control_y2 = (y1+height+y2+5)/2
                                if(s_x<call_x_scale(cid+0.5)){
                                    control_y1 = (y1+y2+height+5)/2+idx*0.5
                                    control_y2 = (y1+height+y2+5)/2-idx*0.5
                                }
                                // let path_d = `M${s_x} ${y1+height} v${5} C${s_x} ${(y1+y2+height+5)/2}, ${call_x_scale(cid+0.5)} ${(y1+y2+height+5)/2}, ${call_x_scale(cid+0.5)} ${y2} `
                                let path_d = `M${s_x} ${y1+height} v${5} C${s_x} ${control_y1}, ${call_x_scale(cid+0.5)} ${control_y2}, ${call_x_scale(cid+0.5)} ${y2} `
                                f_g.append('path').classed('highlight',true)
                                    .attr('d',path_d)
                                    .attr('stroke',that.colorScheme.f_link)
                                    .attr('fill','none').attr('stroke-width',0.5)
                                f_g.append('rect').classed('highlight',true)
                                    .attr('x',call_x_scale(cid)).attr('y',y2-3)
                                    .attr('width',call_x_scale(1)-call_x_scale(0)).attr('height',3)
                                    .attr('fill',that.colorScheme.f_link)      
                                count+=1                          
                            }else{
                                f_g.append('rect').classed('highlight',true)
                                    .attr('x',call_x_scale(idx)).attr('y',y2)
                                    .attr('width',call_x_scale(1)-call_x_scale(0)).attr('height',cover_len)
                                    .attr('fill','white')
                                    .attr('opacity',0.8)
                            }

                        })

                    }).on('mouseout',function(_event){
                        d3.selectAll('.highlight').remove()
                    })
                    
            })
            that.func_list= func_list
            console.log(func_list)
        },
        drawSimu(svg,simu_view){
            d3.select('g.simu').remove()

            let that = this
            let simu_G = svg.append('g').classed('simu',true)

            let link_gap = 40
            let y1 = simu_view.top + 25
            let y2 = simu_view.bottom -link_gap

            let simu_objs = that.simu_objs
            let simuLen = simu_objs.length

            let max_addrLen = Math.max(...simu_objs.map(item=>item.addrLen)) 
            let max_callLen = Math.max(...simu_objs.map(item=>item.callLen)) 
            let total_callen = simu_objs.map(item=>item.callLen).reduce((a,b)=>a+b,0)

            let s_gap = 20
            let tran_width = (simu_view.right-simu_view.left -40 - s_gap*(simuLen-1))/total_callen
            let start_x = simu_view.left+50 //start x for each simulation
            let y_scale = d3.scaleLinear().domain([0,max_addrLen+1]).range([y1,y2])
            let y_gap = y_scale(1)-y_scale(0)



            // add a legend
            let start_y = y_scale(0.5)
            let text_size = that.text_size
            simu_G.append('text')
                            .attr('x',simu_view.left+32).attr('y',y_scale(0)-25)
                            .attr('fill','black')
                            .attr('text-anchor','end').attr('dominant-baseline','middle')
                            .attr('font-family','Arial').attr('font-weight','bold')
                                .attr('font-style','italic')
                                .attr('font-size',text_size*1.1)
                        .text(`Simulations:`)
            simu_G.append('circle')
                .attr('cx',simu_view.left+30+this.r).attr('cy',start_y)
                .attr('r',8).attr('height',(y_gap)*0.9)
                .attr('fill',that.colorScheme['payable'])      
            simu_G.append('text')
                        .attr('x',simu_view.left-50).attr('y',start_y+1)
                        .attr('fill','black')
                        .attr('text-anchor','start').attr('dominant-baseline','middle')
                            .attr('font-family','Arial').attr('font-weight','bold')
                            .attr('font-size',text_size*0.9)
                    .text(`Payable:`)
            start_y += 0.8*y_gap
            simu_G.append('circle')
                .attr('cx',simu_view.left+30+this.r).attr('cy',start_y)
                .attr('r',8).attr('height',(y_gap)*0.9)
                .attr('fill',that.colorScheme['nonpayable'])      
            simu_G.append('text')
                        .attr('x',simu_view.left-50).attr('y',start_y+1)
                        .attr('fill','black')
                        .attr('text-anchor','start').attr('dominant-baseline','middle')
                        .attr('font-family','Arial').attr('font-weight','bold')
                            .attr('font-size',text_size*0.9)
                    .text(`NonPayable:`)
            start_y+=  0.8*y_gap
            simu_G.append('text')
                .attr('x',simu_view.left-50).attr('y',start_y+1)
                .attr('fill','black')
                .attr('text-anchor','start').attr('dominant-baseline','middle')
                .attr('font-family','Arial').attr('font-weight','bold')
                            .attr('font-size',text_size*0.9)
            .text(`Net Balance`)
            start_y+=  0.8*y_gap
            let l_w = 20
            let def = svg.append('defs')
                .append('linearGradient').attr('id','balance')
                    .attr('x1',0).attr('x2',1).attr('y1',0).attr('y2',0)

            def.append('stop').attr('offset','0%').attr('stop-color',that.colorScheme.n)
            def.append('stop').attr('offset','50%').attr('stop-color','white')
            def.append('stop').attr('offset','100%').attr('stop-color',that.colorScheme.p)
            simu_G.append('rect')
                    .attr('x',simu_view.left-50).attr('y',start_y-l_w*0.7)
                    .attr('width',90).attr('height',l_w)
                    .attr('fill','url(#balance)')   
            simu_G.append('text')
                .attr('x',simu_view.left-50).attr('y',start_y+l_w-2)
                .attr('fill','black')
                .attr('text-anchor','start').attr('dominant-baseline','middle')
                    .attr('font-family','Arial').attr('font-weight','bold')
                    .attr('font-size',text_size*0.9)
                    .attr('fill',that.colorScheme.s_legend_text)
            .text(`min`)
            simu_G.append('text')
                .attr('x',simu_view.left+40).attr('y',start_y+l_w-2)
                .attr('fill','black')
                .attr('text-anchor','end').attr('dominant-baseline','middle')
                .attr('font-family','Arial').attr('font-weight','bold')
                    .attr('font-size',text_size*0.9)
                    .attr('fill',that.colorScheme.s_legend_text)
            .text(`max`)
            simu_G.append('text')
                .attr('x',simu_view.left-5).attr('y',start_y+l_w-2)
                .attr('fill','black')
                .attr('text-anchor','middle').attr('dominant-baseline','middle')
                .attr('font-family','Arial').attr('font-weight','bold')
                    .attr('font-size',text_size*0.9)
                    .attr('fill',that.colorScheme.s_legend_text)
            .text(`0`)
            //draw simu
            simu_objs.forEach((simu_D,sid)=>{
                let s_G = simu_G.append('g').classed(`s${sid}`,true)

                let balances = simu_D.balances
                let addresses = simu_D.addresses
                let addrLen = simu_D.addrLenl
                let func_list = simu_D.func_list
                let funcLen = func_list.length
                let maxVal = simu_D.maxVal
                let callLen = simu_D.callLen
                let color_scale = d3.scaleLinear().domain([-maxVal,0,maxVal]).range([that.colorScheme.n,'white',that.colorScheme.p])

                let selected = sid == that.current_simu
                let border_color = selected?'#343a40':that.colorScheme.f_link


                let head_width = 4
                let x_scale = d3.scaleLinear().domain([1,callLen]).range([start_x+head_width,start_x+callLen*tran_width])

                let f_scale = d3.scaleLinear().domain([-0.5,Math.max(funcLen+1,10)]).range([start_x+head_width,start_x+callLen*tran_width])
                func_list.forEach((f,fid)=>{
                    s_G.append('circle')
                            // .attr('cx',start_x+head_width + 12*fid +5).attr('cy',y_scale(0)-8)
                            .attr('cx',f_scale(fid)).attr('cy',y_scale(0)-12)
                            .attr('r',7).attr('height',(y_scale(1)-y_scale(0))*0.9)
                            .attr('fill',that.colorScheme[f[4]?'payable':'nonpayable'])           
                })

                balances['contract'].forEach((b,bid)=>{
                    if(bid>0){
                            s_G.append('rect')
                                .attr('x',x_scale(bid)).attr('y',y_scale(0))
                                .attr('width',tran_width*0.95).attr('height',(y_scale(1)-y_scale(0))*0.9)
                                .attr('fill',color_scale(b))           
                        }
                })
                addresses.forEach((addr,idx)=>{
                    let balance = balances[addr]
                    balance.forEach((b,bid)=>{
                        if(bid>0){
                            s_G.append('rect')
                                .attr('x',x_scale(bid)).attr('y',y_scale(idx+1))
                                .attr('width',tran_width*0.95).attr('height',y_scale(1)-y_scale(0))
                                .attr('fill',color_scale(b))           
                        }
                    })
                    s_G.append('line').classed('hover',true).classed('h_line',true)
                        .attr('x1',start_x+tran_width).attr('y1',y1)
                        .attr('x2',start_x+tran_width).attr('y2',y2)
                        .attr('fill','none').attr('stroke',border_color)
                        .attr('stroke-width',2)
                    s_G.append('line').classed('hover',true).classed('h_line',true)
                        .attr('x1',start_x+head_width+(callLen)*tran_width).attr('y1',y1)
                        .attr('x2',start_x+head_width+(callLen)*tran_width).attr('y2',y2)
                        .attr('fill','none').attr('stroke',border_color)
                        .attr('stroke-width',2)
                    s_G.append('rect').classed('hover',true).classed('h_rect',true)
                        .attr('x',start_x+tran_width).attr('y',y1)
                        .attr('width',head_width+(callLen-1)*tran_width).attr('height',y_scale(1)-y_scale(0))
                        .attr('fill','none').attr('stroke',selected?'#343a40':that.colorScheme.contline)
                        .attr('stroke-width',2)

                })

                // drawtext
                s_G.append('text')
                        .attr('x',start_x + (callLen*tran_width)/2).attr('y',y_scale(0)-27)
                        .attr('fill','black')
                        .attr('text-anchor','middle').attr('dominant-baseline','middle')
                            .attr('font-family','Arial').attr('font-weight',selected?'bold':'bold')
                            .attr("fill",selected?'black':that.colorScheme.s_legend_text)
                            .attr('font-size',text_size)
                .text(`Simulation ${sid}`)
                //draw linker
                if(selected){
                    // let link_d = `M${start_x} ${y2} h${head_width+(callLen)*tran_width} L${simu_view.right} ${y2+50} H${simu_view.left}`

                    let link_d = `M${0} ${y2+link_gap} Q${0.5*(start_x+simu_view.left)} ${y2+link_gap*1.1},${start_x+head_width} ${y2} 
                    h${(callLen)*tran_width} Q${0.5*(start_x+head_width+(callLen)*tran_width+simu_view.right)} ${y2+link_gap}, ${simu_view.right+20} ${y2+link_gap} `
                    s_G.append('path')
                        .attr('d',link_d)
                        .attr('fill','grey')
                        .attr('stroke','grey')
                        .attr("opacity",0.2)
                }
                // bund interaction
                s_G.on('mouseover',function (_event){
                    if(that.current_simu!=sid){
                        s_G.selectAll('.hover').attr('stroke','black')
                        s_G.select('text')
                            .attr('fill','black')
                    }
                }).on('mouseout',function (_event){
                    if(that.current_simu!=sid){
                        s_G.selectAll('.h_line').attr('stroke',that.colorScheme.addrline)
                        s_G.selectAll('.h_rect').attr('stroke',that.colorScheme.contline)
                        s_G.select('text')
                            .attr('fill',that.colorScheme.s_legend_text)
                    }
                }).on('click',function (_event){
                    that.current_simu = sid
                    that.drawInit()
                })
                //update start x
                start_x = start_x + callLen*tran_width + s_gap        
            })
        },
        drawBack(svg,back_view,func_view,state_view){
            d3.select('g.back').remove()

            let that = this
            let Back_G = svg.append('g').classed('back',true)

            let simu_obj = that.simu_objs[this.current_simu]
            let callLen = simu_obj.callLen
            console.log('calllen',callLen)
            let x_scale = d3.scaleLinear().domain([-1,callLen]).range([back_view.left+20,back_view.right])
            let x_gap = x_scale(1)-x_scale(0)

            for(let k=0;k<callLen;k++){
                if(k%2==0){
                    Back_G.append('rect').classed('back',true)
                        .attr('x',x_scale(k)).attr('y',back_view.top)
                        .attr('width',x_gap)
                        .attr('height',func_view.bottom-back_view.top)
                        .attr('fill',that.colorScheme.back)
                    Back_G.append('rect').classed('back',true)
                        .attr('x',x_scale(k)).attr('y',state_view.top)
                        .attr('width',x_gap)
                        .attr('height',state_view.bottom-state_view.top)
                        .attr('fill',that.colorScheme.back)
                }
            }
        },
        drawState(svg,state_view){
            d3.select('g.state').remove()

            let that = this
            let State_G = svg.append('g').classed('state',true)

            let varNodes = that.variablenodes

            let simu_obj = that.simu_objs[this.current_simu]
            let calls = simu_obj.calls
            let callLen = simu_obj.callLen
            let addresses = simu_obj.addresses


            let used_variables = simu_obj.used_variables
            let varLen = used_variables.length
            let type_mapping = {}
            // let type_classes = ['none','uint','int','address','string','mapping','array']
            let type_classes = ['none','uint','int','address']
            used_variables.forEach(v=>{
                let node = varNodes.filter(item=>item['name']==v)[0]
                let v_type = node['type']
                let v_type_class,class_name
                if(v_type.slice(0,4)=='uint'){
                    v_type_class = 1
                    class_name = 'uint'
                }else if(v_type.slice(0,3)=='int'){
                    v_type_class = 2
                    class_name = 'int'
                }else if(v_type=='address'){
                    v_type_class = 3
                    class_name = 'address'
                }else if(v_type=='string'){
                    v_type_class = 4
                    class_name = 'string'
                }else if(v_type.slice(0,7)=='mapping'){
                    v_type_class = 5
                    class_name = 'mapping'
                }else if(v_type.slice(-2)=='[]'){
                    v_type_class = 6
                    class_name = 'array'
                }else {
                    v_type_class = 100
                    class_name = 'none'
                }
                let last_val = node['value']
                type_mapping[v] = [v_type,v_type_class,class_name,last_val]

                let max_value = 0
                if(class_name=='uint'||class_name=='int'){
                    calls.forEach(call=>{
                        if(call['before'][v]){
                            let before = parseInt(call['before'][v],16) 
                            let after = parseInt(call['after'][v],16) 
                            max_value = Math.max(before,after,max_value)
                        }
                    })
                    type_mapping[v] = [v_type,v_type_class,class_name,last_val,max_value]
                }
            })
            console.log(used_variables,type_mapping)

            used_variables = used_variables.sort((a,b)=>type_mapping[a][1]-type_mapping[b][1]).filter(uv=>[1,2,3].indexOf(type_mapping[uv][1])>-1)
            let x_scale = d3.scaleLinear().domain([-1,callLen]).range([state_view.left+20,state_view.right])
            let y_scale = d3.scaleLinear().domain([-0.5,used_variables.length-0.5]).range([state_view.top,state_view.bottom])
            let x_gap = x_scale(1)-x_scale(0)
            let y_gap = y_scale(1)-y_scale(0)
            let r = Math.min(that.r*1.3,y_gap*0.4,x_gap*0.33) 


            //draw start ------------------------------------------------------------
            let text_size = that.text_size
            State_G.append('text')
                            .attr('x',state_view.left+30).attr('y',state_view.top-12)
                            .attr('fill','black')
                            .attr('text-anchor','end').attr('dominant-baseline','middle')
                            .attr('font-family','Arial').attr('font-weight','bold')
                                .attr('font-style','italic')
                                .attr('font-size',text_size*1.1)
                        .text(`States:`)
            let label_x = x_scale(-0.5)

            used_variables.forEach((variable,nid)=>{
                let var_type = varNodes.filter(item=>item['name']==variable)[0]['type']
                let ref_types = ['mapping']
                let non_values = ['address','string']
                if(var_type.slice(0,4)=='uint'||var_type.slice(0,3)=='int'){ //value type
                    State_G.append('circle').classed('state',true)
                    .attr('cx',label_x)
                    .attr('cy',y_scale(nid))
                    .attr('r',r)
                    .attr('fill',that.colorScheme['var'])
                }else if(non_values.indexOf(var_type)>-1){
                    let h = 2*r
                    let tri_d = `M${label_x} ${y_scale(nid)-0.5*h} l${-0.5*h} ${h} h${h}`
                    State_G.append('path').classed('state',true)
                        .attr('d',tri_d)
                        .attr('fill',that.colorScheme['var'])
                        // .attr('opacity',0.7)
                }else if(var_type){
                    State_G.append('rect').classed('state',true)
                        .attr('x',label_x-r)
                        .attr('y',y_scale(nid)-r)
                        .attr('width',r*2).attr('height',r*2)
                        .attr('fill',that.colorScheme['var'])
                }
                // console.log(node)
                State_G.append('text')
                    .attr('x',label_x-1.3*r).attr('y',y_scale(nid))
                    .attr('fill','black')
                    .attr('text-anchor','end').attr('dominant-baseline','middle')
                        .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-size',text_size*0.8)
                .text(`${variable}`)
                State_G.append('text')
                    .attr('x',label_x-1.3*r).attr('y',y_scale(nid)+1.8*r)
                    .attr('fill','grey')
                    .attr('text-anchor','end').attr('dominant-baseline','middle')
                        .attr('font-family','Arial').attr('font-weight','normal')
                        .attr('font-size',text_size*0.8).attr('fill',that.colorScheme.s_legend_text)
                .text(`(${var_type})`)
            })
            //draw state change----------------------------------------------------------------------------
            let copy_type_mapping = JSON.parse(JSON.stringify(type_mapping))
            calls.forEach((call,cid)=>{
                //update draw the background
                if(call['updated'].length>0){
                    
                    call['updated'].forEach(v=>{
                        if(used_variables.indexOf(v)!=-1){
                        State_G.append('rect').classed('state',true)
                                .attr('x',x_scale(cid))
                                .attr('y',y_scale(used_variables.indexOf(v))-y_gap*0.45)
                                .attr('width',x_gap*0.9).attr('height',y_gap*0.9)
                                .attr('fill',that.colorScheme.varback)    
                                .attr('rx',5)
                                // .attr('opacity',0.5)
                        }
                    })

                }
                // draw the updated back and same link
                used_variables.forEach((v,vid)=>{
                    let value
                    let same_check = false
                    if(call['updated'].indexOf(v)!=-1){
                        let before = copy_type_mapping[v][3]
                        let after = call['after'][v]
                        value = after
                        console.log('before',before,after)
                        if(before==after&&before){
                            same_check = true
                        }

                        copy_type_mapping[v][3] = after //update last value
                    }else{ //there is no updates
                        value = copy_type_mapping[v][3]
                        if(value){
                            same_check = true
                        }
                    }
                    //draw same link
                    if(same_check&&cid>0){
                        let same_d = `M${x_scale(cid+0.5)} ${y_scale(used_variables.indexOf(v))} h${-x_gap} `
                        State_G.append('path').classed('state',true)
                            .attr('d',same_d)
                            .attr('fill',that.colorScheme['var'])
                            .attr('stroke','black')
                            .attr('stroke-width',1.5)
                            .attr('stroke-dasharray','3,2')
                    }
                    
                })

            })

            //draw value 
            calls.forEach((call,cid)=>{
                // draw the values  call cid
                used_variables.forEach((v,vid)=>{
                    if(type_mapping[v][2]=='address'||type_mapping[v][2]=='string'){ // address or string
                        let value
                        let no_update = false
                        let same_check = false
                        if(call['updated'].indexOf(v)!=-1){
                            let before = call['before'][v]
                            let after = call['after'][v]
                            if(before==after&&before){
                                same_check =true
                            }
                            value = after
                            // console.log('before',before,after)

                            type_mapping[v][3] = after //update last value
                        }else{ //there is no updates
                            value = type_mapping[v][3]
                            no_update = true
                            console.log(cid,type_mapping)
                        }

                        // draw value
                        if(value){
                            let h = 2*r
                            let tri_d = `M${x_scale(cid+0.5)} ${y_scale(used_variables.indexOf(v))-0.5*h} l${-0.5*h} ${h} h${h} z`
                            if(no_update|| (!no_update&&same_check)){
                                State_G.append('path').classed('state',true)
                                    .attr('d',tri_d)
                                    .attr('fill','white')
                                    .attr('stroke',that.colorScheme['var'])
                                    .attr('stroke-width',1)      
                            }else{
                                State_G.append('path').classed('state',true)
                                    .attr('d',tri_d)
                                    .attr('fill',that.colorScheme['var'])
                                    // .attr('stroke','black')
                                    .attr('stroke-width',0.4)                                
                            }

                            if(type_mapping[v][2]=='address'){
                                let addr_check = 'o'
                                addresses.forEach(addr=>{
                                    if(addr== `0x00000000000000000000000000000000000${value.toString().slice(2)}`){
                                        addr_check = [...value][2]
                                    }
                                })
                                State_G.append('text')
                                            .attr('x',x_scale(cid+0.5)).attr('y',y_scale(used_variables.indexOf(v))+r*0.3)
                                            .attr('fill','black')
                                            .attr('text-anchor','middle').attr('dominant-baseline','middle')
                                                .attr('font-family','Arial').attr('font-weight','bold')
                                                .attr('font-size',r*1.1)
                                            .text(`${addr_check}`)
                            }
                        }


                    }else if(type_mapping[v][2]=='uint'||type_mapping[v][2]=='int'){ // numerical value
                        let v_scale =d3.scaleLinear().domain([0,type_mapping[v][4]]).range([1,r])
                        if(call['updated'].indexOf(v)!=-1){
                            let before = parseInt(call['before'][v],16) 
                            let after = parseInt(call['after'][v],16) 
                            // RECT BAR--------------------------------------
                            // let h = v_scale(after)
                            // State_G.append('rect').classed('state',true)
                            //     .attr('x',x_scale(cid+0.5)-r)
                            //     .attr('y',y_scale(used_variables.indexOf(v))-h*0.5)
                            //     .attr('width',r*2).attr('height',h)
                            //     .attr('fill',that.colorScheme['var'])
                            // circle version =============================================
                            if(after>before){
                                State_G.append('circle').classed('state',true)
                                    .attr('cx',x_scale(cid+0.5))
                                    .attr('cy',y_scale(used_variables.indexOf(v)))
                                    .attr('r',v_scale(after)+1)
                                    .attr('fill',that.colorScheme.p)  
                                if(before>0){
                                    State_G.append('circle').classed('state',true)
                                        .attr('cx',x_scale(cid+0.5))
                                        .attr('cy',y_scale(used_variables.indexOf(v)))
                                        .attr('r',v_scale(before))
                                        .attr('fill',that.colorScheme['var'])                                    
                                }

                            
                            }else{

                                State_G.append('circle').classed('state',true)
                                    .attr('cx',x_scale(cid+0.5))
                                    .attr('cy',y_scale(used_variables.indexOf(v)))
                                    .attr('r',v_scale(before)+1)
                                    .attr('fill',that.colorScheme.n)
                                if(after>0){
                                    State_G.append('circle').classed('state',true)
                                        .attr('cx',x_scale(cid+0.5))
                                        .attr('cy',y_scale(used_variables.indexOf(v)))
                                        .attr('r',v_scale(after))
                                        .attr('fill',that.colorScheme['var'])                                     
                                }
                            }
                            //==================================================================
                            type_mapping[v][3] = after //update last value
                        }else{ //there is no updates
                            let value = type_mapping[v][3]
                            State_G.append('circle').classed('state',true)
                                    .attr('cx',x_scale(cid+0.5))
                                    .attr('cy',y_scale(used_variables.indexOf(v)))
                                    .attr('r',v_scale(value))
                                    .attr('fill','white')
                                    .attr('stroke',that.colorScheme['var'])
                                    .attr('stroke-width',1)      

                            // rect version------------------------------------------
                            // let h = v_scale(value)
                            // State_G.append('rect').classed('state',true)
                            //     .attr('x',x_scale(cid+0.5)-r)
                            //     .attr('y',y_scale(used_variables.indexOf(v))-h*0.5)
                            //     .attr('width',r*2).attr('height',h)
                            //         .attr('fill','white')
                            //         .attr('stroke',that.colorScheme['var'])
                            //         .attr('stroke-width',1)      
                        }


                    }
                })
            })
        },
        drawFunc(svg,func_view){
            d3.select('g.func').remove()

            let that = this
            let Func_G = svg.append('g').classed('func',true)

            let funcNodes = this.functionnodes
            let funcLen = funcNodes.length

            let simu_obj = that.simu_objs[that.current_simu]
            let calls = simu_obj['calls']
            let callLen = simu_obj.callLen
            let addresses = simu_obj.addresses
            let addrLen = simu_obj.addrLen
            let maxtrans = simu_obj.maxtrans
            let maxTranVal = simu_obj.maxTranVal
            let r =that.r
            let x_scale = d3.scaleLinear().domain([-1,callLen]).range([func_view.left+20,func_view.right])
            let y_scale = d3.scaleLinear().domain([-1.5,addrLen]).range([func_view.top,func_view.bottom])
            let con_y = y_scale(-1)
            let x_gap = x_scale(1)-x_scale(0)
            let y_gap = y_scale(1)-y_scale(0)
            let text_size = that.text_size

            let width_scale = d3.scaleLinear().domain([0,maxTranVal]).range([1.5,x_gap/(maxtrans+5)])



            //for contract -------------------------------------------------------------------------------------------------------
            Func_G.append('text')
                    .attr('x',x_scale(0)-2*r).attr('y',con_y)
                    .attr('fill','black')
                    .attr('text-anchor','end').attr('dominant-baseline','middle')
                        .attr('font-family','Arial').attr('font-weight','bold')
                        .attr('font-size',text_size)
                .text('Contract')
            Func_G.append('line')
                .attr("x1",x_scale(0)).attr('x2',x_scale(callLen))
                .attr('y1',con_y).attr('y2',con_y)
                .attr('stroke',that.colorScheme.contline)
                .attr('stroke-width',1)
            Func_G.append('circle')
                .attr('cx',x_scale(0)-2)
                .attr('cy',con_y)
                .attr('r',2)
                .attr('fill',that.colorScheme.contline)
            Func_G.append('circle')
                .attr('cx',x_scale(callLen)+2)
                .attr('cy',con_y)
                .attr('r',2)
                .attr('fill',that.colorScheme.contline)
            //draw address
            for(let i=0;i<addrLen;i++){
                Func_G.append('text')
                    .attr('x',x_scale(0)-2*r).attr('y',y_scale(i))
                    .attr('fill','black')
                    .attr('text-anchor','end').attr('dominant-baseline','middle')
                        .attr('font-family','Arial').attr('font-weight',addresses[i]==this.owner?'bold':'normal')
                        .attr('font-size',text_size)
                .text(`Address ${addresses[i].slice(-5,-4)}`)
                Func_G.append('line')
                    .attr("x1",x_scale(0)-6).attr('x2',x_scale(callLen)+6)
                    .attr('y1',y_scale(i+0.1)).attr('y2',y_scale(i+0.1))
                    .attr('stroke',this.colorScheme.addrline)
                    .attr('stroke-width',1)
                Func_G.append('line')
                    .attr("x1",x_scale(0)-6).attr('x2',x_scale(callLen)+6)
                    .attr('y1',y_scale(i-0.1)).attr('y2',y_scale(i-0.1))
                    .attr('stroke',this.colorScheme.addrline)
                    .attr('stroke-width',1)
                if(i==addrLen-1){
                    Func_G.append('line')
                        .attr("x1",x_scale(0)-6).attr('x2',x_scale(callLen)+6)
                        .attr('y1',y_scale(i+1)).attr('y2',y_scale(i+1))
                        .attr('stroke',this.colorScheme.addrline)
                        .attr('stroke-width',1)
                    Func_G.append('text')
                            .attr('x',x_scale(0)-2*r).attr('y',y_scale(i+1))
                            .attr('fill','black')
                            .attr('text-anchor','end').attr('dominant-baseline','middle')
                                .attr('font-family','Arial').attr('font-weight','normal')
                                .attr('font-size',text_size)
                        .text(`Others`)
                }
            }
            //--------------------------------------------------------------------------------------------------------------------- 

             //draw function transactions------------------------------------------------------------------------------------
            calls.forEach((call,cid)=>{
                // console.log(call)
                let caller = call['caller']
                let internals = call['internals']
                let interLen = internals.length
                let call_tran = 0
                let tran_x = d3.scaleLinear().domain([-1,interLen-1]).range([x_scale(cid),x_scale(cid+1)])
                //draw payments to contracts
                let ether = parseInt(call['ether'],16)
                if(ether>0){
                    call_tran=1
                    tran_x = d3.scaleLinear().domain([-1,interLen]).range([x_scale(cid),x_scale(cid+1)])
                    let x1 = tran_x(-0.5)
                    let y =y_scale(addresses.indexOf(caller))
                    let y1 = y_scale(addresses.indexOf(caller)-0.1)
                    let y2 = con_y
                    let path_d = `M${x_scale(cid)} ${y1} 
                    C${x_scale(cid+1)} ${y1}, ${x_scale(cid)} ${y2}, ${x_scale(cid+1)} ${y2}`
                    if(interLen>0){
                        path_d = `M${x_scale(cid)} ${y1} 
                    C${x_scale(cid+0.5)} ${y1}, ${x_scale(cid)} ${y2}, ${x_scale(cid+0.5)} ${y2}`
                    }
                    Func_G.append('path')
                        .attr("d",path_d)
                        .attr('fill','none')
                        .attr('stroke',that.colorScheme.tran_out)
                        .attr('stroke-width',width_scale(ether))
                        // .attr('opacity',0.8)
                }
                //draw internal transactions

                if(interLen>0){
                    internals.forEach((tran,tid)=>{
                        let interValue = parseInt(tran['value'],16)
                        if(interValue>0){
                            let to = `0x00000000000000000000000000000000000${tran['to'].slice(2)}`
                            let x1 = tran_x(tid+call_tran-0.5)
                            let y1 = addresses.indexOf(to)==-1?y_scale(addrLen):y_scale(addresses.indexOf(to)-0.1)
                            // let y1 = y_scale(addresses.indexOf(to)-0.1)
                            let y2 = con_y
                            let path_d = `M${x_scale(cid+1)} ${y1} 
                            C${x_scale(cid)} ${y1}, ${x_scale(cid+1)} ${y2}, ${x_scale(cid)} ${y2}`
                            if(ether>0){
                                path_d = `M${x_scale(cid+1)} ${y1} 
                            C${x_scale(cid+0.5)} ${y1}, ${x_scale(cid+1)} ${y2}, ${x_scale(cid+0.5)} ${y2}`
                            }
                            // if(call['function']=='ownerWithdraw'){
                            //     Func_G.append('path')
                            //         .attr("d",path_d)
                            //         .attr('fill','none')
                            //         .attr('stroke',that.colorScheme.tran_in)
                            //         .attr('stroke-width',width_scale(interValue)*100)
                            // }}
                            // }else{
                            //     Func_G.append('path')
                            //         .attr("d",path_d)
                            //         .attr('fill','none')
                            //         .attr('stroke',that.colorScheme.tran_in)
                            //         .attr('stroke-width',width_scale(interValue)*5)
                            // }   
                            Func_G.append('path')
                                    .attr("d",path_d)
                                    .attr('fill','none')
                                    .attr('stroke',that.colorScheme.tran_in)
                                    .attr('stroke-width',width_scale(interValue))
                                    }   



                    })
                }
            })
            // --------------------------------------------------------------------------------------------

            //draw balances--------------------------------------------------------------------------------
            let balances = simu_obj.balances
            let maxVal = simu_obj.maxVal
            console.log(balances)

            Object.keys(balances).forEach(addr=>{
                let y
                let b_scale

                //new style
                let b_list = []
                let last_b= 0 
                let current_array = []
                // console.log(addr,balances[addr].length,balances[addr])
                balances[addr].forEach((b,bid)=>{
                    if(bid>0){
                        if(b>0&last_b<0 | b<0&last_b>0){
                            // console.log('bianhao',b,last_b)
                            b_list.push(current_array)
                            current_array=[[bid,b]]
                        }else{
                            current_array.push([bid,b])
                        }
                    }
                    last_b = b
                })
                b_list.push(current_array)

                let current_x = 0
                b_list.forEach((item,idx)=>{
                    let check = Math.max(...item.map(d=>d[1]))>0
                    if(check){
                        if(addr=='contract'){
                            y = con_y
                        }else{
                            y = y_scale(addresses.indexOf(addr)-0.1)
                        }
                        let local_b_scale = d3.scaleLinear().domain([maxVal,0]).range([y-0.4*y_gap,y])
                        let local_line = d3.line().x((d,i)=>x_scale(d[0])).y(d=>local_b_scale(d[1]))
                        let b_data = [[current_x,local_b_scale(0)],...item,[item[item.length-1][0]+1,local_b_scale(0)]]
                        if(idx==b_list.length-1){
                            b_data = [[current_x,local_b_scale(0)],...item,[item[item.length-1][0],local_b_scale(0)]]
                        }
                        Func_G.append('path')
                            .attr('d',local_line(b_data))
                            .attr('fill',that.colorScheme.balance_p)
                            .attr('opacity',0.7)
                    }else{
                        if(addr=='contract'){
                            y = con_y
                        }else{
                            y = y_scale(addresses.indexOf(addr)+0.1)
                        }
                        let local_b_scale = d3.scaleLinear().domain([maxVal,0]).range([y-0.4*y_gap,y])
                        let local_line = d3.line().x((d,i)=>x_scale(d[0])).y(d=>local_b_scale(d[1]))
                        let b_data = [[current_x,local_b_scale(0)],...item,[item[item.length-1][0]+1,local_b_scale(0)]]
                        if(idx==b_list.length-1){
                            b_data = [[current_x,local_b_scale(0)],...item,[item[item.length-1][0],local_b_scale(0)]]
                        }
                        Func_G.append('path')
                            .attr('d',local_line(b_data))
                            .attr('fill',that.colorScheme.balance_n)
                            .attr('opacity',0.7)
                    }
                    current_x = item[item.length-1][0]
                })
                
            })
            //-----------------------------------------------------------------------------------------------------------------------


            //draw function calls\
            let gap_scale = d3.scaleLinear().domain([y_gap,y_gap*addrLen]).range([0.6*x_gap,0.75*x_gap])
            calls.forEach((call,cid)=>{
                // console.log(call)
                let caller = call['caller']
                let functionName = call['function']

                let funcInfo = funcNodes.filter(item=>item['name']==functionName)
                let funcType ="nonpayable"
                if(funcInfo.length>0&&funcInfo[0]['payable']==true){
                    funcType = "payable"
                }
                Func_G.append('rect')
                        .attr('x',x_scale(cid)).attr('y',y_scale(addresses.indexOf(caller)-0.1))
                        .attr('width',x_gap*0.95)
                        .attr('height',0.2*y_gap)
                        .attr('fill',that.colorScheme[funcType])
            })
            //draw  link and triangle
            calls.forEach((call,cid)=>{
                let caller = call['caller']
                //draw payments to contracts
                let ether = parseInt(call['ether'],16)
                let tri_scale = x_gap/5>y_gap*0.1?y_gap*0.1:x_gap/5
                tri_scale = tri_scale*0.9
                let x1 = x_scale(cid+0.5)
                if(ether>0){
                    let y =y_scale(addresses.indexOf(caller)-0.08)
                    let triangle_d = `M${x1} ${y} l${-0.5*tri_scale} ${tri_scale} h${tri_scale}`
                    Func_G.append('path')
                        .attr('d',triangle_d)
                        .attr('fill','black')
                }
                //draw internal transactions
                let internals = call['internals']
                let interLen = internals.length
                if(interLen>0){
                    internals.forEach((tran,tid)=>{
                        let interValue = parseInt(tran['value'],16)
                        if(interValue>0){
                            let to = `0x00000000000000000000000000000000000${tran['to'].slice(2)}`
                            let y = addresses.indexOf(to)==-1?y_scale(addrLen):y_scale(addresses.indexOf(to))
                            //line
                            console.log(to,caller,to!=caller)
                            if(to!=caller){
                                console.log('here',addresses,addresses.indexOf(caller))
                                let y1 = y_scale(addresses.indexOf(caller))> y? y+0.1*y_gap:y_scale(addresses.indexOf(caller))+0.1*y_gap
                                let y2 = y_scale(addresses.indexOf(caller))< y? y-0.1*y_gap:y_scale(addresses.indexOf(caller))-0.1*y_gap
                                let len = Math.abs(y1-y2)-0.2*y_gap
                                let middle_y = (y1+y2)/2
                                let x = x_scale(cid+0.5)
                                let path_d = `M${x} ${y1} C${x+gap_scale(len)} ${middle_y-0.5*len}, ${x+gap_scale(len)} ${middle_y+0.5*len}, ${x} ${y2}`
                                Func_G.append('path')
                                    .attr('d',path_d)
                                    .attr('stroke','black')
                                    .attr("fill",'none')
                                    .attr('stroke-width',2)
                                    .attr('stroke-dasharray','3,2')

                            }
                            let triangle_d = `M${x1} ${y+0.08*y_gap} l${-0.5*tri_scale} ${-tri_scale} h${tri_scale}`
                            Func_G.append('path')
                                .attr('d',triangle_d)
                                .attr('fill','black')
                        }

                    })
                }
            })



        },
        dataInit(){
            let that = this
            console.log(that.AllSimuD)
            let simulations = that.AllSimuD
            let simuLen = simulations.length
            let simu_objs = []
            let funcNodes = this.functionnodes
            let varNodes = this.variablenodes
            simulations.forEach((simu_D,sid)=>{//for each simulation
                let calls = simu_D.filter(item=>item['reverted']==false) // filter out the reverted trans
                let callLen = calls.length
                let addresses =  [...new Set([this.owner,...calls.map(item=>item['caller'])])]
                let addrLen = addresses.length
                // console.log('new',callLen,addrLen)
                //set the initial value with 0
                let balances = {
                        "contract":[0]
                    }
                addresses.forEach(addr=>{
                        balances[addr]=[0]
                    })
                let maxTranVal = 0  //the max value sent to the contract
                let maxtrans = 0 //the number of transactions (max) in the function call
                let used_variables = []
                //for each function call
                calls.forEach((call,cid)=>{
                    Object.keys(balances).forEach(key=>{
                        balances[key]= [...balances[key],balances[key][cid]]
                    })
                    let ether = parseInt(call['ether'],16)
                    maxTranVal = ether>maxTranVal?ether:maxTranVal
                    if(ether>0){
                        let from = call['caller']
                        balances['contract'][cid+1] = balances['contract'][cid+1]+ether
                        balances[from][cid+1] = balances[from][cid+1]-ether
                    }
                    let internals = call['internals']
                    let interLen = internals.length
                    if(interLen>0){
                        maxtrans = maxtrans>interLen+1?maxtrans:interLen+1
                        internals.forEach(tran=>{
                            let value = parseInt(tran['value'],16)
                            if(value>0){
                                balances['contract'][cid+1] = balances['contract'][cid+1]-value
                                let to = `0x00000000000000000000000000000000000${tran['to'].slice(2)}`
                                maxTranVal = value>maxTranVal?value:maxTranVal
                                if(addresses.indexOf(to)>-1){
                                    balances[to][cid+1] = balances[to][cid+1]+value
                                }
                            }
                        })
                    }
                    //variables state
                    used_variables = [...used_variables,...call['updated']]
                })
                //function summary---------------------------------------------------------------
                let called_functions = [...new Set([...calls.map(item=>item['function'])])]
                let func_list = []
                called_functions.forEach((cf,fid)=>{
                    let  func = funcNodes.filter(item=>item['name']==cf)
                    let  groups = calls.filter(f=>f['function']==cf)
                    let call_number = groups.length
                    if(call_number>0){
                        let map = calls.map((f,fid)=>f['function']==cf?fid:-1)
                        let payable = func.length>0?func[0]['payable']:false
                        let ether_number = groups.filter(f=>parseInt(f.ether,16)>0).length
                        let inter_number = groups.filter(f=>f['internals'].length>0).length
                        let call_back = groups.filter(f=>f['internals'].length>0&&f['internals'].filter(i=>`0x00000000000000000000000000000000000${i['to'].slice(2)}`==f['caller']).length>0).length
                        let call_out = groups.filter(f=>f['internals'].length>0&&f['internals'].filter(i=>`0x00000000000000000000000000000000000${i['to'].slice(2)}`!=f['caller']).length>0).length
                        func_list.push([cf,call_number,ether_number,inter_number,payable,call_back,call_out,map])
                        // console.log(cf,call_number,ether_number,inter_number,payable,call_back,call_out,map)
                    }
                })

                let maxVal = Math.max(...Object.values(balances).map(item=>Math.max(...item.map(i=>Math.abs(i)))))
                let simu_obj = {
                    sid,
                    calls,
                    callLen,
                    addresses,
                    addrLen,
                    balances,
                    maxtrans,
                    maxTranVal,
                    maxVal,
                    used_variables:[...new Set(used_variables)].filter(v=>varNodes.filter(item=>item['name']==v)[0]),
                    func_list:func_list.sort((a,b)=>b[1]-a[1])
                }
                // console.log(simu_obj)
                simu_objs.push(simu_obj)
            })
            that.simu_objs = simu_objs.sort((a,b)=>b.callLen-a.callLen)
        },
    },
    created(){
    },
    beforeMount(){
        this.dataInit()
    },
    mounted(){
        window.addEventListener("resize",this.setSvg);
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