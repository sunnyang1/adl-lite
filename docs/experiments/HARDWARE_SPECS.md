# Hardware and Software Environment Specifications

All throughput and latency benchmarks reported in this paper were executed on the following environment unless otherwise noted.

## Hardware

| Component | Specification |
|-----------|---------------|
| CPU | Apple M3 Pro (12-core, 4.06 GHz performance cores, 4 efficiency cores) |
| RAM | 36 GB LPDDR5 |
| Disk | 1 TB NVMe SSD |
| OS | macOS 14.5 (23F79) |

## Software

| Component | Version |
|-----------|---------|
| Python | 3.12.12 (CPython, 64-bit) |
| pydantic | 2.7.4 |
| networkx | 3.3 |
| pytest | 8.3.4 |

## Experiment-Specific Resources

### E1 — Chain Integrity
- **Runtime**: < 1 s
- **Memory**: < 50 MB
- **Notes**: Single-threaded SHA-256 computation

### E6 — IBM AML Pipeline (HI-Small sample)
- **Dataset**: IBM AML HI-Small_Trans.csv (9,300 rows, 201 unique accounts)
- **Runtime**: 299 ms (median of 5 runs)
- **Memory peak**: 45 MB RSS
- **CPU peak**: ~15% (single-core bound during CSV parsing)
- **Throughput**: ~31,100 events/s (9,300 events ÷ 0.299 s)
- **Bottleneck**: CSV row parsing and Event object instantiation, not chain operations or SHA-256 hashing

### E10 — FDE Pipeline
- **Runtime**: 318 ms
- **Memory peak**: 42 MB RSS
- **Notes**: End-to-end import → ontology discovery → consensus registration → action validation

### E11 — Side-Effect Stress
- **Runtime**: 1,247 ms
- **Memory peak**: 55 MB RSS
- **Notes**: 1,000 enqueued effects, 50% simulated failure rate, retry with exponential backoff

## Reproducibility

To reproduce all experiments on your own hardware:

```bash
# Install dependencies
pip install -e ".[dev]"

# Run full experiment suite
python -m experiments.runner all

# Run individual experiments with verbose output
python -m experiments.runner E6 --verbose
python -m experiments.runner E10 --verbose
```

## Extrapolation to Production Scale

The linear complexity of `EventChain.append()` and `verify_integrity()` suggests that throughput will remain constant as dataset size grows, provided memory is sufficient to hold the chains. Extrapolation to the full 5-million-event IBM AML dataset is supported by this linear model but remains unverified empirically (future work, Section 6.5).
