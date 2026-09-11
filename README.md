# Project 04: Employee Directory Portal

A searchable directory of employees with profile photo uploads, PostgreSQL database backend, and direct static image serving via Nginx. Features Ansible roles for deployment and a multi-architecture GitHub Actions CI/CD matrix.

---

## Architecture Overview

```
[ Browser / Client ]
        │
        ▼ (Port 80)
 ┌───────────────┐
 │ Nginx Proxy   │────── Direct static read ─────► [ Named Volume: employee_uploads ]
 └───────┬───────┘                                                   ▲
         │ (Proxy / and API)                                         │
         ▼                                                           │
 ┌───────────────┐                                                   │
 │ Flask App     │────── Saves uploaded profile pictures ────────────┘
 └───────┬───────┘
         │ (SQL ILIKE / INSERT)
         ▼
 ┌───────────────┐
 │ PostgreSQL DB │ (Table: employees)
 └───────────────┘
```

---

## Directory Structure

```text
employee-directory/
├── app/
│   ├── app.py                     # Flask routes (ILIKE search, upload handler, DB init)
│   ├── requirements.txt           # Python dependencies
│   ├── static/
│   │   ├── css/style.css          # Responsive styling & employee card layout
│   │   ├── js/app.js              # Live-search listener (no reload) & AJAX upload
│   │   └── img/placeholder.svg    # Default avatar fallback
│   └── templates/
│       └── index.html             # UI with search bar, card grid, and register modal
├── nginx/
│   └── default.conf               # Direct static serving (/static/uploads) + Flask proxy
├── ansible/
│   ├── inventory.ini              # Target server inventory
│   ├── site.yml                   # Master deployment playbook
│   └── roles/
│       ├── docker_setup/          # Role 1: Docker engine & compose setup
│       ├── app_deploy/            # Role 2: Directory setup & docker compose run
│       └── nginx_config/          # Role 3: Nginx reverse proxy config & reload
├── .github/
│   └── workflows/
│       └── build-push.yml         # Multi-platform matrix buildx & GHCR push
├── Dockerfile                     # Flask container definition
├── docker-compose.yml             # Orchestration of db, app, and nginx services
├── init.sql                       # PostgreSQL schema and initial seed data
└── README.md
```

---

## Quick Start (Local Run)

### 1. Start the Stack
Run Docker Compose from the root directory:
```bash
docker compose up -d --build
```

### 2. Access the Application
Open your web browser and navigate to:
```
http://localhost
```

### 3. Verification of Deliverables

#### Deliverable 1: Live search filters cards without page reload
- Start typing in the search bar (e.g. `Engineer`, `Sarah`, `Design`).
- Inspect the browser Network tab: notice `GET /search?q=...` requests return JSON and cards filter in real-time with zero page reload.

#### Deliverable 2: Uploaded photos survive container restarts via named volume
1. Click **Add Employee**, fill in details, and upload a profile picture.
2. Verify the new employee appears with their picture.
3. Stop and restart the containers:
   ```bash
   docker compose down
   docker compose up -d
   ```
4. Refresh `http://localhost`: The uploaded profile picture persists because it is stored in the Docker named volume `employee_uploads`.

#### Deliverable 3: Nginx serves static files; Flask only handles API logic
- Fetch a static profile picture:
  ```bash
  curl -I http://localhost/static/uploads/<filename>.jpg
  ```
- Response header shows `Server: nginx/...` directly from `/var/www/uploads/`, bypassing Python/Gunicorn.

#### Deliverable 4: Ansible roles run cleanly with `--check` mode
Test the Ansible playbook in dry-run mode:
```bash
ansible-playbook -i ansible/inventory.ini ansible/site.yml --check
```

#### Deliverable 5: GitHub Actions matrix build & push to GHCR
- Push code to your GitHub `main` branch.
- The workflow `.github/workflows/build-push.yml` builds for `linux/amd64` and `linux/arm64` using Docker Buildx.
- Images are pushed to GitHub Container Registry (`ghcr.io`) tagged with:
  - `:latest`
  - `:sha-<git-sha>`

---

## Windows & Docker Desktop Setup Notes

1. **Enable containerd in Docker Desktop**:
   - Open **Settings** > **General** (or **Features in development**).
   - Check **Use containerd for storing images**.
2. **Enable Docker Buildx Builder**:
   - Run the following command in PowerShell:
     ```powershell
     docker buildx create --name multiarch-builder --use
     docker buildx inspect --bootstrap
     ```
3. **GHCR Authentication**:
   - In your GitHub Repository: Go to **Settings > Secrets and variables > Actions**.
   - Ensure the default `GITHUB_TOKEN` has read/write package permissions, or add a Personal Access Token (`GHCR_PAT`) with `write:packages` scope.
