<template>
<n-layout class="h-screen max-h-screen" :content-style="{ display: 'flex', flexDirection: 'column'}">
  <n-layout-header>
      <div class="techname font-bold" style="display: flex; align-items: center; justify-content: space-between; padding-right: 20px;">
        <div style="display:flex; align-items:center; gap:10px; padding-left:20px;">
          <span>ManiScope</span>
          <button
            v-if="maniscopeSessionId && !isImportedWorkspace"
            class="session-chip"
            @click="copySessionLink"
            :title="`Copy session link ${maniscopeSessionId}`"
          >
            Session {{ maniscopeSessionId }}
          </button>
          <span v-else-if="importedSessionId" class="session-chip imported-session-chip">
            Imported {{ importedSessionId }}
          </span>
          <span class="workspace-badge" :class="workspaceBadgeClass">
            {{ workspaceLabel }}
          </span>
          <button
            v-if="isHumanWorkspace && !isImportedWorkspace"
            class="workspace-link-tag"
            type="button"
            title="Open imported study package page"
            @click="openImportedStudyPage"
          >
            Study Import
          </button>
          <button
            v-if="isHumanWorkspace && !isImportedWorkspace"
            class="workspace-link-tag"
            type="button"
            title="Open imported LLM analysis page"
            @click="openImportedAnalysisPage"
          >
            Analysis Import
          </button>
          <button
            v-if="!isImportedWorkspace"
            class="ai-chat-btn"
            @click="toggleChatBox"
            :class="{ active: chatBoxOpen }"
            title="AI Assistant"
          >🤖</button>
        </div>
        <div style="font-size: 14px; font-weight: normal; display: flex; align-items: center; gap: 10px; z-index: 1000;">
          <span style="color: #4a5568;">Coin:</span>
          <div style="display: flex; gap: 5px;">
            <label style="cursor: pointer; display: flex; align-items: center; gap: 4px;">
              <input type="radio" v-model="currentCoin" value="ACT" :disabled="isImportedWorkspace" @change="handleCoinChange" /> ACT
            </label>
            <label style="cursor: pointer; display: flex; align-items: center; gap: 4px; margin-left: 10px;">
              <input type="radio" v-model="currentCoin" value="PNUT" :disabled="isImportedWorkspace" @change="handleCoinChange" /> PNUT
            </label>
          </div>
          <!-- ezio: export/import session buttons -->
          <div v-if="isHumanWorkspace && !isImportedWorkspace" style="display: flex; gap: 6px; margin-left: 16px; border-left: 1px solid #e2e8f0; padding-left: 16px;">
            <button class="session-io-btn" @click="showStudyInfoDialog = true" title="Edit participant and study metadata">
              Study Info
            </button>
            <button class="session-io-btn" @click="onClickExport" title="Export Actions & Annotations as JSON">
              Export
            </button>
            <button class="session-io-btn" @click="onClickImport" title="Import Session from JSON">
              Import
            </button>
            <input
              ref="importFileInput"
              type="file"
              accept=".json,application/json,.zip,application/zip"
              class="session-import-file-input"
              @change="onImportFileChosen"
            />
          </div>
        </div>
      </div>
  </n-layout-header>
<n-layout-content class="flex-1" style="width:100%;height:100%" >
  <n-layout
        style="width:100%;height:100%;overflow:hidden"
        :content-style="{ display: 'flex', flexDirection: 'row', overflow: 'hidden', width: '100%', height: '100%', boxSizing: 'border-box' }"
      >

<div style="flex: 4; min-width:0; display: flex; flex-direction: column; height: 100%; overflow: hidden;">
        <!-- ezio: snapshot shortcut marker -->
        <n-card
            size="small"
            class="panel-card"
            data-snapshot-view="token_distribution"
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
        
        <div style="width:100%;height:40%;flex-shrink:0; overflow:hidden;">
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
        </div>
    </div>


    <div style="flex: 7; min-width:0; display: flex; flex-direction: column; height: 100%; overflow: hidden; margin-left: 5px;">
        <!-- ezio: snapshot shortcut marker -->
        <n-card
          size="small"
          class="panel-card"
          data-snapshot-view="candlestick_chart"
          style="width:100%;height:60%;flex-shrink:0; margin-bottom: 5px;"
          header-style="text-align:left;height:50px;font-size:1.4em;"
          :content-style="{ padding: 0, height: 'calc(100% - 50px)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }"
        >

          <div style="flex:1; border-top:1px solid #eef2f7; border-bottom:1px solid #eef2f7; display:flex; flex-direction:column; overflow:hidden; background:#fff;">
            <div style="width:100%; height:100%; min-height:0; overflow:hidden;">
              <!-- ezio: added ref for snapshot shortcut -->
              <CandlestickChart ref="candlestickChart"
                :manipulation-results="manipulation_detection_results"
                :selected-user="selectedUser"
                :entity-info="selectedEntityInfo"
                :current-coin="currentCoin"
                :sync-target-time-window="behaviorTimeWindow"
                :is-sequential-time="behaviorSequentialTime"
                @time-window-changed="handleKlineTimeWindowChanged"
                @card-click="handleManipulationCardClick"
                @log-action="logUserAction"
                @snapshot-input="handleSnapshotAnnotation('candlestick_chart', $event)"
                style="width:100%;height:100%;"
              />
            </div>
          </div>


        </n-card>
        <!-- ezio: snapshot shortcut marker -->
        <n-card
            size="small"
            class="panel-card"
            data-snapshot-view="behavior_details"
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
    
    <div style="flex: 4; min-width:0; display: flex; flex-direction: column; height: 100%; overflow: hidden; margin-left: 5px;">
        <NotesPanel 
            ref="notesPanel"
            :session-id="maniscopeSessionId"
            :session-mode="sessionMode"
            :actions="userActionSequence"
            :annotations="annotationRecords"
            :read-only="isAgentWorkspace || isImportedWorkspace"
            :snapshot-categories="snapshotCategories"
            :snapshot-quality="snapshotQuality"
            :analysis-payload="importedLlmAnalysis"
            @add-finding-annotation="handleAddFindingAnnotation"
            @delete-annotation="handleDeleteAnnotation"
            @delete-action="handleDeleteAction"
            @update-annotation="handleUpdateAnnotation"
            @add-custom-annotation="handleAddCustomAnnotation"
            @reorder-action="handleReorderAction"
            @toggle-category="onSnapshotCategoryToggle"
            @change-quality="onSnapshotQualityChange"
            @tab-change="handleNotesPanelTabChange"
            @log-action="handleNotesPanelLogAction"
            @analysis-trace="handleLlmAnalysisTrace"
        />
    </div>
      <!-- </n-layout> -->
  </n-layout>

</n-layout-content>

<CodexChatSidebar
  v-if="!isImportedWorkspace"
  :open="chatBoxOpen"
  :session-id="maniscopeSessionId"
  :session-mode="sessionMode"
  :workspace-role="workspaceRole"
  :sync-in-flight="liveTraceSyncInFlight"
  :last-sync-at="lastLiveTraceSyncAt"
  :before-send="syncTraceForChat"
  @send="handleChatSend"
  @assistant-finished="handleAssistantFinished"
  @assistant-interaction="handleAssistantInteraction"
  @close="handleChatClose"
/>

<!-- ezio: export dialog -->
<div v-if="showExportDialog" class="session-io-overlay" @click.self="showExportDialog = false">
  <div class="session-io-dialog">
    <div class="session-io-dialog-header">
      <h3>Export Study Package</h3>
      <button class="session-io-close" @click="showExportDialog = false">×</button>
    </div>
    <div class="session-io-dialog-body">
      <div class="session-io-stats">
        <div><strong>{{ userActionSequence.length }}</strong> actions</div>
        <div><strong>{{ annotationRecords.length }}</strong> annotations</div>
        <div><strong>{{ chatbotLogs.length }}</strong> chat turns</div>
      </div>
      <label class="session-io-checkbox">
        <input type="checkbox" v-model="exportIncludeSnapshots" />
        <span>Include snapshot images (PNG)</span>
      </label>
      <div class="session-io-hint">
        {{ exportIncludeSnapshots
          ? 'Zip will include screenshots, note images, current view captures, chat attachments, and linked response artifacts when available.'
          : 'Zip will contain structured experiment logs and metadata only. Embedded images will be stripped.' }}
      </div>
    </div>
    <div class="session-io-dialog-footer">
      <button class="session-io-btn ghost" @click="showExportDialog = false">Cancel</button>
      <button class="session-io-btn primary" @click="confirmExport">Download ZIP</button>
    </div>
  </div>
</div>

<div v-if="showStudyInfoDialog" class="session-io-overlay" @click.self="showStudyInfoDialog = false">
  <div class="session-io-dialog">
    <div class="session-io-dialog-header">
      <h3>Study Info</h3>
      <button class="session-io-close" @click="showStudyInfoDialog = false">×</button>
    </div>
    <div class="session-io-dialog-body">
      <div class="session-io-form-grid">
        <label class="session-io-field">
          <span>Participant ID</span>
          <input v-model="studyInfo.participantId" class="session-io-input" placeholder="e.g. P07" />
        </label>
        <label class="session-io-field">
          <span>Session Order</span>
          <input v-model="studyInfo.sessionOrder" class="session-io-input" placeholder="e.g. 1" />
        </label>
        <label class="session-io-field">
          <span>Condition</span>
          <input :value="studyConditionLabel" class="session-io-input" disabled />
        </label>
        <label class="session-io-field">
          <span>Dataset</span>
          <input :value="currentCoin" class="session-io-input" disabled />
        </label>
      </div>
      <label class="session-io-field" style="margin-top: 12px;">
        <span>Study Notes</span>
        <textarea
          v-model="studyInfo.studyNotes"
          class="session-io-input session-io-textarea"
          rows="3"
          placeholder="Optional experiment notes or condition annotations..."
        ></textarea>
      </label>
    </div>
    <div class="session-io-dialog-footer">
      <button class="session-io-btn ghost" @click="showStudyInfoDialog = false">Close</button>
      <button class="session-io-btn primary" @click="saveStudyInfo">Save</button>
    </div>
  </div>
</div>

<!-- ezio: import confirm (replace) dialog -->
<div v-if="showImportConflictDialog" class="session-io-overlay" @click.self="cancelImport">
  <div class="session-io-dialog">
    <div class="session-io-dialog-header">
      <h3>Import Session</h3>
      <button class="session-io-close" @click="cancelImport">×</button>
    </div>
    <div class="session-io-dialog-body">
      <div class="session-io-hint" style="margin-bottom:10px;">
        Current session already has
        <strong>{{ userActionSequence.length }}</strong> actions and
        <strong>{{ annotationRecords.length }}</strong> annotations.
      </div>
      <div class="session-io-hint">
        Incoming file contains
        <strong>{{ pendingImportPayload ? pendingImportPayload.userActionSequence.length : 0 }}</strong> actions and
        <strong>{{ pendingImportPayload ? pendingImportPayload.annotationRecords.length : 0 }}</strong> annotations.
      </div>
      <div style="margin-top:14px; color:#c53030;">
        Import will <strong>replace</strong> the current session data. This cannot be undone — export first if you want to keep it.
      </div>
    </div>
    <div class="session-io-dialog-footer">
      <button class="session-io-btn ghost" @click="cancelImport">Cancel</button>
      <button class="session-io-btn primary" @click="applyImport">Replace &amp; Import</button>
    </div>
  </div>
</div>

</n-layout>
</template>


<!-- scripts -->
<script>
import {
  NCard,
  NCheckbox,
  NLayout,
  NLayoutContent,
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
import UserActionTree from './UserActionTree.vue'
// ezio: import AnnotationTimeline for snapshot annotation display
import AnnotationTimeline from './AnnotationTimeline.vue'
import NotesPanel from './NotesPanel.vue'
// ezio: view screenshot utility
import { captureViewByName, isCapturable } from '../utils/viewSnapshot'
import {
  captureMajorVisualizationView,
  captureMajorVisualizationViews,
  createMajorViewApi,
  getMajorViewDataDependencies,
  getMajorViewRenderArgs as getMajorViewRenderArgsFromState,
  renderMajorVisualizationView as renderMajorVisualizationViewFromArgs,
} from '../utils/majorViewApi'
// ezio: session import/export helpers
import {
  buildExportArchive,
  downloadZipArchive,
  parseImportFile,
} from '../utils/sessionIO'
import CodexChatSidebar from './CodexChatSidebar.vue'

export default {
  props: {
    sessionId: {
      type: String,
      default: null,
    },
    sessionMode: {
      type: String,
      default: 'specialized',
      validator: (value) => ['specialized', 'baseline'].includes(value),
    },
    workspaceRole: {
      type: String,
      default: 'human',
      validator: (value) => ['human', 'agent'].includes(value),
    },
    importedPayload: {
      type: Object,
      default: null,
    },
    importedMeta: {
      type: Object,
      default: null,
    },
  },
  components: {
    NSelect,
    NCheckbox,
    NCard,
    NLayout,
    NSwitch,
    NSpace,
    NLayoutHeader,
    NLayoutContent,
    TokenDistribution,
    ControlPanel,
    CandlestickChart,
    BehaviorDetails,
    UserActionTimeline,
    AnnotationTimeline,
    UserActionTree,
    CodexChatSidebar,
    NotesPanel,
  },
  data() {
    return {
      currentCoin: 'ACT', // Can be 'ACT' or 'PNUT'
      // Codex chat sidebar state
      chatBoxOpen: false,
      maniscopeSessionId: this.sessionId,
      sessionRestoreStatus: 'pending',
      lastLiveTraceSyncAt: null,
      lastWorkspaceSyncAt: null,
      latestHumanCurrentState: null,
      liveTraceSyncInFlight: false,
      liveTraceSyncError: '',
      _liveTraceSyncTimer: null,
      _agentTraceRefreshTimer: null,
      _workspaceStateTimer: null,
      _sessionEventQueue: null,
      _workspaceRestoreState: null,
      _initialWorkspaceReadyPromise: null,
      _initialWorkspaceReadySettled: false,
      _initialWorkspaceReadyError: null,
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
      manipulation_detection_results: [], //current manipulation detection results

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
      behaviorSequentialTime: false, // Track if BehaviorDetails is using sequential time
      selectedCardUsers: [],
      userActionSequence: [], // Array to store user actions
      hoverTimers: {}, // Store timers for delayed hover logging
      isZooming: false, // Track if a zoom operation is actively happening
      zoomEndTimer: null, // Timer to clear the zooming state
      isScrollingCards: false, // Track if a card scroll operation is actively happening
      scrollCardsEndTimer: null, // Timer to clear the card scrolling state
      // ezio: annotation recording state
      annotationRecords: [], // Array to store snapshot annotations
      activeBottomTab: 'tree', // 'actions' | 'annotations' | 'tree'
      _annotationSeqId: 0, // auto-increment ID for annotations
      // ezio: action snapshot config — one switch per category
      snapshotCategories: [
        { key: 'hover',         label: 'Hover',           enabled: false, actions: ['hover_manipulation_card', 'hover_kline', 'hover_token_distribution_user', 'hover_behavior_manipulation_box', 'hover_behavior_user_label'] },
        { key: 'zoom_scroll',   label: 'Zoom / Scroll',   enabled: false, actions: ['zoom_kline_chart', 'zoom_behavior_chart', 'scroll_manipulation_cards', 'sync_time_window'] },
        { key: 'click_select',  label: 'Click / Select',  enabled: true,  actions: ['click_manipulation_card', 'click_kline_align_cards', 'select_user_from_network', 'select_user_from_behavior_details'] },
        { key: 'change_toggle', label: 'Change / Toggle', enabled: true,  actions: ['change_coin', 'change_kline_granularity', 'scale_change', 'toggle_show_links', 'toggle_show_related_users', 'toggle_show_manipulation_boxes', 'toggle_sequential_time'] },
        { key: 'system',        label: 'System',          enabled: true,  actions: ['run_entity_detection', 'run_manipulation_detection', 'update_snapshot', 'update_link_detection', 'high_level_finding'] },
      ],
      snapshotQuality: 'full', // ezio: default to full-res; 'thumbnail' | 'full'
      _snapshotCaptureInFlight: false,
      // ezio: awaited by _maybeCaptureSnapshots so target view is captured after its async redraw
      _targetReadyPromise: null,
      // ezio: export/import UI state
      showExportDialog: false,
      exportIncludeSnapshots: true,
      showImportConflictDialog: false,
      showStudyInfoDialog: false,
      pendingImportPayload: null,
      studyInfo: {
        participantId: '',
        sessionOrder: '',
        studyNotes: '',
      },
      analysisMilestones: [],
      chatbotLogs: [],
      llmAnalysisTrace: [],
      importedLlmAnalysis: null,
      majorViewApi: null,
    }
  },
  computed: {
    isImportedWorkspace() {
      return !!this.importedPayload
    },
    importedSessionId() {
      return this.importedMeta?.sessionId || null
    },
    isBaselineSession() {
      return this.sessionMode === 'baseline'
    },
    sessionApiBase() {
      return this.isBaselineSession ? '/api/base/sessions' : '/api/sessions'
    },
    isHumanWorkspace() {
      return this.isBaselineSession || this.workspaceRole !== 'agent'
    },
    isAgentWorkspace() {
      return !this.isBaselineSession && this.workspaceRole === 'agent'
    },
    workspaceLabel() {
      if (this.isImportedWorkspace) return 'Imported Study'
      if (this.isBaselineSession) return 'Baseline'
      return this.isAgentWorkspace ? 'Agent Workspace' : 'Human Workspace'
    },
    workspaceBadgeClass() {
      if (this.isImportedWorkspace) return 'workspace-imported'
      return this.isBaselineSession ? 'workspace-baseline' : `workspace-${this.workspaceRole}`
    },
    studyConditionLabel() {
      return this.isBaselineSession ? 'baseline' : 'full ManiScope'
    },
  },
  watch: {
    selectedUser(newVal) {
      if (newVal) {
        // ezio: stash the in-flight promise so _maybeCaptureSnapshots can await target-view readiness
        this._targetReadyPromise = this.generateBehaviorDetailData()
      } else {
        this.behaviorDetailData = null
        this.selectedEntityInfo = null
      }
    },
  },
  methods: {
    async initializeManiScopeSession() {
      if (this.isImportedWorkspace) {
        this.applyImportedPayload(this.importedPayload)
        this.latestHumanCurrentState = this.importedPayload?.currentState || null
        this._workspaceRestoreState = this.importedPayload?.currentState || null
        this.sessionRestoreStatus = 'imported'
        return
      }
      if (!this.maniscopeSessionId) {
        this.sessionRestoreStatus = 'missing'
        return
      }
      try {
        const response = await fetch(
          `${this.sessionApiBase}/${this.maniscopeSessionId}/workspaces/${this.workspaceRole}`,
        )
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const payload = await response.json()
        if (payload.liveSession) {
          this.applyLiveSession(payload.liveSession)
          this.sessionRestoreStatus = 'restored'
        } else {
          this.sessionRestoreStatus = 'new'
        }
        this.latestHumanCurrentState = payload.currentState || null
        const restoreState = payload.workspaceState || (this.isHumanWorkspace ? payload.currentState : null)
        if (restoreState) {
          this._workspaceRestoreState = restoreState
          this.applyCurrentState(restoreState)
        }
        this.lastLiveTraceSyncAt = payload.latestTraceTimestamp || payload.meta?.lastUpdatedAt || null
        this.lastWorkspaceSyncAt = payload.latestWorkspaceTimestamp || null
      } catch (error) {
        this.sessionRestoreStatus = 'error'
        this.liveTraceSyncError = error && error.message ? error.message : String(error)
        console.error('CryptoVis: failed to initialize ManiScope session', error)
      }
    },
    clonePlain(value) {
      return JSON.parse(JSON.stringify(value))
    },
    applyTraceRecordsFromLiveSession(liveSession, { applyWorkspaceDefaults = true } = {}) {
      if (!liveSession || typeof liveSession !== 'object') return
      if (applyWorkspaceDefaults && (liveSession.coin === 'ACT' || liveSession.coin === 'PNUT')) {
        this.currentCoin = liveSession.coin
      }
      this.userActionSequence = Array.isArray(liveSession.userActionSequence)
        ? liveSession.userActionSequence
        : []
      this.annotationRecords = Array.isArray(liveSession.annotationRecords)
        ? liveSession.annotationRecords
        : []
      this._annotationSeqId = Number.isFinite(liveSession.annotationSeqId)
        ? liveSession.annotationSeqId
        : this.annotationRecords.reduce(
            (maxId, annotation) =>
              Number.isFinite(annotation?.id) && annotation.id >= maxId ? annotation.id + 1 : maxId,
            0,
          )
    },
    applyLiveSession(liveSession) {
      if (!liveSession || typeof liveSession !== 'object') return
      this.applyTraceRecordsFromLiveSession(liveSession, { applyWorkspaceDefaults: true })
      this.studyInfo = {
        participantId: String(liveSession.studyInfo?.participantId || ''),
        sessionOrder: String(liveSession.studyInfo?.sessionOrder || ''),
        studyNotes: String(liveSession.studyInfo?.studyNotes || ''),
      }
      this.analysisMilestones = Array.isArray(liveSession.analysisMilestones)
        ? liveSession.analysisMilestones
        : []
      this.chatbotLogs = Array.isArray(liveSession.chatbotLogs)
        ? liveSession.chatbotLogs
        : []
      this.llmAnalysisTrace = Array.isArray(liveSession.llmAnalysisTrace)
        ? liveSession.llmAnalysisTrace
        : []
      if (Array.isArray(liveSession.config?.snapshotCategories)) {
        this.snapshotCategories = liveSession.config.snapshotCategories
      }
      if (liveSession.config?.snapshotQuality) {
        this.snapshotQuality = liveSession.config.snapshotQuality
      }
    },
    applyCurrentState(currentState) {
      if (!currentState || typeof currentState !== 'object') return
      if (currentState.coin === 'ACT' || currentState.coin === 'PNUT') {
        this.currentCoin = currentState.coin
      }
      if (currentState.snapshotTime) {
        this.snapshot_configuration.time = currentState.snapshotTime
      }
      if (currentState.snapshotConfig && typeof currentState.snapshotConfig === 'object') {
        this.snapshot_configuration = {
          ...this.snapshot_configuration,
          ...this.clonePlain(currentState.snapshotConfig),
        }
      }
      if (currentState.entityConfig && typeof currentState.entityConfig === 'object') {
        this.entity_detection_configuration = this.clonePlain(currentState.entityConfig)
      }
      if (currentState.linkConfig && typeof currentState.linkConfig === 'object') {
        this.link_detection_configuration = this.clonePlain(currentState.linkConfig)
      }
      if (currentState.manipulationConfig && typeof currentState.manipulationConfig === 'object') {
        this.manipulation_detection_configuration = this.clonePlain(currentState.manipulationConfig)
      }
      if (Object.prototype.hasOwnProperty.call(currentState, 'selectedUser')) {
        this.selectedUser = currentState.selectedUser || null
      }
      if (Array.isArray(currentState.selectedCardUsers)) {
        this.selectedCardUsers = currentState.selectedCardUsers
      }
      if (Object.prototype.hasOwnProperty.call(currentState, 'klineTimeWindow')) {
        this.klineTimeWindow = currentState.klineTimeWindow || null
      }
      if (Object.prototype.hasOwnProperty.call(currentState, 'behaviorTimeWindow')) {
        this.behaviorTimeWindow = currentState.behaviorTimeWindow || null
      }
      if (currentState.activeBottomTab) {
        this.activeBottomTab = currentState.activeBottomTab
      }
    },
    buildCurrentState(majorViewScreenshots = null) {
      return {
        sessionId: this.maniscopeSessionId,
        coin: this.currentCoin,
        workspaceRole: this.workspaceRole,
        snapshotTime: this.snapshot_configuration.time,
        snapshotConfig: this.clonePlain(this.snapshot_configuration),
        entityConfig: this.clonePlain(this.entity_detection_configuration),
        linkConfig: this.clonePlain(this.link_detection_configuration),
        manipulationConfig: this.clonePlain(this.manipulation_detection_configuration),
        selectedUser: this.selectedUser,
        selectedCardUsers: this.selectedCardUsers,
        klineTimeWindow: this.klineTimeWindow,
        behaviorTimeWindow: this.behaviorTimeWindow,
        activeBottomTab: this.activeBottomTab,
        chatOpen: this.chatBoxOpen,
        hasEntityResults: !!(this.entity_detection_results && this.entity_detection_results.length > 0),
        hasManipulationResults: !!(this.manipulation_detection_results && this.manipulation_detection_results.length > 0),
        majorViewScreenshots,
      }
    },
    buildSessionEventBody(extra = {}) {
      return {
        coin: this.currentCoin,
        annotationSeqId: this._annotationSeqId,
        snapshotCategories: this.snapshotCategories,
        snapshotQuality: this.snapshotQuality,
        currentState: this.buildCurrentState(null),
        studyInfo: this.clonePlain(this.studyInfo),
        analysisMilestones: this.clonePlain(this.analysisMilestones),
        chatbotLogs: this.clonePlain(this.chatbotLogs),
        llmAnalysisTrace: this.clonePlain(this.llmAnalysisTrace),
        ...extra,
      }
    },
    async collectLlmAnalysisForExport() {
      if (this.isBaselineSession) return null
      try {
        if (!this.$refs?.notesPanel?.getAnalysisExportPayload) return null
        return await this.$refs.notesPanel.getAnalysisExportPayload()
      } catch (error) {
        console.warn('CryptoVis: failed to collect LLM analysis export payload', error)
        return null
      }
    },
    async putWorkspaceState({ includeCurrentViews = false } = {}) {
      if (!this.maniscopeSessionId) return null
      const majorViewScreenshots = includeCurrentViews
        ? await this.captureCurrentMajorViewsForSession()
        : null
      const currentState = this.buildCurrentState(majorViewScreenshots)
      const response = await fetch(
        `${this.sessionApiBase}/${this.maniscopeSessionId}/workspaces/${this.workspaceRole}/state`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ currentState }),
        },
      )
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const payload = await response.json()
      this.lastWorkspaceSyncAt = payload.lastUpdatedAt || new Date().toISOString()
      return payload
    },
    scheduleWorkspaceStateSync(delay = 750) {
      if (!this.maniscopeSessionId) return
      if (this._workspaceStateTimer) clearTimeout(this._workspaceStateTimer)
      this._workspaceStateTimer = setTimeout(() => {
        this._workspaceStateTimer = null
        this.putWorkspaceState().catch((error) => {
          this.liveTraceSyncError = error && error.message ? error.message : String(error)
          console.error('CryptoVis: failed to sync workspace state', error)
        })
      }, delay)
    },
    queueSessionEvent(runEvent) {
      if (!this.maniscopeSessionId) return Promise.resolve(null)
      const previous = this._sessionEventQueue || Promise.resolve()
      this._sessionEventQueue = previous
        .catch(() => {})
        .then(async () => {
          try {
            return await runEvent()
          } catch (error) {
            this.liveTraceSyncError = error && error.message ? error.message : String(error)
            console.error('CryptoVis: failed to send live trace event', error)
            this.scheduleLiveTraceSync()
            return null
          }
        })
      return this._sessionEventQueue
    },
    sendSessionEvent(endpoint, { method = 'POST', body = {} } = {}) {
      if (this.isAgentWorkspace) {
        this.scheduleWorkspaceStateSync()
        return Promise.resolve(null)
      }
      return this.queueSessionEvent(async () => {
        const response = await fetch(`${this.sessionApiBase}/${this.maniscopeSessionId}/events/${endpoint}`, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.buildSessionEventBody(body)),
        })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const payload = await response.json()
        this.lastLiveTraceSyncAt = payload.lastUpdatedAt || new Date().toISOString()
        return payload
      })
    },
    upsertUserActionEvent(actionRecord, actionIndex = null) {
      const index = Number.isInteger(actionIndex)
        ? actionIndex
        : this.userActionSequence.findIndex((action) => action === actionRecord)
      if (index < 0) {
        return this.sendSessionEvent('user-actions', { body: { action: actionRecord } })
      }
      return this.sendSessionEvent(`user-actions/${index}`, {
        method: 'PUT',
        body: { action: actionRecord },
      })
    },
    deleteUserActionEvent(actionIndex) {
      return this.sendSessionEvent(`user-actions/${actionIndex}`, { method: 'DELETE' })
    },
    upsertAnnotationEvent(annotation) {
      if (!annotation || !Number.isFinite(annotation.id)) return Promise.resolve(null)
      return this.sendSessionEvent(`annotations/${annotation.id}`, {
        method: 'PUT',
        body: { annotation },
      })
    },
    deleteAnnotationEvent(annotationId) {
      return this.sendSessionEvent(`annotations/${annotationId}`, { method: 'DELETE' })
    },
    reorderTraceEvent() {
      return this.sendSessionEvent('reorder', {
        body: {
          userActionSequence: this.userActionSequence,
          annotationRecords: this.annotationRecords,
        },
      })
    },
    updateSessionSettingsEvent() {
      return this.sendSessionEvent('settings')
    },
    async captureCurrentMajorViewsForSession() {
      try {
        const captures = await captureMajorVisualizationViews(
          this,
          ['token_distribution', 'candlestick_chart', 'behavior_details'],
          { quality: this.snapshotQuality, includeChrome: true },
        )
        return captures.reduce((acc, result) => {
          if (result?.viewName && result?.image?.dataUrl) {
            acc[result.viewName] = result.image.dataUrl
          }
          return acc
        }, {})
      } catch (error) {
        console.warn('CryptoVis: failed to capture current major views for live trace', error)
        return null
      }
    },
    async syncCurrentTrace({ includeCurrentViews = false } = {}) {
      if (!this.maniscopeSessionId || this.liveTraceSyncInFlight) return null
      if (this._sessionEventQueue) {
        await this._sessionEventQueue.catch(() => {})
      }
      this.liveTraceSyncInFlight = true
      this.liveTraceSyncError = ''
      try {
        if (this.isAgentWorkspace) {
          return await this.putWorkspaceState({ includeCurrentViews })
        }
        const majorViewScreenshots = includeCurrentViews
          ? await this.captureCurrentMajorViewsForSession()
          : null
        const response = await fetch(`${this.sessionApiBase}/${this.maniscopeSessionId}/sync`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            coin: this.currentCoin,
            annotationSeqId: this._annotationSeqId,
            snapshotCategories: this.snapshotCategories,
            snapshotQuality: this.snapshotQuality,
            userActionSequence: this.userActionSequence,
            annotationRecords: this.annotationRecords,
            currentState: this.buildCurrentState(majorViewScreenshots),
            studyInfo: this.clonePlain(this.studyInfo),
            analysisMilestones: this.clonePlain(this.analysisMilestones),
            chatbotLogs: this.clonePlain(this.chatbotLogs),
          }),
        })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const payload = await response.json()
        this.lastLiveTraceSyncAt = payload.lastUpdatedAt || new Date().toISOString()
        return payload
      } catch (error) {
        this.liveTraceSyncError = error && error.message ? error.message : String(error)
        console.error('CryptoVis: failed to sync live trace', error)
        return null
      } finally {
        this.liveTraceSyncInFlight = false
      }
    },
    async syncTraceForChat() {
      let waitsRemaining = 30
      while (this.liveTraceSyncInFlight && waitsRemaining > 0) {
        await new Promise((resolve) => setTimeout(resolve, 100))
        waitsRemaining -= 1
      }
      const result = await this.syncCurrentTrace({ includeCurrentViews: true })
      if (!result) {
        throw new Error(this.liveTraceSyncError || 'Failed to sync the live trace before chat.')
      }
      return result
    },
    async refreshCanonicalTraceForAgent({ force = false } = {}) {
      if (!this.isAgentWorkspace || !this.maniscopeSessionId) return null
      try {
        const response = await fetch(
          `${this.sessionApiBase}/${this.maniscopeSessionId}/workspaces/${this.workspaceRole}`,
        )
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const payload = await response.json()
        this.latestHumanCurrentState = payload.currentState || null
        const latestTraceTimestamp = payload.latestTraceTimestamp || payload.meta?.lastUpdatedAt || null
        if (payload.liveSession && (force || latestTraceTimestamp !== this.lastLiveTraceSyncAt)) {
          this.applyTraceRecordsFromLiveSession(payload.liveSession, {
            applyWorkspaceDefaults: false,
          })
          this.lastLiveTraceSyncAt = latestTraceTimestamp
        }
        return payload
      } catch (error) {
        this.liveTraceSyncError = error && error.message ? error.message : String(error)
        console.error('CryptoVis: failed to refresh agent trace context', error)
        return null
      }
    },
    startAgentTraceRefresh() {
      if (!this.isAgentWorkspace || this._agentTraceRefreshTimer) return
      this._agentTraceRefreshTimer = setInterval(() => {
        this.refreshCanonicalTraceForAgent().catch((error) => {
          console.error('CryptoVis: agent trace refresh failed', error)
        })
      }, 3000)
    },
    scheduleLiveTraceSync(delay = 750) {
      if (!this.maniscopeSessionId) return
      if (this.isAgentWorkspace) {
        this.scheduleWorkspaceStateSync(delay)
        return
      }
      if (this._liveTraceSyncTimer) clearTimeout(this._liveTraceSyncTimer)
      this._liveTraceSyncTimer = setTimeout(() => {
        this._liveTraceSyncTimer = null
        this.syncCurrentTrace().catch((error) => {
          console.error('CryptoVis: scheduled live trace sync failed', error)
        })
      }, delay)
    },
    copySessionLink() {
      if (this.isImportedWorkspace) return
      const path = this.isBaselineSession
        ? `/base/${this.maniscopeSessionId}`
        : `/${this.maniscopeSessionId}/${this.workspaceRole}`
      const url = `${window.location.origin}${path}`
      if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(url).catch(() => {})
      }
    },
    openImportedAnalysisPage() {
      window.open(`${window.location.origin}/analysis-import`, '_blank', 'noopener')
    },
    openImportedStudyPage() {
      window.open(`${window.location.origin}/study-import`, '_blank', 'noopener')
    },
    // ezio: open snapshot for the view under the mouse cursor (triggered by Alt+S)
    openSnapshotByMouse() {
      const el = document.elementFromPoint(this._mouseX, this._mouseY);
      if (!el) return;
      const panel = el.closest('[data-snapshot-view]');
      if (!panel) return;
      const view = panel.dataset.snapshotView;
      const refMap = {
        token_distribution: 'tokenDistribution',
        candlestick_chart: 'candlestickChart',
        behavior_details: 'behaviorDetails',
      };
      const refName = refMap[view];
      if (refName && this.$refs[refName] && typeof this.$refs[refName].openSnapshot === 'function') {
        this.$refs[refName].openSnapshot();
      }
    },
    getMajorViewDataDependencies(viewName, options = {}) {
      return getMajorViewDataDependencies(this, viewName, options)
    },
    normalizeMajorViewNameForReadiness(viewName) {
      if (!viewName) return null
      return getMajorViewDataDependencies(this, viewName).viewName
    },
    hasSnapshotRenderData() {
      const balances = this.snapshot_data?.balances
      return !!(
        balances &&
        typeof balances === 'object' &&
        (Object.keys(balances.users || {}).length > 0 ||
          Object.keys(balances.related_users || {}).length > 0)
      )
    },
    hasObjectRenderData(value) {
      return !!(value && typeof value === 'object' && Object.keys(value).length > 0)
    },
    hasArrayRenderData(value) {
      return Array.isArray(value) && value.length > 0
    },
    getMajorViewReadiness(viewName = null) {
      const viewNames = viewName
        ? [this.normalizeMajorViewNameForReadiness(viewName)]
        : ['token_distribution', 'candlestick_chart', 'behavior_details']
      const views = {}

      viewNames.forEach((name) => {
        const missing = []
        if (name === 'token_distribution') {
          if (!this.hasSnapshotRenderData()) missing.push('snapshotData')
          if (!this.hasArrayRenderData(this.entity_detection_results)) missing.push('entityDetectionResults')
          if (!this.hasObjectRenderData(this.link_generation_results)) missing.push('linkDetectionResults')
          if (!this.hasArrayRenderData(this.manipulation_detection_results)) {
            missing.push('manipulationDetectionResults')
          }
        } else if (name === 'candlestick_chart') {
          const klineRef = this.$refs?.candlestickChart
          if (!this.hasArrayRenderData(klineRef?.ohlc)) missing.push('ohlcData')
          if (!this.hasArrayRenderData(this.manipulation_detection_results)) {
            missing.push('manipulationResults')
          }
        } else if (name === 'behavior_details') {
          const selectedUsers = this.selectedUser
            ? [this.selectedUser]
            : Array.isArray(this.selectedCardUsers)
              ? this.selectedCardUsers
              : []
          if (selectedUsers.length > 0) {
            const behaviorData = this.behaviorDetailData || {}
            const missingUsers = selectedUsers.filter(
              (user) => !Array.isArray(behaviorData[user]) || behaviorData[user].length === 0,
            )
            if (missingUsers.length > 0) missing.push('behaviorData')
          }
          if (!this.hasArrayRenderData(this.manipulation_detection_results)) {
            missing.push('manipulationResults')
          }
        }

        views[name] = {
          ready: missing.length === 0,
          missing,
        }
      })

      return {
        ready: Object.values(views).every((entry) => entry.ready),
        initializing: !!this._initialWorkspaceReadyPromise && !this._initialWorkspaceReadySettled,
        loading: !!(this.loading || this.detecting || this.detectingLinks || this.detectingManipulation),
        error: this._initialWorkspaceReadyError
          ? this._initialWorkspaceReadyError.message || String(this._initialWorkspaceReadyError)
          : null,
        views,
      }
    },
    async ensureMajorViewReady(viewName, options = {}) {
      const normalizedViewName = this.normalizeMajorViewNameForReadiness(viewName)
      const timeoutMs = Number(options.readinessTimeoutMs || options.timeoutMs || 60000)
      const pollMs = Number(options.readinessPollMs || 200)
      const startedAt = Date.now()
      let refreshed = false

      const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

      while (Date.now() - startedAt <= timeoutMs) {
        if (this._initialWorkspaceReadyPromise && !this._initialWorkspaceReadySettled) {
          await this._initialWorkspaceReadyPromise.catch(() => {})
        }
        if (this._targetReadyPromise) {
          await this._targetReadyPromise.catch(() => {})
        }
        await this._awaitViewsSettled()

        const readiness = this.getMajorViewReadiness(normalizedViewName)
        if (readiness.ready) return readiness

        if (!refreshed && options.refreshIfMissing !== false) {
          refreshed = true
          const work = this.initializeForCurrentCoin({
            preserveSnapshotTime: true,
          }).catch((error) => {
            console.error('CryptoVis: readiness refresh failed:', error)
          })
          this._targetReadyPromise = work.then(() => this._awaitViewsSettled())
          await work
          continue
        }

        await wait(pollMs)
      }

      const readiness = this.getMajorViewReadiness(normalizedViewName)
      const missing = readiness.views[normalizedViewName]?.missing || []
      throw new Error(
        `ManiScope ${normalizedViewName} is not ready after ${timeoutMs}ms; missing: ${missing.join(', ') || 'unknown'}`,
      )
    },
    getMajorViewRenderArgs(viewName, options = {}) {
      return getMajorViewRenderArgsFromState(this, viewName, options)
    },
    renderMajorVisualizationView(viewName, args, options = {}) {
      return renderMajorVisualizationViewFromArgs(viewName, args, options)
    },
    captureMajorVisualizationView(viewName, options = {}) {
      return captureMajorVisualizationView(this, viewName, options)
    },
    captureMajorVisualizationViews(viewNamesOrOptions, maybeOptions = {}) {
      return captureMajorVisualizationViews(this, viewNamesOrOptions, maybeOptions)
    },
    installMajorViewApi() {
      this.majorViewApi = createMajorViewApi(this)
      if (typeof window !== 'undefined') {
        window.maniScopeMajorViewApi = this.majorViewApi
      }
    },
    cleanupGlobalHandlers() {
      document.removeEventListener('mousemove', this._onMouseMove);
      document.removeEventListener('keydown', this._onKeyDown);
      if (typeof window !== 'undefined' && window.maniScopeMajorViewApi === this.majorViewApi) {
        delete window.maniScopeMajorViewApi
      }
      this.majorViewApi = null
    },
    normalizeStudyCondition() {
      return this.isBaselineSession ? 'baseline' : 'full ManiScope'
    },
    normalizeStudyView(viewName) {
      const labels = {
        token_distribution: 'Token Distribution',
        kline_chart: 'Manipulation View',
        behavior_details: 'Behavior Detail',
        control_panel: 'Control Panel',
        llm_analysis: 'LLM Analysis',
        chat: 'Chat',
        annotations: 'Annotations',
        actions: 'User Actions',
        tree: 'Action Tree',
        all_views: 'All Views',
        system: 'System',
      }
      return labels[viewName] || viewName || 'System'
    },
    buildStudySystemState() {
      return {
        selectedSnapshot: this.snapshot_configuration.time || null,
        topHolderThreshold: this.snapshot_configuration.top_holder_threshold,
        relatedHolderThreshold: this.snapshot_configuration.related_user_threshold,
        snapshotConfig: this.clonePlain(this.snapshot_configuration),
        entitySettings: this.clonePlain(this.entity_detection_configuration),
        linkSettings: this.clonePlain(this.link_detection_configuration),
        suspiciousPatternSettings: this.clonePlain(this.manipulation_detection_configuration),
        selectedHolderId: this.selectedUser || null,
        selectedCardUsers: this.clonePlain(this.selectedCardUsers || []),
        klineTimeWindow: this.klineTimeWindow,
        behaviorTimeWindow: this.behaviorTimeWindow,
        activeBottomTab: this.activeBottomTab,
        chatOpen: this.chatBoxOpen,
        behaviorSequentialTime: this.behaviorSequentialTime,
      }
    },
    buildTargetObject(actionType, actionInfo = {}) {
      const info = actionInfo && typeof actionInfo === 'object' ? actionInfo : {}
      return {
        holderId: info.targetUserId || info.userId || this.selectedUser || null,
        cardId: info.cardId || null,
        cardUsers: Array.isArray(info.cardUsers) ? info.cardUsers : null,
        timeWindow: info.timeWindow || this.klineTimeWindow || this.behaviorTimeWindow || null,
        parameterName: info.parameterName || null,
        thresholdValue: info.thresholdValue ?? info.threshold ?? null,
        selectedItems: Array.isArray(info.selectedItems) ? info.selectedItems : null,
        raw: this.clonePlain(info),
        actionType,
      }
    },
    inferNoteKind(text, preferredKind = '') {
      const value = String(text || '').trim().toLowerCase()
      if (preferredKind) return preferredKind
      if (!value) return 'finding'
      if (/[?？]$/.test(value) || /^(why|how|whether|what|which)\b/.test(value)) return 'question'
      if (/\b(maybe|possibly|probably|unclear|unsure|not sure|uncertain)\b/.test(value)) return 'uncertainty'
      if (/\b(hypothesis|suspect|likely|assume|might be|could be|suggests)\b/.test(value)) return 'hypothesis'
      if (/\b(conclusion|conclude|final|risk|manipulation|benign|malicious)\b/.test(value)) return 'conclusion'
      return 'finding'
    },
    buildNoteContext(sourceView) {
      return {
        linkedView: this.normalizeStudyView(sourceView),
        selectedObject: {
          holderId: this.selectedUser || null,
          cardUsers: this.clonePlain(this.selectedCardUsers || []),
        },
        timeWindow: this.klineTimeWindow || this.behaviorTimeWindow || null,
      }
    },
    upsertMilestone(name, details = {}) {
      if (!name) return
      const existing = this.analysisMilestones.find((item) => item && item.name === name)
      if (existing) return
      this.analysisMilestones.push({
        name,
        timestamp: new Date().toISOString(),
        condition: this.normalizeStudyCondition(),
        dataset: this.currentCoin,
        participantId: this.studyInfo.participantId || null,
        sessionOrder: this.studyInfo.sessionOrder || null,
        details: this.clonePlain(details),
      })
      this.scheduleLiveTraceSync(0)
    },
    markLatestAssistantResponseUsed(reason, details = {}) {
      for (let index = this.chatbotLogs.length - 1; index >= 0; index -= 1) {
        const entry = this.chatbotLogs[index]
        if (!entry?.response || entry.response.used) continue
        entry.response.used = true
        entry.response.usedAt = new Date().toISOString()
        entry.response.usedReason = reason || 'follow_up_action'
        entry.response.usedDetails = this.clonePlain(details)
        this.scheduleLiveTraceSync(0)
        return entry
      }
      return null
    },
    maybeMarkMilestonesFromNote(record) {
      if (!record) return
      this.upsertMilestone('first_meaningful_evidence_found', {
        noteId: record.id,
        view: record.sourceView,
      })
      if (record.noteKind === 'hypothesis') {
        this.upsertMilestone('first_hypothesis_formed', {
          noteId: record.id,
          text: record.text,
        })
      }
      if (record.noteKind === 'conclusion') {
        this.upsertMilestone('final_risk_assessment_submitted', {
          noteId: record.id,
          text: record.text,
        })
      }
      if (this.markLatestAssistantResponseUsed('note_created', { noteId: record.id })) {
        this.upsertMilestone('first_evidence_added_after_llm_assistance', {
          noteId: record.id,
          noteKind: record.noteKind,
        })
      }
    },
    inferChatResponseTypes(message) {
      const text = String(message?.content || '').toLowerCase()
      const types = []
      if (/\bshould|consider|recommend|suggest\b/.test(text)) types.push('suggestion')
      if (/\bhypothesis|likely|suspect|indicates\b/.test(text)) types.push('inferred hypothesis')
      if (/\bchart|image|screenshot|visual\b/.test(text)) types.push('visual finding')
      if (/\bstatistic|percentage|mean|median|count|volume|balance\b/.test(text)) types.push('statistical finding')
      if (/\bhowever|but|contradict|counter|not consistent\b/.test(text)) types.push('contradictory evidence')
      if (/\bsummary|overall|in short\b/.test(text)) types.push('data summary')
      if (types.length === 0) types.push('explanation')
      return types
    },
    saveStudyInfo() {
      this.showStudyInfoDialog = false
      this.scheduleLiveTraceSync(0)
    },
    toggleChatBox() {
      this.chatBoxOpen = !this.chatBoxOpen
      this.logUserAction('toggle_chat_panel', { open: this.chatBoxOpen })
    },
    handleChatClose() {
      this.chatBoxOpen = false
      this.logUserAction('toggle_chat_panel', { open: false, via: 'close_button' })
    },
    handleNotesPanelTabChange(tab) {
      this.activeBottomTab = tab || 'tree'
      this.logUserAction('switch_notes_panel_tab', {
        tab,
        view: tab === 'llm_analysis' ? 'llm_analysis' : tab,
      })
    },
    handleNotesPanelLogAction(payload) {
      if (!payload || typeof payload !== 'object') return
      this.logUserAction(payload.actionType || 'notes_panel_action', payload.targetObject || payload)
    },
    handleChatSend(payload) {
      const entry = {
        id: payload?.messageId || `chat-${Date.now()}`,
        timestamp: payload?.createdAt || new Date().toISOString(),
        participantId: this.studyInfo.participantId || null,
        condition: this.normalizeStudyCondition(),
        dataset: this.currentCoin,
        sessionOrder: this.studyInfo.sessionOrder || null,
        triggerType: payload?.triggerType || 'manual',
        prompt: payload?.content || '',
        promptAttachments: this.clonePlain(payload?.promptAttachments || []),
        promptContext: this.buildStudySystemState(),
        response: null,
      }
      this.chatbotLogs.push(entry)
      this.upsertMilestone('first_llm_chatbot_request', {
        promptId: entry.id,
        triggerType: entry.triggerType,
      })
      if (entry.triggerType === 'analyze_with_me') {
        this.logUserAction('analyze_with_me_trigger', { promptId: entry.id })
      } else {
        this.logUserAction('chatbot_query', { promptId: entry.id, promptLength: entry.prompt.length })
      }
      this.scheduleLiveTraceSync(0)
    },
    handleAssistantFinished(payload) {
      if (!payload?.requestMessageId || !payload.message) return
      const entry = this.chatbotLogs.find((item) => item.id === payload.requestMessageId)
      if (!entry) return
      entry.response = {
        assistantMessageId: payload.assistantMessageId || null,
        timestamp: payload.message.createdAt || new Date().toISOString(),
        text: payload.message.content || '',
        activity: this.clonePlain(payload.message.activity || []),
        artifacts: this.clonePlain(payload.message.artifacts || []),
        responseTypes: this.inferChatResponseTypes(payload.message),
        linkedEvidence: {
          view: this.normalizeStudyView('chat'),
          holderId: this.selectedUser || null,
          cardUsers: this.clonePlain(this.selectedCardUsers || []),
          timeWindow: this.klineTimeWindow || this.behaviorTimeWindow || null,
          statistic: {
            topHolderThreshold: this.snapshot_configuration.top_holder_threshold,
            relatedHolderThreshold: this.snapshot_configuration.related_user_threshold,
          },
        },
        clicked: false,
        expanded: false,
        accepted: null,
        used: false,
      }
      this.scheduleLiveTraceSync(0)
    },
    handleAssistantInteraction(payload) {
      if (!payload?.messageId) return
      const entry = [...this.chatbotLogs].reverse().find(
        (item) => item.response && item.response.assistantMessageId === payload.messageId,
      )
      if (!entry?.response) return
      if (payload.type === 'toggle_response_details') {
        entry.response.expanded = Boolean(payload.expanded)
      } else if (payload.type === 'click_response_artifact') {
        entry.response.clicked = true
        entry.response.clickedArtifact = this.clonePlain(payload.artifact || null)
      }
      this.scheduleLiveTraceSync(0)
    },
    handleLlmAnalysisTrace(payload) {
      if (this.isImportedWorkspace || this.isAgentWorkspace) return
      if (!payload || typeof payload !== 'object') return
      const traceKey = String(
        payload.traceKey
          || `${payload.eventType || 'llm_analysis'}:${payload.artifactName || ''}:${payload.artifactModifiedAt || ''}`,
      )
      const entry = {
        ...this.clonePlain(payload),
        traceKey,
        timestamp: payload.timestamp || new Date().toISOString(),
        sessionId: this.maniscopeSessionId || null,
        condition: this.normalizeStudyCondition(),
        dataset: this.currentCoin,
        sessionOrder: this.studyInfo.sessionOrder || null,
        currentSystemState: this.buildStudySystemState(),
      }
      const existingIndex = this.llmAnalysisTrace.findIndex((item) => item?.traceKey === traceKey)
      if (existingIndex >= 0) this.llmAnalysisTrace.splice(existingIndex, 1, entry)
      else this.llmAnalysisTrace.push(entry)
      this.scheduleLiveTraceSync(0)
    },
    // ezio: handle annotation submission from snapshot modals
    handleSnapshotAnnotation(sourceView, payload) {
      if (this.isAgentWorkspace) {
        this.scheduleWorkspaceStateSync()
        return
      }
      const record = {
        id: this._annotationSeqId++,
        timestamp: new Date().toISOString(),
        sourceView,
        text: payload.text || '',
        selectedItems: payload.selectedItems || payload.selectedIds || [],
        sketchDataUrl: payload.sketchDataUrl || null,
        noteKind: this.inferNoteKind(payload.text),
        ...this.buildNoteContext(sourceView),
      }
      this.annotationRecords.push(record)
      this.activeBottomTab = 'annotations'
      this.upsertAnnotationEvent(record)
      this.maybeMarkMilestonesFromNote(record)
    },
    // ezio: handle finding annotation added from UserActionTree
    handleAddFindingAnnotation(payload) {
      if (this.isAgentWorkspace) return
      const record = {
        id: this._annotationSeqId++,
        timestamp: new Date().toISOString(),
        sourceView: payload.sourceView,
        text: payload.text || '',
        selectedItems: payload.selectedItems || [],
        sketchDataUrl: null,
        isFinding: true,
        noteKind: this.inferNoteKind(payload.text, 'finding'),
        ...this.buildNoteContext(payload.sourceView),
      }
      this.annotationRecords.push(record)
      this.upsertAnnotationEvent(record)
      this.maybeMarkMilestonesFromNote(record)
    },

    // ezio: delete annotation by id (from tree editor)
    handleDeleteAnnotation(id) {
      if (this.isAgentWorkspace) return
	      const idx = this.annotationRecords.findIndex(a => a.id === id)
	      if (idx !== -1) {
	        this.annotationRecords.splice(idx, 1)
	        this.deleteAnnotationEvent(id)
	      }
	    },

    // ezio: delete action by timestamp (from tree editor)
    handleDeleteAction(timestamp) {
      if (this.isAgentWorkspace) return
	      const idx = this.userActionSequence.findIndex(a => a.timestamp === timestamp)
	      if (idx !== -1) {
	        this.userActionSequence.splice(idx, 1)
	        this.deleteUserActionEvent(idx)
	      }
	    },

    // ezio: update annotation text/color/image (from tree editor)
    handleUpdateAnnotation(payload) {
      if (this.isAgentWorkspace) return
      const ann = this.annotationRecords.find(a => a.id === payload.id)
      if (!ann) return
      if (payload.text !== undefined) ann.text = payload.text
      if (payload.customColor !== undefined) ann.customColor = payload.customColor
      if (payload.sketchDataUrl !== undefined) ann.sketchDataUrl = payload.sketchDataUrl
      ann.noteKind = this.inferNoteKind(ann.text, ann.isFinding ? 'finding' : '')
      this.upsertAnnotationEvent(ann)
    },

    // ezio: add a custom annotation node (from tree editor)
    handleAddCustomAnnotation(payload) {
      if (this.isAgentWorkspace) return
      let timestamp = new Date().toISOString()
      if (payload.afterTimestamp) {
        const allItems = [
          ...this.userActionSequence,
          ...this.annotationRecords
        ].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
        const afterIdx = allItems.findIndex(a => a.timestamp === payload.afterTimestamp)
        if (afterIdx !== -1) {
          const afterTime = new Date(payload.afterTimestamp).getTime()
          const nextItem = allItems[afterIdx + 1]
          const nextTime = nextItem ? new Date(nextItem.timestamp).getTime() : afterTime + 2000
          timestamp = new Date((afterTime + nextTime) / 2).toISOString()
        }
      }
      const record = {
        id: this._annotationSeqId++,
        timestamp,
        sourceView: payload.sourceView || 'token_distribution',
        text: payload.text || '',
        selectedItems: [],
        sketchDataUrl: payload.sketchDataUrl || null,
        customColor: payload.customColor || null,
        noteKind: this.inferNoteKind(payload.text),
        ...this.buildNoteContext(payload.sourceView || 'token_distribution'),
      }
      this.annotationRecords.push(record)
      this.upsertAnnotationEvent(record)
      this.maybeMarkMilestonesFromNote(record)
    },

    // ezio: reorder actions/annotations by swapping timestamps
    handleReorderAction({ timestamp, direction }) {
      if (this.isAgentWorkspace) return
      const allItems = [
        ...this.userActionSequence,
        ...this.annotationRecords
      ].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
      const idx = allItems.findIndex(a => a.timestamp === timestamp)
      if (idx === -1) return
      const swapIdx = direction === 'up' ? idx - 1 : idx + 1
      if (swapIdx < 0 || swapIdx >= allItems.length) return
	      const tsA = allItems[idx].timestamp
	      const tsB = allItems[swapIdx].timestamp
	      allItems[idx].timestamp = tsB
	      allItems[swapIdx].timestamp = tsA
	      this.reorderTraceEvent()
	    },

    // ezio: open export dialog
    onClickExport() {
      if (this.isAgentWorkspace) return
      this.showExportDialog = true
    },
    // ezio: build zip payload + trigger download
    async confirmExport() {
      if (this.isAgentWorkspace) return
      const majorViewScreenshots = this.exportIncludeSnapshots
        ? await this.captureCurrentMajorViewsForSession()
        : null
      const llmAnalysis = await this.collectLlmAnalysisForExport()
      const archive = await buildExportArchive({
        sessionId: this.maniscopeSessionId,
        sessionMode: this.sessionMode,
        coin: this.currentCoin,
        userActionSequence: this.userActionSequence,
        annotationRecords: this.annotationRecords,
        snapshotCategories: this.snapshotCategories,
        snapshotQuality: this.snapshotQuality,
        annotationSeqId: this._annotationSeqId,
        includeSnapshots: this.exportIncludeSnapshots,
        currentState: this.buildCurrentState(majorViewScreenshots),
        studyInfo: this.studyInfo,
        analysisMilestones: this.analysisMilestones,
        chatbotLogs: this.chatbotLogs,
        llmAnalysisTrace: this.llmAnalysisTrace,
        llmAnalysis,
      })
      downloadZipArchive(archive, this.currentCoin)
      this.showExportDialog = false
      this.logUserAction('export_session', {
        actionCount: this.userActionSequence.length,
        annotationCount: this.annotationRecords.length,
        includeSnapshots: this.exportIncludeSnapshots,
      })
    },
    getImportFileInput() {
      const input = this.$refs.importFileInput
      return Array.isArray(input) ? input[0] : input
    },
    // ezio: trigger hidden file input
    onClickImport() {
      if (this.isAgentWorkspace) return
      const input = this.getImportFileInput()
      if (input && typeof input.click === 'function') {
        input.value = ''
        input.click()
      }
    },
    // ezio: parse the selected JSON file
    async onImportFileChosen(e) {
      if (this.isAgentWorkspace) return
      const file = e.target.files && e.target.files[0]
      if (!file) return
      try {
        const parsed = await parseImportFile(file)
        if (parsed.isPatchTraceOnlyForTesting) {
          this.applyPatchTraceImport(parsed)
          return
        }
        const isEmpty =
          this.userActionSequence.length === 0 &&
          this.annotationRecords.length === 0
        if (isEmpty) {
          this.pendingImportPayload = parsed
          this.applyImport()
        } else {
          this.pendingImportPayload = parsed
          this.showImportConflictDialog = true
        }
      } catch (err) {
        window.alert('Invalid session file: ' + (err && err.message ? err.message : err))
      } finally {
        const input = this.getImportFileInput()
        if (input) input.value = ''
      }
    },
    // ezio: user cancelled import
    cancelImport() {
      this.showImportConflictDialog = false
      this.pendingImportPayload = null
    },
    applyPatchTraceImport(parsed) {
      if (this.isAgentWorkspace || !parsed) return
      this.userActionSequence = [
        ...this.userActionSequence,
        ...(parsed.userActionSequence || []),
      ]
      this.annotationRecords = [
        ...this.annotationRecords,
        ...(parsed.annotationRecords || []),
      ]
      const maxId = this.annotationRecords.reduce(
        (m, a) => (Number.isFinite(a?.id) && a.id > m ? a.id : m),
        -1
      )
      this._annotationSeqId = Math.max(
        Number.isFinite(parsed.annotationSeqId) ? parsed.annotationSeqId : 0,
        maxId + 1
      )
      this.showImportConflictDialog = false
      this.pendingImportPayload = null
      this.activeBottomTab = 'tree'
      this.scheduleLiveTraceSync(0)
    },
    applyImportedPayload(parsed) {
      if (!parsed || typeof parsed !== 'object') return
      this.userActionSequence = parsed.userActionSequence || []
      this.annotationRecords = parsed.annotationRecords || []
      this.studyInfo = {
        participantId: String(parsed.studyInfo?.participantId || ''),
        sessionOrder: String(parsed.studyInfo?.sessionOrder || ''),
        studyNotes: String(parsed.studyInfo?.studyNotes || ''),
      }
      this.analysisMilestones = Array.isArray(parsed.analysisMilestones) ? parsed.analysisMilestones : []
      this.chatbotLogs = Array.isArray(parsed.chatbotLogs) ? parsed.chatbotLogs : []
      this.llmAnalysisTrace = Array.isArray(parsed.llmAnalysisTrace) ? parsed.llmAnalysisTrace : []
      this.importedLlmAnalysis = parsed.llmAnalysis && typeof parsed.llmAnalysis === 'object'
        ? parsed.llmAnalysis
        : null
      if (parsed.currentState && typeof parsed.currentState === 'object') {
        this.applyCurrentState(parsed.currentState)
      }
      const maxId = this.annotationRecords.reduce(
        (m, a) => (Number.isFinite(a?.id) && a.id > m ? a.id : m),
        -1
      )
      this._annotationSeqId = Math.max(
        Number.isFinite(parsed.annotationSeqId) ? parsed.annotationSeqId : 0,
        maxId + 1
      )
      this.activeBottomTab = 'tree'
    },
    // ezio: replace current session with imported payload
    applyImport() {
      if (this.isAgentWorkspace) return
      const parsed = this.pendingImportPayload
      if (!parsed) return
      this.applyImportedPayload(parsed)
      this.showImportConflictDialog = false
      this.pendingImportPayload = null
      this.logUserAction('import_session', {
        actionCount: this.userActionSequence.length,
        annotationCount: this.annotationRecords.length,
        chatLogCount: this.chatbotLogs.length,
      })
      this.scheduleLiveTraceSync(0)
    },

    logUserAction(actionType, actionInfo = {}, userId = null) {
      if (this.isImportedWorkspace) return
      if (this.isAgentWorkspace) {
        if (actionType === 'cancel_hover') return
        this.scheduleWorkspaceStateSync()
        return
      }
      // If it's a cancel hover action, clear the timer and return
      if (actionType === 'cancel_hover') {
        const hoverTypeToCancel = actionInfo.hoverType;
        if (hoverTypeToCancel && this.hoverTimers[hoverTypeToCancel]) {
          clearTimeout(this.hoverTimers[hoverTypeToCancel]);
          this.hoverTimers[hoverTypeToCancel] = null;
        }
        return;
      }

      // Mark as zooming when a zoom action starts to suppress hovers and card scrolls
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

      // If we are currently zooming the K-line chart, the manipulation cards might automatically scroll 
      // due to alignment logic. We should ignore these auto-scrolls.
      if (this.isZooming && actionType === 'scroll_manipulation_cards') {
        return;
      }

      // Mark as scrolling cards to suppress manipulation card hovers
      if (actionType === 'scroll_manipulation_cards') {
        this.isScrollingCards = true;
        if (this.scrollCardsEndTimer) {
          clearTimeout(this.scrollCardsEndTimer);
        }
        // Assume scrolling is finished if no new scroll event arrives for 500ms
        this.scrollCardsEndTimer = setTimeout(() => {
          this.isScrollingCards = false;
        }, 500);
      }

      // For hover actions, implement a delay to avoid recording accidental fast fly-overs
      // Also, if the user is currently zooming (or recently zoomed), ignore hovers to prevent zoom misclicks
      // If the user is scrolling cards, ignore card hovers specifically
      if (actionType.startsWith('hover_')) {
        if (this.isZooming) {
          return; // Ignore hovers entirely during zoom operations
        }
        if (this.isScrollingCards && actionType === 'hover_manipulation_card') {
          return; // Ignore card hovers entirely during card scrolling operations
        }

        // Clear any existing timer for this specific hover type
        if (this.hoverTimers[actionType]) {
          clearTimeout(this.hoverTimers[actionType])
        }
        
        // We capture the timestamp at the moment the hover started
        const hoverStartTime = new Date().toISOString()
        
        // Set a new timer. Only log if the user hovers for more than the globally controlled threshold (3000ms)
        this.hoverTimers[actionType] = setTimeout(() => {
          // Double check zooming/scrolling state just in case it started while we were waiting
          if (this.isZooming) return;
          if (this.isScrollingCards && actionType === 'hover_manipulation_card') return;
          
          this._executeLogAction(actionType, actionInfo, userId, hoverStartTime)
        }, 3000) // 3 seconds global threshold for hovers
        
        return; // Exit early, the actual logging happens in the timeout
      }
      
      // For non-hover actions, execute immediately
      this._executeLogAction(actionType, actionInfo, userId)
    },
    
    _executeLogAction(actionType, actionInfo = {}, userId = null, customTimestamp = null) {
      const currentTimestamp = customTimestamp || new Date().toISOString()
      
      // If it's a zoom action, card scroll action, or hover action, try to merge with the previous action if it's also the same type.
      // For hovers, we merge purely based on consecutive matching types, regardless of time elapsed.
      // For navigation (zoom/scroll), we still enforce a 2-second time window for merging.
      if (actionType === 'zoom_kline_chart' || actionType === 'zoom_behavior_chart' || actionType === 'scroll_manipulation_cards' || actionType.startsWith('hover_')) {
        const lastAction = this.userActionSequence[this.userActionSequence.length - 1]
        
        if (lastAction && lastAction.actionType === actionType) {
          const isHoverAction = actionType.startsWith('hover_')
          
          let shouldMerge = false
          
          if (isHoverAction) {
            // Merge all consecutive hovers of the same type infinitely
            shouldMerge = true
          } else {
            // For zoom/scroll, enforce time limit
            const lastTime = new Date(lastAction.timestamp).getTime()
            const currentTime = new Date(currentTimestamp).getTime()
            if (currentTime - lastTime < 2000) {
              shouldMerge = true
            }
          }
          
          if (shouldMerge) {
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

            // ezio: for zoom / scroll merges, re-capture snapshot at the latest state; debounce
            // so only the final frame of a rapid burst is captured, and overwrite so the card
            // keeps only the latest screenshot instead of accumulating the whole burst
            if (actionType === 'zoom_kline_chart' || actionType === 'zoom_behavior_chart' || actionType === 'scroll_manipulation_cards') {
              if (this._snapshotRefreshTimer) clearTimeout(this._snapshotRefreshTimer)
              this._snapshotRefreshTimer = setTimeout(() => {
                this._maybeCaptureSnapshots(lastAction, { append: false })
              }, 400)
            }
            // ezio: for hover merges, append a fresh snapshot so every merged hover has its own thumbnail
            else if (isHoverAction) {
              this._maybeCaptureSnapshots(lastAction, { append: true })
            }
	            this.upsertUserActionEvent(lastAction, this.userActionSequence.length - 1)
	            return
	          }
        }
      }
      
      // Determine the current view state
      const currentViewState = this.buildStudySystemState()

      // Record the effect of the action
      // For cross-component interactions, check actionType or actionInfo for source and target
      let sourceView = 'system';
      let targetView = 'system';
      
      // Infer source and target views based on action types
      if (actionType.includes('kline_chart') || actionType === 'click_manipulation_card' || actionType === 'hover_manipulation_card' || actionType === 'click_kline_align_cards' || actionType === 'scroll_manipulation_cards' || actionType === 'hover_kline' || actionType === 'change_kline_granularity') {
        sourceView = 'kline_chart';
        targetView = (actionType.includes('zoom') || actionType === 'scroll_manipulation_cards' || actionType === 'hover_kline') ? 'kline_chart' : (actionType.includes('click_manipulation_card') ? 'behavior_details' : 'kline_chart');
      } else if (actionType.includes('behavior_chart') || actionType.includes('behavior_user_label') || actionType.includes('behavior_manipulation_box') || actionType === 'toggle_show_related_users' || actionType === 'toggle_show_manipulation_boxes' || actionType === 'toggle_sequential_time') {
        sourceView = 'behavior_details';
        targetView = 'behavior_details';
      } else if (actionType.includes('token_distribution') || actionType === 'select_user_from_network' || actionType === 'toggle_show_links' || actionType === 'scale_change') {
        sourceView = 'token_distribution';
        targetView = actionType.includes('select') ? 'behavior_details' : 'token_distribution';
      } else if (actionType.includes('snapshot') || actionType.includes('detection')) {
        sourceView = 'control_panel';
        targetView = 'all_views';
      } else if (actionType === 'change_coin') {
        sourceView = 'system';
        targetView = 'all_views';
      } else if (actionType === 'sync_time_window') {
        sourceView = actionInfo.source;
        targetView = actionInfo.source === 'kline_chart' ? 'behavior_details' : 'kline_chart';
      } else if (actionType === 'toggle_chat_panel' || actionType === 'chatbot_query' || actionType === 'analyze_with_me_trigger') {
        sourceView = 'chat'
        targetView = 'chat'
      } else if (actionType === 'switch_notes_panel_tab') {
        sourceView = actionInfo.view || 'tree'
        targetView = actionInfo.view || 'tree'
      } else if (actionType.includes('reasoning') || actionType.includes('llm_analysis')) {
        sourceView = 'llm_analysis'
        targetView = 'llm_analysis'
      }

      const normalizedView = this.normalizeStudyView(sourceView === 'system' ? targetView : sourceView)
      const targetObject = this.buildTargetObject(actionType, actionInfo)

      const actionRecord = {
        timestamp: currentTimestamp,
        userId: this.studyInfo.participantId || null,
        selectedHolderId: userId || this.selectedUser || null,
        condition: this.normalizeStudyCondition(),
        dataset: this.currentCoin,
        sessionOrder: this.studyInfo.sessionOrder || null,
        view: normalizedView,
        actionType: actionType,
        sourceView: sourceView,
        targetView: targetView,
        actionInfo: actionInfo,
        targetObject,
        currentSystemState: currentViewState,
        relatedViewWithViewState: currentViewState,
        actionEffect: `Triggered ${actionType}`
      }

      this.userActionSequence.push(actionRecord)
      console.log('User Action Logged:', actionRecord)
      if (sourceView !== targetView && sourceView !== 'system' && targetView !== 'all_views') {
        this.upsertMilestone('first_cross_view_transition', {
          actionType,
          sourceView: this.normalizeStudyView(sourceView),
          targetView: this.normalizeStudyView(targetView),
        })
      }
      this.markLatestAssistantResponseUsed('interaction', {
        actionType,
        view: normalizedView,
      })

      this._maybeCaptureSnapshots(actionRecord)
      this.upsertUserActionEvent(actionRecord, this.userActionSequence.length - 1)

      // Optional: Send to backend
      // fetch('/api/log_action', { method: 'POST', body: JSON.stringify(actionRecord) })
    },

    // ezio: lookup whether this actionType's category is currently enabled
    _isActionSnapshotEnabled(actionType) {
      for (const cat of this.snapshotCategories) {
        if (cat.actions.includes(actionType)) return cat.enabled
      }
      return false
    },

    // ezio: async screenshot capture; sourceSnapshot/targetSnapshot are arrays — one entry per capture.
    // append=true pushes onto the existing array (used for hover/zoom merges); otherwise overwrites with [snap].
    // If targetView is 'all_views', we fan out and capture kline_chart + token_distribution + behavior_details,
    // so actions like change_coin / run_*_detection / update_snapshot produce one thumbnail per view.
    _maybeCaptureSnapshots(actionRecord, { append = false } = {}) {
      if (!this._isActionSnapshotEnabled(actionRecord.actionType)) return
      if (this._snapshotCaptureInFlight) return
      const sourceCapturable = isCapturable(actionRecord.sourceView)
      const isAllViewsTarget = actionRecord.targetView === 'all_views'
      const targetCapturable = !isAllViewsTarget && actionRecord.targetView !== actionRecord.sourceView && isCapturable(actionRecord.targetView)
      // ezio: all_views fan-out re-enabled — it counts as capturable on its own branch below
      if (!sourceCapturable && !targetCapturable && !isAllViewsTarget) return

      this._snapshotCaptureInFlight = true
      const run = async () => {
        try {
          // ezio: pass actionType so viewSnapshot can pick DOM vs SVG capture (hover needs tooltip in PNG)
          const opts = { quality: this.snapshotQuality, candlestickRef: this.$refs.candlestickChart, actionType: actionRecord.actionType }
          if (sourceCapturable) {
            const snap = await captureViewByName(actionRecord.sourceView, opts)
            if (snap) {
              if (append && Array.isArray(actionRecord.sourceSnapshot)) {
                actionRecord.sourceSnapshot.push(snap)
              } else {
                actionRecord.sourceSnapshot = [snap]
              }
            }
          }
          // ezio: wait for target view's async update (fetch + D3 redraw) before capturing,
          // otherwise we snapshot the stale chart. System actions (all_views) chain 2-3 slow
          // backend calls (snapshot → detection → manipulation) that routinely exceed 3s, so
          // give them a 60s hang-guard. BehaviorDetails path keeps the original 3s.
          const waitForTargetReady = async () => {
            if (this._targetReadyPromise) {
              const timeoutMs = isAllViewsTarget ? 60000 : 3000
              const timeout = new Promise((resolve) => setTimeout(resolve, timeoutMs))
              await Promise.race([this._targetReadyPromise.catch(() => {}), timeout])
              await this.$nextTick()
            }
          }
          // ezio: all_views fan-out re-enabled — handlers now stash their async work on
          // _targetReadyPromise (chained through _awaitViewsSettled), so waitForTargetReady
          // blocks until the backend chain + view redraws actually finish.
          if (isAllViewsTarget) {
            await waitForTargetReady()
            const viewNames = ['kline_chart', 'token_distribution', 'behavior_details']
            if (!append || !Array.isArray(actionRecord.targetSnapshot)) {
              actionRecord.targetSnapshot = []
            }
            for (const viewName of viewNames) {
              const snap = await captureViewByName(viewName, opts)
              if (snap) actionRecord.targetSnapshot.push(snap)
            }
          } else if (targetCapturable) {
            await waitForTargetReady()
            const snap = await captureViewByName(actionRecord.targetView, opts)
            if (snap) {
              if (append && Array.isArray(actionRecord.targetSnapshot)) {
                actionRecord.targetSnapshot.push(snap)
              } else {
                actionRecord.targetSnapshot = [snap]
              }
            }
          }
	        } finally {
	          this._snapshotCaptureInFlight = false
	          this._targetReadyPromise = null // ezio: clear so next action starts fresh
	          this.upsertUserActionEvent(actionRecord)
	        }
	      }
      if (typeof window.requestIdleCallback === 'function') {
        window.requestIdleCallback(run, { timeout: 500 })
      } else {
        setTimeout(run, 0)
      }
    },

    // ezio: handlers for UI toggles in UserActionTimeline
	    onSnapshotCategoryToggle(key, enabled) {
	      const cat = this.snapshotCategories.find(c => c.key === key)
	      if (cat) {
	        cat.enabled = enabled
	        this.updateSessionSettingsEvent()
	      }
	    },
	    onSnapshotQualityChange(quality) {
	      this.snapshotQuality = quality
	      this.updateSessionSettingsEvent()
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
    async loadSnapshotTimesForCurrentCoin({ preserveSnapshotTime = false } = {}) {
      const requestedSnapshotTime = this.snapshot_configuration.time
      const response = await fetch(
        `/api/snapshot/times?coin=${encodeURIComponent(this.currentCoin)}`,
      )
      if (!response.ok) throw new Error('Failed to fetch snapshot times')
      const data = await response.json()
      const times = Array.isArray(data.times) ? data.times : []
      this.snapshotTimes = times

      if (times.length > 0) {
        if (preserveSnapshotTime && requestedSnapshotTime && times.includes(requestedSnapshotTime)) {
          this.snapshot_configuration.time = requestedSnapshotTime
        } else {
          // 每次切换币种重新加载时间时，强制选中最新（最后一个）时间
          this.snapshot_configuration.time = times[times.length - 1]
        }
      } else {
        this.snapshot_configuration.time = ''
      }
    },
    async initializeForCurrentCoin(options = {}) {
      await this.loadSnapshotTimesForCurrentCoin(options)
      await this.handleUpdateSnapshot({ ...this.snapshot_configuration })
    },
    // ezio: returns the fetch promise chain so callers can stash it on _targetReadyPromise;
    // trailing nextTicks make it resolve only after BehaviorDetails' drawChart has run.
    generateBehaviorDetailData() {
      if (!this.selectedUser) return Promise.resolve()
      const userSet = new Set([this.selectedUser])
      this.selectedEntityInfo = null

      // Expand via entity results
      if (this.entity_detection_results && Array.isArray(this.entity_detection_results)) {
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
      return fetch('/api/user_behavior/sequences', {
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
        // ezio: BehaviorDetails' watcher wraps drawChart in a $nextTick — wait two ticks so
        // the promise only resolves once the new SVG is actually in the DOM.
        .then(() => this.$nextTick())
        .then(() => this.$nextTick())
        .catch((err) => {
          console.error(
            'CryptoVis: failed to fetch user behavior sequences',
            err,
          )
        })
    },
    // ezio: resolves after Vue flushes the watcher (TokenDistribution/KlineChart redraw)
    // and D3 force simulation has had ~1s to settle. Used to gate all_views screenshot
    // capture for control-panel / change_coin actions so bubbles aren't still clumped
    // mid-simulation when the thumbnail is taken.
    _awaitViewsSettled() {
      return this.$nextTick()
        .then(() => this.$nextTick())
        .then(() => new Promise((resolve) => setTimeout(resolve, 1000)))
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
      // ezio: kick off the coin-init pipeline and stash the promise BEFORE logUserAction so
      // _maybeCaptureSnapshots (scheduled via requestIdleCallback) can't race ahead and
      // capture the blank / old chart. initializeForCurrentCoin → handleUpdateSnapshot will
      // overwrite _targetReadyPromise with its own inner work promise — that's fine, either
      // promise resolves after the same backend chain + view redraws.
      this.resetViewState()
      this.snapshotTimes = [] // 强制清空一下旧的时间列表，让它有重置的感觉
      const work = this.initializeForCurrentCoin().catch((error) => {
        console.error('CryptoVis: Error switching coin:', error)
      })
      this._targetReadyPromise = work.then(() => this._awaitViewsSettled())
      this.logUserAction('change_coin', { coin: this.currentCoin })
      await work
      if (this.isAgentWorkspace) this.scheduleWorkspaceStateSync(0)
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

      if (this.selectedCardUsers.length > 0) {
        const userSet = new Set(this.selectedCardUsers)
        // ezio: stash promise BEFORE logUserAction so _maybeCaptureSnapshots can await target redraw
        this._targetReadyPromise = fetch('/api/user_behavior/sequences', {
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
          // ezio: wait two ticks so BehaviorDetails' drawChart nextTick flushes before capture
          .then(() => this.$nextTick())
          .then(() => this.$nextTick())
          .catch((err) => {
            console.error(
              'CryptoVis: failed to fetch card user behavior sequences',
              err,
            )
          })
      } else {
        this.behaviorDetailData = null
        this._targetReadyPromise = null // ezio: nothing to await when card has no users
      }

      this.logUserAction('click_manipulation_card', { cardUsers: users })
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
      // ezio: wrap body in inner async fn + stash on _targetReadyPromise before logUserAction
      // so the screenshot waits for the full detection + (optional) manipulation chain to finish.
      const work = (async () => {
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
      })()

      this._targetReadyPromise = work.then(() => this._awaitViewsSettled())

      this.logUserAction('run_entity_detection', { config: this.entity_detection_configuration })

      await work
      if (this.isAgentWorkspace) this.scheduleWorkspaceStateSync(0)
    },
    async handleRequestManipulationDetection(newManipulationConfig) {
      console.log(
        'CryptoVis: Running manipulation detection only...',
        newManipulationConfig,
      )
      if (newManipulationConfig) {
        this.manipulation_detection_configuration = { ...newManipulationConfig }
      }
      // ezio: wrap body in inner async fn + stash on _targetReadyPromise before logUserAction
      // so the screenshot waits for the manipulation backend + view redraws.
      const work = (async () => {
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
      })()

      this._targetReadyPromise = work.then(() => this._awaitViewsSettled())

      this.logUserAction('run_manipulation_detection', { config: this.manipulation_detection_configuration })

      await work
      if (this.isAgentWorkspace) this.scheduleWorkspaceStateSync(0)
    },
    async handleUpdateSnapshot(newSnapshotConfig) {
      if (newSnapshotConfig) {
        this.snapshot_configuration = { ...newSnapshotConfig }
      }
      // ezio: extract body into an inner async fn so we can stash the promise on
      // _targetReadyPromise BEFORE logUserAction — screenshot capture will await the
      // full backend chain + view redraws instead of racing ahead on stale state.
      const work = (async () => {
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
      })()

      // ezio: must be set BEFORE logUserAction so _maybeCaptureSnapshots sees the promise
      this._targetReadyPromise = work.then(() => this._awaitViewsSettled())

      this.logUserAction('update_snapshot', { config: this.snapshot_configuration })

      await work
      if (this.isAgentWorkspace) this.scheduleWorkspaceStateSync(0)
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
      // ezio: wrap body in inner async fn + stash on _targetReadyPromise before logUserAction
      // so the screenshot waits for the link-detection backend + view redraws.
      const work = (async () => {
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
      })()

      this._targetReadyPromise = work.then(() => this._awaitViewsSettled())

      this.logUserAction('update_link_detection', { config: this.link_detection_configuration })

      await work
      if (this.isAgentWorkspace) this.scheduleWorkspaceStateSync(0)
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
    // ezio: init mouse position for snapshot shortcut (non-reactive to avoid perf overhead)
    this._mouseX = 0;
    this._mouseY = 0;
    // ezio: track mouse position for snapshot shortcut
    this._onMouseMove = (e) => {
      this._mouseX = e.clientX;
      this._mouseY = e.clientY;
    };
    document.addEventListener('mousemove', this._onMouseMove);
    // ezio: Alt+S (Mac: Option+S) keyboard shortcut to open snapshot for hovered view
    this._onKeyDown = (e) => {
      if (e.altKey && (e.key === 's' || e.key === 'ß' || e.key === 'S')) {
        e.preventDefault();
        this.openSnapshotByMouse();
      }
    };
    document.addEventListener('keydown', this._onKeyDown);
    this.installMajorViewApi()

    const initialWorkspaceReady = (async () => {
      await this.initializeManiScopeSession()
      const restoreState = this._workspaceRestoreState
      await this.initializeForCurrentCoin({ preserveSnapshotTime: !!restoreState?.snapshotTime })
      if (restoreState) {
        this.applyCurrentState(restoreState)
      }
      if (this.isAgentWorkspace) {
        this.startAgentTraceRefresh()
      }
      this.scheduleLiveTraceSync(0)
    })()
    this._initialWorkspaceReadyPromise = initialWorkspaceReady

    try {
      await initialWorkspaceReady
    } catch (error) {
      this._initialWorkspaceReadyError = error
      console.error('CryptoVis: Error during initial load:', error)
    } finally {
      this._initialWorkspaceReadySettled = true
    }
  },
  // ezio: cleanup snapshot shortcut listeners
	  beforeUnmount() {
	    if (this._liveTraceSyncTimer) clearTimeout(this._liveTraceSyncTimer)
	    if (this._agentTraceRefreshTimer) clearInterval(this._agentTraceRefreshTimer)
	    if (this._workspaceStateTimer) clearTimeout(this._workspaceStateTimer)
	    this.cleanupGlobalHandlers()
	  },
	  beforeDestroy() {
	    if (this._liveTraceSyncTimer) clearTimeout(this._liveTraceSyncTimer)
	    if (this._agentTraceRefreshTimer) clearInterval(this._agentTraceRefreshTimer)
	    if (this._workspaceStateTimer) clearTimeout(this._workspaceStateTimer)
	    this.cleanupGlobalHandlers()
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

/* AI chat toggle button in header */
.session-chip {
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #4a5568;
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 11px;
  line-height: 1.2;
  cursor: pointer;
}
.session-chip:hover {
  background: #edf2f7;
  border-color: #a0aec0;
}

.workspace-badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0;
  border: 1px solid transparent;
}

.workspace-human {
  background: #edf7ff;
  color: #1e5f9f;
  border-color: #bee3f8;
}

.workspace-agent {
  background: #f0fff4;
  color: #276749;
  border-color: #9ae6b4;
}

.workspace-baseline {
  background: #fff7ed;
  color: #9a3412;
  border-color: #fed7aa;
}

.workspace-imported {
  background: #eef2ff;
  color: #4338ca;
  border-color: #c7d2fe;
}

.imported-session-chip {
  cursor: default;
}

.workspace-link-tag {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  border: 1px solid #ddd6fe;
  background: #f5f3ff;
  color: #6d28d9;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.workspace-link-tag:hover {
  background: #ede9fe;
  border-color: #c4b5fd;
}

.ai-chat-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid #e2e8f0;
  background: #fff;
  cursor: pointer;
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  line-height: 1;
  padding: 0;
  flex-shrink: 0;
}
.ai-chat-btn:hover {
  border-color: #3182ce;
  background: #ebf8ff;
}
.ai-chat-btn.active {
  border-color: #3182ce;
  background: #3182ce;
}

/* 全局按钮面板和输入系样式覆盖 */
.checkbox {
  --n-color-checked: #4a5568 !important;
  --n-border-checked:  #4a5568 !important;
  --n-border-focus:  #4a5568 !important;
}
.n-switch {
  --n-rail-color-active: #4a5568 !important;
  --n-box-shadow-focus: 0 0 0 2px rgba(74, 85, 104, 0.2) !important;
}
.dataset_label{
  font-size: 15px;
  margin-left: 15%;
}

/* ezio: session import/export UI */
.session-io-btn {
  padding: 4px 12px;
  border: 1px solid #cbd5e0;
  background: #fff;
  color: #2d3748;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.15s;
}
.session-io-btn:hover {
  background: #edf2f7;
  border-color: #a0aec0;
}
.session-io-btn:disabled {
  color: #a0aec0;
  background: #f7fafc;
  border-color: #edf2f7;
  cursor: not-allowed;
}
.session-io-btn:disabled:hover {
  background: #f7fafc;
  border-color: #edf2f7;
}
.session-io-btn.primary {
  background: #3182ce;
  color: #fff;
  border-color: #3182ce;
}
.session-io-btn.primary:hover {
  background: #2b6cb0;
  border-color: #2b6cb0;
}
.session-io-btn.ghost {
  background: transparent;
  border-color: #e2e8f0;
}
.session-import-file-input {
  position: fixed;
  left: -10000px;
  top: auto;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}
.session-io-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}
.session-io-dialog {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
  width: 420px;
  max-width: 92vw;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.session-io-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #edf2f7;
}
.session-io-dialog-header h3 {
  margin: 0;
  font-size: 15px;
  color: #2d3748;
}
.session-io-close {
  border: none;
  background: none;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  color: #718096;
}
.session-io-dialog-body {
  padding: 16px;
  color: #2d3748;
  font-size: 13px;
}
.session-io-stats {
  display: flex;
  gap: 18px;
  margin-bottom: 12px;
  color: #4a5568;
}
.session-io-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.session-io-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #4a5568;
  font-size: 12px;
  font-weight: 600;
}
.session-io-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid #d8e0ec;
  border-radius: 6px;
  background: #fff;
  color: #1f2937;
  font-size: 13px;
}
.session-io-input:disabled {
  background: #f8fafc;
  color: #64748b;
}
.session-io-textarea {
  resize: vertical;
  min-height: 84px;
}
.session-io-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  padding: 6px 0;
}
.session-io-hint {
  color: #718096;
  font-size: 12px;
  line-height: 1.5;
}
.session-io-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 10px 16px;
  border-top: 1px solid #edf2f7;
  background: #f8fafc;
}
</style>
