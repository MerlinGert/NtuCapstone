<template>
    <div style="height:100%;width:100%;background:#ffffff;display:flex;flex-direction:column">
        <div style="padding: 10px; display: flex; gap: 10px; align-items: center;">
            <span>Select Holder:</span>
            <n-select 
                v-model:value="selectedOwner" 
                :options="ownerOptions" 
                placeholder="Select a holder"
                style="width: 300px"
                filterable
            />
        </div>
        <div style="flex:1;position:relative" ref="holder_container">
            <svg class="holderView"></svg>             
        </div>
    </div>
</template>

<script>
import * as d3 from "d3"
import { NSelect } from "naive-ui"

export default {
    name:"holderView",
    components: { NSelect },
    props:['data','functionnodes','variablenodes','simulationData'],
    data(){
        return {
            svgHeight: 0,
            svgWidth: 0,
            margin:{left:60,right:50,top:20,bottom:30},
            allData: {},
            selectedOwner: null,
            ownerOptions: []
        }
    },
    watch: {
        selectedOwner(newVal) {
            if (newVal) {
                this.drawChart(newVal)
            }
        }
    },
    methods:{
        setSvg(){
            if(this.$refs.holder_container && this.$refs.holder_container.offsetHeight){
                this.svgHeight = this.$refs.holder_container.offsetHeight;                
                this.svgWidth = this.$refs.holder_container.offsetWidth;
            }
            if (this.selectedOwner) {
                this.drawChart(this.selectedOwner)
            }
        },
        async loadData() {
            try {
                const response = await fetch('/processed/transfers/top_holders_history.json');
                this.allData = await response.json();
                
                // Prepare options for select
                this.ownerOptions = Object.keys(this.allData).map(owner => {
                    const balance = this.allData[owner].ACT?.balance || 0;
                    return {
                        label: `${owner.slice(0, 6)}...${owner.slice(-4)} (Bal: ${balance.toFixed(0)})`,
                        value: owner
                    }
                });
                
                // Select first owner by default
                if (this.ownerOptions.length > 0) {
                    this.selectedOwner = this.ownerOptions[0].value;
                }
            } catch (error) {
                console.error("Failed to load holder history:", error);
            }
        },
        drawChart(owner){
            if (!this.allData[owner] || !this.allData[owner].ACT) return;
            
            const history = this.allData[owner].ACT.history;
            if (!history || history.length === 0) return;

            // Parse dates and values
            const parseTime = d3.timeParse("%Y-%m-%d %H:%M:%S.%L UTC");
            // If parse fails, try ISO format or just use the string if it works with new Date()
            // The python script output format: "2024-10-29 09:58:07.000 UTC"
            // We can replace " UTC" with "Z" or just parse it.
            
            const data = history.map(d => {
                // Remove " UTC" and replace space with T if needed, or just handle manually
                // Simple approach:
                let timeStr = d.time.replace(" UTC", "Z").replace(" ", "T");
                return {
                    date: new Date(timeStr),
                    value: d.balance_after,
                    change: d.change,
                    reason: d.reason,
                    context: d.context
                };
            }).sort((a, b) => a.date - b.date);

            // Setup SVG
            const svg = d3.select("svg.holderView");
            svg.selectAll("*").remove();
            
            svg.attr("width", this.svgWidth)
               .attr("height", this.svgHeight);

            const width = this.svgWidth - this.margin.left - this.margin.right;
            const height = this.svgHeight - this.margin.top - this.margin.bottom;

            const g = svg.append("g")
                .attr("transform", `translate(${this.margin.left},${this.margin.top})`);

            // Scales
            const x = d3.scaleTime()
                .domain(d3.extent(data, d => d.date))
                .range([0, width]);

            const y = d3.scaleLinear()
                .domain([0, d3.max(data, d => d.value) * 1.1])
                .range([height, 0]);

            // Axes
            g.append("g")
                .attr("transform", `translate(0,${height})`)
                .call(d3.axisBottom(x));

            g.append("g")
                .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(".2s")));

            // Line
            const line = d3.line()
                .x(d => x(d.date))
                .y(d => y(d.value))
                .curve(d3.curveStepAfter); // Step chart makes sense for balance changes

            g.append("path")
                .datum(data)
                .attr("fill", "none")
                .attr("stroke", "#4a90e2")
                .attr("stroke-width", 1.5)
                .attr("d", line);

            // Area fill under line
            const area = d3.area()
                .x(d => x(d.date))
                .y0(height)
                .y1(d => y(d.value))
                .curve(d3.curveStepAfter);

            g.insert("path", ":first-child")
                .datum(data)
                .attr("fill", "#4a90e2")
                .attr("fill-opacity", 0.1)
                .attr("d", area);
                
            // Add tooltip logic (simple circle on hover)
            const focus = g.append("g")
                .attr("class", "focus")
                .style("display", "none");

            focus.append("circle")
                .attr("r", 5);

            focus.append("rect")
                .attr("class", "tooltip-bg")
                .attr("width", 200)
                .attr("height", 60)
                .attr("x", 10)
                .attr("y", -30)
                .attr("rx", 4)
                .attr("ry", 4)
                .attr("fill", "white")
                .attr("stroke", "#ccc");

            const tooltipText = focus.append("text")
                .attr("x", 18)
                .attr("y", -10);
                
            const tooltipLine1 = tooltipText.append("tspan")
                .attr("x", 18)
                .attr("dy", "0em")
                .style("font-weight", "bold");
                
            const tooltipLine2 = tooltipText.append("tspan")
                .attr("x", 18)
                .attr("dy", "1.2em");
                
            const tooltipLine3 = tooltipText.append("tspan")
                .attr("x", 18)
                .attr("dy", "1.2em");

            svg.append("rect")
                .attr("class", "overlay")
                .attr("width", width)
                .attr("height", height)
                .attr("transform", `translate(${this.margin.left},${this.margin.top})`)
                .style("opacity", 0)
                .on("mouseover", () => focus.style("display", null))
                .on("mouseout", () => focus.style("display", "none"))
                .on("mousemove", mousemove);

            const bisectDate = d3.bisector(d => d.date).left;

            function mousemove(event) {
                const x0 = x.invert(d3.pointer(event)[0]);
                const i = bisectDate(data, x0, 1);
                const d0 = data[i - 1];
                const d1 = data[i];
                if (!d0) return;
                const d = d1 && (x0 - d0.date > d1.date - x0) ? d1 : d0;
                
                focus.attr("transform", `translate(${x(d.date)},${y(d.value)})`);
                tooltipLine1.text(`Date: ${d.date.toLocaleString()}`);
                tooltipLine2.text(`Bal: ${d.value.toFixed(2)}`);
                tooltipLine3.text(`Change: ${d.change > 0 ? '+' : ''}${d.change.toFixed(2)} (${d.context})`);
            }
        },

    },
    mounted(){
        this.setSvg();
        window.addEventListener("resize", this.setSvg);
        this.loadData();
    },
    unmounted(){
        window.removeEventListener("resize",this.setSvg)
    }
}
</script>

<style>
.holderView {
    width: 100%;
    height: 100%;
}
</style>