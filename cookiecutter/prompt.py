"""Functions for prompting the user for project info."""
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path
from jinja2.exceptions import UndefinedError
from rich.prompt import Confirm, InvalidResponse, Prompt, PromptBase
from cookiecutter.exceptions import UndefinedVariableInTemplate
from cookiecutter.utils import create_env_with_context, rmtree

def read_user_variable(var_name, default_value, prompts=None, prefix=''):
    """Prompt user for variable and return the entered value or given default.

    :param str var_name: Variable of the context to query the user
    :param default_value: Value that will be returned if no input happens
    :param prompts: Optional dict with custom prompts for variables
    :param prefix: Optional prefix to use for variable prompts
    :returns: User's input or default value
    """
    if prompts is None:
        prompts = {}

    prompt_text = prompts.get(var_name, f'{prefix}{var_name}')
    return Prompt.ask(prompt_text, default=default_value)

class YesNoPrompt(Confirm):
    """A prompt that returns a boolean for yes/no questions."""
    yes_choices = ['1', 'true', 't', 'yes', 'y', 'on']
    no_choices = ['0', 'false', 'f', 'no', 'n', 'off']

    def process_response(self, value: str) -> bool:
        """Convert choices to a bool."""
        value = value.lower()
        if value in self.yes_choices:
            return True
        if value in self.no_choices:
            return False
        raise InvalidResponse(self.validate_error_message)

def read_user_yes_no(var_name, default_value, prompts=None, prefix=''):
    """Prompt the user to reply with 'yes' or 'no' (or equivalent values).

    - These input values will be converted to ``True``:
      "1", "true", "t", "yes", "y", "on"
    - These input values will be converted to ``False``:
      "0", "false", "f", "no", "n", "off"

    :param str var_name: Variable as specified in the context
    :param default_value: Value that will be returned if no input happens
    :param prompts: Optional dict with custom prompts for variables
    :param prefix: Optional prefix to use for variable prompts
    :returns: User's boolean choice
    """
    if prompts is None:
        prompts = {}

    prompt_text = prompts.get(var_name, f'{prefix}{var_name}')
    return YesNoPrompt.ask(prompt_text, default=default_value)

def read_repo_password(question):
    """Prompt the user to enter a password.

    :param str question: Question to the user
    :returns: The entered password
    """
    return Prompt.ask(question, password=True)

def read_user_choice(var_name, options, prompts=None, prefix=''):
    """Prompt the user to choose from several options for the given variable.

    The first item will be returned if no input happens.

    :param str var_name: Variable as specified in the context
    :param list options: Sequence of options that are available to select from
    :param prompts: Optional dict with custom prompts for variables
    :param prefix: Optional prefix to use for variable prompts
    :return: Exactly one item of ``options`` that has been chosen by the user
    """
    if not options:
        raise ValueError('Options list must not be empty')

    if prompts is None:
        prompts = {}

    prompt_text = prompts.get(var_name, f'{prefix}{var_name}')
    choices = [str(i) for i in range(len(options))]
    choice_map = dict(zip(choices, options))

    choice_lines = [f'{i}) {opt}' for i, opt in enumerate(options)]
    choice_text = '\n'.join(choice_lines)
    prompt_text = f'{prompt_text}\n{choice_text}\nChoose from {min(choices)} to {max(choices)}'

    choice = Prompt.ask(prompt_text, choices=choices, default='0')
    return choice_map[choice]

DEFAULT_DISPLAY = 'default'

def process_json(user_value, default_value=None):
    """Load user-supplied value as a JSON dict.

    :param str user_value: User-supplied value to load as a JSON dict
    :param default_value: Value to return if parsing fails
    :returns: The parsed JSON dict or default value
    """
    try:
        user_dict = json.loads(user_value, object_pairs_hook=OrderedDict)
        return user_dict
    except Exception:
        return default_value

class JsonPrompt(PromptBase[dict]):
    """A prompt that returns a dict from JSON string."""
    default = None
    response_type = dict
    validate_error_message = '[prompt.invalid]  Please enter a valid JSON string'

    def process_response(self, value: str) -> dict:
        """Convert choices to a dict."""
        try:
            return json.loads(value, object_pairs_hook=OrderedDict)
        except Exception:
            raise InvalidResponse(self.validate_error_message)

def read_user_dict(var_name, default_value, prompts=None, prefix=''):
    """Prompt the user to provide a dictionary of data.

    :param str var_name: Variable as specified in the context
    :param default_value: Value that will be returned if no input is provided
    :param prompts: Optional dict with custom prompts for variables
    :param prefix: Optional prefix to use for variable prompts
    :return: A Python dictionary to use in the context.
    """
    if prompts is None:
        prompts = {}

    prompt_text = prompts.get(var_name, f'{prefix}{var_name}')
    return JsonPrompt.ask(prompt_text, default=json.dumps(default_value))

def render_variable(env, raw, cookiecutter_dict):
    """Render the next variable to be displayed in the user prompt.

    Inside the prompting taken from the cookiecutter.json file, this renders
    the next variable. For example, if a project_name is "Peanut Butter
    Cookie", the repo_name could be be rendered with:

        `{{ cookiecutter.project_name.replace(" ", "_") }}`.

    This is then presented to the user as the default.

    :param Environment env: A Jinja2 Environment object.
    :param raw: The next value to be prompted for by the user.
    :param dict cookiecutter_dict: The current context as it's gradually
        being populated with variables.
    :return: The rendered value for the default variable.
    """
    if not isinstance(raw, str):
        return raw

    template = env.from_string(raw)
    rendered = template.render(**cookiecutter_dict)

    return rendered

def _prompts_from_options(options: dict) -> dict:
    """Process template options and return friendly prompt information."""
    prompts = {}
    for key, raw in options.items():
        if not isinstance(raw, dict):
            continue

        display = raw.get('_display', DEFAULT_DISPLAY)
        if not isinstance(display, str):
            continue

        prompts[key] = display

    return prompts

def prompt_choice_for_template(key, options, no_input):
    """Prompt user with a set of options to choose from.

    :param key: Key name for the choice
    :param options: Available choices
    :param no_input: Do not prompt for user input and return the first available option.
    :returns: The selected choice
    """
    if no_input:
        return next(iter(options.values()))

    choices = []
    display = []
    for opt_key, opt_val in options.items():
        choices.append(opt_key)
        if isinstance(opt_val, dict):
            opt_display = opt_val.get('_display', DEFAULT_DISPLAY)
            display.append(f'{opt_key} - {opt_display}')
        else:
            display.append(opt_key)

    prompt_text = f'{key}\n' + '\n'.join(display)
    choice = Prompt.ask(prompt_text, choices=choices, default=choices[0])
    return options[choice]

def prompt_choice_for_config(cookiecutter_dict, env, key, options, no_input, prompts=None, prefix=''):
    """Prompt user with a set of options to choose from.

    :param cookiecutter_dict: Dict to use for rendering options
    :param env: Jinja2 Environment for rendering
    :param key: Key name for the choice
    :param options: Available choices
    :param no_input: Do not prompt for user input and return the first available option.
    :param prompts: Optional dict with custom prompts for variables
    :param prefix: Optional prefix to use for variable prompts
    :returns: The selected choice
    """
    rendered_options = [render_variable(env, opt, cookiecutter_dict) for opt in options]
    return read_user_choice(key, rendered_options, prompts=prompts, prefix=prefix)

def prompt_for_config(context, no_input=False):
    """Prompt user to enter a new config.

    :param dict context: Source for field names and sample values.
    :param no_input: Do not prompt for user input and use only values from context.
    :returns: A new config dict with user's responses
    """
    cookiecutter_dict = context['cookiecutter']
    env = create_env_with_context(context)
    prompts = _prompts_from_options(cookiecutter_dict)

    for key, raw in cookiecutter_dict.items():
        if key.startswith('_'):
            cookiecutter_dict[key] = raw
            continue

        try:
            if isinstance(raw, list):
                # Choice field
                val = prompt_choice_for_config(
                    cookiecutter_dict, env, key, raw,
                    no_input, prompts
                )
            elif isinstance(raw, bool):
                # Boolean field
                val = read_user_yes_no(
                    key, raw,
                    prompts=prompts
                ) if not no_input else raw
            elif isinstance(raw, dict):
                # Dict field
                val = read_user_dict(
                    key, raw,
                    prompts=prompts
                ) if not no_input else raw
            else:
                # String field
                val = render_variable(env, raw, cookiecutter_dict)
                if not no_input:
                    val = read_user_variable(
                        key, val,
                        prompts=prompts
                    )
            cookiecutter_dict[key] = val
        except UndefinedError as err:
            msg = f"Unable to render variable '{key}': {err.message}"
            raise UndefinedVariableInTemplate(msg, err.message, context, key)

    return context

def choose_nested_template(context: dict, repo_dir: str, no_input: bool=False) -> str:
    """Prompt user to select the nested template to use.

    :param context: Source for field names and sample values.
    :param repo_dir: Repository directory.
    :param no_input: Do not prompt for user input and use only values from context.
    :returns: Path to the selected template.
    """
    cookiecutter_dict = context['cookiecutter']
    if '_template' not in cookiecutter_dict:
        return context

    template_dir = cookiecutter_dict['_template']
    if not isinstance(template_dir, dict):
        return context

    template_path = prompt_choice_for_template('_template', template_dir, no_input)
    if not isinstance(template_path, str):
        return context

    cookiecutter_dict['_template'] = template_path
    return context

def prompt_and_delete(path, no_input=False):
    """
    Ask user if it's okay to delete the previously-downloaded file/directory.

    If yes, delete it. If no, checks to see if the old version should be
    reused. If yes, it's reused; otherwise, Cookiecutter exits.

    :param path: Previously downloaded zipfile.
    :param no_input: Suppress prompt to delete repo and just delete it.
    :return: True if the content was deleted
    """
    if no_input:
        rmtree(path)
        return True

    ok_to_delete = YesNoPrompt.ask(
        f'You have downloaded {path} before. Is it okay to delete and re-download it?',
        default=True
    )

    if ok_to_delete:
        rmtree(path)
        return True

    ok_to_reuse = YesNoPrompt.ask(
        'Do you want to re-use the existing version?',
        default=True
    )

    if ok_to_reuse:
        return False

    sys.exit()