# Documentation

This directory contains the Sphinx documentation for the User Workspaces Server.

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
pip install -r requirements/docs_requirements.txt
```

### Build API Docs
```bash
sphinx-apidoc -f -o docs/ src/user_workspaces_server/ src/user_workspaces_server/migrations
```

### Building HTML Documentation

From the `docs/` directory:

```bash
sphinx-build docs docs/_build
```

The generated documentation will be available in `_build/html/index.html`.

## Viewing the Documentation

After building, open `_build/html/index.html` in your web browser.