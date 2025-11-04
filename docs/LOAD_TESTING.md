# Load Testing Guide

## Tools

### Option 1: Apache Bench (ab)
```bash
# Install
sudo apt-get install apache2-utils

# Run test
ab -n 10000 -c 100 http://localhost:8080/
```

### Option 2: wrk (Recommended)
```bash
# Install
sudo apt-get install wrk

# Run test
wrk -t4 -c100 -d30s http://localhost:8080/
```

### Option 3: Locust (Python-based)
```bash
# Install
pip install locust

# Create locustfile.py (see below)
locust -f locustfile.py --host=http://localhost:8080
```

## Load Test Results Template

### Test Configuration
- **Date**: [Date of test]
- **Tool**: [ab/wrk/locust]
- **Target**: http://localhost:8080
- **Duration**: [e.g., 30 seconds]
- **Concurrent Users**: [e.g., 100]
- **Total Requests**: [e.g., 10,000]

### Results

#### Throughput
- **Requests per second**: [RPS]
- **Average latency**: [ms]
- **P50 latency**: [ms]
- **P95 latency**: [ms]
- **P99 latency**: [ms]
- **Max latency**: [ms]

#### Errors
- **Total errors**: [count]
- **Error rate**: [%]
- **5xx errors**: [count]
- **4xx errors**: [count]
- **Timeouts**: [count]

#### Resources
- **CPU usage**: [%]
- **Memory usage**: [MB]
- **Network I/O**: [MB/s]

### Sample Results (Target)

```
Phase 1 (Basic Reverse Proxy):
- RPS: 5,000 req/s
- Avg latency: 2ms
- P95 latency: 5ms
- Error rate: < 0.1%

Phase 2 (With Health Checks):
- RPS: 4,500 req/s
- Avg latency: 3ms
- P95 latency: 8ms
- Error rate: < 0.1%

Phase 4 (With Metrics):
- RPS: 4,000 req/s
- Avg latency: 4ms
- P95 latency: 10ms
- Error rate: < 0.1%
```

## Load Test Script Example

```python
# load_test.py
import asyncio
import aiohttp
import time
from statistics import mean, median

async def make_request(session, url):
    start = time.time()
    try:
        async with session.get(url) as resp:
            await resp.text()
            latency = (time.time() - start) * 1000
            return {"status": resp.status, "latency": latency}
    except Exception as e:
        return {"status": "error", "latency": None, "error": str(e)}

async def run_load_test(url, num_requests, concurrency):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(num_requests):
            tasks.append(make_request(session, url))
            if len(tasks) >= concurrency:
                results = await asyncio.gather(*tasks)
                tasks = []
                yield results
        
        if tasks:
            results = await asyncio.gather(*tasks)
            yield results

# Run test
async def main():
    url = "http://localhost:8080/"
    latencies = []
    errors = 0
    
    async for batch in run_load_test(url, 10000, 100):
        for result in batch:
            if result["status"] == 200:
                latencies.append(result["latency"])
            else:
                errors += 1
    
    print(f"Average latency: {mean(latencies):.2f}ms")
    print(f"Median latency: {median(latencies):.2f}ms")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Interpreting Results

### Good Performance Indicators
- RPS > 5,000 req/s
- P95 latency < 10ms
- Error rate < 0.1%
- CPU usage < 80%
- Memory stable (no leaks)

### Bottlenecks to Watch
- **High latency**: Network issues, backend slow
- **High error rate**: Backend failures, timeout issues
- **CPU saturation**: Need optimization or more cores
- **Memory leaks**: Check for unclosed connections

