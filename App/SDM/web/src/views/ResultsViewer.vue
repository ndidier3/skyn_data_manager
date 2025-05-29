<template>
  <div class="results-viewer">
    <div class="row">
      <!-- Study List -->
      <div class="col-md-4">
        <div class="card">
          <div class="card-header">
            <h5 class="mb-0">Studies</h5>
          </div>
          <div class="list-group list-group-flush">
            <a
              v-for="study in studies"
              :key="study.id"
              href="#"
              class="list-group-item list-group-item-action"
              :class="{ active: selectedStudy && selectedStudy.id === study.id }"
              @click.prevent="selectStudy(study)"
            >
              <div class="d-flex w-100 justify-content-between">
                <h6 class="mb-1">{{ study.name }}</h6>
                <small>{{ formatDate(study.created_at) }}</small>
              </div>
              <p class="mb-1">{{ study.description }}</p>
              <small>ID: {{ study.subid }}</small>
            </a>
          </div>
        </div>
      </div>

      <!-- Study Details -->
      <div class="col-md-8">
        <div v-if="selectedStudy" class="card">
          <div class="card-header">
            <h5 class="mb-0">{{ selectedStudy.name }}</h5>
          </div>
          <div class="card-body">
            <div class="study-info mb-4">
              <p><strong>Description:</strong> {{ selectedStudy.description }}</p>
              <p><strong>Subject ID:</strong> {{ selectedStudy.subid }}</p>
              <p><strong>Dataset:</strong> {{ selectedStudy.dataset_identifier }}</p>
              <p><strong>Created:</strong> {{ formatDate(selectedStudy.created_at) }}</p>
            </div>

            <!-- Results Tabs -->
            <ul class="nav nav-tabs" role="tablist">
              <li class="nav-item" v-for="tab in resultTabs" :key="tab.id">
                <a
                  class="nav-link"
                  :class="{ active: activeTab === tab.id }"
                  href="#"
                  @click.prevent="activeTab = tab.id"
                >
                  {{ tab.name }}
                </a>
              </li>
            </ul>

            <div class="tab-content mt-3">
              <!-- Days Results -->
              <div v-if="activeTab === 'days'" class="tab-pane active">
                <results-table :data="dayResults" />
                <results-plot :data="dayPlots" />
              </div>

              <!-- Curves Results -->
              <div v-if="activeTab === 'curves'" class="tab-pane active">
                <results-table :data="curveResults" />
                <results-plot :data="curvePlots" />
              </div>

              <!-- Events Results -->
              <div v-if="activeTab === 'events'" class="tab-pane active">
                <results-table :data="eventResults" />
                <results-plot :data="eventPlots" />
              </div>
            </div>
          </div>
        </div>
        <div v-else class="text-center text-muted">
          <p>Select a study to view results</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex'
import ResultsTable from '@/components/ResultsTable.vue'
import ResultsPlot from '@/components/ResultsPlot.vue'

export default {
  name: 'ResultsViewer',
  components: {
    ResultsTable,
    ResultsPlot
  },
  data() {
    return {
      activeTab: 'days',
      resultTabs: [
        { id: 'days', name: 'Days' },
        { id: 'curves', name: 'Curves' },
        { id: 'events', name: 'Events' }
      ]
    }
  },
  computed: {
    ...mapState({
      studies: state => state.studies.list,
      selectedStudy: state => state.studies.selected,
      dayResults: state => state.studies.dayResults,
      dayPlots: state => state.studies.dayPlots,
      curveResults: state => state.studies.curveResults,
      curvePlots: state => state.studies.curvePlots,
      eventResults: state => state.studies.eventResults,
      eventPlots: state => state.studies.eventPlots
    })
  },
  methods: {
    ...mapActions({
      fetchStudies: 'studies/fetchStudies',
      fetchStudyDetails: 'studies/fetchStudyDetails'
    }),
    formatDate(date) {
      return new Date(date).toLocaleString()
    },
    async selectStudy(study) {
      await this.fetchStudyDetails(study.id)
    }
  },
  created() {
    this.fetchStudies()
  }
}
</script>

<style scoped>
.results-viewer {
  padding: 1rem;
}

.study-info {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
}

.study-info p {
  margin-bottom: 0.5rem;
}

.nav-tabs {
  border-bottom: 1px solid #dee2e6;
}

.nav-tabs .nav-link {
  border: none;
  color: #495057;
  cursor: pointer;
}

.nav-tabs .nav-link.active {
  color: #007bff;
  border-bottom: 2px solid #007bff;
  background: none;
}

.tab-content {
  min-height: 200px;
}
</style> 