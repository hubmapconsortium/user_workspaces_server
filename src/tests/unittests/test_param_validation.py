from unittest import TestCase
from unittest.mock import PropertyMock, patch

from user_workspaces_server.validation.validate_job_params import ParamValidator


class ParamValidatorTests(TestCase):

    def setUp(self):
        """Set up test fixtures."""

        # Valid minimal config for testing
        self.valid_param_config = {
            "test_req_int_param": {
                "display_name": "Test Required Int Param",
                "description": "For testing required int params.",
                "variable_name": "test_req_int_param",
                "default_value": 1,
                "validation": {
                    "type": "int",
                    "min": 1,
                    "max": 4,
                    "required": True,
                },
            },
            "test_bool_param": {
                "display_name": "Test Boolean Param",
                "description": "For testing boolean params.",
                "variable_name": "test_bool_param",
                "default_value": False,
                "validation": {
                    "type": "bool",
                    "required": False,
                },
            },
            "test_categorical_param": {
                "display_name": "Test Categorical Param",
                "description": "For testing categorical params.",
                "variable_name": "test_categorical_param",
                "default_value": "category1",
                "validation": {
                    "type": "str",
                    "enums": ["category1", "category2", "category3"],
                    "required": False,
                },
            },
        }
        self.param_details = patch(
            "user_workspaces_server.validation.validate_job_params.ParamValidator.param_details",
            new_callable=PropertyMock,
        )
        self.mock_param_details = self.param_details.start()
        self.mock_param_details.return_value = self.valid_param_config
        self.addCleanup(self.param_details.stop)

        self.validator = ParamValidator()

    def test_validate_required_params_good(self):
        self.validator.validate({"test_req_int_param": 2, "test_bool_param": True})
        assert self.validator.errors == []

    def test_validate_required_params_bad(self):
        self.validator.validate({"test_bool_param": True})
        assert self.validator.errors == ["Missing required: test_req_int_param"]

    def test_validate_allowed(self):
        allowed = self.validator._validate_allowed(
            {"test_req_int_param": 1, "bad_param": "bad_val"}
        )
        assert allowed == {"test_req_int_param": 1}

    def test_validate_type_bad(self):
        self.validator.validate({"test_req_int_param": "1"})
        assert self.validator.errors == [
            "test_req_int_param: Value '1' of type str does not match required type int."
        ]

    def test_validate_below_min(self):
        self.validator.validate({"test_req_int_param": 0})
        assert self.validator.errors == ["test_req_int_param: Value '0' not above minimum of 1."]

    def test_validate_above_max(self):
        self.validator.validate({"test_req_int_param": 5})
        assert self.validator.errors == ["test_req_int_param: Value '5' above maximum of 4."]

    def test_validate_categorical_good(self):
        self.validator.validate({"test_req_int_param": 4, "test_categorical_param": "category1"})
        assert self.validator.errors == []

    def test_validate_categorical_bad(self):
        self.validator.validate(
            {"test_req_int_param": 4, "test_categorical_param": "not_a_category"}
        )
        assert self.validator.errors == [
            "test_categorical_param: Value 'not_a_category' is invalid. Valid values: category1, category2, category3."
        ]
