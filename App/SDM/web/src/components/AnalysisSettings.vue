<template>
  <div class="settings-tabs-container">
    <ul class="nav nav-tabs settings-tabs" role="tablist">
      <li class="nav-item" v-for="tab in tabs" :key="tab.id">
        <a class="nav-link" 
           :class="{ active: activeTab === tab.id }"
           @click.prevent="$emit('update:activeTab', tab.id)"
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
              v-model="localSettings.gaps_and_non_wear.non_wear_method"
              style="min-width: 100px;"
              @change="updateSettings"
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
                 v-model="localSettings.day.enabled"
                 @change="updateSettings">
          <label class="form-check-label" for="enableDayAnalysis">Run Day Analysis</label>
        </div>
        <div v-if="localSettings.day.enabled">
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
                   v-model.number="localSettings.day.day_start_hour"
                   @change="updateSettings">
          </div>
          <div class="form-check form-switch mb-3">
            <input class="form-check-input" 
                   type="checkbox" 
                   id="makeGraphs"
                   v-model="localSettings.day.make_graphs"
                   @change="updateSettings">
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
                 v-model="localSettings.curve.enabled"
                 @change="updateSettings">
          <label class="form-check-label" for="enableCurveAnalysis">Run Curve Analysis</label>
        </div>
        <div v-if="localSettings.curve.enabled">
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
                    v-model="localSettings.curve.flag_selections[flagObj.flag][param]"
                    :style="'min-width: 80px;'"
                    @change="updateSettings"
                  >
                    <option value="off">Off</option>
                    <option v-for="opt in getParamOptions(param, localSettings.curve.flag_selections[flagObj.flag][param])" :key="opt" :value="opt">{{ opt }}</option>
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
      <button class="btn btn-secondary" @click="$emit('load-defaults')">Load Defaults</button>
      <button class="btn btn-primary" @click="$emit('start-processing')" :disabled="isProcessing">
        {{ isProcessing ? 'Processing...' : 'Start Processing' }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AnalysisSettings',
  props: {
    settings: {
      type: Object,
      required: true
    },
    processingStatus: {
      type: Object,
      required: true
    },
    activeTab: {
      type: String,
      required: true
    },
    isProcessing: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      localSettings: JSON.parse(JSON.stringify(this.settings)),
      tabs: [
        { id: 'gaps', name: 'Gaps & Non-Wear' },
        { id: 'smooth', name: 'Smooth & Impute' },
        { id: 'day', name: 'Day Analysis' },
        { id: 'curve', name: 'Curve Analysis' }
      ]
    }
  },
  computed: {
    curveFlagsWithParams() {
      const flags = this.localSettings.curve.flag_selections
      return Object.keys(flags)
        .filter(flag => this.getFlagParams(flag).length > 0)
        .map(flag => ({ flag, params: flags[flag] }))
    }
  },
  methods: {
    updateSettings() {
      this.$emit('update:settings', this.localSettings)
    },
    getFlagParams(flag) {
      return Object.keys(this.localSettings.curve.flag_selections[flag])
        .filter(p => p !== 'active' && this.localSettings.curve.flag_selections[flag][p] !== undefined)
    },
    formatFlagName(flag) {
      let name = flag.replace(/_/g, ' ')
      name = name.replace(/(curve|periphery)$/i, '')
      name = name.replace(/\s+/g, ' ').trim()
      return name.charAt(0).toUpperCase() + name.slice(1)
    },
    formatParamName(param) {
      let name = param.replace(/_/g, ' ')
      return name.charAt(0).toUpperCase() + name.slice(1)
    },
    getParamOptions(param, value) {
      if (typeof value === 'number') {
        if (value >= 0 && value <= 1 && !Number.isInteger(value)) {
          const step = 0.05
          const opts = []
          for (let v = 0.0; v <= 1.0001; v += step) opts.push(Number(v.toFixed(2)))
          return opts
        } else if (param.includes('cutoff') || param.includes('duration')) {
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
          const opts = []
          for (let v = 0; v <= value * 2 + 10; v += 1) opts.push(v)
          return opts
        }
      } else if (typeof value === 'string') {
        return [value]
      } else {
        return [value]
      }
    }
  },
  watch: {
    settings: {
      handler(newSettings) {
        this.localSettings = JSON.parse(JSON.stringify(newSettings))
      },
      deep: true
    }
  }
}
</script>

<style scoped>
.settings-tabs {
  margin-bottom: 20px;
}

.settings-tab-content {
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 0 0 8px 8px;
  min-height: 200px;
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

.status-indicator {
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 12px;
  margin-left: 8px;
}
</style> 