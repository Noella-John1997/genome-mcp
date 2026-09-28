FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY genome_mcp ./genome_mcp
RUN pip install --no-cache-dir . && useradd -m app
USER app
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "genome-mcp web --host 0.0.0.0 --port ${PORT}"]
