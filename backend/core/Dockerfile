FROM alpine:3.20.0

RUN apk add --update py-pip
RUN apk add python3 py-pip gcc py3-mysqlclient tshark python3-dev musl-dev linux-headers

RUN mkdir /opt/backend
COPY ./requirements.txt /opt/backend/requirements.txt
# remove that file to be able to use pip without venv
RUN rm /usr/lib/python3.12/EXTERNALLY-MANAGED 
RUN pip3 install -r /opt/backend/requirements.txt

WORKDIR /opt/backend