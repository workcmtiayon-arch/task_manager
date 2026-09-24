FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY docker/entrypoint.sh /usr/local/bin/task-manager-entrypoint
RUN chmod +x /usr/local/bin/task-manager-entrypoint

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/task-manager-entrypoint"]
