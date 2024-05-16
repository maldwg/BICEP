FROM node:latest as build

RUN mkdir /opt/frontend
WORKDIR /opt/frontend
COPY ./ /opt/frontend/
RUN npm install
RUN npm run build 


FROM nginx:latest

# Copy the build output to replace the default nginx contents.
COPY --from=build /opt/frontend/dist/frontend/browser /usr/share/nginx/html

# Expose port 80
EXPOSE 80