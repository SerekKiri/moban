"""
    moban.template
    ~~~~~~~~~~~~~~~~~~~

    Bring jinja2 to command line

    :copyright: (c) 2016 by Onni Software Ltd.
    :license: MIT License, see LICENSE for more details

"""

import os
import sys
import argparse

import yaml
from jinja2 import Environment, FileSystemLoader


PROGRAM_NAME = 'moban'
DEFAULT_YAML_SUFFIX = '.yml'
# .moban.yaml, default moban configuration file
DEFAULT_MOBAN_FILE = '.%s%s' % (PROGRAM_NAME, DEFAULT_YAML_SUFFIX)
LABEL_CONFIG = 'configuration'
LABEL_CONFIG_DIR = '%s_dir' % LABEL_CONFIG
LABEL_TEMPLATE = 'template'
LABEL_TMPL_DIRS = '%s_dir' % LABEL_TEMPLATE
LABEL_OVERRIDES = 'overrides'
LABEL_OUTPUT = 'output'
LABEL_TARGETS = 'targets'
DEFAULT_OPTIONS = {
    # .moban.cd, default configuration dir
    LABEL_CONFIG_DIR: os.path.join('.', '.%s.cd' % PROGRAM_NAME),
    # .moban.td, default template dirs
    LABEL_TMPL_DIRS: ['.', os.path.join('.', '.%s.td' % PROGRAM_NAME)],
    # moban.output, default output file name
    LABEL_OUTPUT: '%s.output' % PROGRAM_NAME,
    # data.yml, default data input file
    LABEL_CONFIG: 'data%s' % DEFAULT_YAML_SUFFIX
}


def main():
    """
    program entry point
    """
    parser = create_parser()
    if os.path.exists(DEFAULT_MOBAN_FILE):
        handle_moban_file(parser)
    else:
        handle_command_line(parser)


def create_parser():
    """
    construct the program options
    """
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        description="Yet another jinja2 cli command for static text generation")
    parser.add_argument(
        '-cd', '--%s' % LABEL_CONFIG_DIR,
        help="the directory for configuration file lookup"
    )
    parser.add_argument(
        '-c', '--%s' % LABEL_CONFIG,
        help="the dictionary file"
    )
    parser.add_argument(
        '-td', '--%s' % LABEL_TMPL_DIRS, nargs="*",
        help="the directories for template file lookup"
    )
    parser.add_argument(
        '-t', '--%s' % LABEL_TEMPLATE,
        help="the template file"
    )
    parser.add_argument(
        '-o', '--output',
        help="the output file"
    )
    return parser


def handle_moban_file(parser):
    """
    act upon default moban file
    """
    options = {}
    if len(sys.argv) > 1:
        options = vars(parser.parse_args())
    more_options = open_yaml(None, DEFAULT_MOBAN_FILE)
    if more_options is None:
        print("%s is an invalid yaml file." % DEFAULT_MOBAN_FILE)
        parser.print_help()
        sys.exit(-1)
    if LABEL_TARGETS not in more_options:
        print("No targets in %s" % DEFAULT_MOBAN_FILE)
        sys.exit(0)
    if LABEL_CONFIG in more_options:
        options = merge(options, more_options[LABEL_CONFIG])
    options = merge(options, DEFAULT_OPTIONS)
    data = open_yaml(options[LABEL_CONFIG_DIR],
                     options[LABEL_CONFIG])
    jobs = []
    for target in more_options[LABEL_TARGETS]:
        for key, value in target.items():
            jobs.append((value, key))
    do_template(options[LABEL_TMPL_DIRS], data, jobs)


def handle_command_line(parser):
    """
    act upon command options
    """
    options = vars(parser.parse_args())
    options = merge(options, DEFAULT_OPTIONS)
    if options[LABEL_TEMPLATE] is None:
        print("No template found")
        parser.print_help()
        sys.exit(-1)
    data = open_yaml(options[LABEL_CONFIG_DIR],
                     options[LABEL_CONFIG])
    do_template(options[LABEL_TMPL_DIRS],
                data,
                [(options[LABEL_TEMPLATE], options[LABEL_OUTPUT])])


def merge(left, right):
    """
    deep merge dictionary on the left with the one
    on the right.

    Fill in left dictionary with right one where
    the value of the key from the right one in
    the left one is missing or None.
    """
    if isinstance(left, dict) and isinstance(right, dict):
        for key, value in right.items():
            if key not in left:
                left[key] = value
            elif left[key] is None:
                left[key] = value
            else:
                left[key] = merge(left[key], value)
    return left


def open_yaml(base_dir, file_name):
    """
    chained yaml loader
    """
    the_file = file_name
    if not os.path.exists(the_file):
        if base_dir:
            the_file = os.path.join(base_dir, file_name)
            if not os.path.exists(the_file):
                raise IOError("Both %s and %s does not exist" % (file_name,
                                                                 the_file))
        else:
            raise IOError("File %s does not exist" % the_file)
    with open(the_file, 'r') as data_yaml:
        data = yaml.load(data_yaml)
        if data is not None:
            parent_data = None
            if LABEL_OVERRIDES in data:
                parent_data = open_yaml(base_dir,
                                        data.pop(LABEL_OVERRIDES))
            if parent_data:
                return merge(data, parent_data)
            else:
                return data
        else:
            return None


def do_template(template_dirs, data, jobs):
    """
    apply jinja2 here

    :param template_dirs: a list of template directories
    :param data: data configuration
    :param jobs: a list of jobs
    """
    template_loader = FileSystemLoader(template_dirs)
    env = Environment(loader=template_loader,
                      trim_blocks=True,
                      lstrip_blocks=True)
    for (template_file, output) in jobs:
        print("Templating %s to %s" % (template_file, output))
        template = env.get_template(template_file)
        with open(output, 'w') as output_file:
            content = template.render(**data)
            output_file.write(content)
