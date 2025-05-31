<template>
  <div>
    <!-- Modal Backdrop -->
    <div v-if="show" class="modal-backdrop" @click="close"></div>
    
    <!-- Modal -->
    <div v-if="show" class="modal-container">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Register New Study</h2>
          <button class="close-button" @click="close">&times;</button>
        </div>
        
        <div class="modal-body">
          <div v-if="loading" class="loading">
            <div class="spinner"></div>
            <p>Checking study status...</p>
          </div>
          
          <div v-else-if="error" class="error-message">
            {{ error }}
          </div>
          
          <div v-else-if="studyExists" class="study-exists">
            <div class="study-id-display">
              <p><strong>Study ID:</strong> {{ studyId }}</p>
            </div>
            <h3>Study Already Exists</h3>
            <p>This study has already been registered in the system.</p>
            <div class="study-details">
              <p><strong>Name:</strong> {{ study.name }}</p>
              <p><strong>Description:</strong> {{ study.description }}</p>
              <p><strong>Created:</strong> {{ formatDate(study.created_at) }}</p>
              <p><strong>Last Updated:</strong> {{ formatDate(study.last_updated) }}</p>
            </div>
            <div class="button-group">
              <button class="btn btn-secondary" @click="close">Close</button>
              <button class="btn btn-primary" @click="proceedToAnalysis">Proceed to Analysis</button>
            </div>
          </div>
          
          <div v-else class="study-form">
            <div class="study-id-display">
              <p><strong>Study ID:</strong> {{ studyId }}</p>
            </div>
            <form @submit.prevent="registerStudy">
              <div class="form-group">
                <label for="name">Study Name</label>
                <input 
                  id="name"
                  v-model="form.name"
                  type="text"
                  required
                  placeholder="Enter study name"
                >
              </div>
              
              <div class="form-group">
                <label for="description">Description</label>
                <textarea 
                  id="description"
                  v-model="form.description"
                  required
                  placeholder="Enter study description"
                ></textarea>
              </div>
              
              <div class="button-group">
                <button type="button" class="btn btn-secondary" @click="close">Cancel</button>
                <button type="submit" class="btn btn-primary" :disabled="registering">
                  {{ registering ? 'Registering...' : 'Register Study' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { mapActions } from 'vuex'
import moment from 'moment'

export default {
  name: 'StudyRegistrationModal',
  
  props: {
    show: {
      type: Boolean,
      required: true
    },
    studyId: {
      type: String,
      required: true
    },
    subId: {
      type: String,
      required: true
    }
  },
  
  data() {
    return {
      loading: false,
      error: null,
      studyExists: false,
      study: null,
      registering: false,
      form: {
        name: '',
        description: ''
      }
    }
  },
  
  watch: {
    show(newVal) {
      if (newVal) {
        this.checkStudyStatus()
      } else {
        this.resetState()
      }
    }
  },
  
  methods: {
    ...mapActions('studies', ['checkPriorAnalysis', 'createStudy']),
    
    async checkStudyStatus() {
      this.loading = true
      this.error = null
      
      try {
        const response = await this.checkPriorAnalysis(this.studyId)
        this.studyExists = response.exists
        this.study = response.study
      } catch (error) {
        this.error = error.message || 'Failed to check study status'
      } finally {
        this.loading = false
      }
    },
    
    async registerStudy() {
      this.registering = true
      this.error = null
      
      try {
        const studyData = {
          ...this.form,
          study_id: this.studyId,
          subid: this.subId
        }
        await this.createStudy(studyData)
        this.$emit('study-registered', studyData)
        this.close()
      } catch (error) {
        this.error = error.message || 'Failed to register study'
      } finally {
        this.registering = false
      }
    },
    
    proceedToAnalysis() {
      this.$emit('proceed-to-analysis', this.study)
      this.close()
    },
    
    close() {
      if (!this.registering) {
        this.$emit('modal-canceled')
      }
      this.$emit('update:show', false)
    },
    
    resetState() {
      this.loading = false
      this.error = null
      this.studyExists = false
      this.study = null
      this.registering = false
      this.form = {
        name: '',
        description: ''
      }
    },
    
    formatDate(date) {
      return moment(date).format('MMMM D, YYYY h:mm A')
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
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1001;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #eee;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #2c3e50;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 1rem;
}

.loading {
  text-align: center;
  padding: 2rem;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  color: #e74c3c;
  text-align: center;
  padding: 1rem;
}

.study-exists {
  padding: 1rem;
}

.study-details {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
  margin: 1rem 0;
}

.study-details p {
  margin: 0.5rem 0;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #2c3e50;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group textarea {
  min-height: 100px;
  resize: vertical;
}

.button-group {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: background-color 0.2s;
}

.btn-primary {
  background-color: #3498db;
  color: white;
}

.btn-primary:hover {
  background-color: #2980b9;
}

.btn-primary:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #95a5a6;
  color: white;
}

.btn-secondary:hover {
  background-color: #7f8c8d;
}

.study-id-display {
  background: #f8f9fa;
  padding: 0.75rem;
  border-radius: 4px;
  margin: 1rem 0;
  border: 1px solid #e9ecef;
}

.study-id-display p {
  margin: 0;
  color: #495057;
  font-family: monospace;
  font-size: 1.1em;
}

.study-id-display strong {
  color: #2c3e50;
  margin-right: 0.5rem;
}
</style> 