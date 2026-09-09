# JOIN deployment

JOIN uses the shared `AhmetB-Dev/django-devops-template@v1` CI/CD standard.

## Production layout

- Public API: `https://join-api.ahmet-balci.de`
- Existing host port: `8001`
- Production stack: Django/Gunicorn + PostgreSQL + Redis
- Project path may remain the existing `/opt/join/app`; configure this as `VPS_APP_DIR`.
- The existing Nginx and Let's Encrypt setup can remain unchanged as long as it proxies to `127.0.0.1:8001`.

## GitHub repository configuration

Repository secrets:

- `VPS_HOST` — only the VPS hostname/IP, without `ssh`, username or port syntax.
- `VPS_SSH_PRIVATE_KEY` — the project-specific JOIN deploy private key.
- `VPS_KNOWN_HOSTS` — trusted `known_hosts` entry for the VPS.

Repository variables:

- `VPS_USER` — the existing JOIN deploy user.
- `VPS_APP_DIR` — use the existing server checkout path, currently `/opt/join/app` if unchanged.

GitHub Environment:

- `production`
- Deployment branch restricted to `main`
- No duplicate VPS secrets/variables in the Environment.

## Server environment

Keep the real production `.env` only on the VPS. Do not commit it.
Use `.env.production.example` as documentation.

At minimum, production needs a strong Django secret, PostgreSQL password, the public API hostname and the real frontend origin for CORS.

## Deployment flow

Pull request:

`CI -> Ruff/pip-audit -> PostgreSQL/Redis Django test stack`

Merge/push to `main`:

`CI -> immutable GHCR image -> production gate -> SSH -> compose.prod.yaml -> migrations -> health/readiness -> rollback on failed app rollout`
