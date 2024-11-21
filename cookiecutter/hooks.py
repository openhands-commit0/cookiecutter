"""Functions for discovering and executing various cookiecutter hooks."""
import errno
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from jinja2.exceptions import UndefinedError
from cookiecutter import utils
from cookiecutter.exceptions import FailedHookException
from cookiecutter.utils import create_env_with_context, create_tmp_repo_dir, rmtree, work_in
logger = logging.getLogger(__name__)
_HOOKS = ['pre_prompt', 'pre_gen_project', 'post_gen_project']
EXIT_SUCCESS = 0

def valid_hook(hook_file, hook_name):
    """Determine if a hook file is valid.

    :param hook_file: The hook file to consider for validity
    :param hook_name: The hook to find
    :return: The hook file validity
    """
    filename = os.path.basename(hook_file)
    basename = os.path.splitext(filename)[0]

    return hook_name == basename and os.path.isfile(hook_file)

def find_hook(hook_name, hooks_dir='hooks'):
    """Return a dict of all hook scripts provided.

    Must be called with the project template as the current working directory.
    Dict's key will be the hook/script's name, without extension, while values
    will be the absolute path to the script. Missing scripts will not be
    included in the returned dict.

    :param hook_name: The hook to find
    :param hooks_dir: The hook directory in the template
    :return: The absolute path to the hook script or None
    """
    if not os.path.exists(hooks_dir):
        logger.debug('No hooks directory found')
        return None

    hook_dir_candidates = [hooks_dir]
    if os.path.exists('cookiecutter.json'):
        hook_dir_candidates.append(os.path.join(hooks_dir, hook_name))

    for candidate in hook_dir_candidates:
        if not os.path.exists(candidate):
            continue

        for hook_file in os.listdir(candidate):
            hook_path = os.path.join(candidate, hook_file)
            if valid_hook(hook_path, hook_name):
                return os.path.abspath(hook_path)

    return None

def run_script(script_path, cwd='.'):
    """Execute a script from a working directory.

    :param script_path: Absolute path to the script to run.
    :param cwd: The directory to run the script from.
    """
    run_thru_shell = sys.platform.startswith('win')
    if script_path.endswith('.py'):
        script_command = [sys.executable, script_path]
    else:
        script_command = [script_path]

    try:
        proc = subprocess.Popen(
            script_command,
            shell=run_thru_shell,
            cwd=cwd
        )
        exit_status = proc.wait()
        if exit_status != EXIT_SUCCESS:
            raise FailedHookException(
                f'Hook script failed (exit status: {exit_status})'
            )
    except OSError as os_error:
        if os_error.errno == errno.ENOEXEC:
            raise FailedHookException(
                'Hook script failed, might be an empty or invalid script file'
            )
        raise FailedHookException(
            'Hook script failed (error: {})'.format(os_error)
        )

def run_script_with_context(script_path, cwd, context):
    """Execute a script after rendering it with Jinja.

    :param script_path: Absolute path to the script to run.
    :param cwd: The directory to run the script from.
    :param context: Cookiecutter project template context.
    """
    _, extension = os.path.splitext(script_path)

    with open(script_path, 'r', encoding='utf-8') as f:
        contents = f.read()

    try:
        env = create_env_with_context(context)
        script_contents = env.from_string(contents).render(**context)
    except UndefinedError as err:
        msg = f"Unable to render hook script '{script_path}': {err.message}"
        raise UndefinedError(msg)

    # Write rendered script to temp file
    temp_dir = create_tmp_repo_dir()
    temp_script = os.path.join(temp_dir, f'hook{extension}')

    with open(temp_script, 'w', encoding='utf-8') as f:
        f.write(script_contents)

    # Set appropriate mode
    mode = os.stat(script_path).st_mode
    os.chmod(temp_script, mode)

    try:
        run_script(temp_script, cwd)
    finally:
        rmtree(temp_dir)

def run_hook(hook_name, project_dir, context):
    """
    Try to find and execute a hook from the specified project directory.

    :param hook_name: The hook to execute.
    :param project_dir: The directory to execute the script from.
    :param context: Cookiecutter project context.
    """
    with work_in(project_dir):
        hook_path = find_hook(hook_name)
        if hook_path:
            run_script_with_context(hook_path, project_dir, context)

def run_hook_from_repo_dir(repo_dir, hook_name, project_dir, context, delete_project_on_failure):
    """Run hook from repo directory, clean project directory if hook fails.

    :param repo_dir: Project template input directory.
    :param hook_name: The hook to execute.
    :param project_dir: The directory to execute the script from.
    :param context: Cookiecutter project context.
    :param delete_project_on_failure: Delete the project directory on hook
        failure?
    """
    with work_in(repo_dir):
        try:
            run_hook(hook_name, project_dir, context)
        except Exception:
            if delete_project_on_failure:
                rmtree(project_dir)
            logger.error(
                "Stopping generation because %s hook "
                "script didn't exit successfully",
                hook_name
            )
            raise

def run_pre_prompt_hook(repo_dir: 'os.PathLike[str]') -> Path:
    """Run pre_prompt hook from repo directory.

    :param repo_dir: Project template input directory.
    """
    # Create a temporary directory for the pre-prompt hook
    temp_dir = create_tmp_repo_dir()

    try:
        with work_in(repo_dir):
            hook_path = find_hook('pre_prompt')
            if hook_path:
                run_script(hook_path, temp_dir)
    except Exception:
        rmtree(temp_dir)
        raise

    return Path(temp_dir)