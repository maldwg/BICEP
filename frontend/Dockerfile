FROM node:latest as build

RUN mkdir /opt/frontend
WORKDIR /opt/frontend
COPY ./ .
RUN npm install
RUN npm run build --prod


FROM nginx:latest

RUN mkdir /etc/nginx/logs

# Copy the build output to replace the default nginx contents.
COPY --from=build /opt/frontend/dist/frontend /usr/share/nginx/html
COPY ./default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80