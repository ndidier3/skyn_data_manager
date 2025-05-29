<template>
  <div class="results-plot">
    <div v-if="!data || !data.plots || data.plots.length === 0" class="text-center text-muted">
      <p>No plots available</p>
    </div>
    <div v-else class="plot-grid">
      <div v-for="(plot, index) in data.plots" :key="index" class="plot-item">
        <h5 class="plot-title">{{ plot.title || `Plot ${index + 1}` }}</h5>
        <img :src="plot.path" :alt="plot.title || `Plot ${index + 1}`" class="plot-image" />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ResultsPlot',
  props: {
    data: {
      type: Object,
      default: () => null
    }
  }
}
</script>

<style scoped>
.results-plot {
  margin-top: 1rem;
}

.plot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  padding: 1rem;
}

.plot-item {
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1rem;
}

.plot-title {
  margin-bottom: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  color: #333;
}

.plot-image {
  width: 100%;
  height: auto;
  border-radius: 2px;
}
</style> 