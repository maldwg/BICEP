FROM mariadb:latest

COPY ./bicep.sql /docker-entrypoint-initdb.d/bicep.sql
COPY ./my.cnf /etc/mysql/my.cnf
