# HTTP Load Balancer - Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT REQUESTS                          │
│                    (HTTP/HTTPS on Port 8080)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HTTP LOAD BALANCER                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  aiohttp.web.Application (Port 8080)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                        │
│  ┌───────────────────────┼─────────────────────────────────┐   │
│  │  Balancer Handler      │                                 │   │
│  │  - Request forwarding  │                                 │   │
│  │  - Response aggregation│                                 │   │
│  └───────────────────────┼─────────────────────────────────┘   │
│                          │                                        │
│  ┌───────────────────────┼─────────────────────────────────┐   │
│  │  ServerPool            │                                 │   │
│  │  - Round-robin selection│                                 │   │
│  │  - Server management   │                                 │   │
│  └───────────────────────┼─────────────────────────────────┘   │
│                          │                                        │
│  ┌───────────────────────┼─────────────────────────────────┐   │
│  │  HealthChecker         │                                 │   │
│  │  - Periodic health     │                                 │   │
│  │  - Status tracking     │                                 │   │
│  └───────────────────────┼─────────────────────────────────┘   │
│                          │                                        │
│  ┌───────────────────────┼─────────────────────────────────┐   │
│  │  MetricsCollector      │                                 │   │
│  │  - Request counting    │                                 │   │
│  │  - Latency tracking    │                                 │   │
│  └───────────────────────┼─────────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  BACKEND 1   │  │  BACKEND 2   │  │  BACKEND 3   │
│  :9001       │  │  :9002       │  │  :9003       │
│              │  │              │  │              │
│  ┌────────┐ │  │  ┌────────┐ │  │  ┌────────┐ │
│  │ /health│ │  │  │ /health│ │  │  │ /health│ │
│  └────────┘ │  │  └────────┘ │  │  └────────┘ │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Component Breakdown

### 1. Load Balancer (Main Component)
- **Technology**: Python 3.12+ with asyncio
- **Framework**: aiohttp
- **Port**: 8080
- **Responsibilities**:
  - Accept client HTTP requests
  - Route requests to backend servers
  - Aggregate responses
  - Handle errors and timeouts

### 2. Server Pool
- **Algorithm**: Round-robin (Phase 1)
- **Future**: Weighted round-robin, least connections
- **Data Structure**: deque for efficient rotation

### 3. Health Checker
- **Method**: Periodic HTTP GET requests to `/health` endpoint
- **Interval**: Configurable (default: 10 seconds)
- **Status**: Healthy/Unhealthy based on response time and status code

### 4. Metrics Collector
- **Metrics**: Request count, latency, error rate, active connections
- **Storage**: In-memory (Phase 4: Prometheus-compatible)
- **Endpoint**: `/metrics` for monitoring

## Data Flow

1. **Client Request** → Load Balancer receives HTTP request
2. **Server Selection** → ServerPool selects next healthy server (round-robin)
3. **Request Forwarding** → Balancer forwards request to selected backend
4. **Response Handling** → Backend response is returned to client
5. **Metrics Update** → MetricsCollector records request/response data

## Failure Handling

- **Backend Down**: HealthChecker marks server as unhealthy → excluded from pool
- **Timeout**: Request times out → returns 504 Gateway Timeout
- **Connection Error**: Retries with next server (if configured)
- **All Backends Down**: Returns 503 Service Unavailable

## Scalability Considerations

- **Horizontal**: Multiple load balancer instances behind DNS
- **Vertical**: Single instance can handle thousands of concurrent connections (async)
- **Bottlenecks**: 
  - Network I/O (mitigated by async)
  - CPU (minimal for basic routing)

