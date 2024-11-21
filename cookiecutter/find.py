"""Functions for finding Cookiecutter templates and other components."""
import logging
import os
from pathlib import Path
from jinja2 import Environment
from cookiecutter.exceptions import NonTemplatedInputDirException
logger = logging.getLogger(__name__)

def find_template(repo_dir: 'os.PathLike[str]', env: Environment) -> Path:
    """Determine which child directory of ``repo_dir`` is the project template.

    :param repo_dir: Local directory of newly cloned repo.
    :param env: Jinja2 environment for rendering template variables.
    :return: Relative path to project template.
    :raises: NonTemplatedInputDirException if no valid template directory is found.
    """
    repo_dir = Path(repo_dir)
    logger.debug('Searching %s for the project template.', repo_dir)

    # Check for a cookiecutter.json file in the repo_dir
    template_dir = repo_dir
    if (template_dir / 'cookiecutter.json').exists():
        return template_dir

    # Check for a cookiecutter.json file in a _cookiecutter directory
    template_dir = repo_dir / '_cookiecutter'
    if (template_dir / 'cookiecutter.json').exists():
        return template_dir

    # Check for a cookiecutter.json file in a cookiecutter directory
    template_dir = repo_dir / 'cookiecutter'
    if (template_dir / 'cookiecutter.json').exists():
        return template_dir

    # Check for a cookiecutter.json file in any of the subdirectories
    for dir_name in os.listdir(repo_dir):
        dir_path = repo_dir / dir_name
        if dir_path.is_dir() and not dir_name.startswith('.'):
            # Try to render the directory name with Jinja2
            try:
                rendered_name = env.from_string(dir_name).render()
                rendered_path = repo_dir / rendered_name
                if (rendered_path / 'cookiecutter.json').exists():
                    return rendered_path
            except Exception:
                pass

            # Try the original directory name
            if (dir_path / 'cookiecutter.json').exists():
                return dir_path

    raise NonTemplatedInputDirException