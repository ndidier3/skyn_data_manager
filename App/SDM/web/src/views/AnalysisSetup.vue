<template>
  <div class="analysis-setup">
    <div class="settings-container">
      <h2>Analysis Setup</h2>
      
      <!-- Processing Mode -->
      <div class="form-group mb-4">
        <div class="form-check form-switch">
          <input class="form-check-input" type="checkbox" v-model="isBatchMode">
          <label class="form-check-label">Batch Processing</label>
        </div>
      </div>

      <!-- File Selection -->
      <div v-if="!isBatchMode">
        <div class="row">
          <div class="col-md-6">
            <div class="form-group">
              <label for="subid">Subject ID</label>
              <input type="text" class="form-control" id="subid" v-model="subid" required>
            </div>
          </div>
          <div class="col-md-6">
            <div class="form-group">
              <label for="datasetId">Dataset ID</label>
              <input type="text" class="form-control" id="datasetId" v-model="datasetId" required>
            </div>
          </div>
        </div>
      </div>

      <div v-else>
        <div class="form-group">
          <label for="inputFolder">Input Folder</label>
          <input type="text" class="form-control" id="inputFolder" v-model="inputFolder" required>
        </div>
      </div>

      <!-- Settings Tabs -->
      <ul class="nav nav-tabs settings-tabs" role="tablist">
        <li class="nav-item" v-for="tab in tabs" :key="tab.id">
          <a class="nav-link" 
             :class="{ active: activeTab === tab.id }"
             @click.prevent="activeTab = tab.id"
             href="#">
            {{ tab.name }}
          </a>
        </li>
      </ul>

      <div class="tab-content settings-tab-content">
        <!-- Gaps & Non-Wear Settings -->
        <div v-if="activeTab === 'gaps'" class="tab-content-section">
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
              <span class="status-label">Fill Gaps with Null Rows</span>
              <span class="status-badge">Not Complete</span>
            </div>
          </div>
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
              <span class="status-label">Detect Non-Wear</span>
              <span class="status-badge">Not Complete</span>
            </div>
            <div class="d-flex justify-content-between align-items-center mt-2">
              <label for="nonWearMethod" class="form-label mb-0">Non-Wear Method</label>
              <select
                class="form-select w-auto"
                id="nonWearMethod"
                v-model="settings.gaps_and_non_wear.non_wear_method"
                v-if="settings.gaps_and_non_wear.non_wear_method !== undefined"
                style="min-width: 100px;"
              >
                <option value="auto">Auto</option>
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
              <span class="status-badge">Not Complete</span>
            </div>
          </div>
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
              <span class="status-label">Impute Gaps</span>
              <span class="status-badge">Not Complete</span>
            </div>
          </div>
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
              <span class="status-label">Impute Non-Wear</span>
              <span class="status-badge">Not Complete</span>
            </div>
          </div>
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
              <span class="status-label">Impute Jumps</span>
              <span class="status-badge">Not Complete</span>
            </div>
          </div>
          <div class="status-item mb-3">
            <div class="d-flex justify-content-between align-items-center">
              <span class="status-label">Impute Plummets</span>
              <span class="status-badge">Not Complete</span>
            </div>
          </div>
        </div>

        <!-- Curve Analysis Settings -->
        <div v-if="activeTab === 'curve'" class="tab-content-section">
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

        <!-- Day Analysis Settings -->
        <div v-if="activeTab === 'day'" class="tab-content-section">
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

      <!-- Action Buttons -->
      <div class="mt-4">
        <button class="btn btn-secondary" @click="loadDefaults">Load Defaults</button>
        <button class="btn btn-primary" @click="startProcessing">Start Processing</button>
      </div>
    </div>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex'

export default {
  name: 'AnalysisSetup',
  data() {
    return {
      isBatchMode: false,
      subid: '',
      datasetId: '',
      inputFolder: '',
      activeTab: 'gaps',
      tabs: [
        { id: 'gaps', name: 'Gaps & Non-Wear' },
        { id: 'smooth', name: 'Smooth & Impute' },
        { id: 'curve', name: 'Curve Analysis' },
        { id: 'day', name: 'Day Analysis' }
      ]
    }
  },
  computed: {
    ...mapState({
      settings: state => state.settings.currentSettings
    }),
    curveFlagsWithParams() {
      // Return an array of { flag, params } for flags with at least one parameter
      const flags = this.settings.curve.flag_selections
      return Object.keys(flags)
        .filter(flag => this.getFlagParams(flag).length > 0)
        .map(flag => ({ flag, params: flags[flag] }))
    }
  },
  created() {
    // Load default settings when component is created
    this.loadDefaults()
  },
  methods: {
    ...mapActions({
      loadDefaultSettings: 'settings/loadDefaultSettings',
      createStudy: 'studies/createStudy',
      processStudy: 'studies/processStudy',
      showNotification: 'notifications/showNotification'
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
        await this.loadDefaultSettings()
        this.showNotification({
          title: 'Success',
          message: 'Default settings loaded successfully'
        })
      } catch (error) {
        this.showNotification({
          title: 'Error',
          message: 'Failed to load default settings',
          type: 'danger'
        })
      }
    },
    async startProcessing() {
      try {
        if (!this.isBatchMode) {
          if (!this.subid || !this.datasetId) {
            throw new Error('Subject ID and Dataset ID are required')
          }

          // Create study
          const study = await this.createStudy({
            name: `Study ${this.subid}_${this.datasetId}`,
            description: 'Single file processing',
            subid: this.subid,
            dataset_identifier: this.datasetId
          })

          // Process study
          await this.processStudy({
            studyId: study.study_id,
            options: {
              use_prior_save: false,
              smooth_and_impute: true,
              adjust_for_gaps_and_non_wear: true,
              analyze_days: true,
              identify_curves: true
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
          // TODO: Implement batch processing
          this.showNotification({
            title: 'Error',
            message: 'Batch processing not implemented yet',
            type: 'warning'
          })
        }
      } catch (error) {
        this.showNotification({
          title: 'Error',
          message: error.message,
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
</style> 