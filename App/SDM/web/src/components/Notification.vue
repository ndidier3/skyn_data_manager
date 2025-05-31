<template>
  <div class="notifications">
    <transition-group name="notification">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        class="notification"
        :class="[notification.type]"
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
    </transition-group>
  </div>
</template>

<script>
import { mapState, mapMutations } from 'vuex'

export default {
  name: 'Notification',
  data() {
    return {
      timeouts: new Map()
    }
  },
  computed: {
    ...mapState('notifications', {
      notifications: state => state.notifications
    })
  },
  methods: {
    ...mapMutations('notifications', {
      removeNotification: 'REMOVE_NOTIFICATION'
    }),
    setupTimeout(notification) {
      // Clear any existing timeout for this notification
      if (this.timeouts.has(notification.id)) {
        clearTimeout(this.timeouts.get(notification.id))
        this.timeouts.delete(notification.id)
      }

      // Only set timeout for notifications that don't require manual removal
      if (!notification.requiresManualRemoval && notification.timeout !== false) {
        const timeout = notification.timeout || 5000
        console.log('Setting timeout for notification:', notification.id, 'timeout:', timeout)
        
        const timeoutId = setTimeout(() => {
          console.log('Timeout triggered for notification:', notification.id)
          this.removeNotification(notification.id)
          this.timeouts.delete(notification.id)
        }, timeout)
        
        this.timeouts.set(notification.id, timeoutId)
      }
    }
  },
  watch: {
    notifications: {
      handler(newNotifications) {
        console.log('Notifications updated:', newNotifications)
        
        // Setup timeouts for new notifications
        newNotifications.forEach(notification => {
          if (!this.timeouts.has(notification.id)) {
            this.setupTimeout(notification)
          }
        })
        
        // Clean up timeouts for removed notifications
        this.timeouts.forEach((timeoutId, notificationId) => {
          if (!newNotifications.find(n => n.id === notificationId)) {
            clearTimeout(timeoutId)
            this.timeouts.delete(notificationId)
          }
        })
      },
      deep: true
    }
  },
  beforeDestroy() {
    // Clean up all timeouts when component is destroyed
    this.timeouts.forEach(timeoutId => clearTimeout(timeoutId))
    this.timeouts.clear()
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
  pointer-events: auto;
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

.notification.critical {
  border-left: 4px solid #dc3545;
  background-color: #fff5f5;
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

/* Slide animations */
.notification-enter-active {
  transition: all 0.3s ease-out;
}

.notification-leave-active {
  transition: all 0.3s ease-in;
}

.notification-enter {
  transform: translateX(100%);
  opacity: 0;
}

.notification-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* Ensure notifications stack properly */
.notification-move {
  transition: transform 0.3s ease;
}
</style> 