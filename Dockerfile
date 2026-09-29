# Built from ghcr.io/hasnaintypes/hermes-agent-railway:latest, a copy of
# nousresearch/hermes-agent:latest with the inherited `VOLUME ["/opt/data"]`
# stripped — Railway's runtime silently drops the container CMD when that
# instruction is present (see github.com/NousResearch/hermes-agent/issues/91560).
FROM ghcr.io/hasnaintypes/hermes-agent-railway:latest
CMD ["gateway", "run"]
