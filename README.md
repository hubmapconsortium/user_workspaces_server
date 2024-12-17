# User Workspaces Server
The User Workspaces Server is an HTTP/Websocket server which allows developers to create workspaces and launch interactive sessions on a variety of resources. API documentation is on [SmartAPI](https://smart-api.info/ui/bf965a56ce398f8b37de68c05b4ef125#).

## Django App Configuration
This application is written in Django and it includes an example_config.json file. Copy the file and rename it config.json and modify it with the appropriate information.

## Development

### Local development
Create a new Python (3.10>=) environment:

```
virtualenv -p 3.10 venv
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

## REST API Common Workflows

The most common workflows for this service are:
- User authorization
- Workspace creation
- TODO: Job launching/monitoring

Complete API documentation is on [SmartAPI](https://smart-api.info/ui/bf965a56ce398f8b37de68c05b4ef125#).

### User authorization

This workflow is highly dependent on the `api_user_authentication` that you have chosen in your config.json. In this section, we will describe the Globus **user token** based authentication.

#### POST request to <base_url>/tokens/

The body of this request should be structured as follows:
```
{
	“auth_token”: “groups.api.globus.org token”
}
```

This request will return the following
```
{
	“token”: “user token”
}
```

This token should be saved somewhere as it will be used on any subsequent requests, for this user.

Regardless of the chosen `api_user_authentiation`, you will want to include this token in the **header** of any other requests, so that the user workspaces server can correctly identify the user.

You will want to set a custom `UWS-Authorization` header, and include the token in the area marked as "xxx"

```
UWS-Authorization: Token xxxx
```

Curl example of a token, `abcd1234`
```
curl --header "UWS-Authorization: Token abcd1234" <base_url>/workspaces/
```

### Workspace creation

In this section, we will describe how to create a new workspace.

#### POST request to <base_url>/workspaces/

The body of this request should be structured as follows:
```
{
  "name": workspace_name,
  "description": workspace_description,
  "workspace_details": {
    "symlinks": [
      {
        “name”: “Symlink Name”,
        “path”: “full_path/to/directory”
      }
    ],
    "files": [
      {
        “name”: “File Name”,
        “content”: “file content”
      }
    ]
  }
}

```

This request will return the following
```
{
  "message": response_message,
  "success": success_boolean,
  "data": {
    "id": 0,
    "description": "string",
    "disk_space": 0,
    "datetime_created": "string",
    "workspace_details": {
      "request_workspace_details": {},
      "current_workspace_details": {}
    }
  }
}

```

### Updating API Documentation

The documentation for the REST API calls is hosted on [SmartAPI](https://smart-api.info/ui/bf965a56ce398f8b37de68c05b4ef125#).  Modifying the `user-workspaces-spec.yaml` file and committing the changes to GitHub should update the API shown on SmartAPI. SmartAPI allows users to register API documents. The documentation is associated with this GitHub account: api-developers@hubmapconsortium.org.
