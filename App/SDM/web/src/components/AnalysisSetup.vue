<template>
  <div class="analysis-setup">
    <ProcessingModeToggle
      :is-batch-mode="isBatchMode"
      @update:is-batch-mode="isBatchMode = $event"
    />

    <FileSelection
      v-if="!isBatchMode"
      :selected-file="selectedFile"
      :file-error="fileError"
      :study-status="studyStatus"
      :subject-status="subjectStatus"
      :has-prior-analysis="hasPriorAnalysis"
      @file-selected="handleFileSelect"
      @load-prior="loadPriorAnalysis"
      @start-new="startNewAnalysis"
    />

    <BatchDirectorySelection
      v-else
      :selected-directory="selectedDirectory"
      :directory-error="directoryError"
      :valid-files="validFiles"
      :registered-studies="registeredStudies"
      @directory-selected="handleDirectorySelect"
      @study-registered="handleStudyRegistered"
    />

    <AnalysisSettings
      v-if="showAnalysisSettings"
      :settings="settings"
      :processing-status="processingStatus"
      :active-tab="activeTab"
      :is-processing="isProcessing"
      @update:settings="updateSettings"
      @update:active-tab="activeTab = $event"
      @load-defaults="loadDefaultSettings"
      @start-processing="startProcessing"
    />
  </div>
</template>

<script>
import ProcessingModeToggle from './ProcessingModeToggle.vue'
import FileSelection from './FileSelection.vue'
import BatchDirectorySelection from './BatchDirectorySelection.vue'
import AnalysisSettings from './AnalysisSettings.vue'

export default {
  name: 'AnalysisSetup',
  components: {
    ProcessingModeToggle,
    FileSelection,
    BatchDirectorySelection,
    AnalysisSettings
  },
  data() {
    return {
      isBatchMode: false,
      selectedFile: null,
      selectedDirectory: '',
      fileError: null,
      directoryError: null,
      studyStatus: null,
      subjectStatus: null,
      hasPriorAnalysis: false,
      validFiles: [],
      registeredStudies: new Set(),
      activeTab: 'gaps',
      isProcessing: false,
      settings: {
        gaps_and_non_wear: {
          non_wear_method: 'auto'
        },
        smooth: {
          enabled: true
        },
        day: {
          enabled: false,
          day_start_hour: 0,
          make_graphs: false
        },
        curve: {
          enabled: false,
          flag_selections: {}
        }
      },
      processingStatus: {
        gaps: { status: 'not_started', message: 'Not Started' },
        smooth: { status: 'not_started', message: 'Not Started' },
        day: { status: 'not_started', message: 'Not Started' },
        curve: { status: 'not_started', message: 'Not Started' }
      }
    }
  },
  computed: {
    showAnalysisSettings() {
      if (!this.isBatchMode) {
        return !!this.selectedFile
      }
      // For batch mode, only show settings if all studies are registered
      const studyIds = new Set()
      this.validFiles.forEach(file => {
        const studyId = file.split('_')[1]
        if (studyId) studyIds.add(studyId)
      })
      return studyIds.size > 0 && Array.from(studyIds).every(id => this.registeredStudies.has(id))
    }
  },
  methods: {
    handleFileSelect(event) {
      const file = event.target.files[0]
      if (!file) return

      // Reset states
      this.fileError = null
      this.studyStatus = null
      this.subjectStatus = null
      this.hasPriorAnalysis = false

      // Validate file
      if (!file.name.match(/\.(csv|xlsx|xls)$/i)) {
        this.fileError = 'Please select a valid CSV or Excel file'
        return
      }

      this.selectedFile = file
      this.checkFileStatus()
    },
    handleDirectorySelect(event) {
      const files = Array.from(event.target.files)
      if (!files.length) return

      // Reset states
      this.directoryError = null
      this.validFiles = []
      this.registeredStudies.clear()

      // Validate files
      const validFiles = files.filter(file => 
        file.name.match(/\.(csv|xlsx|xls)$/i)
      )

      if (validFiles.length === 0) {
        this.directoryError = 'No valid CSV or Excel files found in the directory'
        return
      }

      this.validFiles = validFiles.map(f => f.name)
      this.selectedDirectory = files[0].webkitRelativePath.split('/')[0]
    },
    async checkFileStatus() {
      if (!this.selectedFile) return

      try {
        // TODO: Implement API calls to check file status
        // For now, using mock data
        this.studyStatus = { exists: true }
        this.subjectStatus = { exists: false }
        this.hasPriorAnalysis = true
      } catch (error) {
        console.error('Error checking file status:', error)
      }
    },
    loadPriorAnalysis() {
      // TODO: Implement loading prior analysis
      console.log('Loading prior analysis...')
    },
    startNewAnalysis() {
      // TODO: Implement starting new analysis
      console.log('Starting new analysis...')
    },
    updateSettings(newSettings) {
      this.settings = newSettings
    },
    loadDefaultSettings() {
      // TODO: Implement loading default settings
      console.log('Loading default settings...')
    },
    handleStudyRegistered(studyData) {
      this.registeredStudies.add(studyData.study_id)
    },
    async startProcessing() {
      if (this.isProcessing) return

      this.isProcessing = true
      this.resetProcessingStatus()

      try {
        if (this.isBatchMode) {
          await this.processBatchFiles()
        } else {
          await this.processSingleFile()
        }
      } catch (error) {
        console.error('Error during processing:', error)
        this.updateProcessingStatus('error', 'Processing failed')
      } finally {
        this.isProcessing = false
      }
    },
    resetProcessingStatus() {
      Object.keys(this.processingStatus).forEach(key => {
        this.processingStatus[key] = { status: 'not_started', message: 'Not Started' }
      })
    },
    updateProcessingStatus(stage, status, message) {
      if (this.processingStatus[stage]) {
        this.processingStatus[stage] = { status, message }
      }
    },
    async processSingleFile() {
      // TODO: Implement single file processing
      console.log('Processing single file...')
    },
    async processBatchFiles() {
      // TODO: Implement batch processing
      console.log('Processing batch files...')
    }
  }
}
</script>

<style scoped>
.analysis-setup {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}
</style> 