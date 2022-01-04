from user_workspaces_server.controllers.userauthenticationmethods.abstract_user_authentication import \
    AbstractUserAuthentication
import pwd
import subprocess


class LocalUserAuthentication(AbstractUserAuthentication):
    def __init__(self, config):
        self.create_external_users = config.get('create_external_users', False)
        self.operating_system = config.get('operating_system', '').lower()

    def has_permission(self, internal_user):
        external_user_mapping = self.get_external_user_mapping({
            "user_id": internal_user,
            "user_authentication_name": type(self).__name__
        })

        if not external_user_mapping:
            # If the mapping does not exist, we have to try to "find" an external user
            # based on the info we have from the internal user
            external_user = self.get_external_user({'username': internal_user.username})

            if not external_user:
                # No user found, return false
                if self.create_external_users:
                    external_user = self.create_external_user({'name': internal_user.username})
                    if not external_user:
                        return False
                else:
                    return False

            # User found, create mapping
            external_user_mapping = self.create_external_user_mapping({
                'user_id': internal_user,
                'user_authentication_name': type(self).__name__,
                'external_user_id': external_user['external_user_uid'],
                'external_username': external_user['external_user_name']
            })
            # If the mapping does exist, we just get that external user, to confirm it exists
            return external_user_mapping \
                if self.get_external_user({'external_user_id': external_user_mapping.external_user_id}) \
                else False
        else:
            return external_user_mapping

    def api_authenticate(self, request):
        return True

    def create_external_user(self, user_info):
        if self.operating_system == 'linux':
            output = subprocess.run(['useradd', user_info['name']], capture_output=True)
            if output.returncode == 0:
                external_user = pwd.getpwnam(user_info['name'])
            else:
                # TODO: Add logging here
                external_user = False
        elif self.operating_system == 'osx':
            external_user = False
        else:
            external_user = False
        # Need to return username and id
        return external_user

    def get_external_user(self, external_user_info):
        try:
            if 'username' in external_user_info:
                external_user = pwd.getpwnam(external_user_info['username'])
            elif 'external_user_id' in external_user_info:
                external_user = pwd.getpwuid(int(external_user_info['external_user_id']))
            else:
                external_user = False
            return {
                'external_user_name': external_user[0],
                'external_user_uid': external_user[2],
                'external_user_gid': external_user[3]
            } if external_user else external_user
        except Exception as e:
            print(e)
            return False

    def delete_external_user(self, user_id):
        pass
