import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import router from './router'
import './assets/styles/main.scss'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')

const isLocalDevHost = ['localhost', '127.0.0.1'].includes(window.location.hostname)

async function clearDevServiceWorkers() {
  if (!('serviceWorker' in navigator)) return

  const registrations = await navigator.serviceWorker.getRegistrations()
  await Promise.all(registrations.map((registration) => registration.unregister()))

  if ('caches' in window) {
    const cacheNames = await caches.keys()
    await Promise.all(cacheNames.map((cacheName) => caches.delete(cacheName)))
  }

  console.log('Development mode: cleared service workers and caches for localhost')
}

if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js')
      console.log('SW registered:', registration.scope)

      if (registration.active) {
        await registration.update()
      }
    } catch (err) {
      console.log('SW registration failed:', err)
    }
  })
} else if (isLocalDevHost) {
  window.addEventListener('load', () => {
    clearDevServiceWorkers().catch((err) => {
      console.log('Failed to clear development service workers:', err)
    })
  })
}

window.pushPermissionGranted = false

window.requestWebPushPermission = async function() {
  if (!('Notification' in window)) {
    console.log('This browser does not support notifications')
    return false
  }

  if (Notification.permission === 'granted') {
    window.pushPermissionGranted = true
    return true
  }

  if (Notification.permission === 'denied') {
    return false
  }

  try {
    const permission = await Notification.requestPermission()
    if (permission === 'granted') {
      window.pushPermissionGranted = true
      return true
    }
    return false
  } catch (err) {
    console.error('Error requesting push permission:', err)
    return false
  }
}

window.checkPushPermission = function() {
  if (!('Notification' in window)) {
    return 'unsupported'
  }
  return Notification.permission
}
