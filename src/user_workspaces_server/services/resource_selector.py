import logging
from typing import Dict, List, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)


class ResourceSelectionError(Exception):
    """Raised when no suitable resource can be found."""

    pass


class LoadTracker:
    """Track current job counts per resource for utilization scoring."""

    def get_job_count(self, resource_name: str) -> int:
        """Get current active job count for resource (by class name)."""
        from user_workspaces_server.models import Job

        return Job.objects.filter(
            resource_name=resource_name,
            status__in=[Job.Status.PENDING, Job.Status.RUNNING],
        ).count()


class ResourceSelector:
    """
    Intelligent resource selection based on job requirements,
    resource capabilities, user permissions, and current load.
    """

    def __init__(self, available_resources: Dict):
        self.available_resources = available_resources
        self.load_tracker = LoadTracker()

    def select_resource(self, job_type: str, resource_options: Dict, user):
        """
        Two-phase resource selection: filter then score.

        Returns:
            Tuple of (resource_key, AbstractResource). resource_key is the
            key in available_resources (e.g. "hive_gpu_cluster").

        Falls back to main_resource if no eligible resources are found.
        """
        eligible = self._filter_eligible_resources(job_type, resource_options, user)

        if not eligible:
            logger.warning(
                "No eligible resources found for job_type=%s resource_options=%s; "
                "falling back to main_resource",
                job_type,
                resource_options,
            )
            main_resource_key = settings.UWS_CONFIG["main_resource"]
            return main_resource_key, self.available_resources[main_resource_key]

        scored = self._score_resources(eligible, job_type, resource_options)
        best = scored[0]

        logger.info(
            "Resource selection completed",
            extra={
                "job_type": job_type,
                "resource_options": resource_options,
                "eligible_count": len(eligible),
                "selected_resource": best["resource_name"],
                "score": best["score"],
            },
        )

        return best["resource_name"], best["resource"]

    # ------------------------------------------------------------------
    # Phase 1: Filter
    # ------------------------------------------------------------------

    def _filter_eligible_resources(
        self, job_type: str, resource_options: Dict, user
    ) -> List[Tuple[str, object]]:
        eligible = []

        for resource_name, resource in self.available_resources.items():
            capabilities = resource.config.get("capabilities")
            selection = resource.config.get("selection_criteria")

            # Resources without capabilities/selection_criteria config are
            # skipped; fallback to main_resource handles this case.
            if capabilities is None or selection is None:
                logger.debug(
                    "Resource %s has no capabilities/selection_criteria config; skipping",
                    resource_name,
                )
                continue

            # Check 1: GPU requirement
            if resource_options.get("gpu_enabled", False):
                if not capabilities.get("gpu_enabled", False):
                    logger.debug("Resource %s filtered: no GPU support", resource_name)
                    continue

            # Check 2: CPU capacity
            requested_cpus = resource_options.get("num_cpus", 0)
            if requested_cpus > capabilities.get("max_cpus", 0):
                logger.debug(
                    "Resource %s filtered: requested %s CPUs > max %s",
                    resource_name,
                    requested_cpus,
                    capabilities.get("max_cpus"),
                )
                continue

            # Check 3: Memory capacity (both in MB)
            requested_memory_mb = resource_options.get("memory_mb", 0)
            if requested_memory_mb > capabilities.get("max_memory_mb", 0):
                logger.debug(
                    "Resource %s filtered: requested %s MB memory > max %s MB",
                    resource_name,
                    requested_memory_mb,
                    capabilities.get("max_memory_mb"),
                )
                continue

            # Check 4: Time limit (both in minutes)
            requested_minutes = resource_options.get("time_limit_min", 0)
            if requested_minutes > capabilities.get("max_time_minutes", 0):
                logger.debug(
                    "Resource %s filtered: requested %s min > max %s min",
                    resource_name,
                    requested_minutes,
                    capabilities.get("max_time_minutes"),
                )
                continue

            # Check 5: User authorization via the resource's own auth method
            if not self._user_has_resource_permission(user, resource):
                logger.debug(
                    "Resource %s filtered: user %s lacks permission",
                    resource_name,
                    getattr(user, "username", user),
                )
                continue

            # Check 6: Health status
            if not self._is_resource_healthy(resource):
                logger.debug("Resource %s filtered: health check failed", resource_name)
                continue

            eligible.append((resource_name, resource))

        return eligible

    # ------------------------------------------------------------------
    # Phase 2: Score
    # ------------------------------------------------------------------

    def _score_resources(
        self, eligible: List[Tuple], job_type: str, resource_options: Dict
    ) -> List[Dict]:
        scored = []

        for resource_name, resource in eligible:
            score = 0.0
            selection = resource.config["selection_criteria"]
            capabilities = resource.config["capabilities"]

            # Factor 1: Base priority (0-100 points)
            score += selection.get("priority", 0) * 10

            # Factor 2: Job type preference (+50 if preferred)
            if job_type in selection.get("preferred_for_job_types", []):
                score += 50

            # Factor 3: Resource efficiency (0-30 points)
            if resource_options.get("gpu_enabled"):
                score += 30  # GPU job on GPU resource
            elif not capabilities.get("gpu_enabled"):
                score += 20  # CPU job on CPU-only resource (right-sizing)

            # Factor 4: Cost optimization
            cost = selection.get("cost_per_core_hour", 1.0)
            score -= cost * 5

            # Factor 5: Current load — scale score down by utilization so a
            # fully-loaded resource can never beat an idle one on priority alone.
            utilization = self._get_utilization(resource_name, resource)
            score *= (1 - utilization)

            scored.append(
                {
                    "resource_name": resource_name,
                    "resource": resource,
                    "score": score,
                    "utilization": utilization,
                }
            )

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_utilization(self, resource_name: str, resource) -> float:
        """Return utilization as a fraction [0, 1] based on active job count."""
        max_jobs = resource.config.get("capabilities", {}).get("max_concurrent_jobs", 0)
        if not max_jobs:
            return 0.0

        current = self.load_tracker.get_job_count(type(resource).__name__)
        return min(current / max_jobs, 1.0)

    def _is_resource_healthy(self, resource) -> bool:
        """
        Returns True if the resource passes its health check.

        NOTE: This calls health_check() which makes a live HTTP request on
        every job submission. Consider caching results if this becomes a
        bottleneck (e.g. 30s TTL).
        """
        connection_details = resource.config.get("connection_details", {})
        if not connection_details.get("health_check_url"):
            # No health check URL configured; assume healthy.
            return True

        try:
            result = resource.health_check()
            return result.get("connected", False)
        except Exception as e:
            logger.warning("Health check raised exception for %s: %s", resource, e)
            return False

    def _user_has_resource_permission(self, user, resource) -> bool:
        """
        Check if the user has permission to use this resource by delegating to
        the resource's own user authentication method (has_permission).

        For GlobusUserAuthentication this verifies the external user mapping
        exists and, when the auth controller is configured with
        allowed_globus_groups, confirms the user is still a member.

        Returns True for auth methods whose has_permission always succeeds
        (e.g. LocalUserAuthentication) or when the user passes all checks.
        Returns False if the auth method denies access or raises an exception.
        """
        try:
            result = resource.resource_user_authentication.has_permission(user)
            return bool(result)
        except Exception as e:
            logger.warning(
                "has_permission raised for resource %s user %s: %s",
                type(resource).__name__,
                getattr(user, "username", user),
                e,
            )
            return False
