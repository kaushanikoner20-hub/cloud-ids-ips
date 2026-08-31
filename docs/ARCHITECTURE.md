# Cloud-Based Intrusion Detection and Prevention System (Cloud IDS/IPS)

**Document type:** Architecture and design (no implementation)  
**Audience:** Project team, faculty reviewers, evaluators  
**Scope:** Simulated / authorized events only. This system does not generate, weaponize, or execute real-world unauthorized attacks.

---

## 1. Complete architecture

### 1.1 Design goals

The system is a **demonstration-grade cloud IDS/IPS**: it ingests structured network/security events, scores them with **deterministic rules** and an **unsupervised anomaly model**, stores alerts, and **simulates** blocking of high-risk source IPs. It is suitable for Docker-based local demos and later deployment on a cloud VM or container platform.

Academic honesty constraints:

- Rule-based detection covers a **small, named set** of patterns (rate, failed auth, port scan). It is not a complete signature IDS.
- Isolation Forest flags **statistical outliers in simulated feature space**. It does not claim to detect every unknown cyberattack.
- IPS is a **controlled abstraction**: demonstration mode writes to a blocked-IP collection and never issues uncontrolled network-level drops.
- The traffic generator emits **benign and labeled synthetic events** for demos and tests. It is not attack tooling.

### 1.2 High-level topology

```text
┌─────────────────────┐
│  Event simulator    │  Python CLI / optional HTTP client
│  (synthetic events) │
└──────────┬──────────┘
           │ POST /api/v1/events  (JSON, authenticated demo token optional)
           ▼
┌──────────────────────────────────────────────────────────────────┐
│  FastAPI application (API + static dashboard)                    │
│                                                                  │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐               │
│  │ Ingest API │─▶│ Event bus   │─▶│ Detection    │               │
│  │ validation │  │ (in-process │  │ orchestrator │               │
│  └────────────┘  │  pipeline)  │  └──┬───────┬───┘               │
│                  └─────────────┘     │       │                   │
│                         ┌────────────┘       └─────────┐         │
│                         ▼                              ▼         │
│              ┌──────────────────┐           ┌─────────────────┐  │
│              │ Rule engine      │           │ ML anomaly      │  │
│              │ (windowed state) │           │ service         │  │
│              └────────┬─────────┘           └────────┬────────┘  │
│                       │  detections                  │ score     │
│                       └──────────────┬───────────────┘           │
│                                      ▼                           │
│                           ┌─────────────────────┐                │
│                           │ Severity merger     │                │
│                           │ Alert writer        │                │
│                           └──────────┬──────────┘                │
│                                      │                           │
│                    ┌─────────────────┼─────────────────┐         │
│                    ▼                 ▼                 ▼         │
│             ┌────────────┐   ┌────────────┐   ┌───────────────┐  │
│             │ MongoDB    │   │ IPS        │   │ Dashboard     │  │
│             │ alerts,    │   │ abstraction│   │ (HTML/JS     │  │
│             │ events,    │   │ (demo      │   │  Chart.js    │  │
│             │ blocks     │   │  blocklist)│   │  polling)    │  │
│             └────────────┘   └────────────┘   └───────────────┘  │
└──────────────────────────────────────────────────────────────────┘
           ▲
           │  MongoDB (events, alerts, blocked_ips, model_meta, audit)
           │
┌──────────┴──────────┐
│  MongoDB 7          │  Docker service
└─────────────────────┘
```

### 1.3 Runtime process model

| Process | Role |
|---|---|
| `api` (Uvicorn + FastAPI) | HTTP APIs, static dashboard, detection pipeline, IPS demo adapter |
| `mongodb` | Persistence |
| `simulator` (on demand) | CLI that POSTs synthetic events; not a long-running production service |

Detection runs **in-process** after ingest (synchronous request path with bounded work). This keeps the academic demo simple and Docker-friendly. A future cloud scale-out can replace the in-process orchestrator with a queue (e.g. Redis/RabbitMQ) without changing collection schemas.

Windowed rule state (request counts, failed logins, distinct ports) lives in an **in-memory sliding-window store** keyed by source IP, with optional persistence of last-seen counters in MongoDB for restart resilience. For v1, in-memory + process restart is acceptable if documented.

### 1.4 Request lifecycle (one event)

1. Client POSTs a validated `NetworkEvent`.
2. API persists a raw event document (`events` collection) for audit/replay.
3. Orchestrator:
   - Updates sliding windows for that `src_ip`.
   - Runs all enabled rules; collects zero or more `RuleHit`s.
   - Extracts ML features; Isolation Forest returns `anomaly_score`, `is_anomaly`, and top contributing features (see §7).
   - Merges hits + ML into a single **severity** (`low` | `medium` | `high`) and optional `attack_type`.
4. If any rule hit or ML anomaly: write `alerts` document.
5. If severity is `high` **and** IPS is enabled: call `Blocker.block(src_ip, reason, ttl)` (demo adapter upserts `blocked_ips`).
6. Response returns ingest acknowledgement plus detection summary (useful for simulator and tests). Dashboard does not depend on this; it polls read APIs.

Duplicate / burst handling: ingest is idempotent only if the client supplies `event_id`. Duplicate `event_id` is stored once (unique index).

### 1.5 Severity policy (deterministic, documented)

Severity is **not** a black-box. Proposed merge rules (tunable via env):

| Condition | Severity |
|---|---|
| ML anomaly only, score below medium threshold | `low` |
| Single medium-weight rule (e.g. elevated rate below DDoS threshold) | `medium` |
| Brute-force or port-scan rule hit | `medium` (escalate to `high` if window count ≥ escalate threshold) |
| DDoS / high request-rate rule hit | `high` |
| Any rule hit **and** ML anomaly | max(rule severity, `medium`) then +1 step, capped at `high` |
| IPS block action | only when final severity is `high` (configurable) |

Attack type when multiple rules fire: primary = highest-weight rule; others listed in `rule_hits[]`.

### 1.6 Cloud deployment shape (without locking a vendor)

The same Docker Compose stack maps to:

- One VM (AWS EC2 / Azure VM / GCP Compute) running Compose, or
- Managed MongoDB + a container for the API (later).

Environment variables carry secrets and thresholds. No cloud-vendor SDKs in v1. Health endpoints support load balancer probes.

### 1.7 Security posture (academic, still required)

- Dashboard and APIs bind to configurable host; default Docker internal network.
- Optional `API_TOKEN` for mutating endpoints (`POST /events`, block/unblock). Read APIs may be open on localhost for demo.
- Pydantic validation on all bodies; reject extra unexpected large payloads via size limits.
- Structured JSON logs; no secrets in logs.
- Simulator talks only to the local/demo API base URL.

---

## 2. Directory and file structure

```text
cloud-ids-ips/
├── ARCHITECTURE.md                 # this document
├── README.md                       # run, demo, academic disclaimer (implementation phase)
├── .env.example
├── .gitignore
├── pyproject.toml                  # or requirements.txt + requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI factory, CORS, static mount, routers
│   ├── config.py                   # pydantic-settings from environment
│   ├── logging_config.py           # structured logging setup
│   ├── dependencies.py             # DB, token, blocker, detector wiring
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes_events.py        # ingest
│   │   ├── routes_alerts.py        # list/filter/stats
│   │   ├── routes_ips.py           # blocked IPs, demo unblock
│   │   ├── routes_health.py
│   │   └── routes_dashboard.py     # optional JSON used only by UI
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── event.py                # NetworkEvent ingest + stored view
│   │   ├── alert.py
│   │   ├── ips.py
│   │   ├── stats.py
│   │   └── common.py               # Severity, AttackType enums
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── mongo.py                # client, indexes, lifespan
│   │   └── repositories/
│   │       ├── events_repo.py
│   │       ├── alerts_repo.py
│   │       └── blocked_ips_repo.py
│   │
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # rules + ML + severity merge
│   │   ├── window_store.py         # sliding windows by src_ip
│   │   ├── severity.py
│   │   └── rules/
│   │       ├── __init__.py         # Rule protocol + registry
│   │       ├── base.py
│   │       ├── high_request_rate.py
│   │       ├── brute_force.py
│   │       └── port_scan.py
│   │
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── features.py             # event → feature vector
│   │   ├── anomaly.py              # IsolationForest wrapper
│   │   ├── train.py                # fit from baseline/simulated benign events
│   │   └── explain.py              # simple feature contribution helper
│   │
│   ├── ips/
│   │   ├── __init__.py
│   │   ├── blocker.py              # Blocker protocol
│   │   ├── demo_blocker.py         # MongoDB blocklist (demonstration)
│   │   └── noop_blocker.py         # tests / dry-run
│   │
│   ├── services/
│   │   ├── ingest_service.py
│   │   └── stats_service.py        # aggregations for dashboard
│   │
│   └── static/                     # dashboard (no build step)
│       ├── index.html
│       ├── css/styles.css
│       └── js/
│           ├── api.js
│           ├── charts.js
│           └── app.js
│
├── simulator/
│   ├── __init__.py
│   ├── cli.py                      # python -m simulator
│   ├── scenarios.py                # benign, rate-burst, auth-fail, port-scan, mixed
│   └── client.py                   # HTTP client to ingest API
│
├── scripts/
│   ├── train_model.py              # offline training entry
│   └── seed_demo.py                # optional demo seed
│
├── models/                         # gitignored binaries; keep .gitkeep
│   └── .gitkeep                    # isolation_forest.joblib produced at train/start
│
├── tests/
│   ├── conftest.py
│   ├── test_rules.py
│   ├── test_severity.py
│   ├── test_features.py
│   ├── test_anomaly.py
│   ├── test_ingest_api.py
│   ├── test_alerts_api.py
│   ├── test_ips_demo.py
│   └── test_simulator_scenarios.py
│
└── docs/                           # optional later: API notes, demo script for viva
```

Implementation phase may add `app/core/` if shared exceptions grow; keep it out of v1 unless needed.

---

## 3. Module responsibilities

| Module | Responsibility | Must not do |
|---|---|---|
| `app.main` | Create FastAPI app, lifespan (Mongo connect, load/train ML, create indexes), mount static dashboard | Business logic |
| `app.config` | Typed settings: Mongo URI, thresholds, `IPS_MODE=demo\|noop`, `ML_MODEL_PATH`, poll-friendly CORS | Read os.environ ad hoc elsewhere |
| `app.api.*` | HTTP mapping, status codes, OpenAPI tags | Direct sklearn / window mutation |
| `app.schemas.*` | Request/response contracts, enums, validation | DB driver types |
| `app.db.mongo` | Motor or PyMongo client, index creation | Detection |
| `app.db.repositories` | CRUD and aggregations | HTTP |
| `app.detection.rules` | Each rule: `evaluate(context) -> Optional[RuleHit]`. Registry for extra rules later | Packet capture, exploits |
| `app.detection.window_store` | Per-IP counters: requests, failed auth, dest ports, timestamps | Persistence of alerts |
| `app.detection.orchestrator` | Sequence: windows → rules → ML → merge → persist → IPS | UI |
| `app.detection.severity` | Pure functions: hits + ML → severity, attack_type | I/O |
| `app.ml.features` | Deterministic feature extraction | Training |
| `app.ml.anomaly` | Load Isolation Forest; `predict` / `score_samples` | Claim attack taxonomy |
| `app.ml.train` | Fit on benign baseline (simulated); persist joblib | Live unsupervised retraining in v1 (optional later) |
| `app.ml.explain` | Rank features by deviation vs training stats (mean/std or path-length proxy) | SHAP dependency in v1 (optional later) |
| `app.ips.blocker` | Protocol: `block`, `unblock`, `is_blocked`, `list_active` | OS firewall / cloud ACL calls in v1 |
| `app.ips.demo_blocker` | Upsert `blocked_ips` with reason, timestamps, TTL, `enforcement=simulated` | Real drop of packets |
| `app.services.ingest_service` | Glue: validate uniqueness, call orchestrator | HTML |
| `app.services.stats_service` | Dashboard aggregates | Detection |
| `simulator` | Emit **synthetic** events with scenario labels for demos | Payload construction for real services, credential stuffing against third parties |
| `tests` | Fast unit + API tests with mongomock or ephemeral Mongo | Live internet targets |

**Rule plugin contract (for later rules):**

```text
class Rule(Protocol):
    id: str
    name: str
    default_severity: Severity
    def evaluate(self, event: NetworkEvent, window: IpWindow) -> RuleHit | None
```

New rules register in `rules/__init__.py` without changing the orchestrator.

**IPS extension contract:**

```text
class Blocker(Protocol):
    async def block(self, ip: str, reason: str, severity: Severity, ttl_seconds: int) -> BlockResult
    async def unblock(self, ip: str, reason: str) -> None
    async def is_blocked(self, ip: str) -> bool
    async def list_active(self) -> list[BlockedIp]
```

A future `CloudAclBlocker` would implement the same protocol behind `IPS_MODE=cloud` after explicit authorization. v1 ships only `demo` and `noop`.

---

## 4. API endpoints

Base path: `/api/v1`. OpenAPI at `/docs` and `/redoc`. Dashboard at `/`.

### 4.1 Health

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Liveness: process up |
| GET | `/api/v1/health/ready` | Readiness: Mongo ping, ML model loaded |

### 4.2 Event ingest

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/events` | Ingest one event; run detection; return `IngestResult` |
| POST | `/api/v1/events/batch` | Ingest up to N events (simulator bursts); bounded `max_batch` |

`IngestResult` (response): `event_id`, `accepted`, `alert_created`, `alert_id?`, `severity?`, `attack_types[]`, `ml`, `blocked?`.

### 4.3 Alerts

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/alerts` | Paginated list; query: `severity`, `attack_type`, `src_ip`, `since`, `until`, `limit`, `offset` |
| GET | `/api/v1/alerts/{alert_id}` | Single alert with rule hits, ML explanation, linked `event_id` |
| GET | `/api/v1/alerts/recent` | Last N for live table (default 20) |

### 4.4 Statistics (dashboard)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/stats/summary` | `total_alerts`, `active_threats` (unresolved high/medium in window), `blocked_ip_count`, `events_ingested` |
| GET | `/api/v1/stats/attack-distribution` | Counts by `attack_type` |
| GET | `/api/v1/stats/severity-distribution` | Counts by severity |
| GET | `/api/v1/stats/trends` | Time buckets: query `bucket=minute\|hour`, `since` |
| GET | `/api/v1/stats/top-sources` | Optional: top `src_ip` by alert count (demo useful) |

**Active threats definition:** alerts with `severity` in `{medium, high}` created within `ACTIVE_THREAT_WINDOW_SECONDS` and `status != resolved`.

### 4.5 IPS (demonstration)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/ips/blocked` | Active simulated blocks |
| POST | `/api/v1/ips/blocked` | Manual demo block (authorized token); still simulated |
| DELETE | `/api/v1/ips/blocked/{ip}` | Demo unblock / expire |
| GET | `/api/v1/ips/check/{ip}` | Whether IP is currently on the demo blocklist |

Manual block exists so the viva can show IPS without waiting for a high-severity auto-block.

### 4.6 Model (read-only, academic transparency)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/ml/info` | Algorithm name, trained_on, n_estimators, contamination, feature names, disclaimer text |

No unauthenticated model upload in v1.

### 4.7 Out of scope for v1 APIs

- WebSocket push (polling is enough)
- User accounts / RBAC beyond optional static token
- PCAP upload
- Real firewall control

---

## 5. MongoDB collections and schemas

Database name: `cloud_ids` (env `MONGO_DB`).

Indexes are created at startup.

### 5.1 `events`

Raw ingest audit trail.

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `event_id` | string (UUID) | unique |
| `received_at` | datetime | server UTC |
| `occurred_at` | datetime | client timestamp |
| `src_ip` | string | validated IPv4/IPv6 |
| `dst_ip` | string | |
| `src_port` | int | 0–65535 |
| `dst_port` | int | |
| `protocol` | string | `tcp` \| `udp` \| `icmp` \| `http` \| `https` \| `other` |
| `http_method` | string? | |
| `http_path` | string? | truncated |
| `http_status` | int? | |
| `bytes_in` | int | ≥ 0 |
| `bytes_out` | int | ≥ 0 |
| `duration_ms` | int | ≥ 0 |
| `auth_success` | bool? | null if not an auth event |
| `auth_event` | bool | |
| `user_id` | string? | simulated identity only |
| `sensor_id` | string | e.g. `sim-1` |
| `labels` | object? | simulator-only: `scenario`, `expected_attack`; **not used by detectors** |
| `payload_meta` | object | size, content_type; **no raw exploit payloads** |

Indexes: unique `event_id`; `src_ip` + `occurred_at`; `received_at`.

### 5.2 `alerts`

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `alert_id` | string (UUID) | unique |
| `event_id` | string | |
| `created_at` | datetime | |
| `src_ip` | string | |
| `dst_ip` | string | |
| `severity` | string | `low` \| `medium` \| `high` |
| `attack_type` | string | see enum §6 |
| `attack_types` | string[] | all hits |
| `title` | string | human summary |
| `description` | string | |
| `rule_hits` | array | `{rule_id, name, severity, evidence}` |
| `ml` | object | `{is_anomaly, score, threshold, top_features: [{name, value, zscore}]}` |
| `status` | string | `open` \| `resolved` (v1: mostly `open`) |
| `ips_action` | string | `none` \| `simulated_block` |
| `blocked_ip_id` | string? | |

Indexes: unique `alert_id`; `created_at`; `severity`; `attack_type`; `src_ip`; compound for dashboard filters.

### 5.3 `blocked_ips`

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `ip` | string | unique among **active** (partial unique index on `ip` where `active: true`) |
| `active` | bool | |
| `reason` | string | |
| `severity` | string | |
| `enforcement` | string | always `simulated` in v1 |
| `source` | string | `auto` \| `manual` |
| `created_at` | datetime | |
| `expires_at` | datetime | TTL-style; app also filters expired |
| `alert_id` | string? | |
| `unblocked_at` | datetime? | |
| `unblock_reason` | string? | |

Indexes: `ip` + `active`; `expires_at`.

### 5.4 `model_meta`

Single-document or versioned history.

| Field | Type | Notes |
|---|---|---|
| `algorithm` | string | `IsolationForest` |
| `sklearn_version` | string | |
| `trained_at` | datetime | |
| `n_samples` | int | |
| `feature_names` | string[] | |
| `contamination` | float | |
| `n_estimators` | int | |
| `feature_stats` | object | mean/std per feature for explanation |
| `disclaimer` | string | stored copy of academic limitation text |

### 5.5 `audit_log` (optional v1)

Mutating IPS actions and config reloads. Useful for viva.

| Field | Type |
|---|---|
| `at` | datetime |
| `action` | string |
| `actor` | string | `system` \| `demo-admin` |
| `detail` | object |

---

## 6. Event data schema

Canonical ingest model (`NetworkEvent`). This is a **telemetry record**, not a packet dump.

```text
NetworkEvent
  event_id: UUID                    # optional on ingest; server assigns if missing
  occurred_at: datetime             # ISO-8601 UTC
  src_ip: IPvAnyAddress
  dst_ip: IPvAnyAddress
  src_port: int 0..65535
  dst_port: int 0..65535
  protocol: Enum
  http_method: Optional[str]        # GET, POST, ...
  http_path: Optional[str]          # max length e.g. 256
  http_status: Optional[int]
  bytes_in: int >= 0
  bytes_out: int >= 0
  duration_ms: int >= 0
  auth_event: bool = false
  auth_success: Optional[bool]
  user_id: Optional[str]
  sensor_id: str = "default"
  labels: Optional[{                # simulator / tests only
    scenario: str
    expected_attack: Optional[str]
  }]
```

**Attack type enum** (stored on alerts, not required on ingest):

- `benign` (no alert, or unused)
- `ddos_volumetric` (high request rate)
- `brute_force`
- `port_scan`
- `anomaly` (ML-only)
- `mixed` (multiple rules; or keep primary + `attack_types[]`)

**Simulator scenarios** (synthetic only):

| Scenario | What it emits | Intended detection |
|---|---|---|
| `benign_web` | Sparse HTTP-like events, varied IPs, successful auth | Little/no alerts |
| `rate_burst` | Many events, same `src_ip`, short window | high request rate / DDoS |
| `auth_failures` | Repeated `auth_event=true`, `auth_success=false` | brute force |
| `port_sweep` | Same `src_ip`, many distinct `dst_port` | port scan |
| `mixed_demo` | Interleaved benign + the above | dashboard variety |
| `ml_outlier` | Feature values far from training baseline (e.g. extreme bytes/duration) without matching a rule | Isolation Forest |

The simulator **must not** include exploit payloads, password lists for real systems, or instructions to target third-party hosts. Destination IPs are RFC 5737 documentation addresses (e.g. `192.0.2.0/24`) and RFC 3849 IPv6 docs range.

---

## 7. ML feature schema

### 7.1 Design choice

**Algorithm:** `sklearn.ensemble.IsolationForest` (unsupervised).

**Training:** Fit once at startup (or via `scripts/train_model.py`) on a **benign simulated baseline** generated by the same feature extractor. Persist `models/isolation_forest.joblib` plus `feature_stats.json`.

**Inference:** For each event, build a feature vector from the **event plus current window** (so ML can see rate-like context without duplicating rule logic verbatim).

**Limitation (to show on dashboard and `/ml/info`):**  
Isolation Forest scores how isolated a point is in the chosen feature space. Unusual simulated telemetry may score as anomalous; this is **not** equivalent to identifying novel APT techniques, encrypted C2, or zero-days.

### 7.2 Feature vector (v1, fixed order)

All numeric; extractor fills defaults if a field is absent.

| # | Name | Source | Rationale |
|---|---|---|---|
| 0 | `requests_in_window` | window store | volume |
| 1 | `failed_auth_in_window` | window | auth abuse |
| 2 | `unique_dst_ports_in_window` | window | scanning-like spread |
| 3 | `unique_dst_ips_in_window` | window | fan-out |
| 4 | `bytes_in` | event | size outlier |
| 5 | `bytes_out` | event | size outlier |
| 6 | `duration_ms` | event | timing outlier |
| 7 | `dst_port` | event | unusual ports vs baseline |
| 8 | `http_status` | event (0 if N/A) | error clustering |
| 9 | `auth_fail_flag` | 1 if auth_event and not success else 0 | discrete fail |
| 10 | `protocol_code` | small int map | protocol mix |
| 11 | `hour_of_day` | occurred_at UTC hour | time-of-day shift (weak) |

Window length: `DETECTION_WINDOW_SECONDS` (default 60). Same window as rules for consistency.

### 7.3 Outputs

| Field | Meaning |
|---|---|
| `raw_score` | `decision_function` (higher = more normal in sklearn IsolationForest) |
| `anomaly_score` | inverted/normalized 0–1 for UI (“higher = more anomalous”) |
| `is_anomaly` | `predict() == -1` or `anomaly_score >= ML_THRESHOLD` |
| `top_features` | up to 3 features with largest absolute z-score vs training mean/std |

Do not map `is_anomaly` to a CVE or named malware family.

### 7.4 Retraining (v1)

- Default: train on generated benign sample (e.g. 5k–20k rows) if no joblib present.
- Optional: `ML_RETRAIN_ON_START=true`.
- No online learning in v1 (avoids poisoning the demo model with attack scenarios).

---

## 8. Testing strategy

### 8.1 Principles

- Prefer **pure unit tests** for rules, severity, features (no Mongo).
- API tests use FastAPI `TestClient` + **ephemeral Mongo** (GitHub Actions service) or `mongomock` if Motor compatibility is awkward; prefer real Mongo in CI via Docker.
- Simulator tests assert **payload shape and scenario rates**, not that they compromise a host.
- No tests that send traffic to the public internet.

### 8.2 Unit tests

| Area | Examples |
|---|---|
| `high_request_rate` | N events from one IP inside window → hit; below threshold → no hit |
| `brute_force` | K failed auth → hit; successes reset or do not count |
| `port_scan` | M distinct dst_ports → hit |
| `severity` | ML-only low; DDoS high; mixed escalation |
| `features` | Stable vector length and types; missing HTTP fields → zeros |
| `explain` | Extreme bytes_in ranks in top_features |
| `demo_blocker` | block upsert; expired not active; unblock |

### 8.3 API / integration tests

- POST event → 201/200, event stored
- Rate-burst sequence → alert `ddos_volumetric`, optional simulated block if high
- GET stats after seed → counts match
- Duplicate `event_id` → no double alert
- Validation: bad IP, negative bytes → 422
- Ready probe fails if Mongo down (optional)

### 8.4 ML tests

- Fit tiny Isolation Forest on synthetic blob; inliers vs obvious outliers
- Do **not** assert 100% detection of “attacks”
- Assert disclaimer present on `/ml/info`

### 8.5 What we will not test

- Packet-level captures
- Real firewall insertion
- Adversarial robustness of Isolation Forest (out of academic v1 scope; can be mentioned as future work)

### 8.6 Manual demo checklist (viva)

1. Compose up; open dashboard.
2. Run `benign_web` — charts stay quiet.
3. Run `rate_burst` — DDoS alerts, trend spike, possible block.
4. Run `auth_failures` and `port_sweep`.
5. Show blocked IPs page and OpenAPI `/docs`.
6. Unblock via API; confirm list updates on poll.

---

## 9. Docker services

### 9.1 Compose (v1)

| Service | Image / build | Ports | Notes |
|---|---|---|---|
| `mongodb` | `mongo:7` | `27017` (dev only; consider internal-only in “prod” compose overlay) | Volume `mongo_data`; healthcheck `mongosh ping` |
| `api` | build `Dockerfile` | `8000:8000` | Depends on healthy Mongo; env from `.env` |
| `simulator` | same image, different command (optional profile) | none | `profiles: [demo]` so it does not loop forever unless requested |

**API container:** Python 3.11-slim, non-root user, `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Copy `app/static` into the image.

**Networks:** single bridge `idsnet`. API connects with `MONGO_URI=mongodb://mongodb:27017`.

**Volumes:**

- `mongo_data` — database
- optional bind `./models` — persist trained model between restarts

### 9.2 Environment variables (`.env.example`)

```text
MONGO_URI=
MONGO_DB=cloud_ids
API_HOST=0.0.0.0
API_PORT=8000
API_TOKEN=                     # empty = open (local demo only)
LOG_LEVEL=INFO

DETECTION_WINDOW_SECONDS=60
RATE_LIMIT_EVENTS=100          # requests/window → DDoS rule
BRUTE_FORCE_FAILURES=8
PORT_SCAN_UNIQUE_PORTS=12
SEVERITY_ESCALATE_COUNT=20

ML_MODEL_PATH=/app/models/isolation_forest.joblib
ML_CONTAMINATION=0.05
ML_N_ESTIMATORS=200
ML_THRESHOLD=0.65
ML_TRAIN_ON_START=true

IPS_MODE=demo                  # demo | noop
IPS_BLOCK_ON_HIGH=true
IPS_TTL_SECONDS=3600
ACTIVE_THREAT_WINDOW_SECONDS=600

CORS_ORIGINS=http://localhost:8000
```

### 9.3 Cloud mapping

| Compose | Typical cloud |
|---|---|
| `api` service | VM + Docker, or ECS/Cloud Run/Azure Container Apps |
| `mongodb` | MongoDB Atlas or VM-hosted Mongo with auth + network restriction |
| env file | Secret Manager / App Settings |
| `/health/ready` | ALB / Cloud Load Balancing health check |

v1 does not include Kubernetes manifests; Compose is the academic artifact. A short README section will describe “lift to one cloud VM”.

---

## 10. Development order

Build in vertical slices so each step is demoable.

### Phase 0 — Scaffold (no detection yet)

1. `pyproject` / requirements, `config`, logging, FastAPI app, health routes.
2. Docker Compose + Mongo + Dockerfile.
3. Pydantic `NetworkEvent`; POST `/events` that **only stores** events.
4. Empty dashboard shell served as static files.

### Phase 1 — Persistence and read APIs

5. Repositories, indexes.
6. `GET /alerts` (empty), `GET /stats/summary` zeros.
7. pytest + TestClient + Mongo.

### Phase 2 — Rule engine

8. `window_store` + three rules + registry.
9. Orchestrator without ML (ML stub returns not-anomaly).
10. Alerts written; severity tests.
11. Dashboard: total alerts, recent table, severity.

### Phase 3 — IPS abstraction

12. `Blocker` protocol + `demo_blocker` + `noop`.
13. Auto-block on high; GET/DELETE blocked; dashboard blocked list.

### Phase 4 — ML

14. Feature extractor + train script + Isolation Forest wrapper + explain helper.
15. Wire into orchestrator; `/ml/info`; dashboard note on limitations.
16. `ml_outlier` simulator scenario.

### Phase 5 — Dashboard completeness

17. Chart.js: attack distribution, trends, active threats.
18. Polling interval (e.g. 3–5 s) from `api.js`.
19. Visual polish (academic, readable).

### Phase 6 — Simulator and demo pack

20. CLI scenarios, README demo script, seed script.
21. Compose `demo` profile.

### Phase 7 — Hardening for evaluation

22. Input limits, token on mutating routes, structured errors.
23. Expand tests to coverage of rules + ingest + IPS.
24. README: architecture summary, how to run, academic disclaimer, future work (queue, real authorized enforcement, supervised models).

**Do not** start with Kubernetes, WebSockets, or a custom JS framework. **Do not** implement real packet blocking.

---

## 11. Dashboard information architecture

Single page (`index.html`), sections:

1. Header: system name, health badge, last poll time, ML disclaimer one-liner.
2. KPI cards: total alerts, active threats, blocked IPs, events ingested.
3. Charts: attack-type doughnut/bar (Chart.js); severity; trends line.
4. Live alerts table: time, src IP, type, severity, ML score, IPS action.
5. Blocked IPs table: IP, reason, created, expires, simulated badge.

Poll: `summary` + `trends` + `attack-distribution` + `alerts/recent` + `ips/blocked` on one timer.

---

## 12. Risks and explicit non-goals

| Risk | Mitigation |
|---|---|
| Overclaiming ML | Disclaimer on UI and `/ml/info`; tests do not require perfect attack classification |
| Real-world misuse of simulator | Documentation IPs only; no exploit payloads; README ethics note |
| In-memory windows lost on restart | Document; optional later Mongo snapshots |
| Isolation Forest overlap with rules | Acceptable; merger handles dual evidence; ML-only path still useful |
| Blocking the wrong IP in a real network | v1 enforcement is simulated only |

**Non-goals (v1):** packet sniffing, Suricata/Snort rule import, TLS inspection, multi-tenant SaaS, mobile app, generating offensive tooling, unsupervised blocking on a production VPC.

---

## 13. Suggested implementation stack (locked for v1)

| Concern | Choice |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI + Uvicorn |
| Validation / settings | Pydantic v2 + pydantic-settings |
| Mongo | Motor (async) **or** PyMotor-style; if teaching sync is simpler, PyMongo + `def` routes is acceptable — pick **Motor + async routes** for cleaner FastAPI |
| ML | scikit-learn IsolationForest, joblib |
| Features helpers | numpy; pandas only in training script if useful |
| Web | Static HTML/CSS/JS + Chart.js (CDN or vendored) |
| Tests | pytest, httpx/TestClient |
| Containers | Docker + Compose |
| Logging | `logging` + JSON formatter (e.g. python-json-logger) |

**Decision recorded:** use **Motor + async FastAPI** for the API process.

---

## 14. Next step

After this document is accepted, implementation starts at **Phase 0** (scaffold, Compose, event store only). No detection or IPS until Phase 0 stores events reliably and `/docs` is live.
