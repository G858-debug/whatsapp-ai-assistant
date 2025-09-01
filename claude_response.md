<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5274 -->
<!-- Tokens: ~101,830 -->

## ANALYSIS
We need to convert the Refiloe dashboard into a Progressive Web App (PWA) that can be installed on phones. This requires creating a service worker for offline functionality, updating the manifest.json with proper configuration, and creating a dashboard HTML template with PWA capabilities including install prompts and offline indicators.

## FILES TO CHANGE

### FILE: static/manifest.json
```json
{
  "name": "Refiloe Calendar",
  "short_name": "Refiloe",
  "description": "Personal training calendar and business management dashboard",
  "start_url": "/dashboard",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#f5e6d3",
  "orientation": "portrait",
  "scope": "/",
  "icons": [
    {
      "src": "/static/icons/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-96x96.png",
      "sizes": "96x96",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-128x128.png",
      "sizes": "128x128",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-144x144.png",
      "sizes": "144x144",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-152x152.png",
      "sizes": "152x152",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-384x384.png",
      "sizes": "384x384",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "shortcuts": [
    {
      "name": "Today's Schedule",
      "short_name": "Today",
      "description": "View today's training sessions",
      "url": "/dashboard?view=today",
      "icons": [{"src": "/static/icons/icon-96x96.png", "sizes": "96x96"}]
    },
    {
      "name": "Add Session",
      "short_name": "Add",
      "description": "Schedule a new training session",
      "url": "/dashboard?action=add",
      "icons": [{"src": "/static/icons/icon-96x96.png", "sizes": "96x96"}]
    }
  ],
  "categories": ["fitness", "productivity", "business"],
  "lang": "en-ZA"
}
```

### NEW FILE: static/service-worker.js
```javascript
// Service Worker for Refiloe Calendar PWA
const CACHE_NAME = 'refiloe-calendar-v1';
const DATA_CACHE_NAME = 'refiloe-data-v1';
const STATIC_CACHE_URLS = [
  '/',
  '/dashboard',
  '/static/manifest.json',
  '/static/css/dashboard.css',
  '/static/js/dashboard.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[ServiceWorker] Install');
  
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[ServiceWorker] Caching static assets');
      return cache.addAll(STATIC_CACHE_URLS);
    }).then(() => {
      self.skipWaiting();
    })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[ServiceWorker] Activate');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== DATA_CACHE_NAME) {
            console.log('[ServiceWorker] Removing old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Handle API calls (network-first strategy)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Clone the response before caching
          const responseToCache = response.clone();
          
          // Cache successful API responses
          if (response.status === 200) {
            caches.open(DATA_CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
          }
          
          return response;
        })
        .catch(() => {
          // If network fails, try cache
          return caches.match(event.request).then((response) => {
            if (response) {
              return response;
            }
            
            // Return offline response for API calls
            return new Response(JSON.stringify({
              offline: true,
              error: 'No network connection',
              cached: false
            }), {
              headers: { 'Content-Type': 'application/json' },
              status: 503
            });
          });
        })
    );
    return;
  }
  
  // Handle static assets (cache-first strategy)
  event.respondWith(
    caches.match(event.request).then((response) => {
      if (response) {
        return response;
      }
      
      return fetch(event.request).then((response) => {
        // Don't cache non-successful responses
        if (!response || response.status !== 200 || response.type !== 'basic') {
          return response;
        }
        
        // Clone the response
        const responseToCache = response.clone();
        
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });
        
        return response;
      });
    }).catch(() => {
      // Return offline page for navigation requests
      if (event.request.mode === 'navigate') {
        return caches.match('/dashboard');
      }
    })
  );
});

// Background sync for queued actions
self.addEventListener('sync', (event) => {
  console.log('[ServiceWorker] Background sync', event.tag);
  
  if (event.tag === 'sync-calendar-updates') {
    event.waitUntil(syncCalendarUpdates());
  }
});

// Push notifications
self.addEventListener('push', (event) => {
  console.log('[ServiceWorker] Push received');
  
  let data = {};
  if (event.data) {
    data = event.data.json();
  }
  
  const title = data.title || 'Refiloe Calendar';
  const options = {
    body: data.body || 'You have a new notification',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/icon-72x72.png',
    vibrate: [200, 100, 200],
    data: data,
    actions: data.actions || []
  };
  
  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  console.log('[ServiceWorker] Notification click');
  
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow(event.notification.data.url || '/dashboard')
  );
});

// Message handler for client communication
self.addEventListener('message', (event) => {
  console.log('[ServiceWorker] Message received:', event.data);
  
  if (event.data.action === 'skipWaiting') {
    self.skipWaiting();
  }
  
  if (event.data.action === 'clearCache') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            return caches.delete(cacheName);
          })
        );
      }).then(() => {
        return event.ports[0].postMessage({ cleared: true });
      })
    );
  }
});

// Helper function to sync calendar updates
async function syncCalendarUpdates() {
  try {
    // Get queued updates from IndexedDB
    const queue = await getQueuedUpdates();
    
    if (queue.length === 0) {
      return;
    }
    
    // Try to sync each queued update
    for (const update of queue) {
      try {
        const response = await fetch(update.url, {
          method: update.method,
          headers: update.headers,
          body: JSON.stringify(update.body)
        });
        
        if (response.ok) {
          // Remove from queue if successful
          await removeFromQueue(update.id);
        }
      } catch (error) {
        console.error('[ServiceWorker] Sync failed for update:', update.id);
      }
    }
  } catch (error) {
    console.error('[ServiceWorker] Sync error:', error);
  }
}

// IndexedDB helpers for queue management
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('RefiloeDB', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('syncQueue')) {
        db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}

async function getQueuedUpdates() {
  const db = await openDB();
  const tx = db.transaction('syncQueue', 'readonly');
  const store = tx.objectStore('syncQueue');
  
  return new Promise((resolve, reject) => {
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function removeFromQueue(id) {
  const db = await openDB();
  const tx = db.transaction('syncQueue', 'readwrite');
  const store = tx.objectStore('syncQueue');
  
  return new Promise((resolve, reject) => {
    const request = store.delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}
```

### NEW FILE: templates/dashboard.html
```html
<!DOCTYPE html>
<html lang="en-ZA">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Refiloe Calendar - Personal Training Dashboard</title>
    
    <!-- PWA Meta Tags -->
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#f5e6d3">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="application-name" content="Refiloe Calendar">
    
    <!-- Apple Specific Meta Tags for iOS -->
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="Refiloe">
    <link rel="apple-touch-icon" href="/static/icons/icon-192x192.png">
    <link rel="apple-touch-icon" sizes="152x152" href="/static/icons/icon-152x152.png">
    <link rel="apple-touch-icon" sizes="180x180" href="/static/icons/icon-180x180.png">
    
    <!-- Splash Screens for iOS -->
    <link rel="apple-touch-startup-image" href="/static/splash/splash-640x1136.png" media="(device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2)">
    <link rel="apple-touch-startup-image" href="/static/splash/splash-750x1334.png" media="(device-width: 375px) and (device-height: 667px) and (-webkit-device-pixel-ratio: 2)">
    <link rel="apple-touch-startup-image" href="/static/splash/splash-1242x2208.png" media="(device-width: 414px) and (device-height: 736px) and (-webkit-device-pixel-ratio: 3)">
    
    <style>
        :root {
            --primary-color: #f5e6d3;
            --secondary-color: #8b7355;
            --text-color: #333;
            --bg-color: #ffffff;
            --error-color: #dc3545;
            --success-color: #28a745;
            --offline-color: #ffc107;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            -webkit-tap-highlight-color: transparent;
        }
        
        /* Header */
        .header {
            background-color: var(--primary-color);
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--secondary-color);
        }
        
        /* Offline Indicator */
        .offline-indicator {
            display: none;
            background-color: var(--offline-color);
            color: #000;
            padding: 0.5rem;
            text-align: center;
            font-weight: 500;
        }
        
        .offline-indicator.show {
            display: block;
        }
        
        /* Install Banner */
        .install-banner {
            display: none;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            margin: 1rem;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .install-banner.show {
            display: block;
        }
        
        .install-banner-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .install-banner-text h3 {
            margin-bottom: 0.25rem;
        }
        
        .install-banner-text p {
            font-size: 0.9rem;
            opacity: 0.9;
        }
        
        .install-banner-buttons {
            display: flex;
            gap: 0.5rem;
        }
        
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1rem;
            transition: transform 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn-install {
            background-color: white;
            color: #667eea;
            font-weight: 600;
        }
        
        .btn-dismiss {
            background-color: transparent;
            color: white;
            border: 1px solid white;
        }
        
        /* Calendar Container */
        .calendar-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem;
        }
        
        /* Calendar Header */
        .calendar-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .month-year {
            font-size: 1.25rem;
            font-weight: 600;
        }
        
        .calendar-nav {
            display: flex;
            gap: 0.5rem;
        }
        
        .nav-btn {
            padding: 0.5rem 1rem;
            background-color: var(--primary-color);
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        /* Calendar Grid */
        .calendar-grid {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 1px;
            background-color: #e0e0e0;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .calendar-day {
            background-color: white;
            min-height: 80px;
            padding: 0.5rem;
            position: relative;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .calendar-day:hover {
            background-color: #f5f5f5;
        }
        
        .calendar-day.today {
            background-color: #fff3e0;
        }
        
        .calendar-day.selected {
            background-color: #e3f2fd;
        }
        
        .day-number {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        
        .day-events {
            font-size: 0.8rem;
        }
        
        .event-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--secondary-color);
            margin-right: 4px;
        }
        
        /* Settings Button */
        .settings-btn {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background-color: var(--secondary-color);
            color: white;
            border: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }
        
        /* Settings Panel */
        .settings-panel {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background-color: white;
            transform: translateY(100%);
            transition: transform 0.3s;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
            z-index: 200;
        }
        
        .settings-panel.show {
            transform: translateY(0);
        }
        
        .settings-content {
            padding: 1.5rem;
            max-height: 70vh;
            overflow-y: auto;
        }
        
        .settings-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .settings-item {
            padding: 1rem 0;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .settings-item:last-child {
            border-bottom: none;
        }
        
        /* Loading State */
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 2rem;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid var(--secondary-color);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .calendar-grid {
                grid-template-columns: repeat(7, 1fr);
                font-size: 0.9rem;
            }
            
            .calendar-day {
                min-height: 60px;
                padding: 0.25rem;
            }
            
            .day-events {
                display: none;
            }
            
            .event-dot {
                display: block;
                margin: 2px auto;
            }
        }
    </style>
</head>
<body>
    <!-- Header -->
    <header class="header">
        <div class="header-content">
            <div class="logo">Refiloe Calendar</div>
            <div id="connectionStatus">
                <span id="onlineStatus" style="color: var(--success-color);">● Online</span>
            </div>
        </div>
    </header>
    
    <!-- Offline Indicator -->
    <div id="offlineIndicator" class="offline-indicator">
        <span>📶 You're offline - viewing cached data</span>
    </div>
    
    <!-- Install Banner -->
    <div id="installBanner" class="install-banner">
        <div class="install-banner-content">
            <div class="install-banner-text">
                <h3>Install Refiloe Calendar</h3>
                <p>Get quick access from your home screen</p>
            </div>
            <div class="install-banner-buttons">
                <button id="installBtn" class="btn btn-install">Install</button>
                <button id="dismissBtn" class="btn btn-dismiss">Later</button>
            </div>
        </div>
    </div>
    
    <!-- Main Calendar Container -->
    <main class="calendar-container">
        <div class="calendar-header">
            <button class="nav-btn" id="prevMonth">←</button>
            <div class="month-year" id="currentMonth">Loading...</div>
            <button class="nav-btn" id="nextMonth">→</button>
        </div>
        
        <div id="calendarGrid" class="calendar-grid">
            <div class="loading">
                <div class="spinner"></div>
            </div>
        </div>
    </main>
    
    <!-- Settings Button -->
    <button class="settings-btn" id="settingsBtn">⚙️</button>
    
    <!-- Settings Panel -->
    <div class="settings-panel" id="settingsPanel">
        <div class="settings-content">
            <div class="settings-header">
                <h2>Settings</h2>
                <button class="btn" id="closeSettings">✕</button>
            </div>
            
            <div class="settings-item">
                <h3>App Installation</h3>
                <p>Install Refiloe Calendar for quick access</p>
                <button id="settingsInstallBtn" class="btn btn-install" style="margin-top: 0.5rem;">
                    Add to Home Screen
                </button>
            </div>
            
            <div class="settings-item">
                <h3>Clear Cache</h3>
                <p>Remove all cached data and fetch fresh content</p>
                <button id="clearCacheBtn" class="btn" style="margin-top: 0.5rem;">
                    Clear Cache
                </button>
            </div>
            
            <div class="settings-item">
                <h3>Notifications</h3>
                <label>
                    <input type="checkbox" id="notificationsToggle"> 
                    Enable session reminders
                </label>
            </div>
            
            <div class="settings-item">
                <h3>Version</h3>
                <p>Refiloe Calendar v1.0.0</p>
                <p id="updateStatus">Checking for updates...</p>
            </div>
        </div>
    </div>
    
    <script>
        // PWA Installation
        let deferredPrompt;
        let installCount = parseInt(localStorage.getItem('appUseCount') || '0');
        
        // Track app usage
        installCount++;
        localStorage.setItem('appUseCount', installCount.toString());
        
        // Service Worker Registration
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/static/service-worker.js')
                    .then(registration => {
                        console.log('ServiceWorker registered:', registration);
                        
                        // Check for updates
                        registration.addEventListener('updatefound', () => {
                            const newWorker = registration.installing;
                            newWorker.addEventListener('statechange', () => {
                                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                    document.getElementById('updateStatus').textContent = 'Update available! Refresh to apply.';
                                }
                            });
                        });
                    })
                    .catch(err => {
                        console.error('ServiceWorker registration failed:', err);
                    });
            });
        }
        
        // Install prompt handler
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            
            // Show install banner after 3 uses
            if (installCount >= 3 && !isAppInstalled()) {
                showInstallBanner();
            }
        });
        
        // Check if app is installed
        function isAppInstalled() {
            if (window.matchMedia('(display-mode: standalone)').matches) {
                return true;
            }
            if (window.navigator.standalone === true) {
                return true;
            }
            return false;
        }
        
        // Show install banner
        function showInstallBanner() {
            const banner = document.getElementById('installBanner');
            banner.classList.add('show');
        }
        
        // Install button click handler
        document.getElementById('installBtn').addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                console.log(`User response to install prompt: ${outcome}`);
                deferredPrompt = null;
                document.getElementById('installBanner').classList.remove('show');
            }
        });
        
        // Settings install button
        document.getElementById('settingsInstallBtn').addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                deferredPrompt = null;
            } else if (!isAppInstalled()) {
                alert('To install: \n\niOS: Tap the share button and select "Add to Home Screen"\n\nAndroid: Check your browser menu for "Install App"');
            } else {
                alert('App is already installed!');
            }
        });
        
        // Dismiss banner
        document.getElementById('dismissBtn').addEventListener('click', () => {
            document.getElementById('installBanner').classList.remove('show');
            localStorage.setItem('installBannerDismissed', 'true');
        });
        
        // Online/Offline detection
        function updateOnlineStatus() {
            const onlineStatus = document.getElementById('onlineStatus');
            const offlineIndicator = document.getElementById('offlineIndicator');
            
            if (navigator.onLine) {
                onlineStatus.textContent = '● Online';
                onlineStatus.style.color = 'var(--success-color)';
                offlineIndicator.classList.remove('show');
                
                // Sync any queued updates
                if ('sync' in self.registration) {
                    self.registration.sync.register('sync-calendar-updates');
                }
            } else {
                onlineStatus.textContent = '○ Offline';
                onlineStatus.style.color = 'var(--offline-color)';
                offlineIndicator.classList.add('show');
            }
        }
        
        window.addEventListener('online', updateOnlineStatus);
        window.addEventListener('offline', updateOnlineStatus);
        updateOnlineStatus();
        
        // Settings panel
        document.getElementById('settingsBtn').addEventListener('click', () => {
            document.getElementById('settingsPanel').classList.add('show');
        });
        
        document.getElementById('closeSettings').addEventListener('click', () => {
            document.getElementById('settingsPanel').classList.remove('show');
        });
        
        // Clear cache
        document.getElementById('clearCacheBtn').addEventListener('click', async () => {
            if (confirm('This will remove all cached data. Continue?')) {
                if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                    const messageChannel = new MessageChannel();
                    messageChannel.port1.onmessage = (event) => {
                        if (event.data.cleared) {
                            alert('Cache cleared successfully!');
                            window.location.reload();
                        }
                    };
                    
                    navigator.serviceWorker.controller.postMessage(
                        { action: 'clearCache' },
                        [messageChannel.port2]
                    );
                }
            }
        });
        
        // Calendar functionality
        let currentDate = new Date();
        let calendarData = [];
        
        async function loadCalendarData() {
            const