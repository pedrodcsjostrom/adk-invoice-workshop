# Built by Cloud Build, not by a local Docker daemon: `gcloud builds submit`
# needs nothing installed on an attendee's laptop beyond gcloud itself.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    # The local JSON Lines store, until issue #9 swaps in Firestore. It points
    # at /tmp because a Cloud Run container's disk is memory and is gone at the
    # next scale-to-zero: nothing here is meant to be durable.
    INVOICE_RECORDS_PATH=/tmp/invoice_records.jsonl

WORKDIR /app

# Dependencies first, so editing the agent does not reinstall the ADK.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY invoice_agent/ ./invoice_agent/
COPY data/ ./data/
COPY server.py ./

# Cloud Run overrides this with its own $PORT; the default keeps
# `docker run -p 8080:8080` working unchanged.
EXPOSE 8080
CMD ["python", "server.py"]
