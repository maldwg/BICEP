FROM node:latest as build
ARG PRODUCTION

ENV PRODUCTION=${PRODUCTION}
RUN mkdir /opt/frontend
WORKDIR /opt/frontend
COPY ./ .
RUN npm install
RUN  npm install -g @angular/cli@
RUN if [ "$PRODUCTION" = "True" ]; then ng build --configuration=production; else ng build --configuration=development; fi


FROM nginx:latest

RUN mkdir /etc/nginx/logs

# Copy the build output to replace the default nginx contents.
COPY --from=build /opt/frontend/dist/frontend /usr/share/nginx/html
COPY ./default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80