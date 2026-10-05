# Собирается из корня репозитория (см. docker-compose.yml), чтобы взять config/nginx.conf

# 1. Сборка фронтенда
FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# 2. Раздача собранного сайта через nginx + прокси запросов /api к бэкенду
FROM nginx:1.27-alpine
COPY config/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
