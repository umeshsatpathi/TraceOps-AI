FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    RUNNING_IN_DOCKER=true

WORKDIR /app

# Install curl for container health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY api/ ./api/
COPY ingestion/ ./ingestion/
COPY scanners/ ./scanners/
COPY demoshop/ ./demoshop/
COPY graph_db.py .
COPY graph_tools.py .
COPY graph_intelligence.py .
COPY agent.py .
COPY agent_graph_tools_v2.py .
COPY seed_graph.py .
COPY dashboard.py .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
