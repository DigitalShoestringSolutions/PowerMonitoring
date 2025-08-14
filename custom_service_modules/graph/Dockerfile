FROM node:19-alpine AS appbuild
COPY ./code/package.json /
RUN npm install
RUN npm -v
COPY ./code /
RUN npm run build

FROM nginx
COPY --from=appbuild /build /usr/share/nginx/html
COPY ./static_config/nginx/nginx.conf /etc/nginx/nginx.conf
COPY ./static_config/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY ./static_config/ui /usr/share/nginx/html/config/
