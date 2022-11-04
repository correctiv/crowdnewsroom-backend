FROM python:3.6-buster AS base

FROM base AS build-backend

RUN mkdir /install

WORKDIR /install

COPY requirements.txt /requirements.txt

RUN pip install --prefix=/install -r /requirements.txt
RUN pip install --prefix=/install uwsgi


FROM node:10-buster AS build-frontend

RUN mkdir /install

WORKDIR /install

COPY theme .

RUN yarn install \
    && yarn build \
    && rm -rf node_modules

FROM base AS runtime

ENV PORT=8000

COPY . /app

WORKDIR /app

RUN set -xe \
    && apt-get -q -y update \
    && apt-get -q -y install --no-install-recommends gettext \
    && apt-get clean \
    && apt-get autoclean \
    && apt-get -y autoremove \
    && rm -rf /var/cache/apt/* \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build-backend /install /usr/local
COPY --from=build-frontend /install /app/theme

RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

VOLUME /app/public/static
VOLUME /app/public/media

ENTRYPOINT ["/app/docker-entrypoint.sh"]

CMD ["uwsgi", "--http", "0.0.0.0:8000", "--module", "crowdnewsroom.wsgi", "--master", "--check-static", "/app/public"]