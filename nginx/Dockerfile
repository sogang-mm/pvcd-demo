FROM nginx:stable

WORKDIR /workspace
ADD . .

RUN mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.old
COPY ./nginx.conf /etc/nginx/nginx.conf
COPY ./app.conf /etc/nginx/conf.d/app.conf