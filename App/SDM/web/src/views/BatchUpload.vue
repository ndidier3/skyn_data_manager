<template>
  <div class="batch-upload">
    <BatchDirectorySelection
      :selected-directory.sync="selectedDirectory"
      :directory-error.sync="directoryError"
      :valid-files.sync="validFiles"
      :registered-studies="registeredStudies"
      @study-registered="handleStudyRegistered"
      @confirmed="handleConfirmed"
      @revise="handleRevise"
    />
    
    <div v-if="isConfirmed" class="settings-container mt-4">
      <h3 class="mb-3">Batch Load Settings</h3>
      <BatchSettings
        :selected-directory="selectedDirectory"
        :valid-files="validFiles"
        :registered-studies="registeredStudies"
      />
    </div>
  </div>
</template>

<script>
import BatchDirectorySelection from '@/components/BatchDirectorySelection.vue'
import BatchSettings from '@/components/BatchSettings.vue'

export default {
  name: 'BatchUpload',
  components: {
    BatchDirectorySelection,
    BatchSettings
  },
  data() {
    return {
      selectedDirectory: '',
      directoryError: null,
      validFiles: [],
      registeredStudies: new Set(),
      isConfirmed: false
    }
  },
  methods: {
    handleStudyRegistered(studyData) {
      this.registeredStudies.add(studyData.study_id)
    },
    handleConfirmed() {
      this.isConfirmed = true
    },
    handleRevise() {
      this.isConfirmed = false
    }
  }
}
</script>

<style scoped>
.batch-upload {
  padding: 1rem;
}

.settings-container {
  border-top: 1px solid #dee2e6;
  padding-top: 1rem;
}
</style> 