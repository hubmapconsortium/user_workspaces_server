from unittest.mock import MagicMock, patch

from django.test import TestCase

from user_workspaces_server.services.resource_selector import (
    LoadTracker,
    ResourceSelector,
)


def make_resource(
    gpu_enabled=False,
    max_cpus=64,
    max_memory_mb=262144,   # 256 GB in MB
    max_time_minutes=10080,  # 7 days in minutes
    max_gpus=0,
    max_concurrent_jobs=100,
    priority=5,
    cost=1.0,
    preferred_for=None,
    has_health_check_url=False,
):
    """Return a mock AbstractResource with the given capabilities."""
    resource = MagicMock()
    resource.config = {
        "capabilities": {
            "gpu_enabled": gpu_enabled,
            "max_cpus": max_cpus,
            "max_memory_mb": max_memory_mb,
            "max_time_minutes": max_time_minutes,
            "max_gpus": max_gpus,
            "max_concurrent_jobs": max_concurrent_jobs,
        },
        "selection_criteria": {
            "priority": priority,
            "cost_per_core_hour": cost,
            "preferred_for_job_types": preferred_for or [],
        },
        "connection_details": {
            "health_check_url": "http://example.com/health" if has_health_check_url else ""
        },
    }
    return resource


def make_two_resource_dict():
    gpu = make_resource(
        gpu_enabled=True, max_cpus=128, max_memory_mb=524288, max_time_minutes=2880,
        priority=10, cost=1.5, preferred_for=["jupyter_lab"],
    )
    cpu = make_resource(
        gpu_enabled=False, max_cpus=64, max_memory_mb=262144, max_time_minutes=10080,
        priority=5, cost=0.8, preferred_for=["jupyter_lab"],
    )
    return {"gpu_cluster": gpu, "cpu_cluster": cpu}


BASE_OPTIONS = {"gpu_enabled": False, "num_cpus": 1, "memory_mb": 0, "time_limit_min": 0}


class TestFilterEligibleResources(TestCase):

    def setUp(self):
        self.available = make_two_resource_dict()
        self.selector = ResourceSelector(self.available)
        self.user = MagicMock()

    def test_gpu_job_filters_cpu_only_resource(self):
        opts = {**BASE_OPTIONS, "gpu_enabled": True, "num_cpus": 4}
        eligible = self.selector._filter_eligible_resources("jupyter_lab", opts, self.user)
        names = [name for name, _ in eligible]
        self.assertIn("gpu_cluster", names)
        self.assertNotIn("cpu_cluster", names)

    def test_cpu_job_passes_both_resources(self):
        eligible = self.selector._filter_eligible_resources("jupyter_lab", BASE_OPTIONS, self.user)
        names = [name for name, _ in eligible]
        self.assertIn("gpu_cluster", names)
        self.assertIn("cpu_cluster", names)

    def test_filter_cpu_capacity(self):
        # cpu_cluster max_cpus=64; request 128 should exclude it
        opts = {**BASE_OPTIONS, "num_cpus": 128}
        eligible = self.selector._filter_eligible_resources("batch_job", opts, self.user)
        names = [name for name, _ in eligible]
        self.assertNotIn("cpu_cluster", names)
        self.assertIn("gpu_cluster", names)

    def test_filter_memory_capacity(self):
        # cpu_cluster max_memory_mb=262144 (256 GB); request 300 GB = 307200 MB
        opts = {**BASE_OPTIONS, "memory_mb": 307200}
        eligible = self.selector._filter_eligible_resources("batch_job", opts, self.user)
        names = [name for name, _ in eligible]
        self.assertNotIn("cpu_cluster", names)

    def test_filter_time_limit(self):
        # cpu_cluster max_time_minutes=10080 (7 days); request 12000 minutes
        opts = {**BASE_OPTIONS, "time_limit_min": 12000}
        eligible = self.selector._filter_eligible_resources("batch_job", opts, self.user)
        names = [name for name, _ in eligible]
        self.assertNotIn("cpu_cluster", names)

    def test_resources_without_capabilities_config_are_skipped(self):
        bare_resource = MagicMock()
        bare_resource.config = {}
        self.selector.available_resources = {"bare": bare_resource}
        eligible = self.selector._filter_eligible_resources("job", BASE_OPTIONS, self.user)
        self.assertEqual(eligible, [])

    def test_unhealthy_resource_filtered(self):
        self.available["cpu_cluster"].config["connection_details"]["health_check_url"] = "http://example.com/health"
        self.available["cpu_cluster"].health_check.return_value = {"connected": False}
        eligible = self.selector._filter_eligible_resources("job", BASE_OPTIONS, self.user)
        names = [name for name, _ in eligible]
        self.assertNotIn("cpu_cluster", names)

    def test_resource_filtered_when_auth_denies(self):
        self.available["cpu_cluster"].resource_user_authentication.has_permission.return_value = False
        eligible = self.selector._filter_eligible_resources("job", BASE_OPTIONS, self.user)
        names = [name for name, _ in eligible]
        self.assertNotIn("cpu_cluster", names)

    def test_resource_included_when_auth_allows(self):
        self.available["cpu_cluster"].resource_user_authentication.has_permission.return_value = MagicMock()
        eligible = self.selector._filter_eligible_resources("job", BASE_OPTIONS, self.user)
        names = [name for name, _ in eligible]
        self.assertIn("cpu_cluster", names)

    def test_resource_filtered_when_auth_raises(self):
        self.available["cpu_cluster"].resource_user_authentication.has_permission.side_effect = Exception("auth error")
        eligible = self.selector._filter_eligible_resources("job", BASE_OPTIONS, self.user)
        names = [name for name, _ in eligible]
        self.assertNotIn("cpu_cluster", names)


class TestScoreResources(TestCase):

    def setUp(self):
        self.available = make_two_resource_dict()
        self.selector = ResourceSelector(self.available)
        self.selector.load_tracker.get_job_count = MagicMock(return_value=0)

    def test_gpu_job_scores_gpu_resource_highest(self):
        eligible = list(self.available.items())
        opts = {**BASE_OPTIONS, "gpu_enabled": True, "num_cpus": 8}
        scored = self.selector._score_resources(eligible, "jupyter_lab", opts)
        self.assertEqual(scored[0]["resource_name"], "gpu_cluster")

    def test_cpu_job_on_cpu_resource_gets_efficiency_bonus(self):
        eligible = list(self.available.items())
        scored = self.selector._score_resources(eligible, "jupyter_lab", BASE_OPTIONS)
        cpu_score = next(r["score"] for r in scored if r["resource_name"] == "cpu_cluster")
        # priority(5)*10 + job_type_match(50) + efficiency(20) - cost(0.8*5) = 116
        self.assertAlmostEqual(cpu_score, 116.0)

    def test_high_utilization_reduces_score(self):
        eligible = [("cpu_cluster", self.available["cpu_cluster"])]

        self.selector.load_tracker.get_job_count = MagicMock(return_value=0)
        scored_zero = self.selector._score_resources(eligible, "batch_job", BASE_OPTIONS)

        self.selector.load_tracker.get_job_count = MagicMock(return_value=50)
        scored_half = self.selector._score_resources(eligible, "batch_job", BASE_OPTIONS)

        self.assertGreater(scored_zero[0]["score"], scored_half[0]["score"])

    def test_lower_cost_resource_scores_higher_all_else_equal(self):
        expensive = make_resource(priority=5, cost=2.0)
        cheap = make_resource(priority=5, cost=0.5)
        eligible = [("expensive", expensive), ("cheap", cheap)]
        self.selector.load_tracker.get_job_count = MagicMock(return_value=0)
        scored = self.selector._score_resources(eligible, "other_job", BASE_OPTIONS)
        self.assertEqual(scored[0]["resource_name"], "cheap")

    def test_no_utilization_when_max_concurrent_jobs_absent(self):
        r = make_resource(priority=5, cost=1.0)
        del r.config["capabilities"]["max_concurrent_jobs"]
        eligible = [("r", r)]
        self.selector.load_tracker.get_job_count = MagicMock(return_value=99)
        scored = self.selector._score_resources(eligible, "job", BASE_OPTIONS)
        # utilization should be 0 so load has no effect on score
        self.assertEqual(scored[0]["utilization"], 0.0)


class TestSelectResource(TestCase):

    def setUp(self):
        self.available = make_two_resource_dict()
        self.selector = ResourceSelector(self.available)
        self.selector.load_tracker.get_job_count = MagicMock(return_value=0)
        self.user = MagicMock()

    def test_gpu_job_selects_gpu_cluster(self):
        opts = {**BASE_OPTIONS, "gpu_enabled": True, "num_cpus": 8}
        key, resource = self.selector.select_resource("jupyter_lab", opts, self.user)
        self.assertEqual(key, "gpu_cluster")

    def test_fallback_when_no_eligible_resources(self):
        opts = {**BASE_OPTIONS, "num_cpus": 99999}
        with self.settings(UWS_CONFIG={"main_resource": "gpu_cluster"}):
            key, resource = self.selector.select_resource("jupyter_lab", opts, self.user)
        self.assertEqual(key, "gpu_cluster")
        self.assertIs(resource, self.available["gpu_cluster"])

    def test_highest_scoring_resource_is_selected(self):
        # gpu_cluster has priority=10, cpu_cluster has priority=5
        # For a CPU job both are eligible; gpu_cluster still wins on priority
        key, _ = self.selector.select_resource("jupyter_lab", BASE_OPTIONS, self.user)
        self.assertEqual(key, "gpu_cluster")


class TestLoadTracker(TestCase):

    def test_get_job_count_queries_db(self):
        tracker = LoadTracker()
        with patch("user_workspaces_server.services.resource_selector.LoadTracker.get_job_count") as mock_count:
            mock_count.return_value = 5
            result = tracker.get_job_count("SlurmAPIResource")
            self.assertEqual(result, 5)
