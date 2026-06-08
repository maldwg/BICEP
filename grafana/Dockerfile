FROM grafana/grafana:13.0.2

COPY ./defaults.ini /usr/share/grafana/conf/defaults.ini
ADD ./provisioning /usr/share/grafana/conf/provisioning/
COPY ./provisioning/dashboards/dashboards.json /var/lib/grafana/dashboards/dashboards.json
RUN grafana cli plugins install vonage-status-panel
