FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
RUN /root/.local/bin/uv sync --frozen

# Copy application code
COPY src ./src

# Expose port
EXPOSE 8000

# Run the application
CMD ["/root/.local/bin/uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]