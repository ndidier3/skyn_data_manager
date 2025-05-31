import axios from 'axios'

const state = {
  list: [],
  selected: null,
  dayResults: null,
  dayPlots: null,
  curveResults: null,
  curvePlots: null,
  eventResults: null,
  eventPlots: null,
  loading: false,
  error: null,
  processingStatus: {
    gaps: { status: 'not_started', message: 'Not Started' },
    smooth: { status: 'not_started', message: 'Not Started' },
    day: { status: 'not_started', message: 'Not Started' },
    curve: { status: 'not_started', message: 'Not Started' }
  }
}

const getters = {
  isLoading: state => state.loading,
  hasError: state => state.error !== null,
  errorMessage: state => state.error,
  processingStatus: state => state.processingStatus,
  isProcessingComplete: state => {
    return Object.values(state.processingStatus).every(
      status => status.status === 'completed'
    )
  }
}

const actions = {
  async fetchStudies({ commit }) {
    commit('SET_LOADING', true)
    try {
      const response = await axios.get('/api/studies')
      commit('SET_STUDIES', response.data)
    } catch (error) {
      commit('SET_ERROR', 'Failed to fetch studies')
      console.error('Error fetching studies:', error)
    } finally {
      commit('SET_LOADING', false)
    }
  },

  async fetchStudyDetails({ commit }, studyId) {
    commit('SET_LOADING', true)
    try {
      const response = await axios.get(`/api/studies/${studyId}`)
      commit('SET_SELECTED_STUDY', response.data)
      
      // Fetch all results for the study
      await Promise.all([
        actions.fetchDayResults({ commit }, studyId),
        actions.fetchCurveResults({ commit }, studyId),
        actions.fetchEventResults({ commit }, studyId)
      ])
    } catch (error) {
      commit('SET_ERROR', 'Failed to fetch study details')
      console.error('Error fetching study details:', error)
    } finally {
      commit('SET_LOADING', false)
    }
  },

  async fetchDayResults({ commit }, studyId) {
    try {
      const response = await axios.get(`/api/studies/${studyId}/days`)
      commit('SET_DAY_RESULTS', response.data)
    } catch (error) {
      console.error('Error fetching day results:', error)
    }
  },

  async fetchCurveResults({ commit }, studyId) {
    try {
      const response = await axios.get(`/api/studies/${studyId}/curves`)
      commit('SET_CURVE_RESULTS', response.data)
    } catch (error) {
      console.error('Error fetching curve results:', error)
    }
  },

  async fetchEventResults({ commit }, studyId) {
    try {
      const response = await axios.get(`/api/studies/${studyId}/events`)
      commit('SET_EVENT_RESULTS', response.data)
    } catch (error) {
      console.error('Error fetching event results:', error)
    }
  },

  async createStudy({ commit }, studyData) {
    commit('SET_LOADING', true)
    try {
      const response = await axios.post('/api/studies', studyData)
      commit('ADD_STUDY', response.data)
      return response.data
    } catch (error) {
      commit('SET_ERROR', 'Failed to create study')
      console.error('Error creating study:', error)
      throw error
    } finally {
      commit('SET_LOADING', false)
    }
  },

  async processStudy({ commit }, { studyId, options, settings }) {
    try {
        console.log('Processing study with ID:', studyId);  // Debug log
        
        // First get the numeric ID for the study
        const response = await axios.get(`/api/studies/check-prior/${studyId}`);
        console.log('Check prior response:', response.data);  // Debug log
        
        if (!response.data.exists) {
            // If study doesn't exist at all, throw error
            throw new Error('Study not found');
        }
        
        // Get the numeric ID from the study object
        const numericId = response.data.study.id;
        console.log('Using numeric ID:', numericId);  // Debug log
        
        // Process the study
        const result = await axios.post(`/api/studies/${numericId}/process`, {
        options,
        settings
        });
        
        console.log('Process result:', result.data);  // Debug log
        return result.data;
    } catch (error) {
        console.error('Error processing study:', error);
        throw error;
    }
  },

  async checkPriorAnalysis({ commit }, { dataset_identifier }) {
    try {
      const response = await axios.get(`/api/studies/check-prior/${dataset_identifier}`)
      return response.data
    } catch (error) {
      console.error('Error checking prior analysis:', error)
      return null
    }
  }
}

const mutations = {
  SET_LOADING(state, loading) {
    state.loading = loading
  },
  SET_ERROR(state, error) {
    state.error = error
  },
  SET_STUDIES(state, studies) {
    state.list = studies
  },
  SET_SELECTED_STUDY(state, study) {
    state.selected = study
  },
  ADD_STUDY(state, study) {
    state.list.push(study)
  },
  UPDATE_STUDY(state, updatedStudy) {
    const index = state.list.findIndex(s => s.study_id === updatedStudy.study_id)
    if (index !== -1) {
      state.list.splice(index, 1, updatedStudy)
    }
    if (state.selected && state.selected.study_id === updatedStudy.study_id) {
      state.selected = updatedStudy
    }
  },
  SET_DAY_RESULTS(state, results) {
    state.dayResults = results.features
    state.dayPlots = results.plots
  },
  SET_CURVE_RESULTS(state, results) {
    state.curveResults = results.features
    state.curvePlots = results.plots
  },
  SET_EVENT_RESULTS(state, results) {
    state.eventResults = results.features
    state.eventPlots = results.plots
  },
  SET_PROCESSING_STATUS(state, { step, status, message }) {
    state.processingStatus[step] = { status, message }
  },
  RESET_PROCESSING_STATUS(state) {
    state.processingStatus = {
      gaps: { status: 'not_started', message: 'Not Started' },
      smooth: { status: 'not_started', message: 'Not Started' },
      day: { status: 'not_started', message: 'Not Started' },
      curve: { status: 'not_started', message: 'Not Started' }
    }
  }
}

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations
} 