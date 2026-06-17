# 前端在 Mac 本地原生编译后，此镜像仅做 Nginx 部署
FROM nginx:alpine

COPY dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
