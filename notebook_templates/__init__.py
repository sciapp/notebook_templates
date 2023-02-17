# coding: utf-8
"""
Blueprint for a Jupyter notebook templating server.
"""

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

import glob
import json
import os
import typing

import flask
from flask_wtf import FlaskForm
import itsdangerous.url_safe
from wtforms.fields import StringField


class UseTemplateForm(FlaskForm):
    params = StringField()
    destination = StringField()


class NotebookTemplateError(Exception):
    def __init__(
            self,
            error_message: str,
            error_code: int = -1,
            status_code: int = 500
    ) -> None:
        self.error_message = error_message
        self.error_code = error_code
        self.status_code = status_code


def handle_notebook_template_errors(e):
    error_message = getattr(e, 'error_message', 'An unknown error occurred')
    error_code = getattr(e, 'error_code', -1)
    status_code = getattr(e, 'status_code', 400)
    return flask.render_template(
        'error.html',
        error_message=error_message,
        error_code=error_code
    ), status_code


notebook_templates = flask.Blueprint(
    'notebook_templates',
    __name__,
    url_prefix='/',
    static_folder=os.path.join(os.path.dirname(__file__), 'static'),
    static_url_path='notebook_templates_static',
    template_folder=os.path.join(os.path.dirname(__file__), 'templates')
)
notebook_templates.register_error_handler(NotebookTemplateError, handle_notebook_template_errors)


@notebook_templates.route('/')
def index() -> typing.Any:
    authentication_result = notebook_templates.handle_authentication()
    if authentication_result is not None:
        return authentication_result

    return flask.render_template(
        "templates.html",
        templates=flask.current_app.config['NOTEBOOK_TEMPLATES']
    )


@notebook_templates.route("/t/<path:path>", methods=['GET', 'POST'])
def use_template(path: str) -> typing.Any:

    authentication_result = notebook_templates.handle_authentication()
    if authentication_result is not None:
        return authentication_result

    if path not in flask.current_app.config['NOTEBOOK_TEMPLATES']:
        raise NotebookTemplateError(
            error_message='The requested template does not exist.',
            error_code=13
        )

    serializer = itsdangerous.url_safe.URLSafeTimedSerializer(
        secret_key=flask.current_app.config['SECRET_KEY']
    )

    form = UseTemplateForm()
    if form.validate_on_submit():
        try:
            destination = serializer.loads(form.destination.data, salt='create_template_destination', max_age=30 * 60)
            params = serializer.loads(form.params.data, salt='create_template_params', max_age=30 * 60)
        except Exception:
            raise NotebookTemplateError(
                error_message='An error occured while creating the notebook. Please try again in a few minutes.',
                error_code=2
            )
        try:
            _create_template_instance(os.path.join(flask.current_app.config['NOTEBOOK_TEMPLATE_DIR'], path), destination, params)
        except Exception:
            raise NotebookTemplateError(
                error_message='An error occured while creating the notebook. Please try again in a few minutes.',
                error_code=11
            )
        try:
            jupyterhub_url = notebook_templates.get_jupyterhub_url_for_destination(destination)
        except Exception:
            raise NotebookTemplateError(
                error_message='The notebook was created successfully, but there was an error determining its JupyterHub URL.',
                error_code=14
            )
        if jupyterhub_url:
            return flask.redirect(jupyterhub_url)
        if 'data' in destination:
            notebook_name = os.path.basename(destination['relative'])
            return flask.Response(
                destination['data'],
                status=200,
                headers={
                    'Content-Disposition': f'attachment; filename="{notebook_name}"',
                    'Content-Type': 'application/vnd.jupyter'
                }
            )
        return flask.render_template('instance_created.html')

    params = {}
    if 'params' in flask.request.form:
        try:
            params.update(json.loads(flask.request.form.get('params', '{}')))
        except Exception:
            pass
    if 'params' in flask.request.args:
        try:
            params.update(json.loads(flask.request.args.get('params', '{}')))
        except Exception:
            pass

    try:
        relative_destination = path.format(**params)
    except KeyError as e:
        missing_parameter = e.args[0]
        raise NotebookTemplateError(
            error_message=f'The parameter "{missing_parameter}" is missing.',
            error_code=15
        )

    try:
        destination = notebook_templates.get_destination_for_notebook(relative_destination)
    except Exception:
        raise NotebookTemplateError(
            error_message=f'Unable to determine notebook destination.',
            error_code=16
        )

    form.destination.data = serializer.dumps(
        destination,
        salt='create_template_destination'
    )
    form.params.data = serializer.dumps(
        params,
        salt='create_template_params'
    )
    return flask.render_template(
        'confirm_instance_creation.html',
        path=path,
        destination=destination,
        form=form
    )


def load_templates(
        template_dir: str
) -> typing.List[str]:
    """
    Load the list of templates existing in a given template directory.

    :param template_dir: the directory in which to search for templates
    :return: the list of template paths
    """
    templates = []
    for file_name in glob.glob(os.path.join(template_dir, '**', '*.ipynb'), recursive=True):
        # do not follow links out of template_dir
        if os.path.abspath(file_name) != os.path.realpath(file_name):
            continue
        file_name = os.path.relpath(file_name, template_dir)
        templates.append(file_name)
    return templates


def _create_template_instance(
        template_path: str,
        destination: typing.Any,
        params: typing.Mapping[str, typing.Any]
) -> None:
    """
    Create an instance of a template.

    :param template_path: the path to the template
    :param destination: the destination where the instance should be saved
    :param params: user-defined parameters to include in the template
    """
    with open(template_path) as template_file:
        template = json.load(template_file)

    _insert_params_into_notebook(template, params)
    notebook = json.dumps(template, indent=1).encode('utf-8')

    notebook_templates.save_notebook_to_destination(notebook, destination)


def _insert_params_into_notebook(
        notebook: typing.Dict[str, typing.Any],
        params: typing.Mapping[str, typing.Any]
) -> None:
    """
    Insert the given parameters into a Jupyter notebook.

    The parameters are inserted as a new cell, which is placed behind the
    first cell. If there are no parameters, no new cell will be created.

    Currently, only the following languages are supported:

    - Python
    - Julia
    - C

    For all other languages, a fallback implementation is used that might create incorrect results.

    :param notebook: the Jupyter notebook
    :param params: the parameter mapping
    """
    if not params:
        return

    metadata = notebook.get('metadata', {})
    kernelspec = metadata.get('kernelspec', {})
    language = kernelspec.get('language', '').lower()

    source = []
    for key, value in params.items():
        if value is None:
            if language == 'python':
                source.append(f'{key} = None # not set\n')
            elif language == 'julia':
                source.append(f'{key} = nothing # not set\n')
            elif language == 'c':
                source.append(f'int {key} = 0; /* not set */\n')
            else:
                source.append(f'{key} = 0\n')
        else:
            if language == 'c':
                if isinstance(value, str):
                    source.append(f'const char *{key} = {json.dumps(value)};\n')
                elif isinstance(value, int):
                    source.append(f'int {key} = {json.dumps(value)};\n')
                elif isinstance(value, float):
                    source.append(f'double {key} = {json.dumps(value)};\n')
                elif isinstance(value, bool):
                    source.append(f'int {key} = {1 if value else 0};\n')
                else:
                    source.append(f'{key} = {json.dumps(value)};\n')
            else:
                source.append(f'{key} = {json.dumps(value)}\n')

    params_cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source
    }
    notebook["cells"].insert(1, params_cell)
