# User Workspaces Server

The User Workspaces Server is an HTTP/Websocket server which allows developers to create workspaces and launch interactive sessions on a variety of resources.

## Django App Configuration
This application is written in Django and it includes an example_config.json file in the instance directory. Copy the file and rename it config.json and modify with the appropriate information.

## Local development
This assumes you are developing the code with the Django development server

### Install dependencies
Create a new Python 3(.8>=) environment:

```
virtualenv -p 3.8 venv
source venv/bin/activate
```

Upgrade pip and install dependencies
```
pip install --upgrade pip
pip install -r requirements.txt
```

Perform django migration
```
python manage.py migrate
```

You will want to run the Django server/qcluster as root user, since it will be in charge of creating new users, running jobs as different users, etc.
```
sudo python manage.py qcluster &
sudo python manage.py runserver
```

## Docker development

In the case that you wish to launch a docker compose cluster to do your development/testing, there is a docker-compose.yml file that can be used.

You will want to be sure to modify this file such that it uses your machine's information/paths.

Build/start the docker compose cluster
```
docker compose build
docker compose up -d
```

### Updating API Documentation

The documentation for the REST API calls is hosted on SmartAPI.  Modifying the `user-workspaces-spec.yaml` file and committing the changes to GitHub should update the API shown on SmartAPI. SmartAPI allows users to register API documents. The documentation is associated with this GitHub account: api-developers@hubmapconsortium.org.