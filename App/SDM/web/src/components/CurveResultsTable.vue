<template>
  <div class="results-table">
    <table class="table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Start Time</th>
          <th>Duration</th>
          <th>Peak Activity</th>
          <th>Total Activity</th>
          <th>Curve Type</th>
          <th>Quality Score</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(result, index) in results" :key="index">
          <td>{{ formatDate(result.date) }}</td>
          <td>{{ formatTime(result.start_time) }}</td>
          <td>{{ formatDuration(result.duration) }}</td>
          <td>{{ formatNumber(result.peak_activity) }}</td>
          <td>{{ formatNumber(result.total_activity) }}</td>
          <td>{{ result.curve_type }}</td>
          <td>{{ formatNumber(result.quality_score) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  name: 'CurveResultsTable',
  props: {
    results: {
      type: Array,
      default: () => []
    }
  },
  methods: {
    formatDate(date) {
      if (!date) return ''
      return new Date(date).toLocaleDateString()
    },
    formatTime(time) {
      if (!time) return ''
      return new Date(time).toLocaleTimeString()
    },
    formatNumber(value) {
      if (value === null || value === undefined) return '-'
      return Number(value).toFixed(2)
    },
    formatDuration(minutes) {
      if (minutes === null || minutes === undefined) return '-'
      const hours = Math.floor(minutes / 60)
      const mins = Math.round(minutes % 60)
      return `${hours}h ${mins}m`
    }
  }
}
</script>

<style scoped>
.results-table {
  overflow-x: auto;
}

.table {
  width: 100%;
  margin-bottom: 0;
}

.table th {
  background-color: #f8f9fa;
  font-weight: 600;
  white-space: nowrap;
}

.table td {
  white-space: nowrap;
}
</style> 