#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.pluginscli.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     15 Mar 2021, (12:05 PM)

    Copyright:
           Copyright (C) Josh Sunnex - All Rights Reserved

           Permission is hereby granted, free of charge, to any person obtaining a copy
           of this software and associated documentation files (the "Software"), to deal
           in the Software without restriction, including without limitation the rights
           to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
           copies of the Software, and to permit persons to whom the Software is
           furnished to do so, subject to the following conditions:

           The above copyright notice and this permission notice shall be included in all
           copies or substantial portions of the Software.

           THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""
import json
import logging
import os
import re
import shutil
import subprocess

import inquirer
import requests

from . import plugin_types

from unmanic import config
from unmanic.libs import unlogger, common
from unmanic.libs.plugins import PluginsHandler
from unmanic.libs.unplugins import PluginExecutor

home_directory = common.get_home_dir()
dev_cache_directory = os.path.join(home_directory, '.unmanic', 'dev', 'cache')
dev_library_directory = os.path.join(home_directory, '.unmanic', 'dev', 'library')

menus = {
    "main":          [
        inquirer.List(
            'cli_action',
            message="What would you like to do?",
            choices=[
                'List all installed plugins',
                'Test plugins',
                'Create new plugin',
                'Reload all plugins from disk',
                'Remove plugin',
                'Install test data',
                'Exit',
            ],
        ),
    ],
    "create_plugin": [
        inquirer.Text('plugin_id', message="What's the plugin's id"),
        inquirer.Text('plugin_name', message="What's the plugin's name"),
    ],
}


class BColours:
    HEADER = '\033[44m'
    SUBHEADER = '\033[94m'
    SECTION = '\033[96m'
    RESULTS = '\033[39m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    WARNING = '\033[93m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_table(table_data, col_list=None, sep='\uFFFA', max_col_width=9):
    """
    Pretty print a list of dictionaries (myDict) as a dynamically sized table.
    If column names (col_list) aren't specified, they will show in random order.

    Author: Thierry Husson

    """
    if not col_list:
        col_list = list(table_data[0].keys() if table_data else [])
    my_list = [col_list]  # 1st row = header
    for item in table_data:
        my_list.append([str(item[col] or '') for col in col_list])
    original_col_size = [max(map(len, (sep.join(col)).split(sep))) for col in zip(*my_list)]
    col_size = []
    for col in original_col_size:
        if col > max_col_width:
            col = max_col_width
        col_size.append(col)
    format_str = ' | '.join(["{{:<{}}}".format(i) for i in col_size])
    line = format_str.replace(' | ', '-+-').format(*['-' * i for i in col_size])
    item = my_list.pop(0)
    line_done = False
    while my_list:
        if all(not i for i in item):
            item = my_list.pop(0)
            if line and (sep != '\uFFFA' or not line_done):
                print(line)
                line_done = True
        row = [i[:max_col_width].split(sep, 1) for i in item]
        print(format_str.format(*[i[0] for i in row]))
        item = [i[1] if len(i) > 1 else '' for i in row]


def install_npm_modules(plugin_path):
    package_file = os.path.join(plugin_path, 'package.json')
    if not os.path.exists(package_file):
        return
    subprocess.call(['npm', 'install'], cwd=plugin_path)
    subprocess.call(['npm', 'run', 'build'], cwd=plugin_path)


def install_plugin_requirements(plugin_path):
    requirements_file = os.path.join(plugin_path, 'requirements.txt')
    install_target = os.path.join(plugin_path, 'site-packages')
    if not os.path.exists(requirements_file):
        return
    import pip
    pip.main(['install', '--upgrade', '-r', requirements_file, '--target={}'.format(install_target)])


class PluginsCLI(object):

    def __init__(self, plugins_directory=None):
        # Read settings
        self.settings = config.Config()

        # Set plugins directory
        if not plugins_directory:
            home_directory = common.get_home_dir()
            plugins_directory = os.path.join(home_directory, '.unmanic', 'plugins')
        self.plugins_directory = plugins_directory
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        unmanic_logging.disable_file_handler(debugging=True)
        unmanic_logging.stream_handler.setFormatter(
            logging.Formatter(
                '        - {}%(asctime)s:%(levelname)s:%(name)s - %(message)s{}'.format(BColours.RESULTS, BColours.ENDC),
                datefmt='%Y-%m-%dT%H:%M:%S'
            )
        )
        unmanic_logging.enable_debugging()
        self.logger = unmanic_logging.get_logger(__class__.__name__)

        self.test_data_modifiers = {
            "{cache_path}":    dev_cache_directory,
            "{library_path}":  dev_library_directory,
            "{test_file_in}":  "Big_Buck_Bunny_1080_10s_30MB_h264.mkv",
            "{test_file_out}": "Big_Buck_Bunny_1080_10s_30MB_h264-1616571944.7296877-WORKING-1.mkv"
        }

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def create_new_plugins(self):
        plugin_details = inquirer.prompt(menus.get('create_plugin'))

        # Ensure results are not empty
        if not plugin_details.get('plugin_name') or not plugin_details.get('plugin_id'):
            print("ERROR! Invalid input.")
            return

        # Ensure plugin ID has only underscore and a-z, 0-9
        plugin_details['plugin_id'] = re.sub('[^0-9a-zA-Z]+', '_', plugin_details.get('plugin_id'))
        # Ensure plugin ID is lower case
        plugin_details['plugin_id'] = plugin_details.get('plugin_id').lower()

        # Get list of plugin types
        all_plugin_types = plugin_types.get_all_plugin_types()

        # Build choice selection list from installed plugins
        plugin_details_by_runner = {}
        choices = []
        for plugin_type in all_plugin_types:
            choices.append(all_plugin_types[plugin_type].get('name'))
            plugin_details_by_runner[all_plugin_types[plugin_type].get('name')] = all_plugin_types[plugin_type]

        # Generate menu menu
        print()
        print('INFO: https://docs.unmanic.app/docs/plugins/writing_plugins/plugin_runner_types')
        plugin_runners_inquirer = inquirer.List(
            'selected_plugin',
            message="Which Plugin runner will be used?",
            choices=choices,
        )

        # Prompt for selection of Plugin by ID
        runner_selection = inquirer.prompt([plugin_runners_inquirer])

        # Fetch plugin type details from selection
        plugin_type_details = plugin_details_by_runner[runner_selection.get('selected_plugin')]
        selected_plugin_runner = plugin_type_details.get('runner')
        selected_plugin_runner_docstring = plugin_type_details.get('runner_docstring')

        # Create new plugin path
        new_plugin_path = os.path.join(self.plugins_directory, plugin_details.get('plugin_id'))
        if not os.path.exists(new_plugin_path):
            os.makedirs(new_plugin_path)

        # Create main python file template
        main_plugin_template = [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            "",
            "import logging",
            "",
            "from unmanic.libs.unplugins.settings import PluginSettings",
            "",
            "# Configure plugin logger",
            "logger = logging.getLogger(\"Unmanic.Plugin.{}\")".format(plugin_details.get('plugin_id')),
            "",
            "",
            "class Settings(PluginSettings):",
            "    settings = {}",
            "",
            "    def __init__(self, *args, **kwargs):",
            "        super(Settings, self).__init__(*args, **kwargs)",
            "",
            "",
        ]

        # Create runner function template
        runner_template = [
            'def {}(data):'.format(selected_plugin_runner),
            '    """{}'.format(selected_plugin_runner_docstring),
            '    """',
            '    return',
        ]

        # Write above templates to main python file
        main_python_file = os.path.join(new_plugin_path, 'plugin.py')
        if not os.path.exists(main_python_file):
            with open(main_python_file, 'a') as outfile:
                # Write out main template
                for template_line in main_plugin_template:
                    outfile.write("{}\n".format(template_line))
                # Write out runner function template
                for template_line in runner_template:
                    outfile.write("{}\n".format(template_line))

        # Write plugin info.json
        info_file = os.path.join(new_plugin_path, 'info.json')
        plugin_info = {
            "id":            plugin_details.get('plugin_id'),
            "name":          plugin_details.get('plugin_name'),
            "author":        "",
            "version":       "0.0.1",
            "tags":          "",
            "description":   "",
            "icon":          "",
            "priorities":    {
                selected_plugin_runner: 0
            },
            "compatibility": [PluginsHandler.version]
        }
        if not os.path.exists(info_file):
            with open(info_file, 'w') as outfile:
                json.dump(plugin_info, outfile, sort_keys=True, indent=4)

        # Create requirements.txt file
        common.touch(os.path.join(new_plugin_path, 'requirements.txt'))

        # Create Plugin .gitignore
        plugin_gitignore = os.path.join(new_plugin_path, '.gitignore')
        gitignore_template = [
            '**/__pycache__',
            '*.py[cod]',
            '**/site-packages',
            'settings.json',
        ]
        if not os.path.exists(plugin_gitignore):
            with open(plugin_gitignore, 'a') as outfile:
                for template_line in gitignore_template:
                    outfile.write("{}\n".format(template_line))

        # Insert plugin details to DB
        try:
            plugin_info['plugin_id'] = plugin_info.get('id')
            PluginsHandler.write_plugin_data_to_db(plugin_info, new_plugin_path)
        except Exception as e:
            print("Exception while saving plugin info to DB. - {}".format(str(e)))
            return

        print("Plugin created - '{}'".format((plugin_details.get('plugin_id'))))

    def reload_plugin_from_disk(self):
        # Fetch list of installed plugins
        plugin_results = self.__get_installed_plugins()

        # Build choice selection list from installed plugins
        for plugin in plugin_results:
            print("Reloading Plugin - '{}'".format(plugin.get('plugin_id')))
            plugin_path = os.path.join(self.plugins_directory, plugin.get('plugin_id'))
            # Read plugin info.json
            info_file = os.path.join(plugin_path, 'info.json')
            with open(info_file) as json_file:
                plugin_info = json.load(json_file)

            # Insert plugin details to DB
            try:
                plugin_info['plugin_id'] = plugin_info.get('id')
                PluginsHandler.write_plugin_data_to_db(plugin_info, plugin_path)
            except Exception as e:
                print("Exception while saving plugin info to DB. - {}".format(str(e)))
                return

            install_plugin_requirements(plugin_path)
            install_npm_modules(plugin_path)
            print()
        print()

    def remove_plugin(self):
        # Fetch list of installed plugins
        plugin_results = self.__get_installed_plugins()

        # Build choice selection list from installed plugins
        table_ids = {}
        choices = []
        for plugin in plugin_results:
            choices.append(plugin.get('plugin_id'))
            table_ids[plugin.get('plugin_id')] = plugin.get('id')
        # Append a "return" option
        choices.append('Go Back')

        # Generate menu menu
        remove_plugin_inquirer = inquirer.List(
            'cli_action',
            message="Which Plugin would you like to remove?",
            choices=choices,
        )

        # Prompt for selection of Plugin by ID
        selection = inquirer.prompt([remove_plugin_inquirer])

        # If the 'Go Back' option was given, just return to previous menu
        if not selection or selection.get('cli_action') == "Go Back":
            return

        # Remove the selected Plugin by ID
        plugin_table_id = table_ids[selection.get('cli_action')]
        plugins = PluginsHandler()
        plugins.uninstall_plugins_by_db_table_id([plugin_table_id])
        print()

    def list_installed_plugins(self):
        plugin_results = self.__get_installed_plugins()
        print_table(plugin_results)
        print()
        print()

    @staticmethod
    def __get_installed_plugins(plugin_id=None):
        plugins = PluginsHandler()
        order = [
            {
                "column": 'plugin_id',
                "dir":    'asc',
            },
        ]
        if plugin_id:
            return plugins.get_plugin_list_filtered_and_sorted(order=order, start=0, length=None, plugin_id=plugin_id)
        return plugins.get_plugin_list_filtered_and_sorted(order=order, start=0, length=None)

    def test_installed_plugins(self, plugin_id=None):
        """
        Test all plugin runners for correct return data.
        If plugin_id is provided, only the matching plugin will be tested.

        :param plugin_id:
        :return:
        """
        plugin_executor = PluginExecutor()

        plugin_results = self.__get_installed_plugins(plugin_id=plugin_id)
        for plugin_result in plugin_results:
            # plugin_runners = plugin_executor.get_plugin_runners('worker.process_item')
            print("{1}Testing plugin: '{0}'{2}".format(plugin_result.get("name"), BColours.HEADER, BColours.ENDC))
            plugin_id = plugin_result.get("plugin_id")

            # Reload the plugin
            plugin_executor.reload_plugin_module(plugin_id)

            # Test Plugin runners
            print("  {0}Testing runners{1}".format(BColours.SUBHEADER, BColours.ENDC))
            plugin_types_in_plugin = plugin_executor.get_all_plugin_types_in_plugin(plugin_id)
            if not plugin_types_in_plugin:
                error = "No runners found in plugin"
                print("  -- {1}FAILED: {0}{2}".format(error, BColours.FAIL, BColours.ENDC))
                print()
            else:
                for plugin_type_in_plugin in plugin_types_in_plugin:
                    print("    {1}{0}{2}".format(plugin_type_in_plugin, BColours.SECTION, BColours.ENDC))
                    errors = plugin_executor.test_plugin_runner(plugin_id, plugin_type_in_plugin,
                                                                test_data_modifiers=self.test_data_modifiers)
                    if errors:
                        for error in errors:
                            print("        -- {1}FAILED: {0}{2}".format(error, BColours.FAIL, BColours.ENDC))
                    else:
                        print("        -- {}PASSED{} --".format(BColours.OKGREEN, BColours.ENDC))
                    print()

            # Test Plugin settings
            print("  {0}Testing settings{1}".format(BColours.SUBHEADER, BColours.ENDC))
            errors, plugin_settings = plugin_executor.test_plugin_settings(plugin_id)
            print("    {}Plugin settings schema{}".format(BColours.SECTION, BColours.ENDC))
            if errors:
                for error in errors:
                    print("        -- {1}FAILED: {0}{2}".format(error, BColours.FAIL, BColours.ENDC))
            else:
                formatted_plugin_settings = json.dumps(plugin_settings, indent=1)
                formatted_plugin_settings = formatted_plugin_settings.replace('\n', '\n' + '                    ')
                print("        - {1}Settings: {0}{2}".format(formatted_plugin_settings, BColours.RESULTS, BColours.ENDC))
                print("        -- {}PASSED{} --".format(BColours.OKGREEN, BColours.ENDC))
            print()
            print()

    def test_plugins(self):
        plugin_results = self.__get_installed_plugins()

        # Generate menu choices
        all_plugin_details = {}
        choices = ["Configure Testdata", "Test All Plugins"]
        for plugin_details in plugin_results:
            choices.append(plugin_details.get('plugin_id'))
            all_plugin_details[plugin_details.get('plugin_id')] = plugin_details
        choices.append("Go Back")

        print()
        default_selection = None
        while True:
            plugin_test_inquirer = inquirer.List(
                'selected_plugin',
                message="Which plugin would you like to test?",
                choices=choices,
                default=default_selection,
            )
            selection = inquirer.prompt([plugin_test_inquirer])

            # If the 'Go Back' option was given, just return to previous menu
            if not selection or selection.get('selected_plugin') == "Go Back":
                return

            # Configure test file
            if selection.get('selected_plugin') == "Configure Testdata":
                self.configure_test_data()
                continue

            # If 'Test All Plugins' was selected, then run tests against all plugins
            if selection.get('selected_plugin') == "Test All Plugins":
                self.test_installed_plugins()
                continue

            # Get the details for the selected plugin
            selected_plugin_details = all_plugin_details[selection.get('selected_plugin')]
            # Set that selection as the default for the next time
            default_selection = selection.get('selected_plugin')
            # Test that plugin
            self.test_installed_plugins(plugin_id=selected_plugin_details.get('plugin_id'))

    def configure_test_data(self):

        test_files = []
        for (dir_path, dir_names, file_names) in os.walk(dev_library_directory):
            test_files.extend(file_names)
        print(test_files)

        # Update test file
        print()
        print()
        test_files_inquirer = inquirer.List(
            'selected_file',
            message="Which Plugin runner will be used?",
            choices=test_files,
        )
        runner_selection = {}
        runner_selection = {
            **inquirer.prompt([test_files_inquirer]),
            **runner_selection
        }
        self.test_data_modifiers['{test_file_in}'] = runner_selection.get('selected_file')
        split_file_in = os.path.splitext(runner_selection.get('selected_file'))
        self.test_data_modifiers['{test_file_out}'] = "{}-{}{}".format(split_file_in[0], "WORKING-1", split_file_in[1])

    def install_test_data(self):
        sample_files = {
            "Big_Buck_Bunny_1080_10s_30MB_h264.mkv": "https://test-videos.co.uk/vids/bigbuckbunny/mkv/1080/Big_Buck_Bunny_1080_10s_30MB.mkv",
            "Big_Buck_Bunny_1080_10s_30MB_h264.mp4": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/1080/Big_Buck_Bunny_1080_10s_30MB.mp4",
            "Big_Buck_Bunny_1080_10s_30MB_av1.mp4":  "https://test-videos.co.uk/vids/bigbuckbunny/mp4/av1/1080/Big_Buck_Bunny_1080_10s_30MB.mp4",
            "sample-12s.mp3":                        "https://download.samplelib.com/mp3/sample-12s.mp3",
        }
        if not os.path.exists(dev_cache_directory):
            os.makedirs(dev_cache_directory)
        if not os.path.exists(dev_library_directory):
            os.makedirs(dev_library_directory)
        for key in sample_files:
            library_file = os.path.join(dev_library_directory, key)
            file_url = sample_files.get(key)
            print()
            print("Downloading sample file: '{}'".format(file_url))
            with requests.get(file_url, stream=True) as r:
                r.raise_for_status()
                with open(library_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=None):
                        if chunk:
                            f.write(chunk)

            split_file_in = os.path.splitext(key)
            cache_file = os.path.join(dev_cache_directory, "{}-{}{}".format(split_file_in[0], "WORKING-1", split_file_in[1]))
            shutil.copyfile(library_file, cache_file)

    def main(self, arg):
        switcher = {
            'List all installed plugins':   'list_installed_plugins',
            'Test plugins':                 'test_plugins',
            'Create new plugin':            'create_new_plugins',
            'Reload all plugins from disk': 'reload_plugin_from_disk',
            'Remove plugin':                'remove_plugin',
            'Install test data':            'install_test_data',
        }
        function = switcher.get(arg, None)
        if function:
            getattr(self, function)()
        else:
            self._log("Invalid selection")
            return

    def run(self):
        print()
        while True:
            selection = inquirer.prompt(menus.get('main'))
            if not selection or selection.get('cli_action') == "Exit":
                break
            self.main(selection.get('cli_action'))
