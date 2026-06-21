# ADL Lite Reproducibility Environment
# 
# Build:  docker build -t adl-lite-repro .
# Run:    docker run --rm -v $(pwd)/docs/experiments:/app/docs/experiments adl-lite-repro
#
# This Dockerfile reproduces all experiments reported in the paper.

FROM python:3.10-slim

LABEL maintainer="ADL Lite Authors"
LABEL description="Reproducibility environment for ADL Lite paper experiments"

# Install system dependencies (Git for git-native baselines, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency specification first (for layer caching)
COPY pyproject.toml ./
COPY README.md ./

# Install Python dependencies
# We install in editable mode so experiments can import adl_lite
RUN pip install --no-cache-dir -e ".[dev,experiments]"

# Copy source code
COPY adl_lite/ ./adl_lite/
COPY experiments/ ./experiments/
COPY tests/ ./tests/
COPY data/ ./data/
COPY examples/ ./examples/

# Install the package itself (editable mode already set above)
RUN pip install --no-cache-dir -e ".[dev,experiments]"

# Create output directory for experiment artifacts
RUN mkdir -p /app/docs/experiments

# Health check: verify imports work
RUN python -c "from adl_lite import Event, EventChain, EventType; print('ADL Lite imports OK')"
RUN python -c "from experiments.proof_trace_checker import E24ProofTraceChecker; print('E24 import OK')"

# Default entry point: run all experiments
ENTRYPOINT ["python", "-m", "experiments.runner"]
CMD ["all"]
