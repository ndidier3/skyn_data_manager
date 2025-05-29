import axios from 'axios'

const state = {
  currentSettings: {
    smooth_and_impute: {
      reset_tac: false,
      median_smooth: false,
      impute_gaps: false
    },
    curve: {
      curve_threshold: 0,
      periphery_buffer_before: 0
    },
    day: {
      day_start_hour: 0,
      make_graphs: false
    },
    gaps_and_non_wear: {
      export_excel: false,
      non_wear_method: 'auto'
    }
  },
  defaultSettings: null
}

const mutations = {
  SET_CURRENT_SETTINGS(state, settings) {
    state.currentSettings = settings
  },
  SET_DEFAULT_SETTINGS(state, settings) {
    state.defaultSettings = settings
  }
}

const actions = {
  async loadDefaultSettings({ commit }) {
    try {
      const response = await axios.get('/api/settings/default')
      commit('SET_DEFAULT_SETTINGS', response.data)
      commit('SET_CURRENT_SETTINGS', response.data)
      return response.data
    } catch (error) {
      throw error
    }
  },
  updateSettings({ commit }, settings) {
    commit('SET_CURRENT_SETTINGS', settings)
  },
  async validateSettings({ state }) {
    try {
      const response = await axios.post('/api/settings/validate', state.currentSettings)
      return response.data
    } catch (error) {
      throw error
    }
  }
}

const getters = {
  currentSettings: state => state.currentSettings,
  defaultSettings: state => state.defaultSettings
}

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters
} 