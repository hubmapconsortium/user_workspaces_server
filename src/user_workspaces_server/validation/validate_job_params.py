from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property


class ParamValidator:
    """
    Compares options submitted in request against global parameter
    validation requirements. Validates all and returns True/False.
    Can access errors attr for reporting.
    Strict mode could be implemented to bail on first error.
    """

    @cached_property
    def param_details(self):
        params = {}
        param_list = apps.get_app_config("user_workspaces_server").parameters
        for param in param_list:
            params[param["variable_name"]] = param
        return params

    def __init__(self):
        self.errors = []
        self.valid = None

    def validate(self, options: dict):
        self._validate_required(options)
        cleaned_options = self._validate_allowed(options)
        for param, value in cleaned_options.items():
            try:
                self._validate_type(param, value)
            except ValidationError:
                continue
            self._validate_above_min(param, value)
            self._validate_below_max(param, value)
        if not self.errors:
            self.is_valid = True
        else:
            self.is_valid = False

    def _validate_required(self, resource_options):
        for param, details in self.param_details.items():
            if details.get("validation", {}).get("required"):
                if not details.get("variable_name") in resource_options.keys():
                    self.errors.append(f"Missing required: {param}")

    def _validate_allowed(self, resource_options) -> dict:
        not_allowed = resource_options.keys() - self.param_details.keys()
        # not_allowed are ignored in validation and stripped in the translation step
        if not_allowed:
            resource_options = {
                key: value
                for key, value in resource_options.items()
                if key not in not_allowed
            }
        return resource_options

    def _validate_type(self, param, value):
        if req_type := self.param_details[param].get("validation", {}).get("type"):
            if not type(value).__name__ == req_type:
                msg = f"{param}: Value '{value}' of type {type(value).__name__} does not match required type {req_type}. Skipping further validation of parameter {param}."
                self.errors.append(msg)
                raise ValidationError(msg)

    def _validate_above_min(self, param: str, value: int):
        if min := self.param_details[param].get("validation", {}).get("min"):
            if value < min:
                self.errors.append(
                    f"{param}: Value '{value}' not above minimum of {min}."
                )

    def _validate_below_max(self, param, value):
        if max := self.param_details[param].get("validation", {}).get("max"):
            if value > max:
                self.errors.append(f"{param}: Value '{value}' above maximum of {max}.")
