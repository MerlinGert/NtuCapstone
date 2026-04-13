<template>
<n-layout class="h-screen max-h-screen" :content-style="{ display: 'flex', flexDirection: 'column'}">
  <n-layout-header>
      <div class="techname font-bold" style="display: flex; align-items: center; justify-content: space-between; padding-right: 20px;">
        <span style="padding-left: 20px;">ManiScope</span>
        <div style="font-size: 14px; font-weight: normal; display: flex; align-items: center; gap: 10px; z-index: 1000;">
          <span style="color: #4a5568;">Coin:</span>
          <div style="display: flex; gap: 5px;">
            <label style="cursor: pointer; display: flex; align-items: center; gap: 4px;">
              <input type="radio" v-model="currentCoin" value="ACT" @change="handleCoinChange" /> ACT
            </label>
            <label style="cursor: pointer; display: flex; align-items: center; gap: 4px; margin-left: 10px;">
              <input type="radio" v-model="currentCoin" value="PNUT" @change="handleCoinChange" /> PNUT
            </label>
          </div>
        </div>
      </div>
  </n-layout-header>
<n-layout-content class="flex-1" style="width:100%;height:100%" >
  <n-layout
        style="width:100%;height:100%;overflow:hidden"
        :content-style="{ display: 'flex', flexDirection: 'row', overflow: 'hidden', width: '100%', height: '100%', boxSizing: 'border-box' }"
      >
<div style="flex: 3; min-width:0; overflow:hidden;">
        <n-card
            size="small"
            style="width:100%;height:100%;"
            class="panel-card"
            header-style="text-align:left;height:50px;font-size:1.4em;"
            :content-style="{ padding: 0, height: 'calc(100% - 50px)', overflow: 'hidden' }"
        >
            <ControlPanel 
                :key="`control-panel-${currentCoin}`"
                :loading="detecting"
                :loadingLinks="detectingLinks"
                :loadingManipulation="detectingManipulation"
                :lastResultCount="lastDetectionCount"
                :snapshotConfig="snapshot_configuration"
                :snapshotTimes="snapshotTimes"
                :entityConfig="entity_detection_configuration"
                :linkConfig="link_detection_configuration"
                :manipulationConfig="manipulation_detection_configuration"
                @run-detection="handleRunDetection"
                @update-snapshot="handleUpdateSnapshot"
                @request-manipulation-detection="handleRequestManipulationDetection"
                @update-links="handleUpdateLinks"
                @log-action="logUserAction"
            />
        </n-card>
    </div>

<div style="flex: 6; min-width:0; display: flex; flex-direction: column; height: 100%; overflow: hidden;">
        <n-card
            size="small"
            class="panel-card"
            style="width:100%;height:60%;flex-shrink:0; margin-bottom: 5px;"
            header-style="text-align:left;height:50px;font-size:1.4em;"
            :content-style="{ padding: 0, height: 'calc(100% - 50px)', overflow: 'hidden' }"
        >
            <TokenDistribution ref="tokenDistribution"
                :snapshot-data="snapshot_data"
                :entity-detection-results="entity_detection_results"
                :link-detection-results="link_generation_results"
                :manipulation-detection-results="manipulation_detection_results"
                @detection-complete="handleDetectionComplete"
                @user-selected="handleUserSelect"
                @log-action="logUserAction"
                @snapshot-input="handleSnapshotAnnotation('token_distribution', $event)"
            />
        </n-card>
        
        <!-- ezio: tab-switched panel for User Actions / Annotations -->
        <div class="bottom-tab-panel" style="width:100%;height:40%;flex-shrink:0; display:flex; flex-direction:column; border:1px solid #efeff5; border-radius:3px; background:#fff;">
          <div class="tab-header" style="flex-shrink:0; display:flex; border-bottom:1px solid #eef2f7; background:#f8fafc;">
            <button
              class="tab-btn"
              :class="{ active: activeBottomTab === 'actions' }"
              @click="activeBottomTab = 'actions'"
              style="flex:1; padding:6px 0; border:none; background:none; cursor:pointer; font-size:12px; font-weight:600; color:#718096; border-bottom:2px solid transparent; transition: all 0.2s;"
              :style="activeBottomTab === 'actions' ? 'color:#3182ce; border-bottom-color:#3182ce; background:#fff;' : ''"
            >User Actions</button>
            <button
              class="tab-btn"
              :class="{ active: activeBottomTab === 'annotations' }"
              @click="activeBottomTab = 'annotations'"
              style="flex:1; padding:6px 0; border:none; background:none; cursor:pointer; font-size:12px; font-weight:600; color:#718096; border-bottom:2px solid transparent; transition: all 0.2s;"
              :style="activeBottomTab === 'annotations' ? 'color:#d97706; border-bottom-color:#d97706; background:#fff;' : ''"
            >Annotations</button>
          </div>
          <div style="flex:1; height:0; min-height:0; overflow:hidden;">
            <UserActionTimeline
                v-show="activeBottomTab === 'actions'"
                :actions="userActionSequence"
                style="height:100%;"
            />
            <AnnotationTimeline
                v-show="activeBottomTab === 'annotations'"
                :annotations="annotationRecords"
                style="height:100%;"
            />
          </div>
        </div>
    </div>


    <div style="flex: 9; min-width:0; display: flex; flex-direction: column; height: 100%; overflow: hidden; margin-left: 5px;">
        <n-card
          size="small"
          class="panel-card"
          style="width:100%;height:60%;flex-shrink:0; margin-bottom: 5px;"
          header-style="text-align:left;height:50px;font-size:1.4em;"
          :content-style="{ padding: 0, height: 'calc(100% - 50px)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }"
        >

          <div style="flex:1; border-top:1px solid #eef2f7; border-bottom:1px solid #eef2f7; display:flex; flex-direction:column; overflow:hidden; background:#fff;">
            <div style="width:100%; height:100%; min-height:0; overflow:hidden;">
              <CandlestickChart 
                :manipulation-results="manipulation_detection_results"
                :selected-user="selectedUser"
                :entity-info="selectedEntityInfo"
                :current-coin="currentCoin"
                :sync-target-time-window="behaviorTimeWindow"
                @time-window-changed="handleKlineTimeWindowChanged"
                @card-click="handleManipulationCardClick"
                @log-action="logUserAction"
                @snapshot-input="handleSnapshotAnnotation('candlestick_chart', $event)"
                style="width:100%;height:100%;"
              />
            </div>
          </div>


        </n-card>
        <n-card
            size="small"
            class="panel-card"
            style="width:100%;height:40%;flex-shrink:0;"
            header-style="text-align:left;height:50px;font-size:1.4em;"
            :content-style="{ padding: 0, height: 'calc(100% - 50px)', overflow: 'hidden' }"
        >
            <template #header-extra v-if="selectedUser">
                <div style="display: flex; flex-direction: row; flex-wrap: nowrap; gap: 15px; font-size: 14px; color: #4a5568; align-items: center; margin-right: 10px; white-space: nowrap;">
                    <span style="background: #f7fafc; padding: 2px 8px; border-radius: 4px; border: 1px solid #e2e8f0; display: inline-block;">
                        <strong>User:</strong> {{ selectedUser.length > 8 ? selectedUser.substring(0, 8) + '..' : selectedUser }}
                    </span>
                </div>
            </template>
            <BehaviorDetails
                ref="behaviorDetails"
                :selected-user="selectedUser"
                :selected-users-list="selectedCardUsers"
                :behavior-data="behaviorDetailData"
                :entity-info="selectedEntityInfo"
                :snapshot-time="snapshot_configuration.time"
                :manipulation-results="manipulation_detection_results"
                :sync-target-time-window="klineTimeWindow"
                @time-window-changed="handleBehaviorTimeWindowChanged"
                @user-selected="handleBehaviorDetailUserSelect"
                @log-action="logUserAction"
                @snapshot-input="handleSnapshotAnnotation('behavior_details', $event)"
            />
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
import {
  NCard,
  NCheckbox,
  NLayout,
  NLayoutContent,
  NLayoutFooter,
  NLayoutHeader,
  NSelect,
  NSpace,
  NSwitch,
} from 'naive-ui'
import BehaviorDetails from './BehaviorDetails.vue'
import CandlestickChart from './CandlestickChart.vue'
import ControlPanel from './ControlPanel.vue'
import TokenDistribution from './TokenDistribution.vue'
import UserActionTimeline from './UserActionTimeline.vue'
// ezio: import AnnotationTimeline for snapshot annotation display
import AnnotationTimeline from './AnnotationTimeline.vue'

export default {
  components: {
    NSelect,
    NCheckbox,
    NCard,
    NLayout,
    NSwitch,
    NSpace,
    NLayoutHeader,
    NLayoutFooter,
    NLayoutContent,
    TokenDistribution,
    ControlPanel,
    CandlestickChart,
    BehaviorDetails,
    UserActionTimeline,
    AnnotationTimeline,
  },
  data() {
    return {
      currentCoin: 'ACT', // Can be 'ACT' or 'PNUT'
      //new params
      //snapshot configuration
      snapshot_configuration: {
        time: '2024-11-09 23:00:00 UTC', //current snapshot time
        top_holder_threshold: 0.3, //current top holder threshold
        related_user_threshold: 0.2, //current related user threshold
      },
      snapshotTimes: [],
      snapshot_data: {}, //current snapshot data

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
            type: 'action_amount_price', //action_only, action_amount, action_price, action_amount_price
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
            type: 'action_only', //action_only, action_amount, action_price, action_amount_price
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
        enable_manipulation_based: true,
        manipulation_based_params: {
          max_manipulation_time_diff: 120, //max time difference between the first and last manipulation actions in the sequence
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
      detecting: false,
      detectingLinks: false,
      detectingManipulation: false,
      lastDetectionCount: null,
      overview: {
        rows: 0,
        pairs: new Set(),
        dateSet: new Set(),
        dateMin: '',
        dateMax: '',
        topPairs: [],
      },
      loading: false,
      isPartial: false,
      selectedUser: null,
      behaviorDetailData: null,
      selectedEntityInfo: null,
      klineTimeWindow: null,
      behaviorTimeWindow: null,
      selectedCardUsers: [],
      userActionSequence: [], // Array to store user actions
      hoverTimers: {}, // Store timers for delayed hover logging
      isZooming: false, // Track if a zoom operation is actively happening
      zoomEndTimer: null, // Timer to clear the zooming state
      // ezio: annotation recording state
      annotationRecords: [], // Array to store snapshot annotations
      activeBottomTab: 'actions', // 'actions' | 'annotations'
      _annotationSeqId: 0, // auto-increment ID for annotations
    }
  },
  watch: {
    selectedUser(newVal) {
      if (newVal) {
        this.generateBehaviorDetailData()
      } else {
        this.behaviorDetailData = null
        this.selectedEntityInfo = null
      }
    },
  },
  methods: {
    // ezio: handle annotation submission from snapshot modals
    handleSnapshotAnnotation(sourceView, payload) {
      const record = {
        id: this._annotationSeqId++,
        timestamp: new Date().toISOString(),
        sourceView,
        text: payload.text || '',
        selectedItems: payload.selectedItems || payload.selectedIds || [],
        sketchDataUrl: payload.sketchDataUrl || null,
      }
      this.annotationRecords.push(record)
      // ezio: auto-switch to annotations tab when a new annotation arrives
      this.activeBottomTab = 'annotations'
    },

    logUserAction(actionType, actionInfo = {}, userId = null) {
      // Mark as zooming when a zoom action starts to suppress hovers
      if (actionType === 'zoom_kline_chart' || actionType === 'zoom_behavior_chart') {
        this.isZooming = true;
        if (this.zoomEndTimer) {
          clearTimeout(this.zoomEndTimer);
        }
        // Assume zooming is finished if no new zoom event arrives for 500ms
        this.zoomEndTimer = setTimeout(() => {
          this.isZooming = false;
        }, 500);
      }

      // For hover actions, implement a delay to avoid recording accidental fast fly-overs
      // Also, if the user is currently zooming (or recently zoomed), ignore hovers to prevent zoom misclicks
      if (actionType.startsWith('hover_')) {
        if (this.isZooming) {
          return; // Ignore hovers entirely during zoom operations
        }

        // Clear any existing timer for this specific hover type
        if (this.hoverTimers[actionType]) {
          clearTimeout(this.hoverTimers[actionType])
        }
        
        // We capture the timestamp at the moment the hover started
        const hoverStartTime = new Date().toISOString()
        
        // Set a new timer. Only log if the user hovers for more than 500ms
        this.hoverTimers[actionType] = setTimeout(() => {
          // Double check zooming state just in case it started while we were waiting
          if (!this.isZooming) {
            this._executeLogAction(actionType, actionInfo, userId, hoverStartTime)
          }
        }, 500)
        
        return; // Exit early, the actual logging happens in the timeout
      }
      
      // For non-hover actions, execute immediately
      this._executeLogAction(actionType, actionInfo, userId)
    },
    
    _executeLogAction(actionType, actionInfo = {}, userId = null, customTimestamp = null) {
      const currentTimestamp = customTimestamp || new Date().toISOString()
      
      // If it's a zoom action or hover action, try to merge with the previous action if it's also the same type
      // and occurred recently (e.g., within 2 seconds for zoom, 3 seconds for hover)
      if (actionType === 'zoom_kline_chart' || actionType === 'zoom_behavior_chart' || actionType.startsWith('hover_')) {
        const lastAction = this.userActionSequence[this.userActionSequence.length - 1]
        
        if (lastAction && lastAction.actionType === actionType) {
          const lastTime = new Date(lastAction.timestamp).getTime()
          const currentTime = new Date(currentTimestamp).getTime()
          
          const timeLimit = actionType.startsWith('hover_') ? 3000 : 2000;
          
          if (currentTime - lastTime < timeLimit) {
            // Merge by accumulating the action's info and updating timestamp instead of pushing a new one
            lastAction.timestamp = currentTimestamp
            
            // Convert actionInfo to an array to store continuous intermediate steps if it isn't already
            if (!Array.isArray(lastAction.actionInfo)) {
              lastAction.actionInfo = [lastAction.actionInfo]
            }
            lastAction.actionInfo.push({
              time: currentTimestamp,
              data: actionInfo
            })
            
            // Update the view state as well
            lastAction.relatedViewWithViewState.klineTimeWindow = this.klineTimeWindow
            lastAction.relatedViewWithViewState.behaviorTimeWindow = this.behaviorTimeWindow
            return
          }
        }
      }
      
      // Determine the current view state
      const currentViewState = {
        coin: this.currentCoin,
        snapshotTime: this.snapshot_configuration.time,
        selectedUser: this.selectedUser,
        selectedCardUsers: this.selectedCardUsers,
        klineTimeWindow: this.klineTimeWindow,
        behaviorTimeWindow: this.behaviorTimeWindow,
        hasEntityResults: !!(this.entity_detection_results && this.entity_detection_results.length > 0),
        hasManipulationResults: !!(this.manipulation_detection_results && this.manipulation_detection_results.length > 0)
      }

      // Record the effect of the action
      // For cross-component interactions, check actionType or actionInfo for source and target
      let sourceView = 'system';
      let targetView = 'system';
      
      // Infer source and target views based on action types
      if (actionType.includes('kline_chart') || actionType === 'click_manipulation_card' || actionType === 'hover_manipulation_card') {
        sourceView = 'kline_chart';
        targetView = actionType.includes('zoom') ? 'kline_chart' : (actionType.includes('click') ? 'behavior_details' : 'kline_chart');
      } else if (actionType.includes('behavior_chart') || actionType.includes('behavior_user_label') || actionType.includes('behavior_manipulation_box') || actionType.includes('toggle_show')) {
        sourceView = 'behavior_details';
        targetView = 'behavior_details';
      } else if (actionType.includes('token_distribution') || actionType === 'select_user_from_network') {
        sourceView = 'token_distribution';
        targetView = actionType.includes('select') ? 'behavior_details' : 'token_distribution';
      } else if (actionType.includes('snapshot') || actionType.includes('detection')) {
        sourceView = 'control_panel';
        targetView = 'all_views';
      } else if (actionType === 'change_coin') {
        sourceView = 'header_panel';
        targetView = 'all_views';
      } else if (actionType === 'sync_time_window') {
        sourceView = actionInfo.source;
        targetView = actionInfo.source === 'kline_chart' ? 'behavior_details' : 'kline_chart';
      }

      const actionRecord = {
        timestamp: currentTimestamp,
        userId: userId || this.selectedUser || 'system',
        actionType: actionType,
        sourceView: sourceView,
        targetView: targetView,
        actionInfo: actionInfo,
        relatedViewWithViewState: currentViewState,
        actionEffect: `Triggered ${actionType}`
      }

      this.userActionSequence.push(actionRecord)
      console.log('User Action Logged:', actionRecord)
      
      // Optional: Send to backend
      // fetch('/api/log_action', { method: 'POST', body: JSON.stringify(actionRecord) })
    },
    resetViewState() {
      this.selectedUser = null
      this.selectedCardUsers = []
      this.behaviorDetailData = null
      this.selectedEntityInfo = null
      this.entity_detection_results = null
      this.link_generation_results = null
      this.manipulation_detection_results = null
      this.snapshot_data = {}
      this.overview = {
        rows: 0,
        pairs: new Set(),
        dateSet: new Set(),
        dateMin: '',
        dateMax: '',
        topPairs: [],
      }
    },
    async loadSnapshotTimesForCurrentCoin() {
      const response = await fetch(
        `/api/snapshot/times?coin=${encodeURIComponent(this.currentCoin)}`,
      )
      if (!response.ok) throw new Error('Failed to fetch snapshot times')
      const data = await response.json()
      const times = Array.isArray(data.times) ? data.times : []
      this.snapshotTimes = times

      if (times.length > 0) {
        // 每次切换币种重新加载时间时，强制选中最新（最后一个）时间
        this.snapshot_configuration.time = times[times.length - 1]
      } else {
        this.snapshot_configuration.time = ''
      }
    },
    async initializeForCurrentCoin() {
      await this.loadSnapshotTimesForCurrentCoin()
      await this.handleUpdateSnapshot({ ...this.snapshot_configuration })
    },
    generateBehaviorDetailData() {
      if (!this.selectedUser) return
      const userSet = new Set([this.selectedUser])
      this.selectedEntityInfo = null

      // Expand via entity results
      if (this.entity_detection_results) {
        const targetEntity = this.entity_detection_results.find((entity) =>
          entity.users?.includes(this.selectedUser),
        )
        if (targetEntity?.users) {
          this.selectedEntityInfo = targetEntity
          targetEntity.users.forEach((member) => {
            userSet.add(member)
          })
        }
      }

      // Expand via link results
      if (this.link_generation_results) {
        const mapsToCheck = [
          this.link_generation_results.target_relations_for_links,
          this.link_generation_results.target_related_relations_for_links,
        ]
        mapsToCheck.forEach((map) => {
          if (map) {
            Object.keys(map).forEach((key) => {
              const [u1, u2] = key.split('-')
              if (u1 === this.selectedUser) userSet.add(u2)
              if (u2 === this.selectedUser) userSet.add(u1)
            })
          }
        })
      }

      // Fetch behavior sequences
      fetch('/api/user_behavior/sequences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          users: Array.from(userSet),
          coin: this.currentCoin,
        }),
      })
        .then((res) => {
          if (!res.ok) throw new Error('Network response was not ok')
          return res.json()
        })
        .then((sequences) => {
          const data = {}
          Array.from(userSet).forEach((user) => {
            data[user] = sequences[user] || []
          })
          // Use Object.freeze to prevent Vue from making this massive dataset deeply reactive
          // Deep reactivity on 70,000+ objects freezes the main thread.
          this.behaviorDetailData = Object.freeze(data)
          console.log(
            'CryptoVis: behaviorDetailData generated for users',
            userSet,
            this.behaviorDetailData,
          )
        })
        .catch((err) => {
          console.error(
            'CryptoVis: failed to fetch user behavior sequences',
            err,
          )
        })
    },
    handleKlineTimeWindowChanged(event) {
      this.klineTimeWindow = event
      this.logUserAction('zoom_kline_chart', { timeWindow: event }, this.selectedUser)
    },
    handleBehaviorTimeWindowChanged(event) {
      this.behaviorTimeWindow = event
      this.logUserAction('zoom_behavior_chart', { timeWindow: event }, this.selectedUser)
    },
    async handleCoinChange() {
      console.log('CryptoVis: coin changed to', this.currentCoin)
      this.logUserAction('change_coin', { coin: this.currentCoin })
      this.resetViewState()
      try {
        // 强制清空一下旧的时间列表，让它有重置的感觉
        this.snapshotTimes = []
        await this.initializeForCurrentCoin()
      } catch (error) {
        console.error('CryptoVis: Error switching coin:', error)
      }
    },
    handleUserSelect(userId) {
      this.selectedCardUsers = [] // clear card mode
      this.selectedUser = userId
      console.log('CryptoVis: selectedUser updated to', userId)
      this.logUserAction('select_user_from_network', { targetUserId: userId }, userId)
    },
    handleBehaviorDetailUserSelect(userId) {
      this.selectedCardUsers = [] // clear card mode
      this.selectedUser = userId
      
      // Call a method on the ref to disable 'Show Related Users' if it exists
      // But we don't have a ref. We can pass it as a prop or rely on the component's reactivity
      // Actually, when selectedUser changes, BehaviorDetails will redraw.
      // If we want to force 'showRelatedUsers' to false, we can either:
      // 1. Give BehaviorDetails a ref and call a method
      // 2. Add a key to force re-render (bad for performance)
      // Let's add a ref to BehaviorDetails and set the property directly
      if (this.$refs.behaviorDetails) {
        this.$refs.behaviorDetails.showRelatedUsers = false;
        // The drawChart method will be called via watch on selectedUser
      }
      
      console.log('CryptoVis: BehaviorDetails user selected, updated to', userId)
      this.logUserAction('select_user_from_behavior_details', { targetUserId: userId }, userId)
    },
    handleManipulationCardClick(users) {
      this.selectedUser = null
      this.selectedEntityInfo = null // clear entity info when card is clicked
      this.selectedCardUsers = users || []
      
      this.logUserAction('click_manipulation_card', { cardUsers: users })
      
      if (this.selectedCardUsers.length > 0) {
        const userSet = new Set(this.selectedCardUsers)
        
        fetch('/api/user_behavior/sequences', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            users: Array.from(userSet),
            coin: this.currentCoin,
          }),
        })
          .then((res) => {
            if (!res.ok) throw new Error('Network response was not ok')
            return res.json()
          })
          .then((sequences) => {
            const data = {}
            Array.from(userSet).forEach((user) => {
              data[user] = sequences[user] || []
            })
            this.behaviorDetailData = Object.freeze(data)
            console.log(
              'CryptoVis: behaviorDetailData generated for card users',
              userSet,
              this.behaviorDetailData,
            )
          })
          .catch((err) => {
            console.error(
              'CryptoVis: failed to fetch card user behavior sequences',
              err,
            )
          })
      } else {
        this.behaviorDetailData = null
      }
    },
    rebuildEntityResults() {
      if (!this.link_generation_results) return

      const tt = this.link_generation_results.target_relations_for_entity || {}
      const tr =
        this.link_generation_results.target_related_relations_for_entity || {}

      const adj = {}
      const addEdge = (u, v, rels) => {
        if (!adj[u]) adj[u] = []
        if (!adj[v]) adj[v] = []
        adj[u].push({ neighbor: v, rels })
        adj[v].push({ neighbor: u, rels })
      }

      const processMap = (map) => {
        Object.keys(map).forEach((key) => {
          const parts = key.split('-')
          if (parts.length >= 2) {
            addEdge(parts[0], parts[1], map[key])
          }
        })
      }

      processMap(tt)
      processMap(tr)

      const visited = new Set()
      const entities = []

      Object.keys(adj).forEach((user) => {
        if (!visited.has(user)) {
          const componentUsers = new Set()
          const queue = [user]
          visited.add(user)
          componentUsers.add(user)

          while (queue.length > 0) {
            const curr = queue.shift()
            if (adj[curr]) {
              adj[curr].forEach((edge) => {
                if (!visited.has(edge.neighbor)) {
                  visited.add(edge.neighbor)
                  componentUsers.add(edge.neighbor)
                  queue.push(edge.neighbor)
                }
              })
            }
          }

          // Collect unique relations for this component
          const compRels = []
          const processedKeys = new Set()
          let hasNonManipulationRels = false

          const checkMap = (map) => {
            Object.keys(map).forEach((key) => {
              if (processedKeys.has(key)) return
              const parts = key.split('-')
              if (parts.length >= 2) {
                if (
                  componentUsers.has(parts[0]) &&
                  componentUsers.has(parts[1])
                ) {
                  map[key].forEach((rel) => {
                    compRels.push(rel)
                    if (
                      rel.type !== 'manipulation_same_group' &&
                      rel.type !== 'manipulation_time_proximity'
                    ) {
                      hasNonManipulationRels = true
                    }
                  })
                  processedKeys.add(key)
                }
              }
            })
          }

          checkMap(tt)
          checkMap(tr)

          // Only create an entity if it has at least one real (non-manipulation) relation
          if (hasNonManipulationRels) {
            entities.push({
              users: Array.from(componentUsers),
              relations: compRels,
            })
          }
        }
      })

      this.entity_detection_results = entities
      console.log(
        `CryptoVis: Rebuilt entity results, total valid entities: ${entities.length}`,
      )
    },
    processManipulationRelations() {
      const enableEntity =
        this.entity_detection_configuration.enable_manipulation_based
      const enableLink =
        this.link_detection_configuration.enable_manipulation_based

      if (!enableEntity && !enableLink) return
      if (
        !this.manipulation_detection_results ||
        this.manipulation_detection_results.length === 0
      )
        return

      const timeDiffEntity =
        this.entity_detection_configuration.manipulation_based_params
          .max_manipulation_time_diff
      const timeDiffLink =
        this.link_detection_configuration.manipulation_based_params
          .max_manipulation_time_diff

      // Prepare User Sets for TT/TR classification
      const balances = this.snapshot_data.balances || {}
      const targetUsers = new Set(
        Object.keys(balances.users || {}).filter((u) => u !== 'Others'),
      )
      const relatedUsers = new Set(Object.keys(balances.related_users || {}))

      const classifyPair = (u1, u2) => {
        const u1T = targetUsers.has(u1)
        const u2T = targetUsers.has(u2)
        const u1R = relatedUsers.has(u1)
        const u2R = relatedUsers.has(u2)

        if (u1T && u2T) return 'tt'
        if ((u1T && u2R) || (u1R && u2T)) return 'tr'
        return null
      }

      let timedEvents = []
      let sameManipulationPairs = []

      this.manipulation_detection_results.forEach((result) => {
        // 1. Same manipulation pairs
        if (result.participants && result.participants.length > 1) {
          for (let i = 0; i < result.participants.length; i++) {
            for (let j = i + 1; j < result.participants.length; j++) {
              sameManipulationPairs.push({
                u1: result.participants[i],
                u2: result.participants[j],
                method: result.detection_method,
                time: result.manipulation_time,
              })
            }
          }
        }

        // 2. Collect events for time-based relations using manipulation_time
        if (
          result.participants &&
          result.manipulation_time &&
          result.manipulation_time.length > 0
        ) {
          const startStr = result.manipulation_time[0]
          const endStr =
            result.manipulation_time.length > 1
              ? result.manipulation_time[1]
              : startStr
          const startTs = new Date(startStr).getTime()
          const endTs = new Date(endStr).getTime()

          if (!Number.isNaN(startTs) && !Number.isNaN(endTs)) {
            result.participants.forEach((p) => {
              timedEvents.push({
                trader: p,
                startTs: startTs,
                endTs: endTs,
                method: result.detection_method,
                timeRange: result.manipulation_time,
              })
            })
          }
        }
      })

      // Sort events by time ascending
      timedEvents.sort((a, b) => a.startTs - b.startTs)

      const getPairKey = (u1, u2) => [u1, u2].sort().join('-')

      // Buckets for new relations
      const buckets = {
        entity: { tt: {}, tr: {} },
        link: { tt: {}, tr: {} },
      }

      const addRelation = (category, u1, u2, type, weight, details) => {
        const pairType = classifyPair(u1, u2)
        if (!pairType) return // Ignore if not TT or TR

        const key = getPairKey(u1, u2)
        const bucket = buckets[category][pairType]

        if (!bucket[key]) bucket[key] = []
        bucket[key].push({
          source: u1,
          target: u2,
          type,
          weight,
          details,
          description: details.description,
        })
      }

      // Sets to track unique relations per pair+type to avoid explosion
      const processedEntityPairs = new Set()
      const processedLinkPairs = new Set()
      const getUniqueKey = (u1, u2, type) => `${getPairKey(u1, u2)}|${type}`

      // Process same manipulation pairs
      sameManipulationPairs.forEach((item) => {
        const { u1, u2, method, time } = item
        const details = {
          description: `Participated in same manipulation group. Method: ${method || 'Unknown'}. Time: ${time ? time.join(' - ') : 'Unknown'}`,
          method,
          time,
        }

        const uKey = getUniqueKey(u1, u2, 'manipulation_same_group')

        if (enableEntity && !processedEntityPairs.has(uKey)) {
          processedEntityPairs.add(uKey)
          addRelation('entity', u1, u2, 'manipulation_same_group', 1, details)
        }
        if (enableLink && !processedLinkPairs.has(uKey)) {
          processedLinkPairs.add(uKey)
          addRelation('link', u1, u2, 'manipulation_same_group', 1, details)
        }
      })

      // Process time-based pairs
      for (let i = 0; i < timedEvents.length; i++) {
        for (let j = i + 1; j < timedEvents.length; j++) {
          let e1 = timedEvents[i]
          let e2 = timedEvents[j]

          let diffMs = Math.abs(e2.startTs - e1.startTs)
          let diffMinutes = diffMs / (1000 * 60)

          let maxThreshold = Math.max(timeDiffEntity, timeDiffLink)
          if (diffMinutes > maxThreshold) break

          if (e1.trader !== e2.trader) {
            const isOverlap = e1.startTs <= e2.endTs && e2.startTs <= e1.endTs
            const overlapStr = isOverlap ? ' (Overlap)' : ''

            const description = `Manipulation time proximity. Diff: ${diffMinutes.toFixed(2)}m${overlapStr}. Methods: ${e1.method}, ${e2.method}.`
            const details = {
              description,
              diffMinutes,
              isOverlap,
              event1: { method: e1.method, time: e1.timeRange },
              event2: { method: e2.method, time: e2.timeRange },
            }

            const uKey = getUniqueKey(
              e1.trader,
              e2.trader,
              'manipulation_time_proximity',
            )

            if (
              enableEntity &&
              diffMinutes <= timeDiffEntity &&
              !processedEntityPairs.has(uKey)
            ) {
              processedEntityPairs.add(uKey)
              addRelation(
                'entity',
                e1.trader,
                e2.trader,
                'manipulation_time_proximity',
                1,
                details,
              )
            }
            if (
              enableLink &&
              diffMinutes <= timeDiffLink &&
              !processedLinkPairs.has(uKey)
            ) {
              processedLinkPairs.add(uKey)
              addRelation(
                'link',
                e1.trader,
                e2.trader,
                'manipulation_time_proximity',
                1,
                details,
              )
            }
          }
        }
      }

      // Merge into link_generation_results
      // Structure: target_relations_for_entity (TT), target_related_relations_for_entity (TR), etc.
      let currentRelations = this.link_generation_results
        ? JSON.parse(JSON.stringify(this.link_generation_results))
        : {}

      // Helper to remove existing manipulation relations
      const cleanRelations = (relationsMap) => {
        if (!relationsMap) return {}
        const cleaned = {}
        Object.keys(relationsMap).forEach((key) => {
          const relations = relationsMap[key]
          if (Array.isArray(relations)) {
            // Filter out manipulation types
            const filtered = relations.filter(
              (r) =>
                r.type !== 'manipulation_same_group' &&
                r.type !== 'manipulation_time_proximity',
            )
            if (filtered.length > 0) {
              cleaned[key] = filtered
            }
          }
        })
        return cleaned
      }

      // Clean up old manipulation relations first to avoid duplicates
      ;[
        'target_relations_for_entity',
        'target_related_relations_for_entity',
        'target_relations_for_links',
        'target_related_relations_for_links',
      ].forEach((key) => {
        if (currentRelations[key]) {
          currentRelations[key] = cleanRelations(currentRelations[key])
        }
      })

      const mergeMap = (targetMapName, sourceMap) => {
        if (Object.keys(sourceMap).length === 0) return

        if (!currentRelations[targetMapName]) {
          currentRelations[targetMapName] = {}
        }
        const targetMap = currentRelations[targetMapName]

        Object.keys(sourceMap).forEach((key) => {
          if (targetMap[key]) {
            targetMap[key] = [...targetMap[key], ...sourceMap[key]]
          } else {
            targetMap[key] = sourceMap[key]
          }
        })
      }

      if (enableEntity) {
        mergeMap('target_relations_for_entity', buckets.entity.tt)
        mergeMap('target_related_relations_for_entity', buckets.entity.tr)
      }

      if (enableLink) {
        mergeMap('target_relations_for_links', buckets.link.tt)
        mergeMap('target_related_relations_for_links', buckets.link.tr)
      }

      this.link_generation_results = currentRelations
      console.log('CryptoVis: Added manipulation based relations:', {
        entityTT: Object.keys(buckets.entity.tt).length,
        entityTR: Object.keys(buckets.entity.tr).length,
        linkTT: Object.keys(buckets.link.tt).length,
        linkTR: Object.keys(buckets.link.tr).length,
      })

      // Rebuild entity results to merge connected entities based on new relations
      if (enableEntity) {
        this.rebuildEntityResults()
      }
    },
    async handleRunDetection(newEntityConfig) {
      console.log('CryptoVis: Running entity detection...', newEntityConfig)
      if (newEntityConfig) {
        this.entity_detection_configuration = { ...newEntityConfig }
      }
      this.logUserAction('run_entity_detection', { config: this.entity_detection_configuration })
      this.loading = true
      try {
        // Prepare detection request
        const balances = this.snapshot_data.balances || {}
        const processedUsers = { ...balances.users }
        delete processedUsers.Others
        const relatedUsers = balances.related_users || {}

        const detectionRequest = {
          target_users: processedUsers,
          related_users: relatedUsers,
          entity_detection_config: this.entity_detection_configuration,
          link_detection_config: this.link_detection_configuration, // Keep it but we won't detect links
          snapshot_time: this.snapshot_configuration.time,
          detect_entity: true,
          detect_link: false, // Disable link detection as requested
          coin: this.currentCoin,
        }

        const detectionResponse = await fetch('/api/detection/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(detectionRequest),
        })

        if (!detectionResponse.ok)
          throw new Error('Failed to run entity detection')

        const detectionResults = await detectionResponse.json()
        console.log(
          'CryptoVis: Entity detection results received:',
          detectionResults,
        )

        // Update entity results only
        this.entity_detection_results = detectionResults.entity_results
        // Update link_generation_results to hold relations if needed by entity detection
        // The backend returns relations even if detect_link is false (it returns entity relations)
        if (detectionResults.relations) {
          this.link_generation_results = {
            ...this.link_generation_results,
            ...detectionResults.relations,
          }
        }

        // Check if we need to re-run manipulation detection
        // Only if (round_trip is enabled AND round_trip.entity_based is enabled) OR (same_direction is enabled AND same_direction.entity_based is enabled)
        const config = this.manipulation_detection_configuration
        const roundTripEntityEnabled =
          config.enable_round_trip_detection &&
          config.round_trip_params?.enable_entity_based
        const sameDirectionEntityEnabled =
          config.enable_same_direction_detection &&
          config.same_direction_params?.enable_entity_based

        if (roundTripEntityEnabled || sameDirectionEntityEnabled) {
          console.log(
            'CryptoVis: Re-running manipulation detection with new entities...',
          )
          const manipulationRequest = {
            target_users: processedUsers,
            related_users: relatedUsers,
            entity_results: this.entity_detection_results,
            manipulation_config: this.manipulation_detection_configuration,
            coin: this.currentCoin,
          }

          const manipulationResponse = await fetch(
            '/api/manipulation_service/detect',
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(manipulationRequest),
            },
          )

          if (manipulationResponse.ok) {
            const manipulationResults = await manipulationResponse.json()
            this.manipulation_detection_results = manipulationResults.results
            console.log(
              'CryptoVis: Manipulation detection results updated:',
              this.manipulation_detection_results,
            )
          } else {
            console.error(
              'CryptoVis: Failed to update manipulation detection results',
            )
          }
        } else {
          console.log(
            'CryptoVis: Skipping manipulation detection (entity-based detection not enabled).',
          )
        }

        // Re-apply manipulation relations since link_generation_results might have been updated
        this.processManipulationRelations()
      } catch (error) {
        console.error('CryptoVis: Error during entity detection:', error)
      } finally {
        this.loading = false
      }
    },
    async handleRequestManipulationDetection(newManipulationConfig) {
      console.log(
        'CryptoVis: Running manipulation detection only...',
        newManipulationConfig,
      )
      if (newManipulationConfig) {
        this.manipulation_detection_configuration = { ...newManipulationConfig }
      }
      this.logUserAction('run_manipulation_detection', { config: this.manipulation_detection_configuration })
      this.detectingManipulation = true // Assuming there's a loading state for manipulation or reuse 'loading'

      try {
        const balances = this.snapshot_data.balances || {}
        const processedUsers = { ...balances.users }
        delete processedUsers.Others
        const relatedUsers = balances.related_users || {}

        const manipulationRequest = {
          target_users: processedUsers,
          related_users: relatedUsers,
          entity_results: this.entity_detection_results,
          manipulation_config: this.manipulation_detection_configuration,
          coin: this.currentCoin,
        }

        const manipulationResponse = await fetch(
          '/api/manipulation_service/detect',
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(manipulationRequest),
          },
        )

        if (manipulationResponse.ok) {
          const manipulationResults = await manipulationResponse.json()
          this.manipulation_detection_results = manipulationResults.results
          console.log(
            'CryptoVis: Manipulation detection results updated:',
            this.manipulation_detection_results,
          )

          // Add manipulation relations
          this.processManipulationRelations()
        } else {
          console.error('CryptoVis: Failed to run manipulation detection')
        }
      } catch (error) {
        console.error('CryptoVis: Error during manipulation detection:', error)
      } finally {
        this.detectingManipulation = false
      }
    },
    async handleUpdateSnapshot(newSnapshotConfig) {
      if (newSnapshotConfig) {
        this.snapshot_configuration = { ...newSnapshotConfig }
      }
      this.logUserAction('update_snapshot', { config: this.snapshot_configuration })
      this.loading = true
      try {
        // 1. Fetch new snapshot data
        console.log('CryptoVis: Fetching updated snapshot data...')
        const response = await fetch('/api/snapshot/process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            time: this.snapshot_configuration.time,
            threshold: this.snapshot_configuration.top_holder_threshold,
            related_user_threshold:
              this.snapshot_configuration.related_user_threshold,
            coin: this.currentCoin,
          }),
        })
        if (!response.ok) throw new Error('Failed to fetch snapshot data')
        const data = await response.json()
        this.snapshot_data = data
        this.snapshotTimes = data.all_times
        if (data.time) {
          this.snapshot_configuration.time = data.time
        }
        console.log(
          'CryptoVis: Updated snapshot data loaded:',
          this.snapshot_data,
        )

        // 2. Run detection service
        const balances = this.snapshot_data.balances || {}
        const processedUsers = { ...balances.users }
        delete processedUsers.Others
        const relatedUsers = balances.related_users || {}

        const detectionRequest = {
          target_users: processedUsers,
          related_users: relatedUsers,
          entity_detection_config: this.entity_detection_configuration,
          link_detection_config: this.link_detection_configuration,
          snapshot_time: this.snapshot_configuration.time,
          detect_entity: true,
          detect_link: true,
          coin: this.currentCoin,
        }

        console.log('CryptoVis: Running unified detection...', detectionRequest)

        const detectionResponse = await fetch('/api/detection/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(detectionRequest),
        })

        if (!detectionResponse.ok) throw new Error('Failed to run detection')

        const detectionResults = await detectionResponse.json()
        console.log('CryptoVis: Detection results received:', detectionResults)

        this.entity_detection_results = detectionResults.entity_results
        this.link_generation_results = detectionResults.relations

        // 3. Run manipulation detection
        console.log('CryptoVis: Running manipulation detection...')
        const manipulationRequest = {
          target_users: processedUsers,
          related_users: relatedUsers,
          entity_results: this.entity_detection_results,
          manipulation_config: this.manipulation_detection_configuration,
          coin: this.currentCoin,
        }

        const manipulationResponse = await fetch(
          '/api/manipulation_service/detect',
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(manipulationRequest),
          },
        )

        if (manipulationResponse.ok) {
          const manipulationResults = await manipulationResponse.json()
          this.manipulation_detection_results = manipulationResults.results
          console.log(
            'CryptoVis: Manipulation detection results updated:',
            this.manipulation_detection_results,
          )

          // Add manipulation relations
          this.processManipulationRelations()
        } else {
          console.error('CryptoVis: Failed to run manipulation detection')
        }
      } catch (error) {
        console.error(
          'CryptoVis: Error during snapshot update and detection:',
          error,
        )
      } finally {
        this.loading = false
      }
    },
    handleDetectionComplete(count) {
      this.detecting = false
      this.lastDetectionCount = count
    },
    async handleUpdateLinks(newLinkConfig) {
      console.log('CryptoVis: Updating links...', newLinkConfig)
      if (newLinkConfig) {
        this.link_detection_configuration = { ...newLinkConfig }
      }
      this.logUserAction('update_link_detection', { config: this.link_detection_configuration })
      this.detectingLinks = true // Assuming 'detectingLinks' or 'loading' is used

      try {
        const balances = this.snapshot_data.balances || {}
        const processedUsers = { ...balances.users }
        delete processedUsers.Others
        const relatedUsers = balances.related_users || {}

        const detectionRequest = {
          target_users: processedUsers,
          related_users: relatedUsers,
          entity_detection_config: this.entity_detection_configuration, // Keep it but we won't detect entities
          link_detection_config: this.link_detection_configuration,
          snapshot_time: this.snapshot_configuration.time,
          detect_entity: false, // Disable entity detection
          detect_link: true, // Enable link detection
          coin: this.currentCoin,
        }

        const detectionResponse = await fetch('/api/detection/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(detectionRequest),
        })

        if (!detectionResponse.ok)
          throw new Error('Failed to run link detection')

        const detectionResults = await detectionResponse.json()
        console.log(
          'CryptoVis: Link detection results received:',
          detectionResults,
        )

        // Update link results only
        this.link_generation_results = detectionResults.relations

        // Add manipulation relations back in
        this.processManipulationRelations()
      } catch (error) {
        console.error('CryptoVis: Error during link detection:', error)
      } finally {
        this.detectingLinks = false
      }
    },
    async fetchInitialSnapshotData() {
      console.log('CryptoVis: Fetching initial snapshot data...')
      try {
        const response = await fetch('/api/snapshot/process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            time: this.snapshot_configuration.time,
            threshold: this.snapshot_configuration.top_holder_threshold,
            related_user_threshold:
              this.snapshot_configuration.related_user_threshold,
            coin: this.currentCoin,
          }),
        })
        if (!response.ok) throw new Error('Failed to fetch snapshot data')
        const data = await response.json()
        this.snapshot_data = data
        this.snapshotTimes = data.all_times
        console.log(
          'CryptoVis: Initial snapshot data loaded:',
          this.snapshot_data,
        )

        // Run unified detection
        const balances = this.snapshot_data.balances || {}
        const processedUsers = { ...balances.users }
        delete processedUsers.Others
        const relatedUsers = balances.related_users || {}

        const detectionRequest = {
          target_users: processedUsers,
          related_users: relatedUsers,
          entity_detection_config: this.entity_detection_configuration,
          link_detection_config: this.link_detection_configuration,
          snapshot_time: this.snapshot_configuration.time,
          detect_entity: true,
          detect_link: true,
          coin: this.currentCoin,
        }

        console.log('CryptoVis: Running unified detection...', detectionRequest)

        const detectionResponse = await fetch('/api/detection/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(detectionRequest),
        })

        if (!detectionResponse.ok) throw new Error('Failed to run detection')

        const detectionResults = await detectionResponse.json()
        console.log('CryptoVis: Detection results received:', detectionResults)

        this.entity_detection_results = detectionResults.entity_results
        this.link_generation_results = detectionResults.relations

        // Run manipulation detection
        console.log('CryptoVis: Running manipulation detection...')
        const manipulationRequest = {
          target_users: processedUsers,
          related_users: relatedUsers,
          entity_results: this.entity_detection_results,
          manipulation_config: this.manipulation_detection_configuration,
          coin: this.currentCoin,
        }

        try {
          const manipulationResponse = await fetch(
            '/api/manipulation_service/detect',
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(manipulationRequest),
            },
          )

          if (manipulationResponse.ok) {
            const manipulationResults = await manipulationResponse.json()
            this.manipulation_detection_results = manipulationResults.results
            console.log(
              'CryptoVis: Manipulation detection results received:',
              this.manipulation_detection_results,
            )

            // Add manipulation relations
            this.processManipulationRelations()
          } else {
            console.error(
              'CryptoVis: Failed to run manipulation detection',
              manipulationResponse.statusText,
            )
          }
        } catch (manError) {
          console.error(
            'CryptoVis: Error running manipulation detection:',
            manError,
          )
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
              console.log(
                'CryptoVis: Calling tokenDistribution.drawChart() after initial detection',
              )
              this.$refs.tokenDistribution.drawChart()
            } else {
              console.warn(
                'CryptoVis: tokenDistribution.drawChart method not found',
              )
            }
          })
        } else {
          console.warn(
            'CryptoVis: tokenDistribution ref not found when updating detection results',
          )
        }
      } catch (error) {
        console.error('CryptoVis: Error fetching initial snapshot data:', error)
      }
    },
  },
  async mounted() {
    try {
      await this.initializeForCurrentCoin()
    } catch (error) {
      console.error('CryptoVis: Error during initial load:', error)
    }
  },
  updated() {},
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
