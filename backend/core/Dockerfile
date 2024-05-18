FROM alpine:latest

RUN apk add --update py-pip
RUN apk add python3 py-pip gcc py3-mysqlclient

RUN mkdir /opt/backend
COPY ./requirements.txt /opt/backend/requirements.txt
# remove that file to be able to use pip without venv
RUN rm /usr/lib/python3.11/EXTERNALLY-MANAGED 
RUN pip3 install -r /opt/backend/requirements.txt

WORKDIR /opt/backend