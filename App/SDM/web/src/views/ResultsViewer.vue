<template>
  <div class="results-viewer">
    <div class="d-flex">
      <!-- Study Selection Button -->
      <button class="btn btn-primary mb-3" @click="showStudySelection = true">
        Select Studies
      </button>
    </div>

    <div class="d-flex">
      <!-- Navigation Sidebar -->
      <div class="nav-sidebar">
        <div class="instance-list">
          <div v-for="instance in selectedInstances" 
               :key="`${instance.study_id}_${instance.subid}`"
               class="instance-item"
               :class="{ 'selected': selectedInstance && selectedInstance.instance_id === instance.instance_id }"
               @click="selectInstance(instance)">
            <div class="instance-header">
              <span class="study-id">Study {{ instance.study_id }}</span>
              <span class="badge" :class="getStatusClass(instance.processing_status)">
                {{ instance.processing_status }}
              </span>
            </div>
            <div class="instance-details">
              <span class="subid">Subject {{ instance.subid }}</span>
              <span class="date">{{ formatDate(instance.instance_created_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Results Content -->
      <div class="results-content">
        <div v-if="selectedInstance" class="instance-details-panel">
          <h3>Study {{ selectedInstance.study_id }} - Subject {{ selectedInstance.subid }}</h3>
          <div class="status-info">
            <span class="badge" :class="getStatusClass(selectedInstance.processing_status)">
              {{ selectedInstance.processing_status }}
            </span>
            <span class="date">Processed: {{ formatDate(selectedInstance.instance_last_updated) }}</span>
          </div>
          
          <!-- Results Tabs -->
          <ul class="nav nav-tabs mt-3">
            <li class="nav-item" v-for="tab in tabs" :key="tab.id">
              <a class="nav-link" 
                 :class="{ 
                   active: activeTab === tab.id,
                   'disabled': !isAnalysisEnabled(tab.id)
                 }"
                 @click="activeTab = tab.id"
                 href="#">
                {{ tab.name }}
                <span v-if="!isAnalysisEnabled(tab.id)" class="badge not-run-badge ms-2">Not Run</span>
              </a>
            </li>
          </ul>

          <div class="tab-content mt-3">
            <transition name="fade" mode="out-in">
              <div :key="activeTab" class="tab-pane">
                <!-- Days Tab -->
                <div v-show="activeTab === 'days'">
                  <div v-if="isAnalysisEnabled('days')">
                    <div v-if="dayResults && dayResults.length > 0">
                      <DayResultsTable :results="dayResults" />
                    </div>
                    <div v-else class="no-results">
                      <p>No day analysis results available.</p>
                    </div>
                  </div>
                  <div v-else class="analysis-disabled">
                    <p>Day analysis was not enabled for this instance.</p>
                    <button class="btn btn-primary" @click="reprocessWithAnalysis('days')">
                      Run Day Analysis
                    </button>
                  </div>
                </div>

                <!-- Curves Tab -->
                <div v-show="activeTab === 'curves'">
                  <div v-if="isAnalysisEnabled('curves')">
                    <div v-if="curveResults && curveResults.length > 0">
                      <CurveResultsTable :results="curveResults" />
                    </div>
                    <div v-else class="no-results">
                      <p>No curve analysis results available.</p>
                    </div>
                  </div>
                  <div v-else class="analysis-disabled">
                    <p>Curve analysis was not enabled for this instance.</p>
                    <button class="btn btn-primary" @click="reprocessWithAnalysis('curves')">
                      Run Curve Analysis
                    </button>
                  </div>
                </div>

                <!-- Events Tab -->
                <div v-show="activeTab === 'events'">
                  <div v-if="isAnalysisEnabled('events')">
                    <div v-if="eventResults && eventResults.length > 0">
                      <EventResultsTable :results="eventResults" />
                    </div>
                    <div v-else class="no-results">
                      <p>No event analysis results available.</p>
                    </div>
                  </div>
                  <div v-else class="analysis-disabled">
                    <p>Event analysis was not enabled for this instance.</p>
                    <button class="btn btn-primary" @click="reprocessWithAnalysis('events')">
                      Run Event Analysis
                    </button>
                  </div>
                </div>
              </div>
            </transition>
          </div>
        </div>
        <div v-else class="no-selection">
          <p>Select a study instance to view results</p>
        </div>
      </div>
    </div>

    <!-- Study Selection Modal -->
    <StudySelectionModal
      :show.sync="showStudySelection"
      :studies="studies"
      @selection-confirmed="handleStudySelection"
    />
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex'
import StudySelectionModal from '@/components/StudySelectionModal.vue'
import DayResultsTable from '@/components/DayResultsTable.vue'
import CurveResultsTable from '@/components/CurveResultsTable.vue'
import EventResultsTable from '@/components/EventResultsTable.vue'

export default {
  name: 'ResultsViewer',
  components: {
    StudySelectionModal,
    DayResultsTable,
    CurveResultsTable,
    EventResultsTable
  },
  data() {
    return {
      showStudySelection: false,
      selectedInstances: [],
      selectedInstance: null,
      activeTab: 'days',
      tabs: [
        { id: 'days', name: 'Days' },
        { id: 'curves', name: 'Curves' },
        { id: 'events', name: 'Events' }
      ],
      pollingInterval: null,
      processingPollInterval: null,
      analysisSettings: {
        day: { enabled: false },
        curve: { enabled: false }
      },
      processingStatus: {
        gaps_and_non_wear: 'not_attempted',
        smooth_and_impute: 'not_attempted',
        identify_curves: 'not_attempted',
        analyze_days: 'not_attempted',
        match_events: 'not_attempted',
        analyze_curves: 'not_attempted',
        export_results: 'not_attempted'
      },
      errors: {},
      isProcessing: false
    }
  },
  computed: {
    ...mapState({
      studies: state => state.studies.list,
      dayResults: state => state.studies.dayResults,
      curveResults: state => state.studies.curveResults,
      eventResults: state => state.studies.eventResults
    }),
    hasErrors() {
      return Object.values(this.errors).some(errorList => errorList.length > 0)
    },
    processingComplete() {
      return Object.values(this.processingStatus).every(status => 
        status === 'success' || status === 'failed'
      )
    }
  },
  watch: {
    'selectedInstance': {
      immediate: true,
      handler(newInstance) {
        if (newInstance) {
          this.updateAnalysisSettings()
        }
      }
    }
  },
  created() {
    this.fetchStudies()
    this.startPolling()
  },
  beforeDestroy() {
    this.stopPolling()
    this.stopProcessingPoll()
  },
  methods: {
    ...mapActions({
      fetchStudies: 'studies/fetchStudies',
      fetchStudyDetails: 'studies/fetchStudyDetails',
      processStudy: 'studies/processStudy'
    }),
    startPolling() {
      this.pollingInterval = setInterval(() => {
        this.fetchStudies()
      }, 5000) // Poll every 5 seconds
    },
    stopPolling() {
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval)
        this.pollingInterval = null
      }
    },
    handleStudySelection(selectedStudies) {
      this.selectedInstances = selectedStudies
      if (selectedStudies.length > 0) {
        this.selectInstance(selectedStudies[0])
      }
    },
    async updateAnalysisSettings() {
      if (!this.selectedInstance?.study_id) return
      
      try {
        const details = await this.fetchStudyDetails(this.selectedInstance.study_id)
        console.log('Study Details Response:', details)
        console.log('Raw settings from details:', details?.settings)
        console.log('Raw status from details:', details?.status)
        
        // Update processing status
        if (details?.status) {
          this.processingStatus = details.status
          console.log('Updated processing status:', this.processingStatus)
        }
        
        // Update errors
        if (details?.errors) {
          this.errors = details.errors
          console.log('Updated errors:', this.errors)
        }
        
        // Update settings
        if (details?.settings) {
          const settings = details.settings
          console.log('Processing settings:', settings)
          this.$set(this.analysisSettings, 'day', { 
            enabled: Boolean(settings.day?.enabled) 
          })
          this.$set(this.analysisSettings, 'curve', { 
            enabled: Boolean(settings.curve?.enabled) 
          })
          console.log('Updated analysis settings:', this.analysisSettings)
        }
        
        console.log('Final state:', {
          processingStatus: this.processingStatus,
          errors: this.errors,
          analysisSettings: this.analysisSettings
        })
      } catch (error) {
        console.error('Error updating analysis settings:', error)
      }
    },
    async selectInstance(instance) {
      if (!instance || !instance.study_id) return
      this.selectedInstance = instance
      await this.updateAnalysisSettings()
    },
    getStatusClass(status) {
      switch (status) {
        case 'completed':
          return 'bg-success'
        case 'processing':
          return 'bg-warning'
        case 'error':
          return 'bg-danger'
        default:
          return 'bg-secondary'
      }
    },
    formatDate(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleString()
    },
    isAnalysisEnabled(analysisType) {
      if (!this.selectedInstance || !this.analysisSettings) {
        console.log('Analysis check failed:', {
          hasInstance: !!this.selectedInstance,
          hasSettings: !!this.analysisSettings,
          analysisType
        })
        return false
      }
      
      let isEnabled = false
      switch (analysisType) {
        case 'days':
          isEnabled = Boolean(this.analysisSettings.day?.enabled) && 
                     this.processingStatus.analyze_days === 'success'
          console.log('Days analysis check:', {
            settingsEnabled: Boolean(this.analysisSettings.day?.enabled),
            status: this.processingStatus.analyze_days,
            isEnabled
          })
          break
        case 'curves':
          isEnabled = Boolean(this.analysisSettings.curve?.enabled) && 
                     this.processingStatus.identify_curves === 'success'
          console.log('Curves analysis check:', {
            settingsEnabled: Boolean(this.analysisSettings.curve?.enabled),
            status: this.processingStatus.identify_curves,
            isEnabled
          })
          break
        case 'events':
          isEnabled = Boolean(this.analysisSettings.curve?.enabled) && 
                     this.processingStatus.match_events === 'success'
          console.log('Events analysis check:', {
            settingsEnabled: Boolean(this.analysisSettings.curve?.enabled),
            status: this.processingStatus.match_events,
            isEnabled
          })
          break
      }
      
      return isEnabled
    },
    async reprocessWithAnalysis(analysisType) {
      if (!this.selectedInstance) return
      
      const settings = {
        day: { enabled: Boolean(this.analysisSettings.day?.enabled) },
        curve: { enabled: Boolean(this.analysisSettings.curve?.enabled) }
      }
      
      // Enable the requested analysis
      switch (analysisType) {
        case 'days':
          settings.day.enabled = true
          break
        case 'curves':
        case 'events':
          settings.curve.enabled = true
          break
      }
      
      console.log('Reprocessing with settings:', settings)
      
      try {
        this.isProcessing = true
        const result = await this.processStudy({
          studyId: this.selectedInstance.study_id,
          options: {
            use_prior_save: true,
            smooth_and_impute: true,
            adjust_for_gaps_and_non_wear: true,
            analyze_days: settings.day.enabled,
            identify_curves: settings.curve.enabled
          },
          settings
        })
        console.log('Process study result:', result)
        
        // Start polling for status updates
        this.startProcessingPoll()
        
        // Immediately update the local settings
        if (analysisType === 'days') {
          this.$set(this.analysisSettings, 'day', { enabled: true })
        } else if (analysisType === 'curves' || analysisType === 'events') {
          this.$set(this.analysisSettings, 'curve', { enabled: true })
        }
        
        // Update status from result
        if (result.status) {
          this.processingStatus = result.status
        }
        if (result.settings) {
          this.updateSettingsFromResult(result.settings)
        }
        
      } catch (error) {
        console.error('Error reprocessing:', error)
        this.isProcessing = false
      }
    },
    
    startProcessingPoll() {
      // Clear any existing polling
      this.stopProcessingPoll()
      
      // Start new polling
      this.processingPollInterval = setInterval(async () => {
        if (!this.selectedInstance) {
          this.stopProcessingPoll()
          return
        }
        
        try {
          const details = await this.fetchStudyDetails(this.selectedInstance.study_id)
          console.log('Processing poll update:', details)
          
          if (details?.status) {
            this.processingStatus = details.status
          }
          if (details?.settings) {
            this.updateSettingsFromResult(details.settings)
          }
          
          // Check if processing is complete
          const isComplete = Object.values(this.processingStatus).every(status => 
            status === 'success' || status === 'failed'
          )
          
          if (isComplete) {
            console.log('Processing complete, stopping poll')
            this.stopProcessingPoll()
            this.isProcessing = false
          }
        } catch (error) {
          console.error('Error polling processing status:', error)
          this.stopProcessingPoll()
          this.isProcessing = false
        }
      }, 2000) // Poll every 2 seconds
    },
    
    stopProcessingPoll() {
      if (this.processingPollInterval) {
        clearInterval(this.processingPollInterval)
        this.processingPollInterval = null
      }
    },
    
    updateSettingsFromResult(settings) {
      if (settings.day_attrs) {
        this.$set(this.analysisSettings, 'day', {
          enabled: Boolean(settings.day_attrs.enabled)
        })
      }
      if (settings.curve_attrs) {
        this.$set(this.analysisSettings, 'curve', {
          enabled: Boolean(settings.curve_attrs.enabled)
        })
      }
    }
  }
}
</script>

<style scoped>
.results-viewer {
  padding: 20px;
}

.nav-sidebar {
  width: 300px;
  border-right: 1px solid #dee2e6;
  padding-right: 20px;
  margin-right: 20px;
}

.instance-list {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.instance-item {
  padding: 12px;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.instance-item:hover {
  background-color: #f8f9fa;
}

.instance-item.selected {
  background-color: #e9ecef;
  border-color: #adb5bd;
}

.instance-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.study-id {
  font-weight: 600;
}

.instance-details {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  color: #6c757d;
}

.results-content {
  flex: 1;
  padding: 20px;
}

.instance-details-panel {
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,.1);
}

.status-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.date {
  color: #6c757d;
  font-size: 0.875rem;
}

.no-selection {
  text-align: center;
  color: #6c757d;
  padding: 40px;
}

.badge {
  font-size: 0.75rem;
  padding: 0.35em 0.65em;
}

.nav-tabs {
  border-bottom: 1px solid #dee2e6;
}

.nav-tabs .nav-link {
  cursor: pointer;
  border: none;
  color: #495057;
  padding: 8px 16px;
}

.nav-tabs .nav-link.active {
  color: #0d6efd;
  border-bottom: 2px solid #0d6efd;
}

.tab-content {
  padding: 20px 0;
}

.nav-link.disabled {
  color: #6c757d;
  cursor: not-allowed;
  opacity: 0.7;
  position: relative;
}

.not-run-badge {
  background-color: #dc3545;
  color: white;
  font-size: 0.75rem;
  padding: 0.35em 0.65em;
  border-radius: 12px;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(220, 53, 69, 0.2);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.4);
  }
  70% {
    box-shadow: 0 0 0 6px rgba(220, 53, 69, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0);
  }
}

.analysis-disabled {
  text-align: center;
  padding: 40px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.analysis-disabled p {
  color: #6c757d;
  margin-bottom: 20px;
}

.no-results {
  text-align: center;
  padding: 40px;
  background-color: #f8f9fa;
  border-radius: 8px;
  color: #6c757d;
}

/* Add these new styles */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.tab-pane {
  position: relative;
}

.nav-link {
  cursor: pointer;
  user-select: none;
}

.nav-link.disabled {
  pointer-events: none;
}
</style> 