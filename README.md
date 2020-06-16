# Jupyter Notebook Templates

The `notebook_templates` package contains a Flask blueprint for working with Jupyter Notebook templates, e.g. for use with SampleDB.

To use the blueprint, you will need to set the `NOTEBOOK_TEMPLATE_DIR` and `NOTEBOOK_TEMPLATES` configuration values and implement four methods that allow the blueprint to work with your JupyterHub instance:
- `get_destination_for_notebook` and `save_notebook_to_destination`, which implement how notebooks can be saved to the persistent storage used by your JupyterHub,
- `handle_authentication`, which implements how users should authenticate themselves, similar to the `Authenticator` used by your JupyterHub, and
- `get_jupyterhub_url_for_destination`, which builds URLs to notebooks in your JupyterHub.

The `examples` folder contains example Flask apps using the blueprint to show how it could be used, including a minimal example (`minimal.py`) which can be run locally and does not require a JupyterHub instance to function.
