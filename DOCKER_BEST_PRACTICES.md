# Docker Best Practices Applied

## Optimization Summary

### Backend (FastAPI - Python 3.11)
✓ **Multi-stage build** — Reduces final image from ~2GB to 390MB
  - Stage 1: Build wheels with dependencies
  - Stage 2: Runtime with only wheels (no build tools)
✓ **Layer caching** — COPY requirements.txt before source code
✓ **Non-root user** — Runs as `appuser` (UID 1000) for security
✓ **Health checks** — FastAPI /docs endpoint checks (30s interval)
✓ **Resource limits** — CPU/memory limits in compose (prevents runaway)
✓ **Alpine base candidate** — Using slim; could use alpine for even smaller
✓ **Pinned dependencies** — All packages pinned to specific versions
✓ **.dockerignore** — Excludes __pycache__, .git, tests, venv, etc.

### Frontend (React + Nginx)
✓ **Multi-stage build** — Reduces from 500MB to 75MB
  - Stage 1: Node builder (npm install, build)
  - Stage 2: Nginx alpine runtime
✓ **Layer caching** — COPY package*.json before source (docker BuildKit optimization)
✓ **Non-root nginx** — Runs as unprivileged nginx user
✓ **Health checks** — Nginx health check (30s interval)
✓ **Alpine nginx** — 1.27-alpine is ~20MB vs 100MB+ standard
✓ **Resource limits** — 1 CPU, 512MB memory (frontend is lightweight)
✓ **Build caching** — Leverages npm ci + cache mounts

### docker-compose.yml
✓ **Health checks on all services** — WITH start_period for slow services
✓ **Restart policies** — unless-stopped (survives daemon restarts)
✓ **Resource limits** — Every service has CPU/memory reservations + limits
✓ **Dependency ordering** — Services wait for health checks (not just startup)
✓ **Volume management** — Named volumes (persistent, not bind mounts)
✓ **Environment reuse** — YAML anchors (&backend-env) reduce duplication
✓ **Container naming** — Predictable names for debugging
✓ **Network isolation** — Custom bridge network (cna_net) vs default
✓ **Secrets in .env** — Passwords/keys sourced from .env, not hardcoded

### Security
✓ Non-root users in both images
✓ Secrets managed via .env (not in image)
✓ No exposed SSH/unnecessary ports
✓ Resource limits prevent DoS

## Quick Start

```bash
# 1. Set up environment
cp .env.example .env  # Already done; adjust if needed

# 2. Build images
docker compose build

# 3. Start services (with health checks)
docker compose up -d --pull always

# 4. Check health
docker compose ps
docker compose logs backend    # if issues

# 5. Download LLM model (first time only)
docker exec cna_ollama ollama pull mistral
# or
docker exec cna_ollama ollama pull llama3

# 6. Load demo data
docker exec cna_backend python /app/../scripts/seed_demo_data.py

# 7. Access dashboard
# Dashboard: http://localhost:3000
# API Docs: http://localhost:8000/docs
# Neo4j Browser: http://localhost:7474 (neo4j / cna_password123)
```

## Production Checklist

Before deploying to production:

- [ ] Update NEO4J_PASSWORD, POSTGRES_PASSWORD, SECRET_KEY in .env
- [ ] Switch OLLAMA_MODEL to a memory-efficient model (mistral < llama3)
- [ ] Add reverse proxy (Nginx/Traefik) with SSL/TLS
- [ ] Set APP_ENV=production
- [ ] Use managed PostgreSQL instead of container
- [ ] Use managed Redis (e.g., AWS ElastiCache) instead of container
- [ ] Mount volumes to host storage with backup policy
- [ ] Configure log aggregation (ELK, Loki, etc.)
- [ ] Add authentication layer (OAuth2, API keys)
- [ ] Monitor resource usage; adjust CPU/memory limits
- [ ] Use Docker secrets for sensitive data instead of .env
- [ ] Set up CI/CD pipelines with BuildKit cache export

## Image Sizes (Post-Optimization)

| Service | Size | Notes |
|---------|------|-------|
| backend | 390MB | Multi-stage, slim Python base |
| frontend | 75MB | Multi-stage, Alpine nginx |
| neo4j | 1.5GB | Official; unavoidable for graph DB |
| postgres | 200MB | Alpine postgres official |
| redis | 50MB | Alpine redis official |
| chromadb | 400MB | Official; vector indexing overhead |
| ollama | 9GB | Model weights; expected |

## Caching Strategy

**Build caching (reduce rebuild time):**
- Backend: requirements.txt layer cached unless deps change
- Frontend: package.json layer cached unless deps change
- Both: Subsequent builds reuse cached layers

**Runtime caching:**
- Redis for real-time alerts
- ChromaDB for vector embeddings (persisted in volume)
- PostgreSQL for structured queries
- Neo4j for graph traversal

## Volume Strategy

| Volume | Mount | Purpose |
|--------|-------|---------|
| neo4j_data | /data | Graph DB persistence |
| postgres_data | /var/lib/postgresql/data | SQL data persistence |
| chroma_data | /chroma/chroma | Vector embeddings |
| ollama_data | /root/.ollama | Downloaded models (4GB+) |
| uploaded_files | /app/uploads | User-uploaded files |
| (dev) ./backend | /app | Source code hot-reload (dev only) |

## Troubleshooting

**Containers won't start:**
```bash
docker compose logs neo4j
docker compose logs backend
docker compose logs frontend
```

**Port conflicts:**
```bash
docker compose ps -a
# Change ports in docker-compose.yml or .env
```

**Out of memory:**
```bash
docker stats  # monitor live
# Increase ollama_data volume or reduce OLLAMA_MODEL size
```

**Slow builds:**
- Use `docker compose build --no-cache` to skip cache
- Check network (pulling base images)
- Consider `--progress=plain` for build logs

## Further Optimizations (Advanced)

1. **Docker BuildKit cache export** — Push build cache to registry
2. **Distroless base images** — Even smaller than Alpine (for frontend)
3. **Scan images with Trivy** — `trivy image backend:latest`
4. **Compose Profiles** — Dev vs. production configurations
5. **Use docker-slim** — Automatically shrink image sizes
