"""Utility functions for handling and fetching repo archives in zip format."""
import os
import tempfile
from pathlib import Path
from typing import Optional
from zipfile import BadZipFile, ZipFile
import requests
from cookiecutter.exceptions import InvalidZipRepository
from cookiecutter.prompt import prompt_and_delete, read_repo_password
from cookiecutter.utils import make_sure_path_exists

def unzip(zip_uri: str, is_url: bool, clone_to_dir: 'os.PathLike[str]'='.', no_input: bool=False, password: Optional[str]=None):
    """Download and unpack a zipfile at a given URI.

    This will download the zipfile to the cookiecutter repository,
    and unpack into a temporary directory.

    :param zip_uri: The URI for the zipfile.
    :param is_url: Is the zip URI a URL or a file?
    :param clone_to_dir: The cookiecutter repository directory
        to put the archive into.
    :param no_input: Do not prompt for user input and eventually force a refresh of
        cached resources.
    :param password: The password to use when unpacking the repository.
    :raises: InvalidZipRepository if the zip file is not a valid cookiecutter template.
    :returns: The path to the unpacked template.
    """
    # Ensure clone_to_dir exists
    clone_to_dir = os.path.expanduser(clone_to_dir)
    clone_to_dir = os.path.normpath(clone_to_dir)
    make_sure_path_exists(clone_to_dir)

    if is_url:
        # Build cache path and download if needed
        zip_path = os.path.join(clone_to_dir, os.path.basename(zip_uri))
        if os.path.exists(zip_path):
            if no_input:
                os.remove(zip_path)
            else:
                download = prompt_and_delete(zip_path)
                if not download:
                    return zip_path

        # Download the zip file
        response = requests.get(zip_uri, stream=True)
        response.raise_for_status()

        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
    else:
        zip_path = os.path.abspath(zip_uri)
        if not os.path.exists(zip_path):
            raise InvalidZipRepository(
                f'Zip file {zip_path} does not exist'
            )

    # Create a temporary directory for the unzipped contents
    temp_dir = tempfile.mkdtemp(prefix='cookiecutter-', suffix='-unzip')

    try:
        # Get password if needed but not provided
        pwd = password
        if pwd is None:
            pwd = os.environ.get('COOKIECUTTER_REPO_PASSWORD')

        with ZipFile(zip_path) as zip_file:
            # Check if password protected
            if zip_file.namelist()[0].endswith('/'):
                base_dir = zip_file.namelist()[0]
            else:
                base_dir = os.path.commonprefix(zip_file.namelist()).rstrip('/')

            if not base_dir:
                raise InvalidZipRepository(
                    'CookieCutter templates must have a top level directory'
                )

            # Try to extract with given password
            try:
                zip_file.extractall(temp_dir, pwd=pwd.encode('utf-8') if pwd else None)
            except (RuntimeError, BadZipFile):
                # Try with a new password if extraction failed
                if not no_input:
                    pwd = read_repo_password('Zip is password protected. Please enter the password')
                    try:
                        zip_file.extractall(temp_dir, pwd=pwd.encode('utf-8') if pwd else None)
                    except (RuntimeError, BadZipFile) as e:
                        raise InvalidZipRepository(
                            'Invalid password provided for protected repository'
                        ) from e
                else:
                    raise InvalidZipRepository(
                        'Unable to extract zip file contents'
                    )

        # Check that the unzipped dir contains a cookiecutter.json
        dir_contents = os.listdir(os.path.join(temp_dir, base_dir))
        if 'cookiecutter.json' not in dir_contents:
            raise InvalidZipRepository(
                'Zip repository does not contain a cookiecutter.json file'
            )

        return os.path.join(temp_dir, base_dir)

    except (BadZipFile, RuntimeError) as e:
        raise InvalidZipRepository(
            'Invalid zip file, not a valid cookiecutter template'
        ) from e