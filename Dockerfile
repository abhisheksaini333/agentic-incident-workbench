FROM node:20.10.0-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.10.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY incident/ ./incident/
COPY scripts/ ./scripts/
COPY fixtures/ ./fixtures/
COPY models/manifest.json ./models/manifest.json
COPY --from=web /web/dist ./frontend/dist/
RUN useradd --uid 10001 --create-home incident && mkdir -p /app/data && chown -R incident:incident /app
USER incident
EXPOSE 8085
CMD ["python", "-m", "incident", "api", "--host", "0.0.0.0", "--port", "8085"]
