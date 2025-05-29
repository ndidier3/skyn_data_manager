const state = {
  notifications: []
}

const mutations = {
  ADD_NOTIFICATION(state, notification) {
    const id = Date.now() + Math.random().toString(36).substr(2, 9)
    state.notifications.push({
      id,
      type: notification.type || 'info',
      title: notification.title || '',
      message: notification.message || '',
      timeout: notification.timeout || 5000
    })
    return id
  },
  REMOVE_NOTIFICATION(state, id) {
    state.notifications = state.notifications.filter(n => n.id !== id)
  }
}

const actions = {
  showNotification({ commit }, notification) {
    const id = commit('ADD_NOTIFICATION', notification)
    if (notification.timeout !== false) {
      setTimeout(() => {
        commit('REMOVE_NOTIFICATION', id)
      }, notification.timeout || 5000)
    }
    return id
  }
}

export default {
  namespaced: true,
  state,
  mutations,
  actions
} 