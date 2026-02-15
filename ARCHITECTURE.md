# OpenClaw Architecture

This document is a quick reference for how OpenClaw components connect and how one candle moves through the system.

## 1) Service Architecture

```mermaid
flowchart LR
  U[User Browser] --> F[Frontend Next.js :3000]
  F -->|HTTP GET /api/risk-state| B[Backend FastAPI :8000]
  F -->|WebSocket /ws/ai-feed| B

  W[Worker Python] -->|POST /internal/ai-event| B
  W -->|Read/Write| D[(PostgreSQL)]
  B -->|Read| D

  W -->|Market data| X[Binance Testnet]
  W -->|LLM decision| O[Ollama :11434]
  W -->|Alerts| T[Telegram Bot API]
```

### Notes
1. Frontend does not call worker directly.
2. Worker publishes events to backend, and backend broadcasts to frontend via WebSocket.
3. Postgres is the state source for trades and daily risk values.

## 2) Candle-to-Decision Pipeline

```mermaid
flowchart TD
  A[Closed Candle from DataFeed] --> B[RiskGuard: killswitch check]
  B -->|Blocked| C[Create KILLSWITCH event]
  B -->|Allowed| D[QuantitativeEngine: setup detection]
  D -->|No valid setup| E[Create WAIT event]
  D -->|Valid setup| F[DecisionEngine via Ollama]
  F --> G[PositionManager: RR/sizing validation]
  G -->|Rejected/Failed| H[Create REJECTED or FAILED event]
  G -->|Executed| I[Place testnet order + save trade]
  I --> J[Create EXECUTED event]

  C --> K[Backend /internal/ai-event]
  E --> K
  H --> K
  J --> K
  K --> L[Broadcast to frontend /ws/ai-feed]

  C --> M[Telegram Alert]
  H --> M
  J --> M
```

## 3) Runtime Components (Docker Compose)

```mermaid
flowchart TB
  subgraph Compose
    FE[frontend]
    BE[backend]
    WK[worker]
    DB[database]
    OL[ollama-brain]
  end

  FE --> BE
  BE --> DB
  WK --> DB
  WK --> OL
  WK --> BE
```

### Notes
1. `frontend` depends on `backend`.
2. `worker` depends on `backend`, `database`, and `ollama-brain`.
3. Health checks gate startup order.
