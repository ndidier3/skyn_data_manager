<template>
  <div class="analysis-setup">
    <div class="settings-container">
      <h2>Analysis Setup</h2>
      
      <!-- Processing Mode -->
      <div class="form-group mb-4">
        <div class="processing-mode-toggle">
          <label class="toggle-label">Single File</label>
          <div class="toggle-switch" @click="isBatchMode = !isBatchMode">
            <div class="toggle-slider" :class="{ 'batch-mode': isBatchMode }"></div>
          </div>
          <label class="toggle-label">Batch</label>
        </div>
      </div>

      <!-- File Selection -->
      <div v-if="!isBatchMode">
        <div class="file-selection mb-4">
          <div class="file-input-wrapper">
            <input 
              type="file" 
              ref="fileInput"
              class="file-input" 
              @change="handleFileSelect"
              accept=".csv,.xlsx,.xls"
              style="display: none;"
            >
            <div class="file-input-trigger" @click="$refs.fileInput.click()">
              <i class="fas fa-file-upload"></i>
              <span>{{ selectedFile ? selectedFile.name : 'Select File' }}</span>
            </div>
          </div>
          <div v-if="fileError" class="text-danger mt-2">
            {{ fileError }}
          </div>
          <div v-if="selectedFile" class="file-info mt-2">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <p class="mb-0"><strong>Subject ID:</strong> {{ extractedSubId }}</p>
              <span class="badge" :class="subjectStatus?.exists ? 'bg-success' : 'bg-secondary'">
                {{ subjectStatus?.exists ? 'Previously Processed' : 'New File' }}
              </span>
            </div>
            <div class="d-flex justify-content-between align-items-center mb-2">
              <p class="mb-0"><strong>Study ID:</strong> {{ extractedStudyId }}</p>
              <span class="badge" :class="studyStatus?.exists ? 'bg-success' : 'bg-secondary'">
                {{ studyStatus?.exists ? 'Registered Study' : 'New Study' }}
              </span>
            </div>
            <div v-if="hasPriorAnalysis" class="prior-analysis-info mt-3 p-2 border rounded">
              <p class="mb-2"><i class="fas fa-info-circle me-2"></i>Previous analysis found for this file</p>
              <div class="d-flex gap-2">
                <button class="btn btn-sm btn-outline-primary" @click="loadPriorAnalysis">
                  <i class="fas fa-history me-1"></i>Load Previous Analysis
                </button>
                <button class="btn btn-sm btn-outline-secondary" @click="startNewAnalysis">
                  <i class="fas fa-plus me-1"></i>Start New Analysis
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else>
        <BatchDirectorySelection
          :selected-directory.sync="selectedDirectory"
          :directory-error.sync="directoryError"
          :valid-files.sync="validFiles"
          :registered-studies="registeredStudies"
          :is-confirmed="isConfirmed"
          @directory-selected="handleDirectorySelect"
          @study-registered="handleStudyRegistered"
          @confirmed="isConfirmed = true"
          @revise="isConfirmed = false"
        />
      </div>

      <!-- Settings Tabs -->
      <div v-if="isConfirmed" class="settings-tabs-container">
      <ul class="nav nav-tabs settings-tabs" role="tablist">
        <li class="nav-item" v-for="tab in tabs" :key="tab.id">
          <a class="nav-link" 
             :class="{ active: activeTab === tab.id }"
             @click.prevent="activeTab = tab.id"
             href="#">
            {{ tab.name }}
              <span class="status-indicator" :class="processingStatus[tab.id].status">
                {{ processingStatus[tab.id].message }}
              </span>
          </a>
        </li>
      </ul>

      <div class="tab-content settings-tab-content">
        <!-- Gaps & Non-Wear Settings -->
        <div v-if="activeTab === 'gaps'" class="tab-content-section">
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
              <span class="status-label">Fill Gaps with Null Rows</span>
                <span class="status-badge" :class="processingStatus.gaps.status">
                  {{ processingStatus.gaps.message }}
                </span>
            </div>
          </div>
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
              <span class="status-label">Detect Non-Wear</span>
                <span class="status-badge" :class="processingStatus.gaps.status">
                  {{ processingStatus.gaps.message }}
                </span>
            </div>
            <div class="d-flex justify-content-between align-items-center mt-2">
              <label for="nonWearMethod" class="form-label mb-0">Non-Wear Method</label>
              <select
                class="form-select w-auto"
                id="nonWearMethod"
                v-model="settings.gaps_and_non_wear.non_wear_method"
                style="min-width: 100px;"
              >
                  <option :value="'auto'">Auto</option>
                <option v-for="n in 6" :key="n" :value="(n + 24).toString()">{{ n + 24 }}</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Smooth & Impute Settings -->
        <div v-if="activeTab === 'smooth'" class="tab-content-section">
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
              <span class="status-label">Median Smoothing</span>
                <span class="status-badge" :class="processingStatus.smooth.status">
                  {{ processingStatus.smooth.message }}
                </span>
            </div>
          </div>
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
              <span class="status-label">Impute Gaps</span>
                <span class="status-badge" :class="processingStatus.smooth.status">
                  {{ processingStatus.smooth.message }}
                </span>
            </div>
          </div>
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
              <span class="status-label">Impute Non-Wear</span>
                <span class="status-badge" :class="processingStatus.smooth.status">
                  {{ processingStatus.smooth.message }}
                </span>
              </div>
            </div>
            <div class="status-item mb-3">
              <div class="d-flex justify-content-between align-items-center">
                <span class="status-label">Impute Jumps</span>
                <span class="status-badge" :class="processingStatus.smooth.status">
                  {{ processingStatus.smooth.message }}
                </span>
            </div>
          </div>
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
                <span class="status-label">Impute Plummets</span>
                <span class="status-badge" :class="processingStatus.smooth.status">
                  {{ processingStatus.smooth.message }}
                </span>
              </div>
            </div>
          </div>

          <!-- Day Analysis Settings -->
          <div v-if="activeTab === 'day'" class="tab-content-section">
            <div class="form-check form-switch mb-3">
              <input class="form-check-input" 
                     type="checkbox" 
                     id="enableDayAnalysis"
                     v-model="settings.day.enabled">
              <label class="form-check-label" for="enableDayAnalysis">Run Day Analysis</label>
            </div>
            <div v-if="settings.day.enabled">
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
                  <span class="status-label">Day Analysis</span>
                  <span class="status-badge" :class="processingStatus.day.status">
                    {{ processingStatus.day.message }}
                  </span>
                </div>
              </div>
              <div class="form-group mb-3">
                <label for="dayStartHour">Day Start Hour</label>
                <input type="number" 
                       class="form-control" 
                       id="dayStartHour"
                       v-model.number="settings.day.day_start_hour">
              </div>
              <div class="form-check form-switch mb-3">
                <input class="form-check-input" 
                       type="checkbox" 
                       id="makeGraphs"
                       v-model="settings.day.make_graphs">
                <label class="form-check-label" for="makeGraphs">Make Graphs</label>
            </div>
          </div>
        </div>

        <!-- Curve Analysis Settings -->
        <div v-if="activeTab === 'curve'" class="tab-content-section">
            <div class="form-check form-switch mb-3">
              <input class="form-check-input" 
                     type="checkbox" 
                     id="enableCurveAnalysis"
                     v-model="settings.curve.enabled">
              <label class="form-check-label" for="enableCurveAnalysis">Run Curve Analysis</label>
            </div>
            <div v-if="settings.curve.enabled">
              <div class="status-item mb-3">
                <div class="d-flex justify-content-between align-items-center">
                  <span class="status-label">Curve Analysis</span>
                  <span class="status-badge" :class="processingStatus.curve.status">
                    {{ processingStatus.curve.message }}
                  </span>
                </div>
              </div>
          <div class="curve-flags-scroll">
            <div v-for="flagObj in curveFlagsWithParams" :key="flagObj.flag" class="status-item mb-3">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="status-label">{{ formatFlagName(flagObj.flag) }}</span>
                <span class="status-badge">Rule</span>
              </div>
              <div class="flag-params ms-2 mt-2">
                <div v-for="param in getFlagParams(flagObj.flag)" :key="param" class="flag-param-row mb-2">
                  <label :for="flagObj.flag + '-' + param" class="flag-param-label me-2">{{ formatParamName(param) }}:</label>
                  <select
                    class="form-select w-auto d-inline-block"
                    :id="flagObj.flag + '-' + param"
                    v-model="settings.curve.flag_selections[flagObj.flag][param]"
                    :style="'min-width: 80px;'"
                  >
                    <option value="off">Off</option>
                    <option v-for="opt in getParamOptions(param, settings.curve.flag_selections[flagObj.flag][param])" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="mt-4">
        <button class="btn btn-secondary" @click="loadDefaults">Load Defaults</button>
          <button class="btn btn-primary" @click="startProcessing" :disabled="isProcessing">
            {{ isProcessing ? 'Processing...' : 'Start Processing' }}
          </button>
        </div>
      </div>

      <div v-else class="text-center text-muted mt-4">
        <p v-if="!hasLoadedData">Please select a file or directory to begin</p>
        <button v-if="!hasLoadedData" class="btn btn-link text-muted p-0 mt-2" @click="loadPriorAnalysis">
          <i class="fas fa-history me-1"></i>or load prior analysis...
        </button>
      </div>
    </div>

    <StudyRegistrationModal
      :show.sync="showRegistrationModal"
      :study-id="extractedStudyId"
      :sub-id="extractedSubId"
      @study-registered="handleStudyRegistered"
      @proceed-to-analysis="handleProceedToAnalysis"
      @modal-canceled="handleModalCancel"
    ></StudyRegistrationModal>

    <!-- Add this after the StudyRegistrationModal component -->
    <div v-if="showBatchRegistrationModal" class="modal-backdrop" @click="closeBatchRegistration"></div>
    
    <div v-if="showBatchRegistrationModal" class="modal-container">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Register New Studies</h2>
          <button class="close-button" @click="closeBatchRegistration">&times;</button>
        </div>
        
        <div class="modal-body">
          <p class="mb-4">Found {{ batchStudies.length }} studies in the selected directory.</p>
          
          <div class="studies-table">
            <table class="table">
              <thead>
                <tr>
                  <th>Study ID</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="study in batchStudies" :key="study.studyId">
                  <td>{{ study.studyId }}</td>
                  <td>
                    <span class="badge" :class="study.exists ? 'bg-success' : 'bg-secondary'">
                      {{ study.exists ? 'Registered' : 'Not Registered' }}
                    </span>
                  </td>
                  <td>
                    <button 
                      v-if="!study.exists"
                      class="btn btn-primary btn-sm"
                      @click="registerBatchStudy(study)"
                    >
                      Register
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <div class="modal-footer mt-4">
            <button 
              class="btn btn-primary"
              :disabled="!canProceedWithBatch"
              @click="proceedWithBatch"
            >
              Proceed with Processing
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { mapState, mapActions, mapGetters } from 'vuex'
import axios from 'axios'
import StudyRegistrationModal from '@/components/StudyRegistrationModal.vue'
import ProcessingModeToggle from '@/components/ProcessingModeToggle.vue'
import FileSelection from '@/components/FileSelection.vue'
import BatchDirectorySelection from '@/components/BatchDirectorySelection.vue'
import AnalysisSettings from '@/components/AnalysisSettings.vue'

export default {
  name: 'AnalysisSetup',
  components: {
    ProcessingModeToggle,
    FileSelection,
    BatchDirectorySelection,
    AnalysisSettings,
    StudyRegistrationModal
  },
  data() {
    return {
      isBatchMode: false,
      selectedFile: null,
      selectedDirectory: '',
      fileError: null,
      directoryError: null,
      validFiles: [],
      hasPriorAnalysis: false,
      priorAnalysisInfo: null,
      studyStatus: null,
      subjectStatus: null,
      activeTab: 'gaps',
      showRegistrationModal: false,
      showBatchRegistrationModal: false,
      batchStudies: [],
      currentBatchStudy: null,
      registeredStudies: new Set(),
      tabs: [
        { id: 'gaps', name: 'Gaps & Non-Wear' },
        { id: 'smooth', name: 'Smooth & Impute' },
        { id: 'day', name: 'Day Analysis' },
        { id: 'curve', name: 'Curve Analysis' }
      ],
      isConfirmed: false
    }
  },
  computed: {
    ...mapState({
      settings: state => state.settings.currentSettings,
      processingStatus: state => state.studies.processingStatus
    }),
    ...mapGetters('studies', ['isProcessingComplete']),
    hasLoadedData() {
      return this.isBatchMode ? this.validFiles.length > 0 : (this.selectedFile && !this.fileError)
    },
    isProcessing() {
      return Object.values(this.processingStatus).some(
        status => status.status === 'processing'
      )
    },
    extractedSubId() {
      if (!this.selectedFile) return ''
      const filename = this.selectedFile.name
      const pattern = /^(\d{3,6})/
      const match = pattern.exec(filename)
      return match ? match[1] : ''
    },
    extractedStudyId() {
      if (!this.selectedFile) return ''
      try {
        const studyId = this.selectedFile.name.split('.')[0].split('_')[1]
        return studyId
      } catch {
        return ''
      }
    },
    curveFlagsWithParams() {
      // Return an array of { flag, params } for flags with at least one parameter
      const flags = this.settings.curve.flag_selections
      return Object.keys(flags)
        .filter(flag => this.getFlagParams(flag).length > 0)
        .map(flag => ({ flag, params: flags[flag] }))
    },
    canProceedWithBatch() {
      return this.batchStudies.every(study => study.exists)
    }
  },
  created() {
    // Load default settings when component is created
    this.loadDefaults()
    console.log('Initial settings:', this.settings)
  },
  watch: {
    settings: {
      handler(newSettings) {
        console.log('Settings updated:', newSettings)
        console.log('Non-wear method:', newSettings.gaps_and_non_wear.non_wear_method)
      },
      deep: true
    },
    'settings.gaps_and_non_wear.non_wear_method': {
      handler(newValue) {
        console.log('Non-wear method changed:', newValue)
      },
      immediate: true
    },
    studyStatus: {
      handler(newStatus) {
        console.log('Study status changed:', newStatus)
        if (newStatus?.exists) {
          // Ensure file details remain visible when study is registered
          this.$nextTick(() => {
            console.log('UI updated after study registration')
          })
        }
      },
      deep: true
    }
  },
  methods: {
    ...mapActions({
      loadDefaultSettings: 'settings/loadDefaultSettings',
      createStudy: 'studies/createStudy',
      processStudy: 'studies/processStudy',
      showNotification: 'notifications/showNotification',
      checkPriorAnalysis: 'studies/checkPriorAnalysis'
    }),
    getFlagParams(flag) {
      // Return all param keys except 'active' and those with empty values
      return Object.keys(this.settings.curve.flag_selections[flag]).filter(p => p !== 'active' && this.settings.curve.flag_selections[flag][p] !== undefined)
    },
    formatFlagName(flag) {
      // Convert snake_case to Title Case and remove trailing _curve/_periphery
      let name = flag.replace(/_/g, ' ')
      name = name.replace(/(curve|periphery)$/i, '')
      name = name.replace(/\s+/g, ' ').trim()
      return name.charAt(0).toUpperCase() + name.slice(1)
    },
    formatParamName(param) {
      // Convert snake_case to Title Case
      let name = param.replace(/_/g, ' ')
      return name.charAt(0).toUpperCase() + name.slice(1)
    },
    getParamOptions(param, value) {
      // Determine dropdown options based on param name and value type
      if (typeof value === 'number') {
        if (value >= 0 && value <= 1 && !Number.isInteger(value)) {
          // Float between 0.0 and 1.0
          const step = 0.05
          const opts = []
          for (let v = 0.0; v <= 1.0001; v += step) opts.push(Number(v.toFixed(2)))
          return opts
        } else if (param.includes('cutoff') || param.includes('duration')) {
          // Larger numbers, use step 0.25, 0.5, 5, or 10 depending on value
          let max = Math.max(10, value * 2)
          let min = 0
          let step = 1
          if (value < 2) step = 0.25
          else if (value < 10) step = 0.5
          else if (value < 100) step = 5
          else step = 10
          const opts = []
          for (let v = min; v <= max; v += step) opts.push(Number(v.toFixed(2)))
          return opts
        } else {
          // Generic number
          const opts = []
          for (let v = 0; v <= value * 2 + 10; v += 1) opts.push(v)
          return opts
        }
      } else if (typeof value === 'string') {
        // For string params, just return the current value
        return [value]
      } else {
        // Fallback
        return [value]
      }
    },
    async loadDefaults() {
      try {
        const defaultSettings = await this.loadDefaultSettings()
        console.log('Loaded default settings:', defaultSettings)
        
        // Ensure gaps_and_non_wear settings are properly initialized
        if (!this.settings.gaps_and_non_wear) {
          this.settings.gaps_and_non_wear = {
            export_excel: false,
            non_wear_method: 'auto',
            fill_gaps: true,
            detect_non_wear: true
          }
        } else if (this.settings.gaps_and_non_wear.non_wear_method === undefined) {
          this.settings.gaps_and_non_wear.non_wear_method = 'auto'
        }
        
        console.log('Final settings after initialization:', this.settings)
        this.showNotification({
          type: 'success',
          title: 'Success',
          message: 'Default settings loaded successfully',
          timeout: 4000 // Dismiss after 4 seconds
        })
      } catch (error) {
        console.error('Error loading default settings:', error)
        this.showNotification({
          type: 'error',
          title: 'Error',
          message: 'Failed to load default settings',
          requiresManualRemoval: true
        })
      }
    },
    async startProcessing() {
      try {
        if (!this.isBatchMode) {
          if (!this.selectedFile) {
            throw new Error('File is required')
          }

          // Check if study exists
          if (!this.studyStatus?.exists) {
            this.showRegistrationModal = true
            return
          }

          console.log('Starting processing...')
          // Process study
          await this.processStudy({
            studyId: this.studyStatus.study.study_id,
            options: {
              use_prior_save: false,
              smooth_and_impute: true,
              adjust_for_gaps_and_non_wear: true,
              analyze_days: this.settings.day.enabled,
              identify_curves: this.settings.curve.enabled
            },
            settings: this.settings
          })

          this.showNotification({
            title: 'Success',
            message: 'Processing started successfully'
          })

          // Navigate to results view
          this.$router.push('/results')
        } else {
          // Batch processing
          if (!this.selectedDirectory) {
            throw new Error('Directory is required')
          }

          // Get all files in directory
          const files = await this.getFilesInDirectory(this.selectedDirectory)
          const validFiles = files.filter(file => {
            const ext = file.name.split('.').pop().toLowerCase()
            return ['csv', 'xlsx', 'xls'].includes(ext)
          })

          if (validFiles.length === 0) {
            throw new Error('No valid files found in directory')
          }

          // Process each file
          for (const file of validFiles) {
            try {
              // Extract study and subject IDs
              const studyId = file.name.split('.')[0].split('_')[1]
              const subId = file.name.split('.')[0].split('_')[0]

              // Check if study exists
              const studyResponse = await axios.get(`/api/studies/${studyId}`)
              let study = studyResponse.data

              // If study doesn't exist, create it
              if (!study) {
                const createResponse = await axios.post('/api/studies', {
                  study_id: studyId,
                  name: `Study ${studyId}`,
                  description: `Automatically created from batch import`
                })
                study = createResponse.data
              }

              // Create SDM instance
              await axios.post('/api/studies/instances', {
                study_id: studyId,
                subid: subId,
                sdp_file_path: file.name
              })

              // Process the study
              await this.processStudy({
                studyId: studyId,
                options: {
                  use_prior_save: false,
                  smooth_and_impute: true,
                  adjust_for_gaps_and_non_wear: true,
                  analyze_days: this.settings.day.enabled,
                  identify_curves: this.settings.curve.enabled
                },
                settings: this.settings
              })
            } catch (error) {
              console.error(`Error processing file ${file.name}:`, error)
              this.showNotification({
                title: 'Error',
                message: `Failed to process ${file.name}: ${error.message}`,
                type: 'danger'
              })
            }
          }

          this.showNotification({
            title: 'Success',
            message: `Processed ${validFiles.length} files`
          })

          // Navigate to results view
          this.$router.push('/results')
        }
      } catch (error) {
        console.error('Error in startProcessing:', error)
        this.showNotification({
          title: 'Error',
          message: error.message || 'Failed to start processing',
          type: 'danger'
        })
      }
    },
    async loadPriorAnalysis() {
      try {
        if (!this.priorAnalysisInfo) {
          throw new Error('No prior analysis information available')
        }

        // Load the prior analysis settings and data
        await this.loadDefaultSettings()
        // TODO: Load the specific prior analysis data
        this.showNotification({
          title: 'Success',
          message: 'Prior analysis loaded successfully',
          type: 'success'
        })
      } catch (error) {
        this.showNotification({
          title: 'Error',
          message: error.message || 'Failed to load prior analysis',
          type: 'danger'
        })
      }
    },
    async startNewAnalysis() {
      this.hasPriorAnalysis = false
      this.priorAnalysisInfo = null
      await this.loadDefaultSettings()
      this.showNotification({
        title: 'Info',
        message: 'Starting new analysis with default settings',
        type: 'info'
      })
    },
    async handleStudyRegistered(studyData) {
      // Add the study to the registeredStudies Set
      this.registeredStudies.add(studyData.study_id)
      // Create a new Set to trigger reactivity
      this.registeredStudies = new Set(this.registeredStudies)
      
      // Update the studyStatus to reflect the newly registered study
      this.studyStatus = {
        exists: true,
        study: studyData
      }
      
      // Set isConfirmed to true to show the settings
      this.isConfirmed = true
      
      // Force a re-render of the BatchDirectorySelection component
      this.$nextTick(() => {
        this.$forceUpdate()
      })
      this.showNotification({
        type: 'success',
        title: 'Success',
        message: 'Study registered successfully',
        timeout: 4000
      })
    },
    handleProceedToAnalysis(study) {
      // Handle proceeding to analysis
      console.log('Proceeding to analysis for study:', study)
      // Add any additional logic you need
    },
    handleModalCancel() {
      // Clear the selected file and reset the file input
      this.selectedFile = null;
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = '';
      }
      this.showRegistrationModal = false;
      this.fileError = null;
      this.studyStatus = null;
      this.subjectStatus = null;
    },
    async handleFileSelect(event) {
      console.log('File select event triggered:', event);
      const file = event.target.files[0];
      console.log('Selected file:', file);
      if (!file) return;

      try {
        // Extract study identifier from filename
        const studyId = this.extractStudyId(file.name);
        const subId = this.extractSubId(file.name);
        console.log('Extracted study ID:', studyId);
        console.log('Extracted subject ID:', subId);
        
        if (!studyId || !subId) {
          this.fileError = 'Invalid filename format. Please ensure the filename follows the required structure.';
          return;
        }

        // Store the selected file and clear any errors
        this.selectedFile = file;
        this.fileError = null;
        
        // Only reset these if we're not coming from study registration
        if (!this.studyStatus?.exists) {
          this.hasPriorAnalysis = false;
          this.priorAnalysisInfo = null;
          this.studyStatus = null;
          this.subjectStatus = null;
        }

        // Check for prior study
        try {
          console.log('Checking for prior study...');
          const studyResponse = await axios.get(`/api/studies/check-prior/${studyId}`);
          console.log('Prior study response:', studyResponse.data);
          
          if (studyResponse.data.exists) {
            this.studyStatus = {
              exists: true,
              study: studyResponse.data.study
            };
            // Set isConfirmed to true since study is already registered
            this.isConfirmed = true;
          } else {
            console.log('New study detected, showing registration modal');
            this.studyStatus = {
              exists: false,
              message: 'New Study'
            };
            this.showRegistrationModal = true;
            return; // Stop here and wait for modal submission
          }

          // Check for prior subject analysis
          console.log('Checking for prior subject analysis...');
          const subjectResponse = await axios.get(`/api/studies/check-subject/${studyId}/${subId}`);
          console.log('Prior subject response:', subjectResponse.data);
          
          if (subjectResponse.data.exists) {
            this.subjectStatus = {
              exists: true,
              instance: subjectResponse.data.instance
            };
          } else {
            this.subjectStatus = {
              exists: false,
              message: 'New File'
            };
          }

          // If both exist, show the prior analysis dialog
          if (this.studyStatus.exists && this.subjectStatus.exists) {
            const date = new Date(this.subjectStatus.instance.created_at).toLocaleDateString();
            const time = new Date(this.subjectStatus.instance.created_at).toLocaleTimeString();
            
            if (confirm(`This file was previously processed on ${date} at ${time}.\n\nWould you like to load the previous analysis?`)) {
              await this.loadPriorAnalysis();
            }
          }
        } catch (error) {
          console.error('Error checking prior analysis:', error);
          if (error.response) {
            if (error.response.status === 503) {
              this.fileError = 'Database connection failed. Please check your database configuration.';
              console.error('Database connection error:', error.response.data.details);
            } else {
              this.fileError = error.response.data.error || 'Error checking for prior analysis. Please try again.';
              console.error('Server error:', error.response.data.details);
            }
          } else if (error.request) {
            this.fileError = 'No response from server. Please check your connection.';
            console.error('No response received:', error.request);
          } else {
            this.fileError = 'Error setting up request. Please try again.';
            console.error('Request setup error:', error.message);
          }
        }
      } catch (error) {
        console.error('Error processing file:', error);
        this.fileError = 'Error processing file. Please try again.';
      }
    },
    async handleDirectorySelect(event) {
      // The actual directory selection is now handled by BatchDirectorySelection
      // This method is kept for any additional processing needed at the parent level
      console.log('Directory selected:', this.selectedDirectory)
    },
    validateFilename(filename) {
      const subid = this.extractSubId(filename)
      const studyId = this.extractStudyId(filename)
      return this.isSubIdValid(subid) && this.isStudyIdValid(studyId)
    },
    extractSubId(filename) {
      const pattern = /^(\d{3,6})/
      const match = pattern.exec(filename)
      return match ? match[1] : ''
    },
    extractStudyId(filename) {
      try {
        return filename.split('.')[0].split('_')[1]
      } catch {
        return ''
      }
    },
    isSubIdValid(subid) {
      return (2 < subid.length) && (7 > subid.length) && /^\d+$/.test(subid)
    },
    isStudyIdValid(studyId) {
      return studyId.length === 3 && /^\d+$/.test(studyId) && studyId !== '000'
    },
    registerBatchStudy(study) {
      this.currentBatchStudy = study
      this.showRegistrationModal = true
    },
    closeBatchRegistration() {
      this.showBatchRegistrationModal = false
      this.batchStudies = []
    },
    async proceedWithBatch() {
      if (!this.canProceedWithBatch) return

      try {
        // First, check which studies need to be registered
        const studyIds = new Set()
        this.validFiles.forEach(file => {
          const studyId = this.extractStudyId(file)
          if (studyId) studyIds.add(studyId)
        })

        // Check each study's registration status
        for (const studyId of studyIds) {
          if (!this.registeredStudies.has(studyId)) {
            try {
              const response = await axios.get(`/api/studies/${studyId}`)
              if (response.data) {
                // Study exists in database, add to registeredStudies
                this.registeredStudies.add(studyId)
              } else {
                // Study doesn't exist, show registration modal
                this.currentBatchStudy = { studyId, exists: false }
                this.showRegistrationModal = true
                return // Stop processing until study is registered
              }
            } catch (error) {
              console.error(`Error checking study ${studyId}:`, error)
              this.showNotification({
                title: 'Error',
                message: `Failed to check study ${studyId}: ${error.message}`,
                type: 'danger'
              })
              return
            }
          }
        }

        // Process each file
        for (const file of this.validFiles) {
          try {
            // Extract study and subject IDs
            const studyId = this.extractStudyId(file)
            const subId = this.extractSubId(file)

            // Create SDM instance
            await axios.post('/api/studies/instances', {
              study_id: studyId,
              subid: subId,
              sdp_file_path: file
            })

            // Process the study
            await this.processStudy({
              studyId: studyId,
              options: {
                use_prior_save: false,
                smooth_and_impute: true,
                adjust_for_gaps_and_non_wear: true,
                analyze_days: this.settings.day.enabled,
                identify_curves: this.settings.curve.enabled
              },
              settings: this.settings
            })
          } catch (error) {
            console.error(`Error processing file ${file}:`, error)
            this.showNotification({
              title: 'Error',
              message: `Failed to process ${file}: ${error.message}`,
              type: 'danger'
            })
          }
        }

        this.showNotification({
          title: 'Success',
          message: `Processed ${this.validFiles.length} files`
        })

        // Close the modal and navigate to results
        this.closeBatchRegistration()
        this.$router.push('/results')
      } catch (error) {
        console.error('Error in batch processing:', error)
        this.showNotification({
          title: 'Error',
          message: error.message || 'Failed to process batch',
          type: 'danger'
        })
      }
    }
  }
}
</script>

<style scoped>
.settings-container {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,.1);
  padding: 20px;
  margin-bottom: 20px;
}

.settings-tabs {
  margin-bottom: 20px;
}

.settings-tab-content {
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 0 0 8px 8px;
  min-height: 200px;
}

.form-group {
  margin-bottom: 1rem;
}

.nav-tabs .nav-link {
  cursor: pointer;
}

.nav-tabs .nav-link.active {
  background-color: #f8f9fa;
  border-bottom-color: #f8f9fa;
}

.status-item {
  background-color: white;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #dee2e6;
}

.status-label {
  font-weight: 500;
  color: #495057;
}

.status-badge {
  background-color: #e9ecef;
  color: #6c757d;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.875rem;
}

.form-select {
  width: 100%;
  padding: 0.375rem 0.75rem;
  font-size: 1rem;
  font-weight: 400;
  line-height: 1.5;
  color: #212529;
  background-color: #fff;
  border: 1px solid #ced4da;
  border-radius: 0.25rem;
  transition: border-color .15s ease-in-out,box-shadow .15s ease-in-out;
}

.form-select:focus {
  border-color: #86b7fe;
  outline: 0;
  box-shadow: 0 0 0 0.25rem rgba(13,110,253,.25);
}

.tab-content-section {
  /* Add any custom styles for tab content here if needed */
}

.status-item .form-label {
  font-weight: 500;
  color: #495057;
  margin-bottom: 0;
}

.curve-flags-scroll {
  max-height: 400px;
  overflow-y: auto;
  padding-right: 8px;
}
.flag-params {
  font-size: 0.95em;
  color: #555;
}
.flag-param-row {
  display: flex;
  align-items: center;
  margin-bottom: 2px;
}
.flag-param-label {
  font-weight: 500;
}
.flag-param-value {
  font-family: monospace;
}

.status-indicator {
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 12px;
  margin-left: 8px;
}

.status-badge.not_started {
  background-color: #e9ecef;
  color: #6c757d;
}

.status-badge.processing {
  background-color: #fff3cd;
  color: #856404;
}

.status-badge.completed {
  background-color: #d4edda;
  color: #155724;
}

.status-badge.error {
  background-color: #f8d7da;
  color: #721c24;
}

.processing-mode-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.toggle-label {
  font-weight: 500;
  color: #495057;
  margin: 0;
  font-size: 0.875rem;
}

.toggle-switch {
  position: relative;
  width: 48px;
  height: 24px;
  background-color: #e9ecef;
  border-radius: 12px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.toggle-switch:hover {
  background-color: #dee2e6;
}

.toggle-slider {
  position: absolute;
  width: 20px;
  height: 20px;
  background-color: #fff;
  border-radius: 50%;
  top: 2px;
  left: 2px;
  transition: transform 0.3s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.toggle-slider.batch-mode {
  transform: translateX(24px);
}

.file-selection,
.directory-selection {
  border: 2px dashed #dee2e6;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
}

.file-input-wrapper,
.directory-input-wrapper {
  position: relative;
}

.file-input,
.directory-input {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  opacity: 0;
  cursor: pointer;
}

.file-input-trigger,
.directory-input-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.file-input-trigger:hover,
.directory-input-trigger:hover {
  background-color: #e9ecef;
}

.file-info,
.directory-info {
  text-align: left;
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
}

.valid-files-list {
  max-height: 200px;
  overflow-y: auto;
  margin-top: 0.5rem;
}

.valid-file-item {
  padding: 0.25rem 0;
  font-size: 0.875rem;
  color: #495057;
  border-bottom: 1px solid #dee2e6;
}

.valid-file-item:last-child {
  border-bottom: none;
}

.badge {
  font-size: 0.75rem;
  padding: 0.35em 0.65em;
  font-weight: 500;
}

.bg-success {
  background-color: #198754 !important;
}

.bg-secondary {
  background-color: #6c757d !important;
}
</style> 