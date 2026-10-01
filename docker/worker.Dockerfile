FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace/api:/workspace/worker

WORKDIR /workspace
COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/app ./api/app
COPY apps/worker/worker ./worker/worker

CMD ["python", "-m", "worker.main"]

