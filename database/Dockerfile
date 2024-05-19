FROM mariadb:latest

COPY ./bicep.sql /docker-entrypoint-initdb.d/bicep.sql
COPY ./test-config.yaml /tmp/test-config.yaml
COPY ./my.cnf /etc/mysql/my.cnf
# CMD [ "tail -f /dev/null" ]