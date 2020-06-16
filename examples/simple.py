# coding: utf-8
"""
Example using the notebook_templates blueprint with Flask-Login

This example uses mock user management based on Flask-Login and hard-coded
user information, one local folder for each user and a pre-existing JupyterHub
that shares the user names used here.

You should NOT use hard-coded user information like this in production, but this
might make it easier for you to adapt the blueprint to your setup.

For more information on Flask-Login, see: https://flask-login.readthedocs.io/
"""

import base64
import os
import sys
import typing

import flask
import flask_login

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
    user_id = flask_login.current_user.user_id
    return {
        'relative': relative_path,
        'absolute': os.path.abspath(os.path.join('user', user_id, relative_path))
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

    In this example, handle_authentication is based on the Flask-Login
    login_required decorator.
    """
    if flask.request.method in flask_login.config.EXEMPT_METHODS:
        return None
    if flask.current_app.config.get('LOGIN_DISABLED'):
        return None
    if not flask_login.current_user.is_authenticated:
        return login_manager.unauthorized()
    return None


# the login blueprint, User class and load_user function mock user management
login = flask.Blueprint('login', __name__)
login_manager = flask_login.LoginManager()


class User(flask_login.UserMixin):
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id

    def get_id(self) -> str:
        return self.user_id

    @staticmethod
    def find_user_by_id(users: typing.Set['User'], user_id: str):
        for user in users:
            if user.user_id == user_id:
                return user
        return None


@login_manager.user_loader
def load_user(user_id):
    users = flask.current_app.config['USERS']
    return User.find_user_by_id(users, user_id)


@login.route('/login/')
@login.route('/login/<user_id>')
def mock_login(user_id=''):
    """
    This is a minimal example login view to support handle_authentication
    and it does NOT follow best practices!

    In practice, you should:
     - use a database or an external user management system to authenticate
       users instead of having hard-coded user information and trusting users
     - use Flask's templating system (i.e. Jinja2)
     - validate the 'next' parameter instead of simply trusting it
     - not perform changes based on a GET request
     - read more about Flask-Login at https://flask-login.readthedocs.io/
    """
    users = flask.current_app.config['USERS']
    if not user_id:
        return (
            "Please log in by visiting one of the following urls:<br/>\n" +
            '\n'.join('<a href="' + flask.url_for('login.mock_login', user_id=user.user_id, next=flask.request.args['next']) + '">login/' + user.user_id+ '</a><br />' for user in users)
        )
    user = User.find_user_by_id(users, user_id)
    if user is None:
        return "No such user exists."
    flask_login.login_user(user, remember=True)
    if 'next' in flask.request.args:
        return flask.redirect(flask.request.args['next'])
    return flask.redirect(flask.url_for('notebook_templates.index'))


def get_jupyterhub_url_for_destination(destination: typing.Any) -> typing.Optional[str]:
    """
    Determine the JupyterHub URL of the notebook at the given destination.

    Usually this will consist of your base JupyterHub URl, followed by
    /user/, followed by the user name (depending on your authenticator),
    followed by the relative path to the notebook.

    :param destination: the destination where the notebook has been saved
    :return: the URL to the notebook on your JupyterHub
    """
    jupyterhub_url = flask.current_app.config['JUPYTERHUB_URL']
    user_id = flask_login.current_user.user_id
    notebook_path = destination['relative']
    return f'{jupyterhub_url}/user/{user_id}/{notebook_path}'


def create_app():
    app = flask.Flask(__name__)

    # set configuration values
    secret_key = base64.b64encode(os.urandom(32)).decode('utf-8')
    app.config['SECRET_KEY'] = secret_key
    notebook_template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    app.config['NOTEBOOK_TEMPLATE_DIR'] = notebook_template_dir
    app.config['NOTEBOOK_TEMPLATES'] = load_templates(notebook_template_dir)
    # insert your JupyterHub URL here
    app.config['JUPYTERHUB_URL'] = 'https://example.com'

    # register the login manager and set up user info
    login_manager.init_app(app)
    login_manager.login_view = 'login.mock_login'
    app.config['USERS'] = {
        User('alice'),
        User('bob')
    }

    # register the main blueprint
    app.register_blueprint(login)

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
