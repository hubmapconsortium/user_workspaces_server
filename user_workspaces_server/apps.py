from django.apps import AppConfig
from user_workspaces_server.controllers.storagemethods import local_file_system_storage
from django.conf import settings


class UserWorkspacesServerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_workspaces_server'
    api_user_authentication = None
    main_storage = None

    def ready(self):
        from user_workspaces_server.controllers.userauthenticationmethods import globus_user_authentication, local_user_authentication
        api_user_authentication_details = settings.CONFIG['available_user_authentication'][
            settings.CONFIG['api_user_authentication']
        ]

        main_storage_method_details = settings.CONFIG['available_storage'][
            settings.CONFIG['main_storage']
        ]

        self.api_user_authentication = globus_user_authentication.GlobusUserAuthentication(
            api_user_authentication_details['connection_details']
        )

        self.main_storage = local_file_system_storage.LocalFileSystemStorage(
            local_user_authentication.LocalUserAuthentication(
                settings.CONFIG['available_user_authentication'][
                    main_storage_method_details['user_authentication_name']
                ]['connection_details']
            ),
            main_storage_method_details['root_dir']
        )
