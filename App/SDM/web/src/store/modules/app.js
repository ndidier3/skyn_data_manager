const state = {
  loading: false,
  notifications: []
}

const mutations = {
  SET_LOADING(state, loading) {
    state.loading = loading
  },
  ADD_NOTIFICATION(state, notification) {
    state.notifications.push(notification)
  },
  REMOVE_NOTIFICATION(state, id) {
    state.notifications = state.notifications.filter(n => n.id !== id)
  }
}

const actions = {
  setLoading({ commit }, loading) {
    commit('SET_LOADING', loading)
  },
  showNotification({ commit }, { title, message, type = 'success' }) {
    const id = Date.now()
    commit('ADD_NOTIFICATION', { id, title, message, type })
    setTimeout(() => {
      commit('REMOVE_NOTIFICATION', id)
    }, 5000)
  },
  removeNotification({ commit }, id) {
    commit('REMOVE_NOTIFICATION', id)
  }
}

export default {
  namespaced: true,
  state,
  mutations,
  actions
} 