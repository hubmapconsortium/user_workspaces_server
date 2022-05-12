from django.apps import AppConfig
from django.conf import settings


class UserWorkspacesServerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_workspaces_server'
    api_user_authentication = None
    main_storage = None
    available_resources = None
    available_storage = None
    available_user_authentication = None
    available_job_types = None

    def ready(self):
        from user_workspaces_server.controllers.storagemethods import local_file_system_storage
        from user_workspaces_server.controllers.userauthenticationmethods import globus_user_authentication, local_user_authentication, psc_api_user_authentication
        from user_workspaces_server.controllers.resources import local_resource
        api_user_authentication_details = settings.CONFIG['available_user_authentication'][
            settings.CONFIG['api_user_authentication']
        ]

        main_storage_method_details = settings.CONFIG['available_storage'][
            settings.CONFIG['main_storage']
        ]

        # TODO: Assign this dynamically.
        self.api_user_authentication = psc_api_user_authentication.PSCAPIUserAuthentication(
            api_user_authentication_details['connection_details']
        )

        self.main_storage = local_file_system_storage.LocalFileSystemStorage(
            psc_api_user_authentication.PSCAPIUserAuthentication(
                settings.CONFIG['available_user_authentication'][
                    main_storage_method_details['user_authentication']
                ]['connection_details']
            ),
            main_storage_method_details['root_dir']
        )

        local_resource_storage_method = settings.CONFIG['available_storage'][settings.CONFIG['available_resources']['local_resource']['storage']]
        local_resource_user_auth_method = settings.CONFIG['available_user_authentication'][settings.CONFIG['available_resources']['local_resource']['user_authentication']]

        self.available_resources = {
            'local_resource': local_resource.LocalResource(
                local_file_system_storage.LocalFileSystemStorage(
                    local_user_authentication.LocalUserAuthentication(
                        settings.CONFIG['available_user_authentication'][
                            local_resource_storage_method['user_authentication']
                        ]['connection_details']
                    ),
                    local_resource_storage_method['root_dir']
                ),
                local_user_authentication.LocalUserAuthentication(
                    local_resource_user_auth_method['connection_details']
                )
            )
        }

        # for resource_index, resource_options in settings.CONFIG['available_resources'].items():
        #     print(resource_index)
