FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --requirement requirements.txt

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin --no-create-home app \
    && mkdir -p /app/media /app/staticfiles /data /var/lib/celery \
    && chown -R app:app /app /data /var/lib/celery

COPY --chown=app:app . .
COPY --chown=app:app docker/entrypoint.sh /usr/local/bin/task-manager-entrypoint
RUN chmod +x /usr/local/bin/task-manager-entrypoint

USER app

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/task-manager-entrypoint"]
