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
  error: null
}

const getters = {
  isLoading: state => state.loading,
  hasError: state => state.error !== null,
  errorMessage: state => state.error
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
    commit('SET_LOADING', true)
    try {
      const response = await axios.post(`/api/studies/${studyId}/process`, {
        options,
        settings
      })
      commit('UPDATE_STUDY', response.data)
      return response.data
    } catch (error) {
      commit('SET_ERROR', 'Failed to process study')
      console.error('Error processing study:', error)
      throw error
    } finally {
      commit('SET_LOADING', false)
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
    const index = state.list.findIndex(s => s.id === updatedStudy.id)
    if (index !== -1) {
      state.list.splice(index, 1, updatedStudy)
    }
    if (state.selected && state.selected.id === updatedStudy.id) {
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
  }
}

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations
} 