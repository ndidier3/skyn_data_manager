<template>
  <div class="notifications">
    <div
      v-for="notification in notifications"
      :key="notification.id"
      class="notification"
      :class="[notification.type, { 'notification-enter': true }]"
    >
      <div class="notification-content">
        <h4 v-if="notification.title" class="notification-title">
          {{ notification.title }}
        </h4>
        <p class="notification-message">{{ notification.message }}</p>
      </div>
      <button
        class="notification-close"
        @click="removeNotification(notification.id)"
        aria-label="Close"
      >
        ×
      </button>
    </div>
  </div>
</template>

<script>
import { mapState, mapMutations } from 'vuex'

export default {
  name: 'Notification',
  computed: {
    ...mapState('notifications', {
      notifications: state => state.notifications
    })
  },
  methods: {
    ...mapMutations('notifications', {
      removeNotification: 'REMOVE_NOTIFICATION'
    })
  }
}
</script>

<style scoped>
.notifications {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}

.notification {
  display: flex;
  align-items: flex-start;
  min-width: 300px;
  max-width: 400px;
  padding: 15px;
  border-radius: 4px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transform: translateX(100%);
  opacity: 0;
  transition: all 0.3s ease-out;
  pointer-events: auto;
}

.notification-enter {
  transform: translateX(0);
  opacity: 1;
}

.notification.success {
  border-left: 4px solid #28a745;
}

.notification.error {
  border-left: 4px solid #dc3545;
}

.notification.warning {
  border-left: 4px solid #ffc107;
}

.notification.info {
  border-left: 4px solid #17a2b8;
}

.notification-content {
  flex: 1;
  margin-right: 10px;
}

.notification-title {
  margin: 0 0 5px;
  font-size: 1rem;
  font-weight: 600;
}

.notification-message {
  margin: 0;
  font-size: 0.875rem;
  color: #666;
}

.notification-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  line-height: 1;
  color: #999;
  cursor: pointer;
  padding: 0;
  margin-left: 10px;
}

.notification-close:hover {
  color: #666;
}
</style> 