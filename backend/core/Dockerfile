FROM alpine:3.20.0

RUN apk add --update py-pip
RUN apk add python3 py-pip gcc py3-mysqlclient tshark python3-dev musl-dev linux-headers openssl

RUN mkdir /opt/backend
COPY ./requirements.txt /opt/backend/requirements.txt
# remove that file to be able to use pip without venv
RUN rm /usr/lib/python3.12/EXTERNALLY-MANAGED 
RUN pip3 install -r /opt/backend/requirements.txt

RUN mkdir -p /opt/sample-data/dc22a2fd-b0a2-4bfa-9038-d0ba3e6fdf29/
COPY ./example-configs/sample-data.csv /opt/sample-data/dc22a2fd-b0a2-4bfa-9038-d0ba3e6fdf29/dataset.csv
COPY ./example-configs/sample-data.pcap /opt/sample-data/dc22a2fd-b0a2-4bfa-9038-d0ba3e6fdf29/dataset.pcap

WORKDIR /opt/backend