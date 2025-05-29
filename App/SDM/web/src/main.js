import Vue from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import axios from 'axios'
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'
import BootstrapVue from 'bootstrap-vue'

// Configure axios defaults
// Use relative URLs to let the Vue dev server handle proxying
axios.defaults.baseURL = ''
axios.defaults.headers.common['Content-Type'] = 'application/json'
axios.defaults.withCredentials = true

// Add response interceptor for error handling
axios.interceptors.response.use(
  response => response,
  error => {
    const message = error.response?.data?.message || 'An error occurred'
    store.dispatch('notifications/showNotification', {
      title: 'Error',
      message,
      type: 'error'
    })
    return Promise.reject(error)
  }
)

Vue.config.productionTip = false

Vue.use(BootstrapVue)

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app') 