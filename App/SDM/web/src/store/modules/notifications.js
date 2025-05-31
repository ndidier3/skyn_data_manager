const state = {
  notifications: []
}

const mutations = {
  ADD_NOTIFICATION(state, notification) {
    const id = Date.now() + Math.random().toString(36).substr(2, 9)
    
    // Determine if notification requires manual removal based on type
    const requiresManualRemoval = notification.type === 'error' || notification.type === 'critical'
    
    // Set default timeout for non-manual notifications
    const timeout = requiresManualRemoval ? false : (notification.timeout || 5000)
    
    state.notifications.push({
      id,
      type: notification.type || 'info',
      title: notification.title || '',
      message: notification.message || '',
      timeout,
      requiresManualRemoval
    })
    return id
  },
  REMOVE_NOTIFICATION(state, id) {
    state.notifications = state.notifications.filter(n => n.id !== id)
  }
}

const actions = {
  showNotification({ commit }, notification) {
    return commit('ADD_NOTIFICATION', notification)
  }
}

export default {
  namespaced: true,
  state,
  mutations,
  actions
} 