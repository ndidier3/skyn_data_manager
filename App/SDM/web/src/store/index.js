import Vue from 'vue'
import Vuex from 'vuex'
import studies from './modules/studies'
import settings from './modules/settings'
import notifications from './modules/notifications'

Vue.use(Vuex)

export default new Vuex.Store({
  modules: {
    studies,
    settings,
    notifications
  }
}) 