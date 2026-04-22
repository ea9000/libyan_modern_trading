// Unregister all service workers and clear caches
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(function(registrations) {
        for (let registration of registrations) {
            registration.unregister();
            console.log('SW unregistered:', registration.scope);
        }
    });
}

// Clear all caches
if ('caches' in window) {
    caches.keys().then(function(cacheNames) {
        cacheNames.forEach(function(cacheName) {
            caches.delete(cacheName);
            console.log('Cache deleted:', cacheName);
        });
    });
}

