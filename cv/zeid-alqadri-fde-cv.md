# Zeid Alqadri

**Forward Deployed Engineer / Solutions Engineer**
Kuala Lumpur, Malaysia
[salaam@zeidgeist.com](mailto:salaam@zeidgeist.com) • (+60) 12 533 0197 • [LinkedIn](https://www.linkedin.com/in/zeidalqadri/) • [zeidgeist.com](http://www.zeidgeist.com)

---

## Profile

Engineer who started in strategy: ~20 years across the energy industry
(PETRONAS, PEMANDU), now shipping production software end-to-end. I embed
with the user, map their real workflow, and build the tool that removes the
bottleneck — the forward-deployed loop. Currently building the Harga pricing
intelligence platform: a tender-discovery, bid-pricing, and supplier-intel
system for Malaysian procurement (ePerolehan, SmartGEP, Petronas).

Bilingual (English / Malay), dual background in economics-finance (MSc, 1st
Class, Bristol) and business information systems (UTP). Comfortable in the
boardroom and in the terminal.

---

## Core Strengths

- **Build-on-platform** — extend and tool existing systems rather than
  rebuilding: direct SQLite, Python, scrapers, scheduled automation, CLI tools.
- **Customer embedding** — from national transformation labs (Somalia NTP,
  adopted Feb 2025) to PETRONAS downstream divisions; translate stakeholder
  need into shipped capability.
- **Automation & data pipelines** — 34-task scheduler (~9k LOC), price
  enrichment, supplier matching, bid qualification, scraping of procurement
  portals.
- **Speed and density** — Bloomberg-terminal-style tooling: every screen is a
  keyboard-driven data surface, no filler.

---

## Selected Engineering Work

### Harga — Pricing Intelligence Platform (2025–present)
Hands-on builder of the full tender-to-bid lifecycle for Malaysian government
and Petronas procurement.

- **harga-cli** — a Bloomberg-terminal-style CLI for bid managers: dense
  ANSI-colored output, subcommands (`bids ls`, `px search`, `td search`,
  `audit`, `status`), direct SQLite, FTS5 search over price memory, no ORM.
  Single-file argparse entrypoint + reusable modules (BidManager CRUD, Scheduler).
- **Tender & price intelligence** — FTS5-indexed price history, supplier
  catalog with embeddings, FX-aware pricing, price memory and supplier scoring.
- **Scheduler pipeline** — 34 background tasks across 8 pipeline stages:
  discovery, scoping, pricing, confidence, packaging, submission, with
  stage-gate approval and escalation. ~9,000 LOC.
- **Submission adapters** — portal-specific adapters for forsah, smartgep,
  eperolehan, etimad; drop-in plugin architecture (`SCRAPER = <Class>`), no
  hardcoded branches.
- **Web layer** — Flask backend decomposed into 15 route modules; vanilla JS
  frontend; CSRF, role-based auth, audit log.

### Scraper Platform — orkes_sec (2025–present)
Standalone, parallel scraping platform for procurement portals.

- 14 portal plugins, 8,400+ tenders in sec.db, 548 bids / 48 submissions in
  harga_v8.db.
- Services: proxy, scheduler+runner+api, guardian, failsafe, tenders-api,
  products-api, analytics, documents, enrich — pm2-managed, isolated ports.
- RAG/embedding integration; submission workflow automation (auto-RFQ,
  auto-email, response packaging, technical proposal generation).

### Additional Builds
- **kuchai** — standalone Windows internet-connectivity troubleshooter
  (`kuchai.exe`, no install, no Python on target).
- **cbaas** — cohort-centric academy backend: auth, rate limiting, nightly CBL
  sync, dedup of token refresh, Ministry of Education briefing page.
- **cungila** — full-stack app hardened across 10 phases (DX, DRY, perf,
  observability, resilience).
- **beslut, klame, baca, putri** — decision/settlement, expense-claims,
  reading, and other full-stack products (FastAPI/Flask + frontend).

---

## Engineering Experience

**Systems & Languages:** Python (argparse, Flask, asyncio, pytest), SQL
(SQLite, FTS5, PostgreSQL), shell, some TypeScript / FastAPI.

**Infrastructure:** pm2 process management, Docker, Cloudflare Workers,
gunicorn, cron, rclone backups.

**Practices:** direct-SQLite performance-first tooling, parameterized queries,
test-first (pytest), structured postmortems, audit logs and idempotency,
self-healing infrastructure.

---

## Career History

### Energy Workstream Lead (Consultant) — PEMANDU Associates, Somalia
Oct 2024 – Dec 2024
- Led the energy workstream for Somalia's National Transformation Plan;
  strategy adopted by Parliament (Feb 2025).

### PETRONAS — Kuala Lumpur, Malaysia (2016–2024)
- **Head of Social Economy** (May 2022 – Jun 2024): conceived and implemented
  PETRONAS' social economy framework; led cross-functional impact teams.
- **Head of Downstream Digital Portfolio Optimisation** (Apr 2020 – Apr 2022):
  ran downstream digital transformation program; digital strategies for
  business processes and CX; managed project portfolio to budget.
- **Head of Downstream Digital Business Development** (Dec 2018 – Mar 2020):
  digital BD, partnerships, transformation deals tied to revenue.
- **Downstream Business Analyst (Petrochemicals)** (Feb 2016 – Nov 2018):
  strategic and comparative analysis of PCG plans; expenditure optimisation.

### PETRONAS Dagangan Berhad — Malaysia (2007–2016)
- Executive Dealers Development & Management (2015–2016): dealer network
  growth, franchisee performance, HSE/sales/CX compliance.
- Retail Territory Manager (2009–2014, Melaka): up to 23 petrol stations,
  revenue/market-share growth, HSE and crisis management.
- Executive Talent Sourcing & People Planning (2007–2009): acquisition
  strategy for experienced/graduate hires; manpower planning to Board approval.

### Earlier
- Barclays Premier League Radio Commentator (Malay), talkSPORT UK (2014–2015).

---

## Education

- **MSc Economics, Finance, and Management** — University of Bristol
  (2015). Minor: Econometrics and Statistics. **1st Class, full scholarship,
  top 5.**
- **B. Business Information System** — Universiti Teknologi PETRONAS (2006).
  Minor: Corporate Management. 3.5 GPA, full scholarship.

---

## Certifications

- **AgilePM Practitioner** — APMG International (2020, active). DSDM
  philosophy, roles, techniques, lifecycle configuration.
- **Strategic Planning & Execution** — PETRONAS Leadership Centre (2022).

---

## How This Maps to Forward Deployed Engineering

- **Deploys with the customer:** did it at national scale (Somalia NTP) and
  corporate scale (PETRONAS downstream); now does it for procurement teams
  with live, daily-used tooling.
- **Ships, not just advises:** the work above is code running in production —
  CLIs, schedulers, scrapers, web apps — not decks.
- **Speed over ceremony:** Bloomberg-terminal design philosophy; muscle-memory
  subcommands; direct SQLite; output density.
- **Deep domain** in the exact vertical (Malaysian gov + Petronas
  procurement) plus economics/finance grounding to speak the customer's
  numbers.
