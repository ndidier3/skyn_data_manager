<template>
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
          <button class="btn btn-sm btn-outline-primary" @click="$emit('load-prior')">
            <i class="fas fa-history me-1"></i>Load Previous Analysis
          </button>
          <button class="btn btn-sm btn-outline-secondary" @click="$emit('start-new')">
            <i class="fas fa-plus me-1"></i>Start New Analysis
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FileSelection',
  props: {
    selectedFile: {
      type: File,
      default: null
    },
    fileError: {
      type: String,
      default: null
    },
    studyStatus: {
      type: Object,
      default: null
    },
    subjectStatus: {
      type: Object,
      default: null
    },
    hasPriorAnalysis: {
      type: Boolean,
      default: false
    }
  },
  computed: {
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
    }
  },
  methods: {
    handleFileSelect(event) {
      this.$emit('file-selected', event)
    }
  }
}
</script>

<style scoped>
.file-selection {
  border: 2px dashed #dee2e6;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
}

.file-input-wrapper {
  position: relative;
}

.file-input {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  opacity: 0;
  cursor: pointer;
}

.file-input-trigger {
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

.file-input-trigger:hover {
  background-color: #e9ecef;
}

.file-info {
  text-align: left;
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
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