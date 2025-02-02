FROM grafana/grafana:11.4.0

COPY ./defaults.ini /usr/share/grafana/conf/defaults.ini
ADD ./provisioning /usr/share/grafana/conf/provisioning/
COPY ./provisioning/dashboards/dashboards.json /var/lib/grafana/dashboards/dashboards.json