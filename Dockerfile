# Built from ghcr.io/hasnaintypes/hermes-agent-railway:latest, a copy of
# nousresearch/hermes-agent:latest with the inherited `VOLUME ["/opt/data"]`
# stripped — Railway's runtime silently drops the container CMD when that
# instruction is present (see github.com/NousResearch/hermes-agent/issues/91560).
FROM ghcr.io/hasnaintypes/hermes-agent-railway:latest

# psycopg2 for custom skills that talk to Neon directly (e.g.
# linkedin-approval-loop's drafts-table state machine). Baked into the
# image's own venv at build time -- /opt/hermes is read-only at runtime,
# so a live pip install wouldn't survive a redeploy anyway.
USER root
RUN /opt/hermes/.venv/bin/python3 -m ensurepip --upgrade \
    && /opt/hermes/.venv/bin/python3 -m pip install --no-cache-dir psycopg2-binary

CMD ["gateway", "run"]
