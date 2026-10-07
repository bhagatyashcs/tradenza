# Changelog

All notable changes to the **Tradenza** platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-10-05

### Added
- **Complete Technical & Product Documentation**:
  - `docs/architecture.md`: Comprehensive Clean Architecture and service layer specification.
  - `docs/database.md`: Full relational schema tables, constraints, foreign keys, and ER diagrams.
  - `docs/api.md`: Detailed route catalog, methods, and request/response contracts.
  - `TRADENZA_PRD.md`: Full Product Requirements Document with personas and functional modules.
  - `TRADER_GENOME.md`: 9-dimensional mathematical formulation and archetype classifier specification.
  - `ai/AURA.md`: Explanatory AI coaching architecture, groundedness principles, and reflective prompt generation.
  - `ACADEMY.md`: Just-in-time behavioral curriculum mapping biases to lessons.
  - `docs/roadmap.md`: Strategic milestone tracking and feature pipeline.
- **Central Intelligence Pipeline**:
  - Unified `AnalyticsService.refresh_user()` orchestrating Behavior, Genome, Insight, and Aura engines on every trade mutation.
- **Digital Twin Behavioral Model**:
  - `DigitalTwinService` synthesizing identity, personality, risk habits, decision profiles, and evolutionary trends.

### Changed
- Dashboard updated to inject unified intelligence payloads and live digital twin persona.
- Standardized trade mutation callbacks to keep portfolio and analytics synchronized.

---

## [0.1.0] - Initial Foundation Release

### Added
- Core Flask application factory with SQLAlchemy and Flask-Migrate integration.
- User authentication subsystem with password hashing and session management.
- Trade journal with support for multi-asset trade logging, P&L calculations, and CSV export.
- Portfolio balance ledger tracking starting balances, deposits, withdrawals, and realized profits.
- Daily equity history snapshots and Chart.js integration for equity curves and returns.
- Initial deterministic `BehaviorEngine` rules (revenge trading, early exits, overtrading, high risk, holding time asymmetry).
- Initial `GenomeEngine` and `InsightEngine` implementations.
