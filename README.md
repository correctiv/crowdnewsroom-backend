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

### Marry Django with Reactjs
* to the django template add: 
```
{% render_bundle "interviewer" %}
```
* in the React component:
render the element to the `<div>` with the corresponding id in the template
* in the webpack.config.js file in theme/ add the corresponding js file as an entry:
```
entry: {
    main: "./src/scripts/index",
    style: "./src/styles/main.sass",
    formResponseDetails: "./src/scripts/form-response-details",
    formResponseList: "./src/scripts/form-response-list",
      invitationList: "./src/scripts/invitation-list",
      investigationManagement: "./src/scripts/investigation-management",
    interviewer: "./src/scripts/interviewer",
},
```
* restart yarn


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
