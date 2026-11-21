# Site de documentação do ContextLab (contextlab.lspr.dev).
# Construa a partir da raiz do repositório: docker build -f site/Dockerfile .

FROM python:3.12-slim AS build
WORKDIR /src
COPY src/ src/
# O gerador usa só a biblioteca padrão; nenhuma dependência é instalada.
RUN PYTHONPATH=src python -m contextlab.viewer.site /site

FROM nginx:1.27-alpine
COPY site/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /site /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
