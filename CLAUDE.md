# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development Setup
```bash
# Create virtual environment (Python 3.10+)
virtualenv -p 3.10 venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements/requirements.txt
pip install -r requirements/test_requirements.txt

# Database migration
cd src && python manage.py migrate

# Run as root user (required for user/job management)
sudo python manage.py qcluster &
sudo python manage.py runserver
```

### Docker Development
```bash
# Build and start Docker Compose cluster
docker compose build
docker compose up -d
```

### Testing and Quality
```bash
# Run tests from src directory
cd src && python manage.py test

# Code formatting and linting
black .
isort .
flake8
```

## Architecture Overview

### Configuration-Driven Plugin System
The system uses a dynamic configuration approach where controllers are loaded at runtime based on JSON configuration files:

- **Configuration Files**: `config.json` and `django_config.json` in `src/` directory
- **Dynamic Loading**: `utils.generate_controller_object()` instantiates controllers based on class names
- **Controller Registry**: `apps.py` loads and registers all configured components during Django startup

### Core Architectural Patterns

#### Abstract Controller Pattern
All major components follow an abstract base class pattern:

1. **Authentication Methods** (`controllers/userauthenticationmethods/`)
   - Abstract: `AbstractUserAuthentication`
   - Implementations: `GlobusUserAuthentication`, `PSCAPIUserAuthentication`, `LocalUserAuthentication`

2. **Storage Methods** (`controllers/storagemethods/`)
   - Abstract: `AbstractStorage` 
   - Implementations: `LocalFileSystemStorage`, `HubmapLocalFileSystemStorage`

3. **Resources** (`controllers/resources/`)
   - Abstract: `AbstractResource`
   - Implementations: `LocalResource`, `SlurmAPIResource`

4. **Job Types** (`controllers/jobtypes/`)
   - Abstract: `AbstractJob`
   - Implementations: `JupyterLabJob`, `LocalTestJob`

#### Dependency Injection Chain
Controllers are composed with dependencies injected during initialization:
- Resources depend on Storage + UserAuthentication
- Storage depends on UserAuthentication  
- All controllers receive configuration dictionaries

### Background Task Architecture

#### Django-Q Integration
- **Queue Management**: Uses Redis as message broker
- **Task Registration**: All background tasks defined in `tasks.py`
- **Automatic Recovery**: On qcluster startup, automatically queues monitoring for active jobs
- **Hook System**: Tasks can specify completion hooks for chaining operations

#### Key Background Operations
- **Job Status Monitoring**: Continuous polling of job states via `update_job_status()`
- **Workspace Management**: Directory synchronization and quota tracking
- **User Quota Updates**: Real-time disk space and core hours calculation
- **Shared Workspace Creation**: Asynchronous workspace copying and email notifications

### Database Design

#### Core Models
- **Workspace**: User workspace containers with status tracking and JSON metadata
- **Job**: Execution units linking workspaces to compute resources
- **UserQuota**: Resource limits and usage tracking
- **ExternalUserMapping**: Links Django users to external authentication systems
- **SharedWorkspaceMapping**: Workspace sharing relationships

#### Status Management
Both Workspaces and Jobs use TextChoices enums for status tracking:
- **Workspace States**: `initializing`, `idle`, `active`, `deleting`, `error`
- **Job States**: `pending`, `running`, `complete`, `failed`, `stopping`

### API Structure

#### RESTful Endpoints
- `/tokens/` - Authentication token management
- `/workspaces/` - Workspace CRUD operations  
- `/jobs/` - Job lifecycle management
- `/users/` - User information and quotas
- `/shared_workspaces/` - Collaborative workspace features
- `/status/` - System health checks

#### WebSocket Integration
- **Real-time Updates**: Job status changes broadcasted via Django Channels
- **Passthrough Support**: WebSocket proxying for interactive sessions
- **Channel Groups**: Per-job status update channels

### Security Model

#### Custom Authentication
- **Token System**: `UserWorkspacesTokenAuthentication` with custom `UWS-Authorization` header
- **Multi-Provider Support**: Pluggable authentication backends (Globus, PSC API, LDAP)
- **External User Mapping**: Links internal Django users with external identity providers

#### Permission Validation
- Storage methods validate user ownership of workspaces
- Resource methods enforce user authentication for job execution
- Path traversal protection prevents directory escape attacks

### Testing Strategy

#### Test Structure
- **Unit Tests**: `tests/unittests/` for isolated component testing  
- **Integration Tests**: `tests/integrationtests/` for end-to-end workflows
- **Controller Tests**: Dedicated test modules for each controller type

#### Test Configuration
- Uses separate `test_django_config.json` and `github_test_django_config.json`
- GitHub Actions configuration in `tests/github_test_django_config.json`

### Key Development Considerations

#### Adding New Controllers
1. Implement the appropriate abstract base class
2. Add class name mapping in `utils.translate_class_to_module()`
3. Update configuration JSON files to register the new controller
4. The system will automatically discover and load the controller at startup

#### Background Task Development
- All tasks must be idempotent and handle failures gracefully
- Use `async_task()` for queueing with optional hooks for task chaining  
- Tasks automatically retry on failure based on Django-Q configuration

#### WebSocket Development
- Consumer classes in `ws_consumers.py` handle WebSocket connections
- Use channel groups for broadcasting updates to multiple clients
- Passthrough consumers proxy WebSocket connections to running jobs

#### Configuration Management
The system requires two configuration files in `src/`:
- `config.json`: UWS-specific settings (controllers, resources, authentication)
- `django_config.json`: Django settings (database, Redis, logging, email)

Example files are provided as `example_config.json` and `example_django_config.json`.