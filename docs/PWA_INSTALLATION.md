# PWA installation

The site provides a web manifest, standalone display mode, responsive layout, and a service worker that caches only the public application shell. Household records are not stored for offline viewing. IndexedDB may store a minimal task completion intent keyed by the member who authenticated online; intents are removed on logout or detectable session revocation. An offline reload is signed out, and the browser does not guess which household member is using a shared device. Browser storage is not strongly encrypted and cannot guarantee revocation while disconnected.

On iPhone: open the trusted HTTPS household URL in Safari, tap Share, choose **Add to Home Screen**, edit the name if desired, then tap **Add**. On iPad use the same Safari steps. Browser and iOS versions can change available PWA behavior; physical-device installation has not been verified here. Web Push, background execution and wake lock are not implemented.
