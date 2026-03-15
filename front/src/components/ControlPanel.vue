<template>
    <div style="padding: 15px; height: 100%; display: flex; flex-direction: column; gap: 10px; overflow-y: auto;">
        <!-- Snapshot Configuration -->
        <div style="font-weight: bold; border-bottom: 1px solid #eee; padding-bottom: 5px;">Snapshot Configuration</div>
        <div style="display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-end;">
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <label style="font-size: 12px; font-weight: bold;">Snapshot Time</label>
                <select v-if="snapshotTimes && snapshotTimes.length > 0" v-model="snapshotConfig.time" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; min-width: 200px;">
                    <option v-for="time in snapshotTimes" :key="time" :value="time">{{ time }}</option>
                </select>
                <input v-else type="text" v-model="snapshotConfig.time" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; min-width: 200px;" placeholder="YYYY-MM-DD HH:mm:ss UTC">
            </div>
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <label style="font-size: 12px; font-weight: bold;">Top Holders Threshold</label>
                <input type="number" v-model.number="snapshotConfig.top_holder_threshold" step="0.01" min="0" max="1" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 80px;">
            </div>
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <label style="font-size: 12px; font-weight: bold;">Related User Threshold</label>
                <input type="number" v-model.number="snapshotConfig.related_user_threshold" step="0.01" min="0" max="1" style="padding: 5px; border: 1px solid #ccc; border-radius: 4px; width: 80px;">
            </div>
            <button @click="$emit('update-snapshot')" :disabled="loading" style="padding: 8px 15px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; height: 36px;">
                {{ loading ? 'Loading...' : 'Update View' }}
            </button>
        </div>

        <!-- Entity Detection Configuration -->
        <div style="border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;">
            <div style="font-weight: bold;">Entity Detection</div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <button @click="$emit('run-detection')" :disabled="loading" style="padding: 5px 15px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 12px;">
                    {{ loading ? 'Detecting...' : 'Run Detection' }}
                </button>
                <span v-if="lastResultCount !== null" style="color: #666; font-size: 12px;">
                    Last Result: {{ lastResultCount }} groups
                </span>
            </div>
        </div>
        
        <div style="display: flex; flex-direction: column; gap: 5px;">
            <!-- Network Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleSection('entity_network')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display:flex; align-items:center; gap:5px;" @click.stop>
                        <input type="checkbox" v-model="entityConfig.enable_network_based">
                        <span>Network Based</span>
                    </div>
                    <span>{{ activeSection === 'entity_network' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeSection === 'entity_network'" style="padding: 10px; display: flex; flex-direction: column; gap: 10px;">
                    <!-- Time Range Removed as it is not in configuration -->

                    <div style="display: flex; align-items: center; gap: 10px;">
                         <label style="font-size: 12px; display: flex; align-items: center; gap: 5px; cursor: pointer;">
                            <input type="checkbox" v-model="entityConfig.transfer_network_based_params.enable_direct_transfer">
                            <span>Direct Transfer</span>
                        </label>
                    </div>

                    <div style="height: 1px; background: #eee; margin: 2px 0;"></div>

                    <!-- Threshold Rules -->
                    <div style="display: flex; gap: 10px;">
                        <div style="flex: 1; display: flex; flex-direction: column; gap: 5px;">
                             <label style="font-size: 12px; display: flex; align-items: center; gap: 5px; cursor: pointer;">
                                <input type="checkbox" v-model="entityConfig.transfer_network_based_params.direct_transfer_params.enable_min_count">
                                <span>Min Tx Count</span>
                            </label>
                            <input type="number" v-model.number="entityConfig.transfer_network_based_params.direct_transfer_params.min_tx_count" min="1" :disabled="!entityConfig.transfer_network_based_params.direct_transfer_params.enable_min_count" style="padding: 4px; border: 1px solid #ccc; border-radius: 4px; width: 100%;">
                        </div>
                        <div style="flex: 1; display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; display: flex; align-items: center; gap: 5px; cursor: pointer;">
                                <input type="checkbox" v-model="entityConfig.transfer_network_based_params.direct_transfer_params.enable_min_volume">
                                <span>Min Volume</span>
                            </label>
                            <input type="number" v-model.number="entityConfig.transfer_network_based_params.direct_transfer_params.min_tx_volume" min="0" :disabled="!entityConfig.transfer_network_based_params.direct_transfer_params.enable_min_volume" style="padding: 4px; border: 1px solid #ccc; border-radius: 4px; width: 100%;">
                        </div>
                    </div>

                    <div style="height: 1px; background: #eee; margin: 2px 0;"></div>

                    <!-- Pattern Rules -->
                    <div style="display: flex; flex-direction: column; gap: 5px;">
                        <div style="display: flex; align-items: center; justify-content: flex-start; gap: 15px; flex-wrap: wrap;">
                            <label style="font-size: 12px; display: flex; align-items: center; gap: 5px; cursor: pointer;">
                                <input type="checkbox" v-model="entityConfig.transfer_network_based_params.enable_funding_relationship">
                                <span>Funding Relationship</span>
                            </label>
                            <label style="display: flex; align-items: center; gap: 5px; font-size: 12px; cursor: pointer;">
                                <input type="checkbox" v-model="entityConfig.transfer_network_based_params.enable_same_sender">
                                <span>Same Sender</span>
                            </label>
                            <label style="display: flex; align-items: center; gap: 5px; font-size: 12px; cursor: pointer;">
                                <input type="checkbox" v-model="entityConfig.transfer_network_based_params.enable_same_recipient">
                                <span>Same Recipient</span>
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Similarity Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleSection('entity_similarity')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display:flex; align-items:center; gap:5px;" @click.stop>
                        <input type="checkbox" v-model="entityConfig.enable_similarity_based">
                        <span>Similarity Based</span>
                    </div>
                    <span>{{ activeSection === 'entity_similarity' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeSection === 'entity_similarity'" style="padding: 10px;">
                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <!-- Trading Action Sequence -->
                        <div style="display: flex; flex-direction: column; gap: 5px; padding-bottom: 5px; border-bottom: 1px dashed #eee;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <input type="checkbox" v-model="entityConfig.similarity_based_params.enable_trading_action_sequence">
                                <span style="font-weight: bold; font-size: 12px;">Trading Action Sequence</span>
                            </div>
                            <div v-if="entityConfig.similarity_based_params.enable_trading_action_sequence" style="display: flex; flex-direction: column; gap: 5px; padding-left: 20px;">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Type:</label>
                                    <select v-model="entityConfig.similarity_based_params.trading_action_sequence_params.type" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 120px; font-size: 11px;">
                                        <option value="action_only">Action Only</option>
                                        <option value="action_amount">Action + Amount</option>
                                        <option value="action_price">Action + Price</option>
                                        <option value="action_amount_price">Action + Amt + Price</option>
                                    </select>
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Min Seq Length:</label>
                                    <input type="number" v-model.number="entityConfig.similarity_based_params.trading_action_sequence_params.min_seq_length" min="2" step="1" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Max Time Diff:</label>
                                    <input type="number" v-model.number="entityConfig.similarity_based_params.trading_action_sequence_params.max_time_diff" min="0" step="1" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                                </div>
                            </div>
                        </div>

                        <!-- Balance Sequence -->
                        <div style="display: flex; flex-direction: column; gap: 5px; padding-bottom: 5px; border-bottom: 1px dashed #eee;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <input type="checkbox" v-model="entityConfig.similarity_based_params.enable_balance_sequence">
                                <span style="font-weight: bold; font-size: 12px;">Balance Sequence</span>
                            </div>
                            <div v-if="entityConfig.similarity_based_params.enable_balance_sequence" style="display: flex; flex-direction: column; gap: 5px; padding-left: 20px;">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Granularity:</label>
                                    <select v-model="entityConfig.similarity_based_params.balance_sequence_params.balance_granularity" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                                        <option value="1Min">1Min</option>
                                        <option value="1H">1H</option>
                                        <option value="1D">1D</option>
                                    </select>
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Similarity:</label>
                                    <input type="number" v-model.number="entityConfig.similarity_based_params.balance_sequence_params.balance_similarity_threshold" min="0" max="1" step="0.05" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                                </div>
                            </div>
                        </div>

                        <!-- Earning Sequence -->
                        <div style="display: flex; flex-direction: column; gap: 5px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <input type="checkbox" v-model="entityConfig.similarity_based_params.enable_earning_sequence">
                                <span style="font-weight: bold; font-size: 12px;">Earning Sequence</span>
                            </div>
                            <div v-if="entityConfig.similarity_based_params.enable_earning_sequence" style="display: flex; flex-direction: column; gap: 5px; padding-left: 20px;">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Granularity:</label>
                                    <select v-model="entityConfig.similarity_based_params.earning_sequence_params.earning_granularity" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                                        <option value="1Min">1Min</option>
                                        <option value="1H">1H</option>
                                        <option value="1D">1D</option>
                                    </select>
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Similarity:</label>
                                    <input type="number" v-model.number="entityConfig.similarity_based_params.earning_sequence_params.earning_similarity_threshold" min="0" max="1" step="0.05" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Entity Manipulation Based -->
             <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleSection('entity_manipulation')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display:flex; align-items:center; gap:5px;" @click.stop>
                        <input type="checkbox" v-model="entityConfig.enable_manipulation_based">
                        <span>Manipulation Based</span>
                    </div>
                    <span>{{ activeSection === 'entity_manipulation' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeSection === 'entity_manipulation'" style="padding: 10px; display: flex; flex-direction: column; gap: 10px;">
                     <div style="display: flex; align-items: center; gap: 10px;">
                        <label style="font-size: 11px; width: 120px;">Max Time Diff:</label>
                        <input type="number" v-model.number="entityConfig.manipulation_based_params.max_manipulation_time_diff" min="0" step="1" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                    </div>
                </div>
            </div>
        </div>

        <!-- Manipulation Detection Configuration -->
        <div style="border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;">
            <div style="font-weight: bold;">Manipulation Detection</div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <button @click="$emit('request-manipulation-detection')" :disabled="loadingManipulation" style="padding: 5px 15px; background: #FF9800; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 12px;">
                    {{ loadingManipulation ? 'Detecting...' : 'Run Detection' }}
                </button>
            </div>
        </div>
        
        <div style="display: flex; flex-direction: column; gap: 5px;">
            <!-- Round Trip -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleManipulationSection('round_trip')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display:flex; align-items:center; gap:5px;" @click.stop>
                         <input type="checkbox" v-model="manipulationConfig.enable_round_trip_detection">
                        <span>Round Trip</span>
                    </div>
                    <span>{{ activeManipulationSection === 'round_trip' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeManipulationSection === 'round_trip'" style="padding: 10px; display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <label style="font-size: 11px; width: 120px;">Max Time Diff:</label>
                        <input type="number" v-model.number="manipulationConfig.round_trip_params.max_time_diff" min="0" step="1" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <label style="font-size: 11px; width: 120px;">Max Position Diff:</label>
                        <input type="number" v-model.number="manipulationConfig.round_trip_params.max_position_diff" min="0" step="1" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <label style="font-size: 11px; width: 120px;">Max Earning:</label>
                        <input type="number" v-model.number="manipulationConfig.round_trip_params.max_earning" min="0" step="0.1" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                         <label style="font-size: 11px; display: flex; align-items: center; gap: 5px; cursor: pointer;">
                            <input type="checkbox" v-model="manipulationConfig.round_trip_params.enable_entity_based">
                            <span>Enable Entity Based</span>
                        </label>
                    </div>
                </div>
            </div>

            <!-- Same Direction -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleManipulationSection('same_direction')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display:flex; align-items:center; gap:5px;" @click.stop>
                         <input type="checkbox" v-model="manipulationConfig.enable_same_direction_detection">
                        <span>Same Direction</span>
                    </div>
                    <span>{{ activeManipulationSection === 'same_direction' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeManipulationSection === 'same_direction'" style="padding: 10px; display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <label style="font-size: 11px; width: 120px;">Max Time Diff:</label>
                        <input type="number" v-model.number="manipulationConfig.same_direction_params.max_time_diff" min="0" step="1" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <label style="font-size: 11px; width: 120px;">Min Seq Length:</label>
                        <input type="number" v-model.number="manipulationConfig.same_direction_params.min_seq_length" min="2" step="1" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <label style="font-size: 11px; width: 120px;">Max Diff Direction:</label>
                        <input type="number" v-model.number="manipulationConfig.same_direction_params.max_diff_direction" min="0" step="1" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                         <label style="font-size: 11px; display: flex; align-items: center; gap: 5px; cursor: pointer;">
                            <input type="checkbox" v-model="manipulationConfig.same_direction_params.enable_entity_based">
                            <span>Enable Entity Based</span>
                        </label>
                    </div>
                </div>
            </div>
        </div>

        <!-- Link Detection Configuration -->
        <div style="border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;">
            <div style="font-weight: bold;">Link Configuration</div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <button @click="$emit('update-links')" :disabled="loadingLinks" style="padding: 5px 15px; background: #9C27B0; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 12px;">
                    {{ loadingLinks ? 'Updating...' : 'Update Links' }}
                </button>
            </div>
        </div>
        
        <div style="display: flex; flex-direction: column; gap: 5px;">
             <!-- Link Network Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleLinkSection('link_network')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display:flex; align-items:center; gap:5px;" @click.stop>
                        <input type="checkbox" v-model="linkConfig.enable_network_based">
                        <span>Network Based</span>
                    </div>
                    <span>{{ activeLinkSection === 'link_network' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeLinkSection === 'link_network'" style="padding: 10px; display: flex; flex-direction: column; gap: 10px;">
                     <!-- Time Range Removed as it is not in configuration -->

                    <div style="display: flex; align-items: center; gap: 10px;">
                         <label style="font-size: 12px; display: flex; align-items: center; gap: 5px; cursor: pointer;">
                            <input type="checkbox" v-model="linkConfig.transfer_network_based_params.enable_direct_transfer">
                            <span>Direct Transfer</span>
                        </label>
                    </div>

                    <div style="height: 1px; background: #eee; margin: 2px 0;"></div>

                    <!-- Threshold Rules -->
                    <div style="display: flex; gap: 10px;">
                        <div style="flex: 1; display: flex; flex-direction: column; gap: 5px;">
                             <label style="font-size: 12px; display: flex; align-items: center; gap: 5px; cursor: pointer;">
                                <input type="checkbox" v-model="linkConfig.transfer_network_based_params.direct_transfer_params.enable_min_count">
                                <span>Min Tx Count</span>
                            </label>
                            <input type="number" v-model.number="linkConfig.transfer_network_based_params.direct_transfer_params.min_tx_count" min="1" :disabled="!linkConfig.transfer_network_based_params.direct_transfer_params.enable_min_count" style="padding: 4px; border: 1px solid #ccc; border-radius: 4px; width: 100%;">
                        </div>
                        <div style="flex: 1; display: flex; flex-direction: column; gap: 5px;">
                            <label style="font-size: 12px; display: flex; align-items: center; gap: 5px; cursor: pointer;">
                                <input type="checkbox" v-model="linkConfig.transfer_network_based_params.direct_transfer_params.enable_min_volume">
                                <span>Min Volume</span>
                            </label>
                            <input type="number" v-model.number="linkConfig.transfer_network_based_params.direct_transfer_params.min_tx_volume" min="0" :disabled="!linkConfig.transfer_network_based_params.direct_transfer_params.enable_min_volume" style="padding: 4px; border: 1px solid #ccc; border-radius: 4px; width: 100%;">
                        </div>
                    </div>

                    <div style="height: 1px; background: #eee; margin: 2px 0;"></div>

                    <!-- Pattern Rules -->
                    <div style="display: flex; flex-direction: column; gap: 5px;">
                        <div style="display: flex; align-items: center; justify-content: flex-start; gap: 15px; flex-wrap: wrap;">
                            <label style="font-size: 12px; display: flex; align-items: center; gap: 5px; cursor: pointer;">
                                <input type="checkbox" v-model="linkConfig.transfer_network_based_params.enable_funding_relationship">
                                <span>Funding Relationship</span>
                            </label>
                            <label style="display: flex; align-items: center; gap: 5px; font-size: 12px; cursor: pointer;">
                                <input type="checkbox" v-model="linkConfig.transfer_network_based_params.enable_same_sender">
                                <span>Same Sender</span>
                            </label>
                            <label style="display: flex; align-items: center; gap: 5px; font-size: 12px; cursor: pointer;">
                                <input type="checkbox" v-model="linkConfig.transfer_network_based_params.enable_same_recipient">
                                <span>Same Recipient</span>
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Link Similarity Based -->
            <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleLinkSection('link_similarity')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display:flex; align-items:center; gap:5px;" @click.stop>
                        <input type="checkbox" v-model="linkConfig.enable_similarity_based">
                        <span>Similarity Based</span>
                    </div>
                    <span>{{ activeLinkSection === 'link_similarity' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeLinkSection === 'link_similarity'" style="padding: 10px;">
                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <!-- Trading Action Sequence -->
                        <div style="display: flex; flex-direction: column; gap: 5px; padding-bottom: 5px; border-bottom: 1px dashed #eee;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <input type="checkbox" v-model="linkConfig.similarity_based_params.enable_trading_action_sequence">
                                <span style="font-weight: bold; font-size: 12px;">Trading Action Sequence</span>
                            </div>
                            <div v-if="linkConfig.similarity_based_params.enable_trading_action_sequence" style="display: flex; flex-direction: column; gap: 5px; padding-left: 20px;">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Type:</label>
                                    <select v-model="linkConfig.similarity_based_params.trading_action_sequence_params.type" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 120px; font-size: 11px;">
                                        <option value="action_only">Action Only</option>
                                        <option value="action_amount">Action + Amount</option>
                                        <option value="action_price">Action + Price</option>
                                        <option value="action_amount_price">Action + Amt + Price</option>
                                    </select>
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Min Seq Length:</label>
                                    <input type="number" v-model.number="linkConfig.similarity_based_params.trading_action_sequence_params.min_seq_length" min="2" step="1" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Max Time Diff:</label>
                                    <input type="number" v-model.number="linkConfig.similarity_based_params.trading_action_sequence_params.max_time_diff" min="0" step="1" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                                </div>
                            </div>
                        </div>

                        <!-- Balance Sequence -->
                        <div style="display: flex; flex-direction: column; gap: 5px; padding-bottom: 5px; border-bottom: 1px dashed #eee;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <input type="checkbox" v-model="linkConfig.similarity_based_params.enable_balance_sequence">
                                <span style="font-weight: bold; font-size: 12px;">Balance Sequence</span>
                            </div>
                            <div v-if="linkConfig.similarity_based_params.enable_balance_sequence" style="display: flex; flex-direction: column; gap: 5px; padding-left: 20px;">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Granularity:</label>
                                    <select v-model="linkConfig.similarity_based_params.balance_sequence_params.balance_granularity" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                                        <option value="1Min">1Min</option>
                                        <option value="1H">1H</option>
                                        <option value="1D">1D</option>
                                    </select>
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Similarity:</label>
                                    <input type="number" v-model.number="linkConfig.similarity_based_params.balance_sequence_params.balance_similarity_threshold" min="0" max="1" step="0.05" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                                </div>
                            </div>
                        </div>

                        <!-- Earning Sequence -->
                        <div style="display: flex; flex-direction: column; gap: 5px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <input type="checkbox" v-model="linkConfig.similarity_based_params.enable_earning_sequence">
                                <span style="font-weight: bold; font-size: 12px;">Earning Sequence</span>
                            </div>
                            <div v-if="linkConfig.similarity_based_params.enable_earning_sequence" style="display: flex; flex-direction: column; gap: 5px; padding-left: 20px;">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Granularity:</label>
                                    <select v-model="linkConfig.similarity_based_params.earning_sequence_params.earning_granularity" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                                        <option value="1Min">1Min</option>
                                        <option value="1H">1H</option>
                                        <option value="1D">1D</option>
                                    </select>
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <label style="font-size: 11px; width: 100px;">Similarity:</label>
                                    <input type="number" v-model.number="linkConfig.similarity_based_params.earning_sequence_params.earning_similarity_threshold" min="0" max="1" step="0.05" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

             <!-- Link Manipulation Based -->
             <div style="border: 1px solid #eee; border-radius: 4px; overflow: hidden;">
                <div @click="toggleLinkSection('link_manipulation')" style="padding: 10px; background: #f9f9f9; cursor: pointer; font-weight: bold; font-size: 13px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display:flex; align-items:center; gap:5px;" @click.stop>
                        <input type="checkbox" v-model="linkConfig.enable_manipulation_based">
                        <span>Manipulation Based</span>
                    </div>
                    <span>{{ activeLinkSection === 'link_manipulation' ? '▼' : '►' }}</span>
                </div>
                <div v-if="activeLinkSection === 'link_manipulation'" style="padding: 10px; display: flex; flex-direction: column; gap: 10px;">
                     <div style="display: flex; align-items: center; gap: 10px;">
                        <label style="font-size: 11px; width: 120px;">Max Time Diff:</label>
                        <input type="number" v-model.number="linkConfig.manipulation_based_params.max_manipulation_time_diff" min="0" step="1" style="padding: 3px; border: 1px solid #ccc; border-radius: 4px; width: 60px;">
                    </div>
                </div>
            </div>

        </div>
    </div>
</template>

<script>
export default {
    name: "ControlPanel",
    props: {
        loading: {
            type: Boolean,
            default: false
        },
        loadingLinks: {
            type: Boolean,
            default: false
        },
        loadingManipulation: {
            type: Boolean,
            default: false
        },
        lastResultCount: {
            type: Number,
            default: null
        },
        snapshotTimes: {
            type: Array,
            default: () => []
        },
        snapshotConfig: {
            type: Object,
            required: true
        },
        entityConfig: {
            type: Object,
            required: true
        },
        linkConfig: {
            type: Object,
            required: true
        },
        manipulationConfig: {
            type: Object,
            required: true
        }
    },
    data() {
        return {
            // UI State
            activeSection: 'entity_network', 
            activeManipulationSection: 'round_trip',
            activeLinkSection: 'link_network',
        }
    },
    methods: {
        toggleSection(section) {
            this.activeSection = this.activeSection === section ? '' : section;
        },
        toggleManipulationSection(section) {
            this.activeManipulationSection = this.activeManipulationSection === section ? '' : section;
        },
        toggleLinkSection(section) {
            this.activeLinkSection = this.activeLinkSection === section ? '' : section;
        }
    }
}
</script>
