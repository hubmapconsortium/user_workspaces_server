from collections import defaultdict

from django.apps import apps


class ParamValidator:
    """
    Compares options submitted in request against global parameter
    validation requirements. Validates all and returns True/False.
    Can access errors attr for reporting.
    Strict mode could be implemented to bail on first error.
    """

    param_details = apps.get_app_config("user_workspaces_server").parameters

    def __init__(self):
        self.errors = defaultdict(list)
        self.valid = False

    def validate(self, options: dict):
        self._validate_required(options)
        for param, value in options.items():
            self._validate_type(param, value)
            self._validate_above_min(param, value)
            self._validate_below_max(param, value)
        if not self.errors:
            self.is_valid = True

    def _validate_required(self, resource_options):
        for param in self.param_details:
            if param.get("validation", {}).get("required"):
                if not param.get("variable_name") in resource_options.keys():
                    self.errors["Missing required"].append(param)

    def _validate_type(self, param, value):
        if req_type := self.param_details(param).get("type"):
            if not str(type(value)) == req_type:
                self.errors[param].append(
                    f"Value {value} of type {type(value)} does not match required type {req_type}."
                )

    def _validate_above_min(self, param: str, value: int):
        if min := self.param_details(param).get("min"):
            if not min < value:
                self.errors[param].append(f"Value {value} not above minimum of {min}.")

    def _validate_below_max(self, param, value):
        if max := self.param_details(param).get("max"):
            if not value < max:
                self.errors[param].append(f"Value {value} above maximum of {max}.")
