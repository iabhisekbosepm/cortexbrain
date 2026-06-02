# {PROJECT_NAME} — Requirements & Phased Implementation Plan

<!--
  PM TEMPLATE v1.0
  ─────────────────
  Usage: Copy this file, rename it to your project, and replace all {PLACEHOLDER} values.
  Sections marked [OPTIONAL] can be removed if not applicable.
  Delete this comment block when done.
-->

---

## Project Summary

| Field | Value |
|-------|-------|
| **Project Name** | {PROJECT_NAME} |
| **One-liner** | {Brief description of what this project does — 1-2 sentences} |
| **Project Type** | {SaaS / Internal Tool / API / Mobile App / CLI / Library / Platform} |
| **Target Users** | {Who uses this — e.g., developers, enterprise admins, end consumers} |
| **PRD Source** | {Link or filename of the original PRD, e.g., `prd-project.md`} |

### Key Constraints

<!-- List any hard constraints: budget, deadline, tech mandates, compliance requirements -->

- {Constraint 1 — e.g., Must use Gemini API}
- {Constraint 2 — e.g., SOC2 compliance required}
- {Constraint 3 — e.g., Must support 1000 concurrent users}

---

## Requirements

<!--
  Priority levels (MoSCoW):
  - Must   — Non-negotiable for launch
  - Should — Important but not blocking launch
  - Could  — Nice to have, do if time permits
  - Won't  — Explicitly out of scope for this version
-->

### R1. {Module Name}

| ID | Requirement | Priority |
|----|------------|----------|
| R1.1 | {Requirement description} | Must / Should / Could |
| R1.2 | {Requirement description} | Must / Should / Could |
| R1.3 | {Requirement description} | Must / Should / Could |

### R2. {Module Name}

| ID | Requirement | Priority |
|----|------------|----------|
| R2.1 | {Requirement description} | Must / Should / Could |
| R2.2 | {Requirement description} | Must / Should / Could |
| R2.3 | {Requirement description} | Must / Should / Could |

### R3. {Module Name}

| ID | Requirement | Priority |
|----|------------|----------|
| R3.1 | {Requirement description} | Must / Should / Could |
| R3.2 | {Requirement description} | Must / Should / Could |
| R3.3 | {Requirement description} | Must / Should / Could |

<!-- Add more R-sections as needed: R4, R5, R6... -->

### Out of Scope (Won't)

<!-- Explicitly list what this version will NOT do, to prevent scope creep -->

- {Feature/capability explicitly excluded}
- {Feature/capability explicitly excluded}

---

## Tech Stack

### Backend

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| API Framework | **{e.g., FastAPI / Express / Spring Boot}** | {Why this choice} |
| Database | **{e.g., PostgreSQL / MongoDB / DynamoDB}** | {Why this choice} |
| Cache / Broker | **{e.g., Redis / RabbitMQ / Kafka}** | {Why this choice} |
| Task Queue | **{e.g., Celery / BullMQ / SQS}** | {Why this choice} |
| {Other} | **{Technology}** | {Why this choice} |

### Frontend

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Framework | **{e.g., Next.js / React / Vue / SvelteKit}** | {Why this choice} |
| Styling | **{e.g., Tailwind / CSS Modules / Styled Components}** | {Why this choice} |
| State Management | **{e.g., Zustand / Redux / Pinia}** | {Why this choice} |
| {Other} | **{Technology}** | {Why this choice} |

### AI / ML [OPTIONAL]

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Primary Model | **{e.g., GPT-4 / Gemini / Claude}** | {Why this choice} |
| Embeddings | **{e.g., OpenAI / Cohere / local}** | {Why this choice} |
| Vector Store | **{e.g., Qdrant / Pinecone / pgvector}** | {Why this choice} |
| {Other} | **{Technology}** | {Why this choice} |

### Infrastructure & DevOps

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Containerization | **{e.g., Docker Compose / Kubernetes}** | {Why this choice} |
| CI/CD | **{e.g., GitHub Actions / GitLab CI / CircleCI}** | {Why this choice} |
| Observability | **{e.g., OpenTelemetry / Datadog / ELK}** | {Why this choice} |
| Testing | **{e.g., pytest / Jest / Playwright}** | {Why this choice} |
| {Other} | **{Technology}** | {Why this choice} |

### Key Architectural Decisions

<!--
  Document the "why" behind non-obvious choices.
  These are the decisions a new team member would ask about.
-->

1. **{Decision title}** — {Explanation of what was chosen and why, including alternatives considered}
2. **{Decision title}** — {Explanation}
3. **{Decision title}** — {Explanation}

---

## Phased Implementation Plan

---

### Phase 1 — {Phase Name} ({Timeline})

**Goal:** {One sentence describing what this phase delivers}

| # | Task | Depends On | Deliverable |
|---|------|-----------|-------------|
| 1.1 | **{Task title}** — {Brief description} ({Req ID}) | — | {Output file/module/endpoint} |
| 1.2 | **{Task title}** — {Brief description} ({Req ID}) | 1.1 | {Output} |
| 1.3 | **{Task title}** — {Brief description} ({Req ID}) | 1.1 | {Output} |
| 1.4 | **{Task title}** — {Brief description} ({Req ID}) | 1.2, 1.3 | {Output} |
| 1.5 | **Tests** — {What is tested} | 1.1-1.4 | {Coverage target} |

**Exit Criteria:**
- {Measurable condition that must be true to move to Phase 2}
- {Measurable condition}
- {Measurable condition}
- All unit tests pass

---

### Phase 2 — {Phase Name} ({Timeline})

**Goal:** {One sentence describing what this phase delivers}

| # | Task | Depends On | Deliverable |
|---|------|-----------|-------------|
| 2.1 | **{Task title}** — {Brief description} ({Req ID}) | Phase 1 | {Output} |
| 2.2 | **{Task title}** — {Brief description} ({Req ID}) | 2.1 | {Output} |
| 2.3 | **{Task title}** — {Brief description} ({Req ID}) | 2.1 | {Output} |
| 2.4 | **Tests** — {What is tested} | 2.1-2.3 | {Coverage target} |

**Exit Criteria:**
- {Measurable condition}
- {Measurable condition}
- All tests pass

---

### Phase 3 — {Phase Name} ({Timeline})

**Goal:** {One sentence describing what this phase delivers}

| # | Task | Depends On | Deliverable |
|---|------|-----------|-------------|
| 3.1 | **{Task title}** — {Brief description} ({Req ID}) | Phase 2 | {Output} |
| 3.2 | **{Task title}** — {Brief description} ({Req ID}) | 3.1 | {Output} |
| 3.3 | **Tests** — {What is tested} | 3.1-3.2 | {Coverage target} |

**Exit Criteria:**
- {Measurable condition}
- {Measurable condition}
- All tests pass

<!--
  Add more phases as needed: Phase 4, Phase 5, etc.
  Typical projects have 3-9 phases.

  Phase templates:
  - Foundation / Scaffolding  — project setup, data models, core API
  - Core Features             — primary functionality
  - Security / Auth           — RBAC, encryption, audit
  - Integrations              — third-party APIs, external systems
  - Frontend                  — UI, dashboards, UX
  - Hardening / Scale         — load testing, monitoring, production readiness
-->

---

## Timeline: Before vs After (AI-Assisted)

<!--
  Fill in estimated durations for manual coding vs AI-assisted (Claude Code).
  This helps stakeholders understand the acceleration.
  Remove this section if not using AI-assisted development.
-->

| Phase | Focus | Manual (Before) | AI-Assisted (After) |
|-------|-------|-----------------|---------------------|
| Phase 1 | {Phase name} | {X weeks} | **{Y days}** |
| Phase 2 | {Phase name} | {X weeks} | **{Y days}** |
| Phase 3 | {Phase name} | {X weeks} | **{Y days}** |
| | | | |
| **Total** | | **{X weeks}** | **{Y weeks}** |
| **Speedup** | | — | **{N}x faster** |

### Weekly Breakdown

```
Week 1  ░░░░░░░░░░  {Phase(s) covered}
Week 2  ░░░░░░░░░░  {Phase(s) covered}
Week 3  ░░░░░░░░░░  {Phase(s) covered}
Week 4  ░░░░░░░░░░  {Phase(s) covered}
...
```

### Caveats

- **+{N} weeks buffer** for: {unexpected issues, environment problems, etc.}
- Design review gates between phases recommended
- Security audit should involve human review
- Timeline assumes {team size and working arrangement}

---

## API Surface [OPTIONAL]

<!--
  List all API endpoints the project will expose.
  Group by domain/module.
-->

### {Domain 1}

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/{resource}` | {What it does} |
| GET | `/api/v1/{resource}` | {What it does} |
| GET | `/api/v1/{resource}/{id}` | {What it does} |
| PUT | `/api/v1/{resource}/{id}` | {What it does} |
| DELETE | `/api/v1/{resource}/{id}` | {What it does} |

### {Domain 2}

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/{resource}` | {What it does} |
| GET | `/api/v1/{resource}` | {What it does} |

---

## Data Models [OPTIONAL]

<!--
  Key entities and their relationships.
  Useful for complex projects with many models.
-->

| Entity | Key Fields | Relationships |
|--------|-----------|---------------|
| {Entity 1} | `id`, `name`, `status`, `created_at` | Has many {Entity 2} |
| {Entity 2} | `id`, `entity1_id`, `type`, `data` | Belongs to {Entity 1} |
| {Entity 3} | `id`, `entity2_id`, `value` | Belongs to {Entity 2} |

---

## Docker Services [OPTIONAL]

<!--
  List all services in Docker Compose.
  Useful for projects with multiple containers.
-->

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| {service-1} | {image:tag} | {host:container} | {What it does} |
| {service-2} | {image:tag} | {host:container} | {What it does} |
| {service-3} | {image:tag} | {host:container} | {What it does} |

---

## Risk Register [OPTIONAL]

<!--
  Known risks and mitigation strategies.
  Helps during planning and stakeholder communication.
-->

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| {Risk description} | High / Medium / Low | High / Medium / Low | {How to prevent or handle it} |
| {Risk description} | High / Medium / Low | High / Medium / Low | {How to prevent or handle it} |
| {Risk description} | High / Medium / Low | High / Medium / Low | {How to prevent or handle it} |

---

## Acceptance Criteria

<!--
  The project is complete when ALL of these are true.
  Map back to requirements (R-IDs) where possible.
-->

- [ ] {Criterion 1 — maps to R1.x}
- [ ] {Criterion 2 — maps to R2.x}
- [ ] {Criterion 3 — maps to R3.x}
- [ ] {Criterion — End-to-end tests pass with no failures}
- [ ] {Criterion — Load test meets target (e.g., p99 < Xs at N concurrent users)}
- [ ] {Criterion — Security audit passed}

---

## Changelog

<!--
  Track major changes to this document.
  Helps when multiple stakeholders review over time.
-->

| Date | Author | Change |
|------|--------|--------|
| {YYYY-MM-DD} | {Name} | Initial draft |
