FROM node:24.20.0-alpine3.23 AS build
ARG PRODUCTION

ENV PRODUCTION=${PRODUCTION}
RUN mkdir /opt/frontend
WORKDIR /opt/frontend
COPY ./ .
RUN npm ci
RUN npm install -g @angular/cli
RUN if [ "$(printf '%s' "$PRODUCTION" | tr '[:upper:]' '[:lower:]')" = "true" ]; then ng build --configuration=production; else ng build --configuration=development; fi


FROM nginx:1.30.4-alpine3.24

RUN mkdir /etc/nginx/logs

# Copy the build output to replace the default nginx contents.
COPY --from=build /opt/frontend/dist/frontend /usr/share/nginx/html
COPY ./default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80