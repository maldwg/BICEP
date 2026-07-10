FROM mariadb:11.2.3

COPY ./bicep.sql /docker-entrypoint-initdb.d/bicep.sql
COPY ./migrations /opt/bicep-migrations
COPY ./my.cnf /etc/mysql/my.cnf
