def translate_class_to_module(class_name):
    translation = {
        "SlurmAPIResource": "slurm_api_resource",
        "LocalResource": "local_resource",
        "LocalFileSystemStorage": "local_file_system_storage",
        "HubmapLocalFileSystemStorage": "hubmap_local_file_system_storage",
        "GlobusUserAuthentication": "globus_user_authentication",
        "LocalUserAuthentication": "local_user_authentication",
        "PSCAPIUserAuthentication": "psc_api_user_authentication",
        "JupyterLabJob": "jupyter_lab_job",
        "LocalTestJob": "local_test_job",
        "AppyterJob": "appyter_job",
        "YACJob": "yac_job",
    }

    try:
        return translation.get(class_name)
    except Exception as e:
        raise e


def generate_controller_object(class_name, module_type, params):
    try:
        o = getattr(
            __import__(
                f"user_workspaces_server.controllers.{module_type}.{translate_class_to_module(class_name)}",
                fromlist=[class_name],
            ),
            class_name,
        )(**params)
        return o
    except Exception as e:
        raise e
