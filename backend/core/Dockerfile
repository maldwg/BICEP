FROM alpine:3.20.0

RUN apk add --update py-pip
RUN apk add python3 py-pip gcc py3-mysqlclient tshark python3-dev musl-dev linux-headers openssl docker docker-compose

RUN mkdir /opt/app
COPY ./requirements.txt /opt/app/requirements.txt
# remove that file to be able to use pip without venv
RUN rm /usr/lib/python3.12/EXTERNALLY-MANAGED 
RUN pip3 install -r /opt/app/requirements.txt

RUN mkdir -p /opt/sample-data/dc22a2fd-b0a2-4bfa-9038-d0ba3e6fdf29/
COPY ./example-configs/sample-data.csv /opt/sample-data/dc22a2fd-b0a2-4bfa-9038-d0ba3e6fdf29/dataset.csv
COPY ./example-configs/sample-data.pcap /opt/sample-data/dc22a2fd-b0a2-4bfa-9038-d0ba3e6fdf29/dataset.pcap

RUN mkdir -p /opt/configuration_data/uuid1
RUN mkdir -p /opt/configuration_data/uuid2
RUN mkdir -p /opt/configuration_data/uuid3
RUN mkdir -p /opt/configuration_data/uuid4
RUN mkdir -p /opt/configuration_data/uuid5
RUN mkdir -p /opt/configuration_data/uuid6
RUN mkdir -p /opt/configuration_data/uuid7
RUN mkdir -p /opt/configuration_data/uuid8


RUN mkdir -p /opt/rulesets/uuid1
RUN mkdir -p /opt/rulesets/uuid2
RUN mkdir -p /opt/rulesets/uuid3
RUN mkdir -p /opt/rulesets/uuid4

COPY ./example-configs/snort.lua /opt/configuration_data/uuid1/snort.lua
COPY ./example-configs/suricata.yaml /opt/configuration_data/uuid2/suricata.yaml
COPY ./example-configs/slips.yaml /opt/configuration_data/uuid3/slips.yaml
COPY ./example-configs/wazuh-compose.yaml /opt/configuration_data/uuid4/wazuh-compose.yaml
COPY ./example-configs/hamstring-compose.yaml /opt/configuration_data/uuid5/hamstring-compose.yaml
COPY ./example-configs/minimal-compose.yaml /opt/configuration_data/uuid6/minimal-compose.yaml
COPY ./example-configs/hamstring_config.yaml /opt/configuration_data/uuid7/hamstring_config.yaml
COPY ./example-configs/hamstring_clickhouse.sql /opt/configuration_data/uuid8/hamstring_clickhouse.sql

COPY ./example-configs/snort-community.rules /opt/rulesets/uuid1/snort-community.rules
COPY ./example-configs/snort-all.rules /opt/rulesets/uuid2/snort-all.rules
COPY ./example-configs/suricata-all.rules /opt/rulesets/uuid3/suricata-all.rules
COPY ./example-configs/suricata-et-open.rules /opt/rulesets/uuid4/suricata-et-open.rules

WORKDIR /opt/app