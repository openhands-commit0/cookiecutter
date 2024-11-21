"""Main `cookiecutter` CLI."""
import collections
import json
import os
import sys
import click
from cookiecutter import __version__
from cookiecutter.config import get_user_config
from cookiecutter.exceptions import ContextDecodingException, FailedHookException, InvalidModeException, InvalidZipRepository, OutputDirExistsException, RepositoryCloneFailed, RepositoryNotFound, UndefinedVariableInTemplate, UnknownExtension
from cookiecutter.log import configure_logger
from cookiecutter.main import cookiecutter

def version_msg():
    """Return the Cookiecutter version, location and Python powering it."""
    python_version = sys.version[:3]
    location = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return f'Cookiecutter {__version__} from {location} (Python {python_version})'

def validate_extra_context(ctx, param, value):
    """Validate extra context."""
    for s in value:
        if '=' not in s:
            raise click.BadParameter(
                'EXTRA_CONTEXT should contain items of the form key=value'
            )

    # Convert tuple -- e.g.: ('program_name=foobar', 'startsecs=66')
    # to dict -- e.g.: {'program_name': 'foobar', 'startsecs': '66'}
    return collections.OrderedDict(s.split('=', 1) for s in value) or None

def list_installed_templates(default_config, passed_config_file):
    """List installed (locally cloned) templates. Use cookiecutter --list-installed."""
    config = get_user_config(default_config=default_config, passed_config_file=passed_config_file)

    template_dir = config.get('cookiecutters_dir')
    if not os.path.exists(template_dir):
        click.echo(f'Error: Cannot list installed templates. Template dir {template_dir} does not exist.')
        sys.exit(1)

    template_names = [d for d in os.listdir(template_dir) if not d.startswith('.')]
    if not template_names:
        click.echo('No installed templates found.')
        sys.exit(0)

    click.echo('Installed templates:')
    for template_name in template_names:
        click.echo(f'  {template_name}')
    sys.exit(0)

@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(__version__, '-V', '--version', message=version_msg())
@click.argument('template', required=False)
@click.argument('extra_context', nargs=-1, callback=validate_extra_context)
@click.option('--no-input', is_flag=True, help='Do not prompt for parameters and only use cookiecutter.json file content. Defaults to deleting any cached resources and redownloading them. Cannot be combined with the --replay flag.')
@click.option('-c', '--checkout', help='branch, tag or commit to checkout after git clone')
@click.option('--directory', help='Directory within repo that holds cookiecutter.json file for advanced repositories with multi templates in it')
@click.option('-v', '--verbose', is_flag=True, help='Print debug information', default=False)
@click.option('--replay', is_flag=True, help='Do not prompt for parameters and only use information entered previously. Cannot be combined with the --no-input flag or with extra configuration passed.')
@click.option('--replay-file', type=click.Path(), default=None, help='Use this file for replay instead of the default.')
@click.option('-f', '--overwrite-if-exists', is_flag=True, help='Overwrite the contents of the output directory if it already exists')
@click.option('-s', '--skip-if-file-exists', is_flag=True, help='Skip the files in the corresponding directories if they already exist', default=False)
@click.option('-o', '--output-dir', default='.', type=click.Path(), help='Where to output the generated project dir into')
@click.option('--config-file', type=click.Path(), default=None, help='User configuration file')
@click.option('--default-config', is_flag=True, help='Do not load a config file. Use the defaults instead')
@click.option('--debug-file', type=click.Path(), default=None, help='File to be used as a stream for DEBUG logging')
@click.option('--accept-hooks', type=click.Choice(['yes', 'ask', 'no']), default='yes', help='Accept pre/post hooks')
@click.option('-l', '--list-installed', is_flag=True, help='List currently installed templates.')
@click.option('--keep-project-on-failure', is_flag=True, help='Do not delete project folder on failure')
def main(template, extra_context, no_input, checkout, verbose, replay, overwrite_if_exists, output_dir, config_file, default_config, debug_file, directory, skip_if_file_exists, accept_hooks, replay_file, list_installed, keep_project_on_failure):
    """Create a project from a Cookiecutter project template (TEMPLATE).

    Cookiecutter is free and open source software, developed and managed by
    volunteers. If you would like to help out or fund the project, please get
    in touch at https://github.com/cookiecutter/cookiecutter.
    """
    # Configure logging
    configure_logger(
        stream_level='DEBUG' if verbose else 'INFO',
        debug_file=debug_file,
    )

    # List installed templates and exit
    if list_installed:
        list_installed_templates(default_config, config_file)

    # Exit if no template is provided
    if not template and not list_installed:
        click.echo('Error: Missing argument "TEMPLATE".')
        sys.exit(1)

    # Input validation
    if replay and no_input:
        click.echo('Error: --no-input and --replay cannot be used together.')
        sys.exit(1)

    if replay and extra_context:
        click.echo('Error: --replay and extra context cannot be used together.')
        sys.exit(1)

    # Run cookiecutter
    try:
        cookiecutter(
            template,
            checkout=checkout,
            no_input=no_input,
            extra_context=extra_context,
            replay=replay,
            overwrite_if_exists=overwrite_if_exists,
            output_dir=output_dir,
            config_file=config_file,
            default_config=default_config,
            password=None,
            directory=directory,
            skip_if_file_exists=skip_if_file_exists,
            accept_hooks=accept_hooks == 'yes',
            keep_project_on_failure=keep_project_on_failure,
            replay_file=replay_file,
        )
    except (ContextDecodingException, OutputDirExistsException, InvalidModeException, FailedHookException, UnknownExtension, InvalidZipRepository, RepositoryNotFound, RepositoryCloneFailed) as e:
        click.echo(f'Error: {e}')
        sys.exit(1)
    except UndefinedVariableInTemplate as undefined_err:
        click.echo(f'{undefined_err.message} is undefined')
        sys.exit(1)
if __name__ == '__main__':
    main()