"""Helper functions for working with version control systems."""
import logging
import os
import subprocess
from pathlib import Path
from shutil import which
from typing import Optional
from cookiecutter.exceptions import RepositoryCloneFailed, RepositoryNotFound, UnknownRepoType, VCSNotInstalled
from cookiecutter.prompt import prompt_and_delete
from cookiecutter.utils import make_sure_path_exists
logger = logging.getLogger(__name__)
BRANCH_ERRORS = ['error: pathspec', 'unknown revision']

def identify_repo(repo_url):
    """Determine if `repo_url` should be treated as a URL to a git or hg repo.

    Repos can be identified by prepending "hg+" or "git+" to the repo URL.

    :param repo_url: Repo URL of unknown type.
    :returns: ('git', repo_url), ('hg', repo_url), or None.
    :raises: UnknownRepoType if the repo type cannot be determined.
    """
    if repo_url.startswith('git+'):
        return 'git', repo_url[4:]
    elif repo_url.startswith('hg+'):
        return 'hg', repo_url[3:]
    elif any(host in repo_url for host in ['github.com', 'gitlab.com', 'gitorious.org']):
        return 'git', repo_url
    elif 'bitbucket.org' in repo_url:
        if repo_url.endswith('.git'):
            return 'git', repo_url
        else:
            return 'hg', repo_url
    elif repo_url.endswith('.git'):
        return 'git', repo_url
    elif repo_url.endswith('.hg'):
        return 'hg', repo_url
    elif '@' in repo_url and ':' in repo_url:
        # SSH URL format: [user@]host:path
        return 'git', repo_url
    raise UnknownRepoType

def is_vcs_installed(repo_type):
    """
    Check if the version control system for a repo type is installed.

    :param repo_type: Name of the version control system to check.
    :returns: True if VCS executable is found, False otherwise.
    """
    return bool(which(repo_type))

def clone(repo_url: str, checkout: Optional[str]=None, clone_to_dir: 'os.PathLike[str]'='.', no_input: bool=False):
    """Clone a repo to the current directory.

    :param repo_url: Repo URL of unknown type.
    :param checkout: The branch, tag or commit ID to checkout after clone.
    :param clone_to_dir: The directory to clone to.
                         Defaults to the current directory.
    :param no_input: Do not prompt for user input and eventually force a refresh of
        cached resources.
    :returns: str with path to the new directory of the repository.
    :raises: VCSNotInstalled if the required VCS is not installed
            RepositoryNotFound if the repository cannot be found
            RepositoryCloneFailed if the repository cannot be cloned
    """
    # Ensure clone_to_dir exists
    clone_to_dir = os.path.expanduser(clone_to_dir)
    clone_to_dir = os.path.normpath(clone_to_dir)
    make_sure_path_exists(clone_to_dir)

    # Get repo type and url
    repo_type, repo_url = identify_repo(repo_url)

    # Check if VCS is installed
    if not is_vcs_installed(repo_type):
        raise VCSNotInstalled(f'{repo_type} is not installed.')

    repo_url = repo_url.rstrip('/')
    if '@' in repo_url and ':' in repo_url:
        # SSH URL format: [user@]host:path
        repo_name = repo_url.rsplit(':', 1)[-1]
    else:
        repo_name = repo_url.rsplit('/', 1)[-1]

    if repo_type == 'git':
        repo_name = repo_name.rsplit('.git', 1)[0]
    elif repo_type == 'hg':
        repo_name = repo_name.rsplit('.hg', 1)[0]

    # Remove existing repo if no_input=True, otherwise prompt
    repo_dir = os.path.join(clone_to_dir, repo_name)
    if os.path.exists(repo_dir):
        if no_input:
            logger.debug('Removing %s', repo_dir)
            subprocess.check_output(['rm', '-rf', repo_dir])
        else:
            if not prompt_and_delete(repo_dir):
                return repo_dir

    # Clone the repo
    clone_cmd = [repo_type, 'clone', repo_url]
    if repo_type == 'git':
        clone_cmd.append(repo_name)

    logger.debug('Running command: %s', ' '.join(clone_cmd))
    try:
        subprocess.check_output(clone_cmd, cwd=str(clone_to_dir), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        output = e.output.decode('utf-8')
        if 'not found' in output.lower():
            raise RepositoryNotFound(
                f'The repository {repo_url} could not be found, '
                'have you made a typo?'
            ) from e
        raise RepositoryCloneFailed(
            f'Failed to clone repository {repo_url}:\n{output}'
        ) from e
    except Exception as e:
        raise RepositoryCloneFailed(
            f'Failed to clone repository {repo_url}:\n{str(e)}'
        ) from e

    # Checkout specific branch, tag, or commit
    if checkout is not None:
        checkout_cmd = None
        if repo_type == 'git':
            checkout_cmd = ['git', 'checkout', checkout]
        elif repo_type == 'hg':
            checkout_cmd = ['hg', 'update', checkout]

        try:
            subprocess.check_output(checkout_cmd, cwd=str(repo_dir), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            output = e.output.decode('utf-8')
            if any(error in output for error in BRANCH_ERRORS):
                raise RepositoryCloneFailed(
                    'The {} branch of repository {} could not be found, '
                    'have you made a typo?'.format(checkout, repo_url)
                ) from e
            raise RepositoryCloneFailed(
                f'Failed to checkout {checkout}:\n{output}'
            ) from e
        except Exception as e:
            raise RepositoryCloneFailed(
                f'Failed to checkout {checkout}:\n{str(e)}'
            ) from e

    # Convert repo_dir to string to match test expectations
    return str(repo_dir)