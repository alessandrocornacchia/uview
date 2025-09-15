FROM prom/prometheus

# Copy the prometheus configuration file (doing so directly in docker compose gives some issues with volume mounting)
COPY prometheus.yml /etc/prometheus/prometheus.yml

# Run prometheus server
CMD [ \
    "--config.file=/etc/prometheus/prometheus.yml", \
    "--storage.tsdb.path=/prometheus", \
    "--web.console.libraries=/etc/prometheus/console_libraries", \
    "--web.console.templates=/etc/prometheus/consoles", \
    "--storage.tsdb.retention.time=14d", \
    "--storage.tsdb.retention.size=100GB" \
]