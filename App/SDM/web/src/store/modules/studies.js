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
    try {
      commit('SET_LOADING', true)
      
      // Ensure studyId is a string
      const studyIdStr = String(studyId)
      
      // Fetch study details
      const response = await axios.get(`/api/studies/${studyIdStr}`)
      commit('SET_CURRENT_STUDY', response.data)
      
      // Fetch day results if available
      try {
        const daysResponse = await axios.get(`/api/studies/${studyIdStr}/days`)
        commit('SET_DAY_RESULTS', daysResponse.data)
      } catch (error) {
        if (error.response?.status === 404) {
          // Day analysis not run, set empty results
          commit('SET_DAY_RESULTS', { features: [], plots: [] })
        } else {
          // Only log unexpected errors
          console.error('Unexpected error fetching day results:', error)
        }
      }
      
      // Fetch curve results if available
      try {
        const curvesResponse = await axios.get(`/api/studies/${studyIdStr}/curves`)
        commit('SET_CURVE_RESULTS', curvesResponse.data)
      } catch (error) {
        if (error.response?.status === 404) {
          // Curve analysis not run, set empty results
          commit('SET_CURVE_RESULTS', { features: [], plots: [] })
        } else {
          // Only log unexpected errors
          console.error('Unexpected error fetching curve results:', error)
        }
      }
      
      // Fetch event results if available
      try {
        const eventsResponse = await axios.get(`/api/studies/${studyIdStr}/events`)
        commit('SET_EVENT_RESULTS', eventsResponse.data)
      } catch (error) {
        if (error.response?.status === 404) {
          // Event analysis not run, set empty results
          commit('SET_EVENT_RESULTS', { features: [], plots: [] })
        } else {
          // Only log unexpected errors
          console.error('Unexpected error fetching event results:', error)
        }
      }
      
      return response.data
    } catch (error) {
      // Only log and throw unexpected errors
      if (error.response?.status !== 404) {
        console.error('Unexpected error fetching study details:', error)
        throw error
      }
      // For 404s, just return null
      return null
    } finally {
      commit('SET_LOADING', false)
    }
  },

  async fetchDayResults({ commit }, studyId) {
    try {
      const studyIdStr = String(studyId)
      const response = await axios.get(`/api/studies/${studyIdStr}/days`)
      commit('SET_DAY_RESULTS', response.data)
    } catch (error) {
      if (error.response?.status !== 404) {
        console.error('Unexpected error fetching day results:', error)
        throw error
      }
      // Set empty results for 404s without throwing
      commit('SET_DAY_RESULTS', { features: [], plots: [] })
    }
  },

  async fetchCurveResults({ commit }, studyId) {
    try {
      const studyIdStr = String(studyId)
      const response = await axios.get(`/api/studies/${studyIdStr}/curves`)
      commit('SET_CURVE_RESULTS', response.data)
    } catch (error) {
      if (error.response?.status !== 404) {
        console.error('Unexpected error fetching curve results:', error)
        throw error
      }
      // Set empty results for 404s without throwing
      commit('SET_CURVE_RESULTS', { features: [], plots: [] })
    }
  },

  async fetchEventResults({ commit }, studyId) {
    try {
      const studyIdStr = String(studyId)
      const response = await axios.get(`/api/studies/${studyIdStr}/events`)
      commit('SET_EVENT_RESULTS', response.data)
    } catch (error) {
      if (error.response?.status !== 404) {
        console.error('Unexpected error fetching event results:', error)
        throw error
      }
      // Set empty results for 404s without throwing
      commit('SET_EVENT_RESULTS', { features: [], plots: [] })
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
        
        // Process the study directly with the study_id
        const result = await axios.post(`/api/studies/${studyId}/process`, {
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
  SET_CURRENT_STUDY(state, study) {
    state.selected = study
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