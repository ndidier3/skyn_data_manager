<template>
  <div>
    <div v-if="show" class="modal-backdrop" @click="close"></div>
    <div v-if="show" class="modal-container">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Select Studies</h2>
          <button class="close-button" @click="close">&times;</button>
        </div>
        
        <div class="modal-body">
          <div class="study-filters mb-3">
            <div class="input-group">
              <input 
                type="text" 
                class="form-control" 
                v-model="searchQuery" 
                placeholder="Search studies..."
              >
              <button 
                class="btn btn-outline-secondary" 
                type="button"
                @click="searchQuery = ''"
              >
                Clear
              </button>
            </div>
          </div>
          
          <div class="studies-table">
            <table class="table">
              <thead>
                <tr>
                  <th>Study ID</th>
                  <th>Subject ID</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="study in filteredStudies" :key="`${study.study_id}_${study.subid}`">
                  <td>{{ study.study_id }}</td>
                  <td>{{ study.subid }}</td>
                  <td>
                    <span class="badge" :class="getStatusClass(study.processing_status)">
                      {{ study.processing_status }}
                    </span>
                  </td>
                  <td>
                    <div class="form-check">
                      <input 
                        class="form-check-input" 
                        type="checkbox" 
                        :id="`study-${study.study_id}-${study.subid}`"
                        :checked="isStudySelected(study)"
                        @change="toggleStudy(study)"
                      >
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <div class="modal-footer mt-4">
            <button 
              class="btn btn-primary"
              @click="confirmSelection"
            >
              Confirm Selection
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'StudySelectionModal',
  props: {
    show: {
      type: Boolean,
      required: true
    },
    studies: {
      type: Array,
      required: true
    }
  },
  data() {
    return {
      searchQuery: '',
      selectedStudies: []
    }
  },
  computed: {
    filteredStudies() {
      if (!this.searchQuery) return this.studies
      
      const query = this.searchQuery.toLowerCase()
      return this.studies.filter(study => 
        study.study_id.toLowerCase().includes(query) ||
        study.subid.toLowerCase().includes(query)
      )
    }
  },
  methods: {
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
    isStudySelected(study) {
      return this.selectedStudies.some(s => 
        s.study_id === study.study_id && s.subid === study.subid
      )
    },
    toggleStudy(study) {
      const index = this.selectedStudies.findIndex(s => 
        s.study_id === study.study_id && s.subid === study.subid
      )
      if (index === -1) {
        this.selectedStudies.push(study)
      } else {
        this.selectedStudies.splice(index, 1)
      }
    },
    confirmSelection() {
      this.$emit('selection-confirmed', this.selectedStudies)
      this.close()
    },
    close() {
      this.$emit('update:show', false)
    }
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1000;
}

.modal-container {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1001;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
}

.modal-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.modal-header {
  padding: 1rem;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  color: #6c757d;
}

.modal-body {
  padding: 1rem;
  max-height: calc(90vh - 120px);
  overflow-y: auto;
}

.studies-table {
  margin-top: 1rem;
}

.table th {
  background-color: #f8f9fa;
  font-weight: 600;
}

.badge {
  font-size: 0.75rem;
  padding: 0.35em 0.65em;
}

.modal-footer {
  padding: 1rem;
  border-top: 1px solid #dee2e6;
  text-align: right;
}
</style> 