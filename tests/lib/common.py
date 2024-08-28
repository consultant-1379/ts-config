#!/usr/bin/env python
import yaml
import os
from subprocess import CalledProcessError, STDOUT, check_output
from jsonschema import Draft4Validator, validators, FormatChecker



def run_cmd(cmd, shell=True, **kwargs):
    try:
        return check_output(cmd, shell=shell, stderr=STDOUT, text=True, **kwargs).rstrip()
    except CalledProcessError as err:
        raise Exception(f"{cmd} failed with: [{err.output.rstrip()}]")


def load_yaml_file(yaml_file):
    try:
        with open(yaml_file) as file:
            return yaml.safe_load(file)
    except Exception as e:
        raise RuntimeError(f'Loading yaml file {yaml_file} error: {e}')


def dump_yaml_file(content, yaml_file):
    with open(yaml_file, 'w') as f:
        yaml.dump(content, f, sort_keys=False)


def read_file(file_path):
    with open(file_path, 'r') as f:
        content = f.readlines()
    return content


def write_file(content, file_path):
    with open(file_path, 'w') as f:
        f.writelines(content)


def extend_with_default(validator_class):
    """Support function to JSON schema validator. Parameters with a
    default value are added if missing completely from configuration.
    """
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for prop, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(prop, subschema["default"])
        for error in validate_properties(validator, properties,
                instance, schema):
            yield error

    return validators.extend(
        validator_class, {"properties": set_defaults})


def valid_resource(resource_content, schema_path, yml, debug=False):
    if resource_content is None:
        raise Exception(f"Config file {yml} is empty")
    schema = load_yaml_file(schema_path)
    Draft4Validator.META_SCHEMA['definitions']['simpleTypes']['enum'].append('file')
    checker = Draft4Validator.TYPE_CHECKER.redefine("file", lambda _, value: os.path.isfile(value))
    fileValidator = validators.extend(Draft4Validator, type_checker=checker)
    DefaultValidatingDraft4Validator = extend_with_default(fileValidator)
    validator = DefaultValidatingDraft4Validator(
            schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(resource_content),
                    key=lambda e: e.path)
    if errors:
        error_message = ''
        for error in errors:
            error_path = list(error.path)
            if len(error_path) == 0:
                msg = f"Invalid configuration: {error.message}"
                error_message += (msg+'\n')
            else:
                formatted_path = error_path[0]
                for x in error_path[1:]:
                    if isinstance(x, int):
                        formatted_path += "[%d]" % x
                    else:
                        formatted_path += "." + x
                msg = f"Invalid configuration of {formatted_path}: {error.message}"
                error_message += (msg+'\n')
        raise Exception(f"Failed to validate yaml file {yml}. \n{error_message}")
    debug and print("Validated yaml config successfully.")
