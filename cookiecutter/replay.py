"""
cookiecutter.replay.

-------------------
"""
import json
import os
from cookiecutter.utils import make_sure_path_exists

def get_file_name(replay_dir, template_name):
    """Get the name of file.

    :param replay_dir: Directory where the replay file will be written.
    :param template_name: Name of the template.
    :returns: Name of the file.
    """
    file_name = template_name.split('/')[-1]
    if not file_name.endswith('.json'):
        file_name = f'{file_name}.json'
    return os.path.join(replay_dir, file_name)

def dump(replay_dir: 'os.PathLike[str]', template_name: str, context: dict):
    """Write json data to file.

    :param replay_dir: Directory where the replay file will be written.
    :param template_name: Name of the template.
    :param context: Context dictionary to be dumped.
    :raises: TypeError if template_name is not a string
             TypeError if context is not a dict
             ValueError if context is empty
             OSError if replay_dir cannot be created
    """
    if not isinstance(template_name, str):
        raise TypeError('Template name is required to be of type str')
    if not isinstance(context, dict):
        raise TypeError('Context is required to be of type dict')
    if not context:
        raise ValueError('Context is required to not be empty')

    make_sure_path_exists(replay_dir)

    replay_file = get_file_name(replay_dir, template_name)
    with open(replay_file, 'w', encoding='utf-8') as f:
        json.dump(context, f, indent=2)

def load(replay_dir, template_name):
    """Read json data from file.

    :param replay_dir: Directory where the replay file is located.
    :param template_name: Name of the template.
    :raises: TypeError if template_name is not a string
             ValueError if context is empty
             IOError if replay file does not exist
    :returns: Context dictionary from the replay file.
    """
    if not isinstance(template_name, str):
        raise TypeError('Template name is required to be of type str')

    replay_file = get_file_name(replay_dir, template_name)
    if not os.path.exists(replay_file):
        raise IOError(f'No replay file found at {replay_file}')

    with open(replay_file, encoding='utf-8') as f:
        context = json.load(f)

    if not context:
        raise ValueError('Context is required to not be empty')

    return context