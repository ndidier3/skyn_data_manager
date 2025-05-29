<template>
  <div id="app">
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
      <div class="container">
        <router-link class="navbar-brand" to="/">SDM Web Interface</router-link>
        <button
          class="navbar-toggler"
          type="button"
          data-toggle="collapse"
          data-target="#navbarNav"
          aria-controls="navbarNav"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav">
            <li class="nav-item">
              <router-link class="nav-link" to="/analysis">Analysis Setup</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/results">Results Viewer</router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <div class="container mt-4">
      <router-view></router-view>
    </div>

    <notification />
  </div>
</template>

<script>
import Notification from '@/components/Notification.vue'

export default {
  name: 'App',
  components: {
    Notification
  }
}
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
}

.navbar {
  margin-bottom: 2rem;
}

.navbar-brand {
  font-weight: 600;
}

.nav-link {
  font-weight: 500;
}

.nav-link.router-link-exact-active {
  color: #fff !important;
  font-weight: 600;
}
</style> 