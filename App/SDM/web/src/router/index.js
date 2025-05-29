import Vue from 'vue'
import VueRouter from 'vue-router'
import AnalysisSetup from '@/views/AnalysisSetup.vue'
import ResultsViewer from '@/views/ResultsViewer.vue'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    redirect: '/analysis'
  },
  {
    path: '/analysis',
    name: 'AnalysisSetup',
    component: AnalysisSetup
  },
  {
    path: '/results',
    name: 'ResultsViewer',
    component: ResultsViewer
  }
]

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes
})

export default router 