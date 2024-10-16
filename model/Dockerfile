FROM python:3.10.9-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
WORKDIR /app
RUN pip install --no-cache-dir --no-deps torch==1.13.1+cpu --extra-index-url https://download.pytorch.org/whl/cpu
COPY model/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY model/ ./model/
COPY models/manifest.json ./models/manifest.json
RUN useradd --uid 10001 --create-home model
USER model
EXPOSE 8087
CMD ["python", "model/server.py", "--host", "0.0.0.0", "--directory", "/models/flan-t5-small"]
