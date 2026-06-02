# CortexBrain — Single Page Website Content & Structure Guide

> Use this document to build a single-page marketing/explainer website for CortexBrain.
> It covers: hero, problem, market landscape, differentiation, how it works, architecture, features, use cases, and CTA.

---

## Section 1: Hero

### Headline
**Your Organization's AI Brain That Actually Learns**

### Subheadline
CortexBrain is an auditable AI knowledge system that gets smarter every time someone corrects it — and you can trace every answer back to its source.

### Tagline
*Enterprise RAG is broken. We fixed it.*

### CTA Button
`Request Early Access` / `See How It Works`

### Hero Visual Suggestion
Animated diagram showing: User asks question → AI answers wrong → User corrects → Correction persists → Next user gets the right answer. Loop with a "memory" icon glowing brighter each cycle.

---

## Section 2: The Problem — Why Enterprise AI Keeps Failing

### Section Headline
**Your AI Assistant Has Amnesia**

### Three Pain Points (use cards or columns)

#### 1. The Statelessness Tax
Every conversation starts from zero. When your senior DevOps engineer corrects the AI — "the port is 3000, not 8080" — that correction vanishes the moment the session ends. The next engineer who asks the same question gets the same wrong answer.

**Real impact:** Teams re-correct their AI assistants 15-30 times per week on the same facts. That's hours of wasted expert time, every single week.

#### 2. The Context Cost Explosion
Traditional RAG systems stuff entire documents into LLM prompts. At enterprise scale — 50,000+ daily queries — this creates exploding costs and degrading accuracy. Research shows that as context windows grow larger, LLMs actually perform *worse* at finding the right information (the "Lost in the Middle" phenomenon).

**Real impact:** You're paying more and getting worse answers as your knowledge base grows. The exact opposite of what should happen.

#### 3. The Accountability Gap
When your AI gives a wrong answer that causes an outage, a bad deployment, or a compliance violation, there is no audit trail. Nobody can answer: "What data did the AI use? How confident was it? Who corrected it last?"

**Real impact:** In regulated industries — healthcare, finance, legal — this isn't just inconvenient. It's a liability that blocks AI adoption entirely.

### Pull Quote
> "We re-correct our AI assistant on the same wrong port number three times a week. It's like training a new employee who forgets everything overnight." — Senior SRE at a 200-person SaaS company

---

## Section 3: What's Available in the Market (And Why It Falls Short)

### Section Headline
**The AI Memory Landscape — Everyone Is Trying, Nobody Has Solved It**

### Market Overview (brief paragraph)
The AI memory and knowledge management space is growing fast. Multiple tools attempt to give LLMs persistent memory. But every existing solution has critical gaps that make them unsuitable for enterprise use.

### Competitor Comparison Table

| Capability | Traditional RAG | Mem0 | Zep / Graphiti | Letta (MemGPT) | Cognee OSS | **CortexBrain** |
|------------|----------------|------|---------------|-----------------|------------|-----------------|
| Persistent Memory | No | Yes | Yes | Yes | Yes | **Yes** |
| Knowledge Graph | No | Optional | Yes | No | Yes | **Yes** |
| Vector Search | Yes | Yes | Yes | Yes | Yes | **Yes** |
| Corrections Persist | No | No | No | No | No | **Yes** |
| Full Audit Trail | No | No | No | No | No | **Yes** |
| Confidence Scoring | No | No | No | No | No | **Yes** |
| Version History | No | No | No | No | No | **Yes** |
| Smart Context Selection | No | No | No | Partial | Partial | **Yes** |
| Self-Learning | No | No | No | No | No | **Yes** |
| Enterprise-Ready | Varies | Partial | No | No | No | **Yes** |

### Key Takeaway (bold callout box)
**Every existing tool treats memory as a feature. CortexBrain treats it as the product.** Competitors give LLMs a place to store things. CortexBrain gives organizations a brain that learns, self-corrects, and can prove where every answer came from.

---

## Section 4: How CortexBrain Beats Other RAGs

### Section Headline
**Not Another RAG. A Complete Knowledge System.**

### The Five Breakthroughs (use icon cards or accordion)

#### 1. Corrections Are Permanent, Not Temporary
**The problem with RAG:** When you correct a RAG-based AI, the correction lives only in that session's chat history. Next session? Same wrong answer.

**CortexBrain's approach:** Every correction triggers a four-step mutation pipeline:
1. **Locate** the wrong fact in the knowledge graph
2. **Version** the old value (archived, never deleted)
3. **Mutate** the node with the corrected value
4. **Meta-Update** records who corrected it, when, and why

The result: correct once, correct forever. Every user benefits immediately.

#### 2. O(1) Context Cost — Not O(n)
**The problem with RAG:** As your knowledge base grows, RAG stuffs more and more tokens into the LLM prompt. Costs scale linearly with document count. Accuracy drops.

**CortexBrain's approach:** Our Spreading Activation Engine uses a neuroscience-inspired algorithm to select only the most relevant subgraph of knowledge — typically under 2,000 tokens — regardless of whether your knowledge base has 1,000 or 1,000,000 nodes.

**Token savings: ~65% compared to standard RAG** — and accuracy improves because the LLM sees only high-signal context.

#### 3. Every Answer Has a Source — And a Confidence Score
**The problem with RAG:** You get an answer. You have no idea if it's reliable. You can't trace it back to a source. You certainly can't audit it.

**CortexBrain's approach:** Every response includes:
- **Confidence score** (high/medium/low/conflicted)
- **Source attribution** (which documents, which corrections, which users)
- **Full version history** (every change to every fact, forever)

When the AI isn't sure, it says so: *"I have moderate confidence in this — the information may need verification."*

#### 4. The System Gets Smarter Automatically
**The problem with RAG:** Your knowledge base is static. If the answer isn't in your documents, you get hallucination or silence.

**CortexBrain's approach:** When the knowledge base can't answer a question, CortexBrain:
1. Generates an answer from general LLM knowledge
2. Auto-ingests the Q&A pair as new knowledge (at lower confidence)
3. The weekly Consolidation Engine promotes validated auto-learned knowledge, archives stale facts, and merges duplicates

The brain literally grows smarter through use.

#### 5. Built for Audit, Not Bolted On
**The problem with RAG:** Audit trails are an afterthought — if they exist at all.

**CortexBrain's approach:** Auditability is architectural, not a feature flag:
- Every mutation (correction, ingestion, consolidation) creates an audit log entry
- Every node has a complete version history traversable via API
- Every answer links to its source nodes with confidence scores
- Export audit trails as CSV/JSON for SOC 2 or internal compliance review

---

## Section 5: How It Works — The Architecture

### Section Headline
**Four Memory Substrates, Working Together**

### Visual: The Memory Model Diagram
```
                    ┌─────────────────────────────┐
                    │        User Query            │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │     Activation Engine         │
                    │  (Spreading Activation BFS)   │
                    └──┬───────────┬────────────┬──┘
                       │           │            │
          ┌────────────▼──┐ ┌─────▼──────┐ ┌───▼────────────┐
          │  M_a (Active)  │ │ M_s (Graph) │ │  M_r (Vector)   │
          │   Redis 7+     │ │  Neo4j 5.x  │ │   LanceDB       │
          │ Session scores │ │ Knowledge   │ │  Embeddings     │
          │ with TTL       │ │ + versions  │ │  for fallback   │
          └────────────────┘ └─────────────┘ └─────────────────┘
                       │           │            │
                    ┌──▼───────────▼────────────▼──┐
                    │      M_meta (PostgreSQL)       │
                    │  Audit logs, confidence,       │
                    │  salience, access tracking      │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │      Metacognition Layer       │
                    │  Confidence gate + salience    │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │     LLM Generation            │
                    │  (Context + confidence prefix) │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │     Answer with Sources        │
                    │  + Confidence + Audit Trail    │
                    └───────────────────────────────┘
```

### The Four Memory Substrates (use tabs or cards)

#### M_a — Active Memory (Redis)
The "working memory." Holds activation scores for the current session. Nodes that are relevant to the current conversation get activated; irrelevant ones decay over time. This is what makes context selection intelligent instead of brute-force.

#### M_s — Semantic Memory (Neo4j)
The "long-term knowledge." A knowledge graph where every fact is a node and every relationship is an edge. When a correction happens, the old value is archived via a `PREVIOUS_VERSION` edge — never deleted. This is the audit trail.

#### M_r — Raw Memory (LanceDB)
The "pattern matcher." Vector embeddings of all ingested content. When the knowledge graph can't find a match, vector similarity search provides a fallback. Best of both worlds: structured graph + unstructured vector.

#### M_meta — Meta Memory (PostgreSQL)
The "self-awareness layer." Tracks confidence scores, salience (importance), access frequency, correction history, and audit logs for every node. This is what powers the metacognition — the system knowing what it knows and how well it knows it.

---

## Section 6: The Query Pipeline (Step by Step)

### Section Headline
**What Happens When You Ask a Question**

### Pipeline Steps (use a vertical timeline or numbered flow)

1. **You ask a question** in natural language via the API, web UI, Slack, or Claude Code

2. **Entity extraction** — The system identifies key concepts in your question ("auth service", "port", "deployment")

3. **Spreading activation** — Starting from matched entities, the system traverses the knowledge graph using a neuroscience-inspired BFS algorithm. Only nodes above the activation threshold (default: 30) are selected. This bounds context to ~2,000 tokens regardless of graph size.

4. **Metadata enrichment** — Each activated node is enriched with confidence, salience, and conflict status from PostgreSQL

5. **Confidence gating** — The system computes a weighted average confidence score:
   - **High (>=0.8):** Answer delivered normally
   - **Medium (0.5-0.8):** "I have moderate confidence in this..."
   - **Low (<0.5):** "I have low confidence..."
   - **Conflicted:** "I have conflicting data from different sources..."

6. **LLM generation** — The activated, confidence-tagged context is sent to the LLM with strict instructions to answer only from provided context

7. **Source attribution** — Every answer includes which nodes were used, their confidence scores, and who last modified them

8. **Continuous learning** — If the knowledge base couldn't answer, the system generates a general-knowledge answer and auto-ingests it for future queries (at lower confidence, with deduplication)

---

## Section 7: Key Features (Feature Grid)

### Section Headline
**Everything You Need for Enterprise AI Knowledge**

### Feature Cards (2x4 or 3x3 grid)

#### Knowledge Ingestion
Upload PDFs, Markdown, plain text, Slack exports, or connect Git repositories. Documents are processed through Cognee's ECL (Extract, Cognify, Load) pipeline into a structured knowledge graph.

#### Versioned Corrections
Correct the AI and the correction persists forever. Full version history for every fact. Conflicting corrections from different users are flagged, not silently overwritten.

#### Confidence Scoring
Every answer comes with a confidence level (high/medium/low/conflicted). The system tells you when it's unsure instead of confidently hallucinating.

#### Smart Context Selection
Spreading activation algorithm selects only the most relevant knowledge nodes. O(1) context cost regardless of knowledge base size. ~65% token savings vs. standard RAG.

#### Full Audit Trail
Complete history of every change to every fact: who changed it, when, why, and what the previous value was. Export-ready for SOC 2 and compliance audits.

#### Self-Learning System
When the knowledge base can't answer, the system learns from its own responses. Weekly consolidation promotes validated knowledge and archives stale facts.

#### Visual Answers
When you ask for diagrams, charts, or visualizations, CortexBrain generates both text and images in a single response using Gemini 2.5 Flash.

#### Admin Dashboard
Real-time monitoring: knowledge health, query volume, confidence trends, token usage, worker status, and mutation logs. Eight dedicated pages for complete system visibility.

---

## Section 8: Use Cases

### Section Headline
**Who Uses CortexBrain?**

### Use Case Cards

#### DevOps / SRE Teams
- Ingest runbooks, postmortems, and infrastructure docs
- Correct the AI during incidents — corrections stick for the next on-call
- Track what knowledge was used during incident response (audit trail)
- Reduce onboarding time for new engineers

#### Engineering Leadership
- Preserve institutional knowledge when senior engineers leave
- Measure ROI: token savings, query volume, correction frequency
- Identify knowledge gaps: which topics have low confidence?
- Justify AI tool spend with concrete metrics

#### Regulated Industries (Healthcare, Legal, Finance)
- Full audit trail for every AI-assisted decision
- Confidence scoring prevents over-reliance on uncertain answers
- Version history satisfies SOC 2 and compliance requirements
- Data residency control (self-hosted option)

#### Knowledge Management Teams
- Consolidate tribal knowledge from Slack, docs, and code repos
- Auto-detect and merge duplicate knowledge
- Track knowledge freshness and identify stale information
- Build a single source of truth that improves over time

---

## Section 9: Technical Specifications (Collapsible/Accordion)

### Section Headline
**Built on Proven Open Source, Enhanced for Enterprise**

### Tech Stack
| Layer | Technology |
|-------|-----------|
| Foundation | Cognee OSS (MIT licensed) |
| Language | Python 3.12 |
| API | FastAPI (async, typed, OpenAPI) |
| Knowledge Graph | Neo4j 5.x |
| Vector Search | LanceDB (via Cognee) |
| Active Memory | Redis 7+ |
| Audit Store | PostgreSQL 16 |
| LLM | Gemini 2.0 Flash (primary), Claude Sonnet 4.5, GPT-4o |
| Background Jobs | Celery + Redis |
| Frontend | Next.js 16, React 19, Tailwind v4 |
| MCP Integration | Claude Code compatible |

### Performance Targets
| Metric | Target |
|--------|--------|
| Query latency (p95) | <= 3 seconds |
| Correction application (p95) | <= 1 second |
| Context tokens per query | ~1,200 (vs. 3,500 for standard RAG) |
| Correction persistence | 100% |
| Audit trail completeness | 100% |
| Retrieval accuracy | >= 85% |

### REST API
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/query` | Natural language query |
| `POST /api/v1/correct` | Submit correction |
| `POST /api/v1/ingest` | Upload documents |
| `GET /api/v1/nodes/{id}/history` | Audit trail |
| `GET /api/v1/health` | System health |
| 14+ total endpoints | Full CRUD + admin |

---

## Section 10: The CortexBrain Difference (Summary Comparison)

### Section Headline
**Standard RAG vs. CortexBrain — Side by Side**

### Comparison Table (use alternating row colors)

| Capability | Standard RAG | CortexBrain |
|------------|-------------|-------------|
| Memory model | Stateless (per-session) | Four-substrate persistent memory |
| Context selection | Stuff everything into prompt | Spreading activation (bounded, intelligent) |
| Corrections | Lost after session ends | Permanent with version history |
| Confidence | None — answers always sound confident | Confidence-gated with 4 levels |
| Audit trail | None | Complete — who, what, when, why |
| Cost scaling | O(n) — linear with docs | O(1) — bounded regardless of size |
| Self-improvement | No | Continuous learning + weekly consolidation |
| Source attribution | None or basic | Every answer cites sources with confidence |
| Conflict detection | None | Flags conflicting corrections |
| Token usage | ~3,500/query | ~1,200/query (65% savings) |
| Accuracy | 60-70% | 85%+ |

---

## Section 11: Call to Action

### Section Headline
**Ready to Give Your Organization a Brain That Learns?**

### CTA Options
- **Primary:** `Request Early Access` → leads to email/form
- **Secondary:** `Read the Technical Docs` → links to API docs
- **Tertiary:** `Star Us on GitHub` → if open-source component available

### Closing Line
*CortexBrain: Because your AI should remember what you teach it.*

---

## Section 12: Footer

### Footer Content
- **Product:** Features | How It Works | Pricing | API Docs
- **Company:** About | Blog | Careers | Contact
- **Resources:** Documentation | GitHub | Status Page
- **Legal:** Privacy Policy | Terms of Service | SOC 2

### Footer Tagline
Built by Abhisek Bose | Powered by Cognee OSS

---

## Design & Implementation Notes

### Recommended Single Page Structure
1. **Hero** (full viewport, dark background, animated visual)
2. **Problem** (3-column cards on light background)
3. **Market** (comparison table with CortexBrain column highlighted)
4. **Differentiation** (5 breakthrough cards with icons)
5. **How It Works** (animated architecture diagram + pipeline flow)
6. **Features** (grid layout with icons)
7. **Use Cases** (tabbed cards)
8. **Tech Specs** (collapsible accordion)
9. **Comparison** (side-by-side table)
10. **CTA** (full viewport, strong call to action)
11. **Footer**

### Color Palette Suggestion
- **Primary:** Deep blue (#1a1a2e) — trust, enterprise
- **Accent:** Electric purple (#6c63ff) — innovation, AI
- **Success:** Green (#10b981) — for "CortexBrain" column highlights
- **Warning:** Amber (#f59e0b) — for competitor gaps
- **Background:** Near-white (#f8fafc) for content sections, dark (#0f172a) for hero/CTA

### Typography Suggestion
- **Headings:** Inter or Plus Jakarta Sans (modern, clean)
- **Body:** Inter or system-ui (readable at all sizes)
- **Code/Tech:** JetBrains Mono or Fira Code

### Key Animations
- Hero: Flowing knowledge graph with pulsing activation nodes
- Problem section: Counter showing "corrections lost per week" ticking up
- Pipeline: Step-by-step reveal as user scrolls
- Comparison table: Row-by-row entrance from left

### SEO Keywords
- Enterprise AI knowledge management
- Auditable AI assistant
- Self-correcting AI knowledge base
- RAG alternative with audit trail
- AI memory for enterprise
- Knowledge graph RAG
- Persistent AI corrections
- AI confidence scoring

### Mobile Considerations
- Comparison tables → swipeable cards on mobile
- Architecture diagram → simplified vertical flow
- Feature grid → stacked cards
- Sticky nav with smooth scroll
