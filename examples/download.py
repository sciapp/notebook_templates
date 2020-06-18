# coding: utf-8
"""
Eample for using the notebook_templates blueprint to download notebooks

This example uses no user management and lets users download the generated
Jupyter notebooks instead of interfacing with a JupyterHub instance.
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
        'relative': relative_path
    }


def save_notebook_to_destination(
        notebook: bytes,
        destination: typing.Any,
) -> None:
    """
    Store the notebook in the destination dictionary itself.

    :param notebook: the notebook as utf-8 encoded text
    :param destination: the destination where the notebook should be saved
    """
    destination['data'] = notebook


def handle_authentication() -> typing.Any:
    """
    There is no need for authentication, as no files are created.
    """
    return None


def get_jupyterhub_url_for_destination(destination: typing.Any) -> typing.Optional[str]:
    """
    Return None so that the user will be served the data instead of a redirect.

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
