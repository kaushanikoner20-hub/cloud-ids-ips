FROM python:3.11-slim

WORKDIR /app

# System deps kept minimal; add build-essential here only if a future
# dependency needs compilation.
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY app ./app

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]