<template>
  <div class="results-table">
    <div v-if="!data || !data.features || data.features.length === 0" class="text-center text-muted">
      <p>No results available</p>
    </div>
    <div v-else>
      <div class="table-responsive">
        <table class="table table-striped">
          <thead>
            <tr>
              <th v-for="header in headers" :key="header">{{ header }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in data.features" :key="index">
              <td v-for="header in headers" :key="header">
                {{ formatValue(row[header]) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ResultsTable',
  props: {
    data: {
      type: Object,
      default: () => null
    }
  },
  computed: {
    headers() {
      if (!this.data || !this.data.features || this.data.features.length === 0) {
        return []
      }
      return Object.keys(this.data.features[0])
    }
  },
  methods: {
    formatValue(value) {
      if (value === null || value === undefined) {
        return '-'
      }
      if (typeof value === 'number') {
        return value.toFixed(2)
      }
      return value
    }
  }
}
</script>

<style scoped>
.results-table {
  margin-top: 1rem;
}

.table {
  margin-bottom: 0;
}

.table th {
  background-color: #f8f9fa;
  border-top: none;
  font-weight: 600;
}

.table td {
  vertical-align: middle;
}
</style> 