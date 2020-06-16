# coding: utf-8
"""
Minimal example using the notebook_templates blueprint.

This example uses no user management, local files and no reachable JupyterHub.

To adapt this to an existing JupyterHub, you should:

- implement handle_authentication to use some form of authentication,
  ideally corresponding to your JupyterHub authenticator class
- adapt get_destination_for_notebook and save_notebook_to_destination to your
  persistent storage implementation
- implement get_jupyterhub_url_for_destination to return a URL based on your
  configuration
"""

import base64
import os
import sys
import typing

import flask

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from notebook_templates import load_templates, notebook_templates


def get_destination_for_notebook(relative_path: str) -> typing.Any:
    """
    Get the destination for a notebook.

    The destination can be of a type of your choice, but it must be
    serializable with itsdangerous. It will be used by the other methods
    defining local behavior to determine where to store the notebook and
    how to access the notebook via your JupyterHub instance.

    :param relative_path: the relative path, based on the template path
    :return: the destination where the notebook should be saved
    """
    return {
        'relative': relative_path,
        'absolute': os.path.abspath(relative_path)
    }


def save_notebook_to_destination(
        notebook: bytes,
        destination: typing.Any,
) -> None:
    """
    Save the notebook to the desired destination.

    :param notebook: the notebook as utf-8 encoded text
    :param destination: the destination where the notebook should be saved
    """
    os.makedirs(os.path.dirname(destination['absolute']), exist_ok=True)
    with open(destination['absolute'], 'wb') as notebook_file:
        notebook_file.write(notebook)


def handle_authentication() -> typing.Any:
    """
    Handle authentication for the various routes of the blueprint.

    This function will be called and if it returns something other than None,
    the route will be return that object. This way you can interface the
    blueprint with a user management system of your choice, e.g. Flask-Login
    or something else corresponding to your Jupyterhub authenticator.

    In this example, there is no authentication.
    """
    return None


def get_jupyterhub_url_for_destination(destination: typing.Any) -> typing.Optional[str]:
    """
    Determine the JupyterHub URL of the notebook at the given destination.

    Usually this will consist of your base JupyterHub URL, followed by
    /user/, followed by the user name (depending on your authenticator),
    followed by the relative path to the notebook.

    :param destination: the destination where the notebook has been saved
    :return: the URL to the notebook on your JupyterHub
    """
    return None


def create_app():
    app = flask.Flask(__name__)

    # set configuration values
    secret_key = base64.b64encode(os.urandom(32)).decode('utf-8')
    app.config['SECRET_KEY'] = secret_key
    notebook_template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    app.config['NOTEBOOK_TEMPLATE_DIR'] = notebook_template_dir
    app.config['NOTEBOOK_TEMPLATES'] = load_templates(notebook_template_dir)

    # register and configure the blueprint itself
    app.register_blueprint(notebook_templates)
    notebook_templates.save_notebook_to_destination = save_notebook_to_destination
    notebook_templates.get_destination_for_notebook = get_destination_for_notebook
    notebook_templates.get_jupyterhub_url_for_destination = get_jupyterhub_url_for_destination
    notebook_templates.handle_authentication = handle_authentication
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
