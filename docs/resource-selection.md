# Intelligent Resource Selection

When a job is submitted, the server automatically selects the most appropriate compute resource rather than routing everything to a single hardcoded `main_resource`. Selection runs in two phases: filter and score.

---

## How It Works

### Phase 1 — Filter (hard constraints)

Resources that cannot fulfil the job are eliminated:

| Check | Resource config field |
|---|---|
| GPU required but resource has none | `capabilities.gpu_enabled` |
| Requested CPUs exceed limit | `capabilities.max_cpus` |
| Requested memory (MB) exceeds limit | `capabilities.max_memory_mb` |
| Requested time (minutes) exceeds limit | `capabilities.max_time_minutes` |
| User lacks permission on this resource | `resource_user_authentication.has_permission()` |
| Health check fails | `connection_details.health_check_url` |

Resources that do not have a `capabilities` section in their config are skipped entirely and never considered by the selector (they remain available as the `main_resource` fallback).

### Phase 2 — Score (soft preferences)

Each eligible resource receives a score and the highest scorer is selected:

```
score = (priority × 10)
      + (50 if job_type in preferred_for_job_types)
      + (30 if GPU job on GPU resource)
      + (20 if CPU job on CPU-only resource)
      - (cost_per_core_hour × 5)
      - (utilization_fraction × 20)
```

`utilization_fraction` = active jobs / `capabilities.max_concurrent_jobs`, capped at 1.0. Omit `max_concurrent_jobs` from a resource's capabilities to disable utilization scoring for that resource.

### Fallback

If no resource passes the filter (e.g. a GPU job on a CPU-only deployment, or impossible resource limits), the server falls back to `main_resource` and logs a warning. No error is raised.

---

## Configuration

Add three optional sections to any resource in `available_resources`. Resources without these sections are ignored by the selector.

### `capabilities`

Hard limits used for filtering. Units match the resource option parameter names directly — no conversion needed. **Required fields** when the section is present: `gpu_enabled`, `max_cpus`, `max_memory_mb`, `max_time_minutes`.

```json
"capabilities": {
  "gpu_enabled": true,
  "gpu_types": ["A100", "V100"],
  "max_cpus": 128,
  "max_memory_mb": 524288,
  "max_time_minutes": 2880,
  "max_gpus": 8,
  "max_concurrent_jobs": 50,
  "partitions": ["GPU", "GPU-shared"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `gpu_enabled` | boolean | yes | Whether the resource has GPU support |
| `max_cpus` | integer | yes | Maximum CPUs per job (matches `num_cpus`) |
| `max_memory_mb` | integer | yes | Maximum memory per job in MB (matches `memory_mb`) |
| `max_time_minutes` | integer | yes | Maximum walltime per job in minutes (matches `time_limit_min`) |
| `gpu_types` | array[string] | no | Available GPU models |
| `max_gpus` | integer | no | Maximum GPUs per job (default: 0) |
| `max_concurrent_jobs` | integer | no | Soft job ceiling for utilization scoring. Omit to skip utilization scoring. |
| `partitions` | array[string] | no | Available Slurm partitions |

### `selection_criteria`

Scoring hints. **Required field**: `priority`.

```json
"selection_criteria": {
  "priority": 10,
  "cost_per_core_hour": 1.5,
  "preferred_for_job_types": ["jupyter_lab"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `priority` | integer (0–100) | yes | Base score multiplier. Higher = preferred when all else is equal. |
| `cost_per_core_hour` | float | no | Relative cost metric. Lower = preferred. (default: 1.0) |
| `preferred_for_job_types` | array[string] | no | Job type keys that earn a +50 bonus on this resource. |

> **Note:** User/group access control is enforced through the resource's `user_authentication` controller (e.g. `GlobusUserAuthentication`), not through `selection_criteria`. Configure `allowed_globus_groups` on the auth controller itself.

---

## Multi-Resource Example

A deployment with a GPU cluster and a CPU cluster:

```json
"available_resources": {
  "hive_gpu_cluster": {
    "name": "Hive GPU Cluster",
    "resource_type": "SlurmAPIResource",
    "storage": "hubmap_local_fs",
    "user_authentication": "globus_auth",
    "connection_details": {
      "root_url": "https://slurm-gpu.hive.psc.edu/proxy",
      "api_token": "...",
      "health_check_url": "https://slurm-gpu.hive.psc.edu/health"
    },
    "cpu_partition": "GPU-shared",
    "gpu_partition": "GPU",
    "capabilities": {
      "gpu_enabled": true,
      "gpu_types": ["A100"],
      "max_cpus": 128,
      "max_memory_mb": 524288,
      "max_time_minutes": 2880,
      "max_gpus": 8,
      "max_concurrent_jobs": 50
    },
    "selection_criteria": {
      "priority": 10,
      "cost_per_core_hour": 1.5,
      "preferred_for_job_types": ["jupyter_lab"]
    }
  },

  "hive_cpu_cluster": {
    "name": "Hive CPU Cluster",
    "resource_type": "SlurmAPIResource",
    "storage": "hubmap_local_fs",
    "user_authentication": "globus_auth",
    "connection_details": {
      "root_url": "https://slurm-cpu.hive.psc.edu/proxy",
      "api_token": "...",
      "health_check_url": "https://slurm-cpu.hive.psc.edu/health"
    },
    "cpu_partition": "RM",
    "capabilities": {
      "gpu_enabled": false,
      "max_cpus": 64,
      "max_memory_mb": 262144,
      "max_time_minutes": 10080,
      "max_gpus": 0,
      "max_concurrent_jobs": 100
    },
    "selection_criteria": {
      "priority": 5,
      "cost_per_core_hour": 0.8,
      "preferred_for_job_types": ["jupyter_lab"]
    }
  }
}
```

With this config:
- A GPU job is routed to `hive_gpu_cluster` (CPU cluster filtered out).
- A CPU job can go to either cluster — GPU cluster scores higher due to priority, but CPU cluster scores an efficiency bonus (+20). Whether they load-balance depends on how close the scores are at runtime.
- If both clusters are unhealthy or over capacity, the job falls back to `main_resource`.

### `environment_details` for multi-resource job types

When multiple resources are configured, each job type's `environment_details` can provide per-resource environment config. The server uses the selected resource's key first, then falls back to the `main_resource` key:

```json
"available_job_types": {
  "jupyter_lab": {
    "name": "Jupyter Lab",
    "job_type": "JupyterLabJob",
    "environment_details": {
      "hive_gpu_cluster": {
        "python_version": "python3.10",
        "module_manager": "virtualenv",
        "modules": ["jupyterlab"],
        "time_limit": "60",
        "environment_name": "JupyterLabJob"
      },
      "hive_cpu_cluster": {
        "python_version": "python3.10",
        "module_manager": "virtualenv",
        "modules": ["jupyterlab"],
        "time_limit": "60",
        "environment_name": "JupyterLabJob"
      },
      "main_resource": {
        "python_version": "python3.10",
        "module_manager": "virtualenv",
        "modules": ["jupyterlab"],
        "time_limit": "60",
        "environment_name": "JupyterLabJob"
      }
    }
  }
}
```

---

## Access Control

Resource-level access control is handled by the resource's `user_authentication` controller, not by the selector config. When a user submits a job, the selector calls `has_permission(user)` on each candidate resource's auth controller. Resources for which the user lacks permission are filtered out.

For `GlobusUserAuthentication`, this means:
- The user must have a stored external mapping (i.e. must have authenticated at least once).
- If `allowed_globus_groups` is set on the auth controller, the user's stored groups token is checked against those groups.

To restrict a resource to a specific group, configure `allowed_globus_groups` on the auth controller assigned to that resource:

```json
"available_user_authentication": {
  "gpu_cluster_auth": {
    "user_authentication_type": "GlobusUserAuthentication",
    "connection_details": {
      "client_id": "...",
      "client_secret": "...",
      "authentication_type": "token",
      "allowed_globus_groups": ["<globus-group-uuid>"]
    }
  }
},
"available_resources": {
  "hive_gpu_cluster": {
    "user_authentication": "gpu_cluster_auth",
    ...
  }
}
```

> **Known limitation:** `has_permission` is currently a placeholder that always returns `True`. Real group membership enforcement is pending Phase 4 implementation in `GlobusUserAuthentication`.

---

## Backward Compatibility

- Existing deployments with no `capabilities` section continue to work unchanged — those resources are skipped by the selector and the `main_resource` fallback is used.
- Adding `capabilities` to a resource opts it into the selector without any other changes required.
- The `main_resource` key in `config.json` still determines the fallback resource.
