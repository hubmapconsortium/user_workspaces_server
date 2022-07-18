from django.apps import AppConfig
from django.conf import settings


def translate_class_to_module(class_name):
    translation = {
        'SlurmAPIResource': 'slurm_api_resource',
        'LocalResource': 'local_resource',
        'LocalFileSystemStorage': 'local_file_system_storage',
        'GlobusUserAuthentication': 'globus_user_authentication',
        'LocalUserAuthentication': 'local_user_authentication',
        'PSCAPIUserAuthentication': 'psc_api_user_authentication'
    }

    try:
        return translation.get(class_name)
    except Exception as e:
        raise e


def generate_object(class_name, type, params):
    try:
        o = getattr(
            __import__(
                f'user_workspaces_server.controllers.{type}.{translate_class_to_module(class_name)}', fromlist=[class_name]
            ),
            class_name
        )(**params)
        return o
    except Exception as e:
        raise e



class UserWorkspacesServerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_workspaces_server'
    api_user_authentication = None
    main_storage = None
    available_resources = {}
    available_storage_methods = {}
    available_user_authentication_methods = {}
    available_job_types = {}

    def ready(self):
        config_user_authentication = settings.CONFIG['available_user_authentication']
        config_storage = settings.CONFIG['available_storage']
        config_resource = settings.CONFIG['available_resources']

        for user_authentication_name, user_authentication_dict in config_user_authentication.items():
            self.available_user_authentication_methods[user_authentication_name] = generate_object(
                user_authentication_dict["user_authentication_type"],
                "userauthenticationmethods",
                {
                    "config": user_authentication_dict
                }
            )

        for storage_name, storage_dict in config_storage.items():
            user_auth_dict = config_user_authentication[storage_dict['user_authentication']]

            self.available_storage_methods[storage_name] = generate_object(
                storage_dict["storage_type"],
                "storagemethods",
                {
                    "config": storage_dict,
                    "storage_user_authentication": generate_object(
                        user_auth_dict['user_authentication_type'],
                        'userauthenticationmethods',
                        {
                            "config": user_auth_dict
                        }
                    )
                }
            )

        for resource_name, resource_dict in config_resource.items():
            user_auth_dict = config_user_authentication[resource_dict['user_authentication']]
            storage_dict = config_storage[resource_dict['storage']]
            storage_user_auth_dict = config_user_authentication[storage_dict['user_authentication']]

            self.available_resources[resource_name] = generate_object(
                resource_dict["resource_type"],
                "resources",
                {
                    "config": resource_dict,
                    "resource_storage": generate_object(
                        storage_dict['storage_type'],
                        "storagemethods",
                        {
                            "config": storage_dict,
                            "storage_user_authentication": generate_object(
                                storage_user_auth_dict['user_authentication_type'],
                                "userauthenticationmethods",
                                {
                                    "config": storage_user_auth_dict
                                }
                            )
                        },
                    ),
                    "resource_user_authentication": generate_object(
                        user_auth_dict['user_authentication_type'],
                        'userauthenticationmethods',
                        {
                            "config": user_auth_dict
                        }
                    )
                }
            )

        self.api_user_authentication = self.available_user_authentication_methods[settings.CONFIG['api_user_authentication']]

        self.main_storage = self.available_storage_methods[settings.CONFIG['main_storage']]
