# Local HTTPS and DNS

Use a trusted HTTPS certificate for PWA installation and secure cookies. Recommended options:

- Point `householdsix.home.arpa` to the NAS using router DNS, Pi-hole, or another local DNS resolver. `.home.arpa` is reserved for home networks.
- Terminate TLS at Synology Reverse Proxy with a certificate trusted by the devices, or enable the Compose Caddy profile (`tls internal`).
- Caddy's internal CA must be installed on each iPhone/iPad and explicitly enabled under certificate trust settings. Trusting a CA allows it to issue certificates accepted by that device; protect its private key and remove the CA if no longer used.
- Do not disable certificate checks. Do not expose the app's HTTP port beyond a trusted proxy or loopback.

Ports are configurable with `HOST_PORT`, `BIND_ADDRESS`, and `CADDY_HTTPS_PORT`. The default app port is loopback-only; host reverse-proxy access requires `BIND_ADDRESS=0.0.0.0`, so restrict ingress accordingly.

For Caddy, export its root certificate with `docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./household-six-root.crt`, then transfer it to the iPhone using an approved local method such as AirDrop. Open the certificate on the phone and install the downloaded profile in **Settings → General → VPN & Device Management**. Then open **Settings → General → About → Certificate Trust Settings** and enable full trust for that root. Labels can vary slightly between iOS releases. Only trust a CA you control; it can issue certificates the device accepts for other sites too. Open the household URL in Safari and use **Share → Add to Home Screen**.
