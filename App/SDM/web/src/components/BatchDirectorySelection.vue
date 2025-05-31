<template>
  <div class="directory-selection mb-4">
    <div class="directory-input-wrapper">
      <input 
        type="file" 
        ref="directoryInput"
        class="directory-input" 
        @change="handleDirectorySelect"
        webkitdirectory
        directory
      >
      <div class="directory-input-trigger" @click="$refs.directoryInput.click()">
        <i class="fas fa-folder-open"></i>
        <span>Select Directory</span>
      </div>
    </div>
    <div v-if="directoryError" class="text-danger mt-2">
      {{ directoryError }}
    </div>

    <!-- Study Sections -->
    <div v-if="validFiles.length > 0" class="study-sections mt-3">
      <!-- Summary View (after confirmation) -->
      <div v-if="isConfirmed" class="summary-view mb-4">
        <div class="summary-stats">
          <div class="summary-stat tooltip-trigger">
            <span class="stat-value">{{ includedStudyCount }}</span>
            <span class="stat-label">Studies Included</span>
            <div class="tooltip-content">
              <div class="tooltip-studies">
                <div v-for="studyId in includedStudies" :key="studyId" class="tooltip-study">
                  <span class="study-id">{{ studyId }}</span>
                  <span v-if="studyNames.get(studyId)" class="study-name">({{ studyNames.get(studyId) }})</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="summary-stat tooltip-trigger">
            <span class="stat-value">{{ excludedStudyCount }}</span>
            <span class="stat-label">Studies Excluded</span>
            <div class="tooltip-content">
              <div class="tooltip-studies">
                <div v-for="studyId in excludedStudyIds" :key="studyId" class="tooltip-study">
                  <span class="study-id">{{ studyId }}</span>
                  <span v-if="studyNames.get(studyId)" class="study-name">({{ studyNames.get(studyId) }})</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="summary-stat tooltip-trigger">
            <span class="stat-value">{{ totalFileCount }}</span>
            <span class="stat-label">Included Files</span>
            <div class="tooltip-content">
              <div class="tooltip-files">
                <div v-for="file in validFiles" :key="file" class="tooltip-file">
                  {{ file }}
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="text-center mt-3">
          <button 
            class="btn btn-outline-secondary btn-sm"
            @click="reviseSelections"
          >
            <i class="fas fa-edit me-1"></i>
            Revise Study Selections
          </button>
        </div>
      </div>

      <!-- Study Management View (before confirmation) -->
      <div v-else>
        <!-- Registered Studies Section -->
        <div v-if="registeredStudyIds.length > 0" class="study-section mb-4">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h4 class="section-title mb-0">Registered Studies</h4>
            <span class="file-count">Total Files: {{ getTotalRegisteredFiles() }}</span>
          </div>
          <div class="study-list">
            <div v-for="studyId in registeredStudyIds" :key="studyId" class="study-item">
              <div class="d-flex justify-content-between align-items-center">
                <div class="study-info">
                  <div class="study-header">
                    <span class="study-id">Study ID: {{ studyId }}</span>
                    <span v-if="studyNames.get(studyId)" class="study-name">({{ studyNames.get(studyId) }})</span>
                  </div>
                  <span class="file-count ms-4 tooltip-trigger">
                    ({{ getStudyFileCount(studyId) }} files)
                    <div class="tooltip-content">
                      <div class="tooltip-files">
                        <div v-for="file in getStudyFiles(studyId)" :key="file" class="tooltip-file">
                          {{ file }}
                        </div>
                      </div>
                    </div>
                  </span>
                </div>
                <div class="study-actions">
                  <button 
                    class="btn btn-sm btn-outline-danger me-2"
                    @click="excludeStudy(studyId)"
                  >
                    Exclude
                  </button>
                  <span class="badge bg-success">Registered</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Register New Studies Section -->
        <div v-if="unregisteredStudyIds.length > 0" class="study-section mb-4">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h4 class="section-title mb-0">Register New Studies</h4>
            <span class="file-count">Total Files: {{ getTotalUnregisteredFiles() }}</span>
          </div>
          <div class="study-list">
            <div v-for="studyId in unregisteredStudyIds" :key="studyId" class="study-item">
              <div class="d-flex justify-content-between align-items-center">
                <div class="study-info">
                  <div class="study-header">
                    <span class="study-id">Study ID: {{ studyId }}</span>
                    <span v-if="studyNames.get(studyId)" class="study-name">({{ studyNames.get(studyId) }})</span>
                  </div>
                  <span class="file-count ms-4 tooltip-trigger">
                    ({{ getStudyFileCount(studyId) }} files)
                    <div class="tooltip-content">
                      <div class="tooltip-files">
                        <div v-for="file in getStudyFiles(studyId)" :key="file" class="tooltip-file">
                          {{ file }}
                        </div>
                      </div>
                    </div>
                  </span>
                </div>
                <div class="study-actions">
                  <button 
                    class="btn btn-sm btn-outline-danger me-2"
                    @click="excludeStudy(studyId)"
                  >
                    Exclude
                  </button>
                  <button 
                    class="btn btn-sm btn-outline-primary"
                    @click="openRegistrationModal(studyId)"
                  >
                    Register
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Excluded Studies Section -->
        <div v-if="excludedStudyIds.length > 0" class="study-section mb-4">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h4 class="section-title mb-0 text-muted">Excluded Studies</h4>
            <span class="file-count">Total Files: {{ excludedStudyIds.reduce((total, id) => total + getStudyFileCount(id), 0) }}</span>
          </div>
          <div class="study-list">
            <div v-for="studyId in excludedStudyIds" :key="studyId" class="study-item">
              <div class="d-flex justify-content-between align-items-center">
                <div class="study-info">
                  <div class="study-header">
                    <span class="study-id">Study ID: {{ studyId }}</span>
                    <span v-if="studyNames.get(studyId)" class="study-name">({{ studyNames.get(studyId) }})</span>
                  </div>
                  <span class="file-count ms-4 tooltip-trigger">
                    ({{ getStudyFileCount(studyId) }} files)
                    <div class="tooltip-content">
                      <div class="tooltip-files">
                        <div v-for="file in getStudyFiles(studyId)" :key="file" class="tooltip-file">
                          {{ file }}
                        </div>
                      </div>
                    </div>
                  </span>
                </div>
                <div class="study-actions">
                  <button 
                    class="btn btn-sm btn-outline-secondary"
                    @click="includeStudy(studyId)"
                  >
                    Include
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Invalid Files Section -->
        <div v-if="invalidFiles.length > 0" class="study-section">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h4 class="section-title mb-0 text-danger">Invalid Files</h4>
            <span class="file-count">Total Files: {{ invalidFiles.length }}</span>
          </div>
          <div class="study-list">
            <div v-for="file in invalidFiles" :key="file" class="study-item">
              <div class="d-flex justify-content-between align-items-center">
                <div class="study-info">
                  <span class="file-name">{{ file }}</span>
                  <span class="invalid-reason ms-4">(Invalid naming convention)</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Confirm Button -->
        <div class="mt-4 text-center">
          <button 
            class="btn btn-primary"
            :disabled="!canConfirm"
            @click="handleConfirm"
          >
            Confirm Batch Load
          </button>
          <div v-if="!canConfirm" class="text-muted mt-2 small">
            All studies must be either registered or excluded before proceeding
          </div>
        </div>
      </div>
    </div>

    <!-- Study Registration Modal -->
    <div v-if="showRegistrationModal" class="modal-overlay">
      <StudyRegistrationModal
        :show="showRegistrationModal"
        :study-id="selectedStudyId"
        :sub-id="selectedSubId"
        @update:show="showRegistrationModal = $event"
        @study-registered="handleStudyRegistered"
        @modal-canceled="closeRegistrationModal"
      />
    </div>
  </div>
</template>

<script>
import StudyRegistrationModal from './StudyRegistrationModal.vue'
import axios from 'axios'

export default {
  name: 'BatchDirectorySelection',
  components: {
    StudyRegistrationModal
  },
  props: {
    selectedDirectory: {
      type: String,
      default: ''
    },
    directoryError: {
      type: String,
      default: null
    },
    validFiles: {
      type: Array,
      default: () => []
    },
    registeredStudies: {
      type: Set,
      default: () => new Set()
    },
    isConfirmed: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      showRegistrationModal: false,
      selectedStudyId: '',
      selectedSubId: '',
      invalidFiles: [],
      excludedStudies: new Set(),
      originalFiles: [],
      studyNames: new Map()
    }
  },
  computed: {
    uniqueStudyIds() {
      const studyIds = new Set()
      this.originalFiles.forEach(file => {
        const studyId = this.extractStudyId(file)
        if (studyId) studyIds.add(studyId)
      })
      return Array.from(studyIds)
    },
    registeredStudyIds() {
      return this.uniqueStudyIds.filter(id => 
        this.registeredStudies.has(id) && !this.excludedStudies.has(id)
      )
    },
    unregisteredStudyIds() {
      return this.uniqueStudyIds.filter(id => 
        !this.registeredStudies.has(id) && !this.excludedStudies.has(id)
      )
    },
    excludedStudyIds() {
      return Array.from(this.excludedStudies)
    },
    canConfirm() {
      // Can confirm when there are valid files and all studies are either registered or excluded
      return this.validFiles.length > 0 && this.unregisteredStudyIds.length === 0
    },
    includedStudyCount() {
      return this.registeredStudyIds.length + this.unregisteredStudyIds.length
    },
    excludedStudyCount() {
      return this.excludedStudyIds.length
    },
    totalFileCount() {
      return this.validFiles.length
    },
    includedStudies() {
      return [...this.registeredStudyIds, ...this.unregisteredStudyIds]
    }
  },
  methods: {
    async handleDirectorySelect(event) {
      const files = Array.from(event.target.files)
      if (!files.length) return

      // Get directory path from first file
      const path = files[0].webkitRelativePath
      const directory = path.split('/')[0]

      // Separate valid and invalid files
      const validFiles = []
      const invalidFiles = []
      
      files.forEach(file => {
        if (this.validateFilename(file.name)) {
          validFiles.push(file.name)
        } else {
          invalidFiles.push(file.name)
        }
      })
      
      if (validFiles.length === 0 && invalidFiles.length === 0) {
        this.$emit('update:directory-error', 'No files found in directory')
        return
      }

      // Store original files
      this.originalFiles = [...validFiles]

      // Check which studies are already registered
      const studyIds = new Set()
      validFiles.forEach(file => {
        const studyId = this.extractStudyId(file)
        if (studyId) studyIds.add(studyId)
      })

      // Check each study's registration status
      for (const studyId of studyIds) {
        try {
          const response = await axios.get(`/api/studies/check-prior/${studyId}`)
          if (response.data && response.data.exists) {
            // Store the study name
            this.studyNames.set(studyId, response.data.study.name)
            this.$emit('study-registered', { study_id: studyId })
          }
        } catch (error) {
          if (!error.response || error.response.status !== 404) {
            console.error(`Error checking study ${studyId}:`, error)
          }
        }
      }

      this.invalidFiles = invalidFiles
      this.$emit('update:valid-files', validFiles)
      this.$emit('update:selected-directory', directory)
      this.$emit('directory-selected', event)
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
    getStudyFileCount(studyId) {
      return this.originalFiles.filter(file => this.extractStudyId(file) === studyId).length
    },
    getTotalRegisteredFiles() {
      return this.registeredStudyIds.reduce((total, studyId) => 
        total + this.getStudyFileCount(studyId), 0)
    },
    getTotalUnregisteredFiles() {
      return this.unregisteredStudyIds.reduce((total, studyId) => 
        total + this.getStudyFileCount(studyId), 0)
    },
    openRegistrationModal(studyId) {
      this.selectedStudyId = studyId
      // Get the first subject ID for this study
      const file = this.validFiles.find(f => this.extractStudyId(f) === studyId)
      this.selectedSubId = file ? this.extractSubId(file) : ''
      this.showRegistrationModal = true
    },
    closeRegistrationModal() {
      this.showRegistrationModal = false
      this.selectedStudyId = ''
      this.selectedSubId = ''
    },
    handleStudyRegistered(studyData) {
      // Store the study name if provided
      if (studyData.name) {
        this.studyNames.set(studyData.study_id, studyData.name)
      }
      // Emit the event to parent with the study ID to be added to registeredStudies
      this.$emit('study-registered', studyData)
      // Close the registration modal
      this.closeRegistrationModal()
      // Force a re-computation of registeredStudyIds and unregisteredStudyIds
      this.$forceUpdate()
    },
    registerStudy(studyId) {
      this.openRegistrationModal(studyId)
    },
    getStudyFiles(studyId) {
      return this.originalFiles.filter(file => this.extractStudyId(file) === studyId)
    },
    excludeStudy(studyId) {
      // Create a new Set to ensure reactivity
      const newExcludedStudies = new Set(this.excludedStudies)
      newExcludedStudies.add(studyId)
      this.excludedStudies = newExcludedStudies
      
      // Filter out files for this study from validFiles
      const remainingFiles = this.validFiles.filter(file => 
        this.extractStudyId(file) !== studyId
      )
      
      // Update valid files
      this.$emit('update:valid-files', remainingFiles)
    },
    includeStudy(studyId) {
      // Create a new Set to ensure reactivity
      const newExcludedStudies = new Set(this.excludedStudies)
      newExcludedStudies.delete(studyId)
      this.excludedStudies = newExcludedStudies
      
      // Get all files for this study from originalFiles
      const studyFiles = this.originalFiles.filter(file => 
        this.extractStudyId(file) === studyId
      )
      
      // Add them back to validFiles
      this.$emit('update:valid-files', [...this.validFiles, ...studyFiles])
    },
    handleConfirm() {
      if (this.canConfirm) {
        this.$emit('confirmed')
      }
    },
    reviseSelections() {
      this.$emit('revise')
    }
  }
}
</script>

<style scoped>
.directory-selection {
  border: 2px dashed #dee2e6;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
}

.directory-input-wrapper {
  position: relative;
}

.directory-input {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  opacity: 0;
  cursor: pointer;
}

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

.directory-input-trigger:hover {
  background-color: #e9ecef;
}

.study-sections {
  text-align: left;
}

.study-section {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
}

.section-title {
  font-size: 1.1rem;
  color: #495057;
}

.file-count {
  color: #6c757d;
  font-size: 0.875rem;
}

.study-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.study-item {
  background-color: white;
  padding: 0.75rem;
  border-radius: 4px;
  border: 1px solid #dee2e6;
}

.study-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.study-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.study-id {
  font-weight: 500;
  color: #495057;
  min-width: 100px;
}

.file-name {
  font-weight: 500;
  color: #dc3545;
}

.invalid-reason {
  color: #dc3545;
  font-size: 0.875rem;
}

.file-count {
  color: #6c757d;
  font-size: 0.875rem;
}

.study-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.tooltip-trigger {
  position: relative;
  cursor: pointer;
}

.tooltip-content {
  display: none;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  top: 100%;
  background-color: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  z-index: 1000;
  min-width: 250px;
  max-width: 400px;
  margin-top: 8px;
}

.tooltip-trigger:hover .tooltip-content {
  display: block;
}

/* Add a small arrow at the top of the tooltip */
.tooltip-content::before {
  content: '';
  position: absolute;
  top: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 6px solid #dee2e6;
}

.tooltip-content::after {
  content: '';
  position: absolute;
  top: -5px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 6px solid white;
}

.tooltip-files {
  max-height: 200px;
  overflow-y: auto;
  padding: 8px;
}

.tooltip-file {
  padding: 4px 8px;
  font-size: 0.875rem;
  color: #495057;
  border-bottom: 1px solid #dee2e6;
}

.tooltip-file:last-child {
  border-bottom: none;
}

.study-name {
  color: #6c757d;
  font-size: 0.9em;
  padding-left: 0.25rem;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.small {
  font-size: 0.875rem;
}

.summary-view {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid #dee2e6;
}

.summary-stats {
  display: flex;
  justify-content: center;
  gap: 3rem;
}

.summary-stat {
  text-align: center;
  position: relative;
  padding: 0.5rem;
  min-width: 120px;
  cursor: pointer;
}

.stat-value {
  display: block;
  font-size: 1.25rem;
  font-weight: 500;
  color: #495057;
  margin-bottom: 0.25rem;
}

.stat-label {
  display: block;
  color: #6c757d;
  font-size: 0.875rem;
}

.tooltip-content {
  min-width: 250px;
  max-width: 400px;
}

.tooltip-studies, .tooltip-files {
  max-height: 250px;
  overflow-y: auto;
  padding: 6px;
}

.tooltip-study, .tooltip-file {
  padding: 3px 6px;
  font-size: 0.875rem;
  color: #495057;
  border-bottom: 1px solid #dee2e6;
}

.tooltip-study:last-child, .tooltip-file:last-child {
  border-bottom: none;
}
</style> 