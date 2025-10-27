# Documentation

This directory contains the Sphinx documentation for the User Workspaces Server.

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
pip install -r requirements/docs_requirements.txt
```

### Building HTML Documentation

From the `docs/` directory:

```bash
make html
```

The generated documentation will be available in `_build/html/index.html`.

### Other Output Formats

Sphinx supports multiple output formats:

```bash
# PDF (requires LaTeX)
make latexpdf

# EPUB
make epub

# Plain text
make text
```

## Documentation Structure

- `index.rst` - Main documentation index
- `overview.rst` - Project overview and key concepts
- `architecture.rst` - Detailed architecture documentation
- `api.rst` - API reference documentation
- `modules.rst` - Auto-generated module documentation
- `setup.rst` - Development setup guide
- `testing.rst` - Testing documentation
- `deployment.rst` - Production deployment guide

## Auto-generated Documentation

Module documentation is automatically generated using `sphinx-apidoc`:

```bash
sphinx-apidoc -o docs/ src/user_workspaces_server --force --separate
```

## Configuration

Documentation configuration is in `conf.py`. Key features:

- ReadTheDocs theme
- Automatic API documentation with `sphinx.ext.autodoc`
- Google/NumPy docstring support with `sphinx.ext.napoleon`
- Type hints support with `sphinx_autodoc_typehints`
- Markdown support with `myst-parser`

## Viewing the Documentation

After building, open `_build/html/index.html` in your web browser, or serve it locally:

```bash
# Serve on http://localhost:8000
python -m http.server 8000 -d _build/html
```