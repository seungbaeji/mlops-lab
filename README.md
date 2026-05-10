# MLOps Lab (Homelab Edition)

This repository is designed for practicing end-to-end MLOps and data engineering in a personal homelab environment. While the current example focuses on IoT data, the stack is modular and extensible for a wide range of data-driven and machine learning scenarios.

---

## Repository Structure

```
mlops-lab/
├── docker/
│   └── iot-mlops/
│       ├── app_config/           # TOML configuration for each service
│       ├── compose.yaml          # Full stack orchestration
│       ├── config/               # Infra configs for DB, MQTT, Redis, etc.
│       └── observability_config/ # Grafana, Prometheus, Tempo, OTEL configs
├── Makefile                      # Development/operation utility commands
├── python/
│   ├── apps/
│   │   ├── iot-simulator/        # Example: IoT data simulator (FastAPI)
│   │   ├── iot-subscriber/       # Example: MQTT subscriber/Redis ingestion
│   │   └── redis-to-postgres/    # Example: Redis → Postgres ETL
│   └── common/                   # Shared modules (observability, etc.)
├── scripts/                      # Development/testing scripts
└── README.md
```

---

## Main Components

- **docker/iot-mlops/compose.yaml**: Orchestrates all services (Docker Compose)
- **iot-simulator**: FastAPI-based IoT sensor data simulator (publishes to MQTT)
- **iot-subscriber**: Subscribes to MQTT, preprocesses data, and ingests into Redis
- **redis-to-postgres**: ETL from Redis Stream to PostgreSQL
- **Observability stack**: Prometheus, Grafana, Tempo, OTEL Collector
- **Common modules**: Shared Python code for observability, config, logging, etc.

> **Note:** The current stack demonstrates an IoT data pipeline, but the architecture is designed to be extended for other data sources, pipelines, and ML/AI workloads.

---

## Getting Started

### 1. Prerequisites
- Install Docker and Docker Compose
- (Optional) Python 3.12+, pipx, uv, poetry (for local development)

### 2. Run the Full Stack

```bash
git clone <repo-url>
cd mlops-lab
make run-iot-mlops
# Or run directly
# docker compose -f docker/iot-mlops/compose.yaml up --build
```

### 3. Service Configuration
- Each service's TOML config is under `docker/iot-mlops/app_config/`
- Infra configs are in `docker/iot-mlops/config/`

---

## Service Endpoints

- **Grafana (Observability Dashboard):** [http://localhost:3000](http://localhost:3000)  (admin/admin)
- **Prometheus (Metrics):** [http://localhost:9090](http://localhost:9090)
- **Simulator API (Sensor Simulator):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Redis Commander:** [http://localhost:8081](http://localhost:8081)
- For other service ports, refer to compose.yaml (can be changed)

---

## Purpose
- Practice end-to-end MLOps and data engineering pipelines
- Experience automation: data generation → ingestion/storage → ETL → observability/monitoring → (inference/deployment planned)
- Gain DevOps/MLOps automation experience in a homelab environment
- **Extensible:** Easily add new data sources, pipelines, and ML/AI services beyond IoT

---

## Development & Utilities
- `make init-python`: Install Python development tools (pipx, uv, poetry, etc.)
- `make precommit`: Run pre-commit hooks and TOML formatting
- `make python-lock`: Lock dependencies for all Python apps

---

## Notes
- Service ports and configs can be adjusted in `docker/iot-mlops/compose.yaml` and each TOML file
- Observability stack: Prometheus, Grafana, Tempo, OTEL Collector integrated
- (Planned) Expansion for model inference/serving, data pipelines, ML model management, etc.

---

This repository is optimized for hands-on MLOps and data engineering practice in a personal homelab. While the current example is IoT-focused, the stack is designed for easy extension to other domains. Feel free to fork or modify for your own use!

