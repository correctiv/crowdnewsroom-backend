# Crowdnewsroom [![Build Status](https://travis-ci.org/correctiv/crowdnewsroom-backend.svg?branch=master)](https://travis-ci.org/correctiv/crowdnewsroom-backend)

This is the backend for the crowdnewsroom.


## Goal

The crowdnewsroom allows journalists to create investigations in which many citizens can contribute by filling out forms to collect data.

## Setup

### Python setup
```bash
virtualenv -p python3.6 venv
source venv/bin/activate
pip install -r requirements.txt
```

### Install frontend dependencies
In the `./theme` folder, you need to install frontend tooling and dependencies using [Yarn](https://yarnpkg.com/).
```bash
cd ./theme && yarn install
```

### Database
You need to set up a postgres database. Django supports many types of databases but we want to use Postgres' JSONB feature
to store user replies as JSON blobs for flexibility.
You can set up a database natively or with docker. To set it up with docker run:
```bash
docker run --name crowdnewsroom-docker -d -p 32770:5432 postgres
docker exec -it crowdnewsroom-docker createdb -U postgres crowdnewsroom
```

## Settings

Move `crowdnewsroom/local_settings.py.example` to `crowdnewsroom/local_settings.py` and update the settings according to your local environment, in case you are not using docker.

You also need to set a couple of environment variables. Namely:
```
DJANGO_SECRET_KEY='<your generated secret key>'
DJANGO_ALLOWED_HOSTS='localhost' # can be comma-separated
```

### Create translation files
```bash
sh ./maketranslations.sh
```

### Compile translation files
```bash
python manage.py compilemessages
```

### Run migrations
```bash
python manage.py migrate
```

### Create a superuser
```bash
python manage.py createsuperuser
```

### Get example data
To load some example data that contains two investigations and some responses run:
```bash
python manage.py seed_data
```

## Bundle frontend assets for development
During development, you need to have Webpack running in a separate terminal. Webpack can be started using Yarn in the theme folder:
```bash
cd ./theme && yarn run dev
```

## Run the Django server
```bash
python manage.py runserver
```

## Test
You can run the test suite with
```bash
python manage.py test
```
This will also run some tests in headless Chrome. You need to have
Chrome and chromedriver installed for those tests to work. If you
do not currently have those you can skip those test by running:
```bash
python manage.py test --exclude-tag browsertest
```

## Check in the frontend build for deployment

For CORRECTIV deployment, there is currently no frontend build task on the server. So when working on the `/theme/` js & css, build it with `yarn build` and check in the bundles.

## Create and Run Docker image

### Build Docker image

`docker build --no-cache -t crowdnewsroom .` to build the image.

The image contains the following tasks:

- install dependencies for python
- install dependencies for frontend
- run frontend build
- install python web server uwsgi

The default command when starting a container from the build image also generates the languages and messages.
The static files are moved to the public folder, and the public folder is exposed as a volume.
Port 8000 is the exposed Port of the web application.

Start the container with `docker run --rm -it -p 8000:8000 -e DJANGO_ALLOWED_HOSTS="*" -e DJANGO_SECRET_KEY=some_secret` for example.

To have a full running crowdnewsroom, the following steps are required:

- build the image as explained above
- start a local postgres server (if you have not already one setup) with `docker run --name crowdnewsroom-db -e POSTGRES_PASSWORD=crowdnewsroom -e POSTGRES_USER=crowdnewsroom -e POSTGRES_DB=crowdnewsroom postgres`
- migrate database with `docker run --rm -it -e DJANGO_ALLOWED_HOSTS="*" -e DJANGO_SECRET_KEY=some_secret --link crowdnewsroom-db -e DATABASE_URL=postgres://crowdnewsroom:crowdnewsroom@crowdnewsroom-db:5432/crowdnewsroom crowdnewsroom python manage.py migrate`
- seed database with `docker run --rm -it -e DJANGO_ALLOWED_HOSTS="*" -e DJANGO_SECRET_KEY=some_secret --link crowdnewsroom-db -e DATABASE_URL=postgres://crowdnewsroom:crowdnewsroom@crowdnewsroom-db:5432/crowdnewsroom crowdnewsroom python manage.py seed_data`
- create superuser with `docker run --rm -it -e DJANGO_ALLOWED_HOSTS="*" -e DJANGO_SECRET_KEY=some_secret --link crowdnewsroom-db -e DATABASE_URL=postgres://crowdnewsroom:crowdnewsroom@crowdnewsroom-db:5432/crowdnewsroom crowdnewsroom python manage.py createsuperuser`
- run web application with ` docker run --rm -it -p 8000:8000 -e DJANGO_ALLOWED_HOSTS="*" -e DJANGO_SECRET_KEY=some_secret --link crowdnewsroom-db -e DATABASE_URL=postgres://crowdnewsroom:crowdnewsroom@crowdnewsroom-db:5432/crowdnewsroom crowdnewsroom`
- open http://0.0.0.0:8000 in your browser

## About
This project uses [BrowserStack](https://www.browserstack.com/) for cross-browser testing and [Crowdin](https://crowdin.com) for translations. Cheers to these tools to support non-profit and Open Source initiatives.


## Permissions

|                                            |  Owner |  Admin | Editor | Viewer|
|--------------------------------------------|:------:|:------:|:------:|:-----:|
| Create new investigation                   | x      |  x     |   x    |  x    |
| Delete investigation                       | x      |        |        |       |
| Add owners  to investigation               | x      |        |        |       |
| Change user roles                          | x      |  x     |        |       |
| Customise investigation                    | x      |  x     |        |       |
| Add or remove new users in an investigation| x      |  x     |        |       |
| Choose, edit, or create an Interviewer     | x      |  x     |        |       |
| Edit a response                            | x      |  x     |        |       |
| Change bucket of response                  | x      |  x     | x      |       |
| Manage assignees/tags for response         | x      |  x     | x      |       |
| Download CSV file                          | x      |  x     | x      |       |
| Make comments on responses                 | x      |  x     | x      | x     |
| Leave an investigation                     | x      |  x     | x      | x     |
