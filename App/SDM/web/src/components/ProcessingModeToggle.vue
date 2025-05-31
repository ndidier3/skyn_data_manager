<template>
  <div class="form-group mb-4">
    <div class="processing-mode-toggle">
      <label class="toggle-label">Single File</label>
      <div class="toggle-switch" @click="$emit('update:isBatchMode', !isBatchMode)">
        <div class="toggle-slider" :class="{ 'batch-mode': isBatchMode }"></div>
      </div>
      <label class="toggle-label">Batch</label>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ProcessingModeToggle',
  props: {
    isBatchMode: {
      type: Boolean,
      required: true
    }
  }
}
</script>

<style scoped>
.processing-mode-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.toggle-label {
  font-weight: 500;
  color: #495057;
  margin: 0;
  font-size: 0.875rem;
}

.toggle-switch {
  position: relative;
  width: 48px;
  height: 24px;
  background-color: #e9ecef;
  border-radius: 12px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.toggle-switch:hover {
  background-color: #dee2e6;
}

.toggle-slider {
  position: absolute;
  width: 20px;
  height: 20px;
  background-color: #fff;
  border-radius: 50%;
  top: 2px;
  left: 2px;
  transition: transform 0.3s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.toggle-slider.batch-mode {
  transform: translateX(24px);
}
</style> 