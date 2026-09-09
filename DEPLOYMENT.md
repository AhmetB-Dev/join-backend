# JOIN production deployment

JOIN uses the shared `AhmetB-Dev/django-devops-template@v1` CI/CD standard and deploys an immutable GHCR application image to the existing VPS.

## Production layout

| Setting | Value |
| --- | --- |
| Public API | `https://join-api.ahmet-balci.de` |
| VPS application path | `/opt/join/app` |
| Host application port | `8001` |
| Application runtime | Django + Gunicorn |
| Database | PostgreSQL |
| Cache / throttle state | Redis |
| Reverse proxy | Host-level Nginx |
| TLS | Let's Encrypt / Certbot |

Nginx proxies the public API to `127.0.0.1:8001`. The Docker web service is therefore not exposed directly on a public interface.

## GitHub repository configuration

### Repository secrets

- `VPS_HOST` — VPS hostname/IP only; no username, `ssh` prefix, protocol or port syntax.
- `VPS_SSH_PRIVATE_KEY` — project-specific JOIN deployment private key.
- `VPS_KNOWN_HOSTS` — trusted SSH host-key entry for the VPS.

### Repository variables

- `VPS_USER=ahmet`
- `VPS_APP_DIR=/opt/join/app`

### GitHub Environment

Create/use the `production` environment and restrict deployments to `main`. Repository secrets and variables remain at repository level; they are not duplicated inside the Environment.

## VPS environment

The real production `.env` lives only on the VPS at `/opt/join/app/.env` and is never committed.

Use `.env.production.example` as the reference template. Important production values include:

```env
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=join-api.ahmet-balci.de,127.0.0.1,localhost
DJANGO_CORS_ALLOWED_ORIGINS=https://ahmet-balci.de
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_TRUST_PROXY_SSL_HEADER=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
```

Set strong unique values for `DJANGO_SECRET_KEY` and `DB_PASSWORD` on the VPS. Do not copy the placeholder values from the example file into production.

`DJANGO_TRUST_PROXY_SSL_HEADER=True` is required because Nginx terminates HTTPS and forwards the original protocol through `X-Forwarded-Proto`. Without it, Django can redirect an already-HTTPS request back to the same HTTPS URL.

`127.0.0.1`/`localhost` remain in `DJANGO_ALLOWED_HOSTS` because the container healthcheck requests `/api/readiness/` internally.

## Nginx contract

The active JOIN Nginx site proxies to the loopback-only application port and forwards the original request metadata. The relevant proxy headers are:

```nginx
location / {
    proxy_pass http://127.0.0.1:8001;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Keep certificate paths and Certbot-managed directives in the server configuration managed by the VPS.

## Deployment flow

### Pull request

```text
CI
-> Ruff + dependency audit
-> Django test stack with PostgreSQL + Redis
```

### Push / merge to `main`

```text
CI
-> publish immutable GHCR image tagged with commit SHA
-> production environment gate
-> SSH to VPS
-> fast-forward checkout
-> pull target image
-> run migrations
-> recreate application service
-> wait for Docker health/readiness
-> prune unused images on success
```

If application rollout health validation fails, `scripts/deploy.sh` attempts to restore the previously running application image. PostgreSQL and Redis remain separate services and are not replaced as part of application-image rollback.

## Health checks

Liveness:

```text
GET /api/health/
```

Readiness:

```text
GET /api/readiness/
```

Readiness verifies both PostgreSQL and Redis. Docker considers the web service healthy only when this endpoint succeeds.

Production smoke check:

```bash
curl -fsS https://join-api.ahmet-balci.de/api/health/
curl -fsS https://join-api.ahmet-balci.de/api/readiness/
```

## Operational notes

- Keep the production `.env` outside Git and preserve it across deployments.
- Do not change the production PostgreSQL password casually on an existing database volume.
- Do not use `docker compose down -v` unless deleting production database data is intentional.
- `APP_IMAGE` is supplied by the deployment workflow and exported by `scripts/deploy.sh` for the full Compose/rollback lifecycle.
- The application repository uses the shared workflow tag `@v1`, not a moving `@main` reference.
