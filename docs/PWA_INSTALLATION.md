# PWA installation

The site provides a web manifest, standalone display mode, responsive layout, and a service worker that caches only the public application shell. Last-loaded household view data is held in browser localStorage; a task/list completion may queue for retry. Do not use this alpha on shared browser profiles or rely on it as the only copy of a change.

On iPhone: open the trusted HTTPS household URL in Safari, tap Share, choose **Add to Home Screen**, edit the name if desired, then tap **Add**. On iPad use the same Safari steps. Browser and iOS versions can change available PWA behavior; physical-device installation has not been verified here. Web Push, background execution and wake lock are not implemented.
