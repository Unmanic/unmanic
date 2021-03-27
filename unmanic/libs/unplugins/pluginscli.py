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
import os
import inquirer

from unmanic import config
from unmanic.libs import unlogger, common
from unmanic.libs.plugins import PluginsHandler
from unmanic.libs.unplugins import PluginExecutor

menus = {
    "main":          [
        inquirer.List(
            'cli_action',
            message="What would you like to do?",
            choices=[
                'Test installed plugins',
                'List installed plugins',
                'Create new plugin',
                'Exit',
            ],
        ),
    ],
    "create_plugin": [
        inquirer.Text('plugin_name', message="What's the plugin's name"),
        inquirer.Text('plugin_id', message="What's the plugin's id"),
    ],
}


class BColours:
    HEADER = '\033[95m'
    SUBHEADER = '\033[94m'
    RESULTS = '\033[96m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    WARNING = '\033[93m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_table(table_data, col_list=None, sep='\uFFFA'):
    """
    Pretty print a list of dictionaries (myDict) as a dynamically sized table.
    If column names (col_list) aren't specified, they will show in random order.

    Author: Thierry Husson

    """
    if not col_list: col_list = list(table_data[0].keys() if table_data else [])
    my_list = [col_list]  # 1st row = header
    for item in table_data: my_list.append([str(item[col] or '') for col in col_list])
    col_size = [max(map(len, (sep.join(col)).split(sep))) for col in zip(*my_list)]
    format_str = ' | '.join(["{{:<{}}}".format(i) for i in col_size])
    line = format_str.replace(' | ', '-+-').format(*['-' * i for i in col_size])
    item = my_list.pop(0);
    line_done = False
    while my_list:
        if all(not i for i in item):
            item = my_list.pop(0)
            if line and (sep != '\uFFFA' or not line_done): print(line); line_done = True
        row = [i.split(sep, 1) for i in item]
        print(format_str.format(*[i[0] for i in row]))
        item = [i[1] if len(i) > 1 else '' for i in row]


class PluginsCLI(object):

    def __init__(self, plugins_directory=None):
        # Read settings
        self.settings = config.CONFIG()

        # Set plugins directory
        if not plugins_directory:
            plugins_directory = os.path.join(os.path.expanduser("~"), '.unmanic', 'plugins')
        self.plugins_directory = plugins_directory
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        unmanic_logging.disable_file_handler()
        self.logger = unmanic_logging.get_logger(__class__.__name__)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def create_new_plugins(self):
        plugin_details = inquirer.prompt(menus.get('create_plugin'))

        # Ensure results are not empty
        if not plugin_details.get('plugin_name') or not plugin_details.get('plugin_id'):
            print("ERROR! Invalid input.")
            return

        # TODO: Ensure plugin ID has only underscore and a-z, 0-9

        # Create new plugin path
        new_plugin_path = os.path.join(self.plugins_directory, plugin_details.get('plugin_id'))
        if not os.path.exists(new_plugin_path):
            os.makedirs(new_plugin_path)

        # Touch main python file
        main_python_file = os.path.join(new_plugin_path, 'plugin.py')
        plugin_template = [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            "",
            "from unmanic.libs.unplugins.settings import PluginSettings",
            "",
            "",
            "class Settings(PluginSettings):",
            "    settings = {}",
            "",
            ""
        ]
        if not os.path.exists(main_python_file):
            with open(main_python_file, 'a') as outfile:
                for plugin_template_line in plugin_template:
                    outfile.write("{}\n".format(plugin_template_line))

        common.touch(os.path.join(new_plugin_path, 'plugin.py'))
        # Create plugin info.json
        info_file = os.path.join(new_plugin_path, 'info.json')
        plugin_info = {
            "id":          plugin_details.get('plugin_id'),
            "name":        plugin_details.get('plugin_name'),
            "author":      "",
            "version":     "0.0.1",
            "tags":        "",
            "description": "",
            "icon":        ""
        }
        if not os.path.exists(info_file):
            with open(info_file, 'w') as outfile:
                json.dump(plugin_info, outfile, sort_keys=True, indent=4)

        # Insert plugin details to DB

        try:
            PluginsHandler.write_plugin_data_to_db(plugin_info, new_plugin_path)
        except Exception as e:
            print("Exception while saving plugin info to DB. - {}".format(str(e)))
            return

        print("Plugin created - '{}'".format((plugin_details.get('plugin_id'))))

    @staticmethod
    def list_installed_plugins():
        plugins = PluginsHandler()
        order = {
            "column": 'position',
            "dir":    'desc',
        }
        plugin_results = plugins.get_plugin_list_filtered_and_sorted(order=order, start=0, length=None)
        print_table(plugin_results)
        print()

    @staticmethod
    def test_installed_plugins():
        """
        Test all plugin runners for correct return data

        :return:
        """
        plugin_executor = PluginExecutor()

        plugins = PluginsHandler()
        order = {
            "column": 'position',
            "dir":    'desc',
        }
        plugin_results = plugins.get_plugin_list_filtered_and_sorted(order=order, start=0, length=None)
        for plugin_result in plugin_results:
            # plugin_runners = plugin_executor.get_plugin_runners('worker.process_item')
            print("{1}Testing plugin: '{0}'{2}".format(plugin_result.get("name"), BColours.HEADER, BColours.ENDC))
            plugin_id = plugin_result.get("plugin_id")

            # Test Plugin runners
            print("  {0}Testing runners{1}".format(BColours.SUBHEADER, BColours.ENDC))
            plugin_types_in_plugin = plugin_executor.get_all_plugin_types_in_plugin(plugin_id)
            if not plugin_types_in_plugin:
                error = "No runners found in plugin"
                print("    - {1}FAILED: {0}{2}".format(error, BColours.FAIL, BColours.ENDC))
            else:
                for plugin_type_in_plugin in plugin_types_in_plugin:
                    errors = plugin_executor.test_plugin_runner(plugin_id, plugin_type_in_plugin)
                    if errors:
                        for error in errors:
                            print("    - {1}FAILED: {0}{2}".format(error, BColours.FAIL, BColours.ENDC))
                    else:
                        print("    - {}PASSED{}".format(BColours.OKGREEN, BColours.ENDC))

            # Test Plugin settings
            print("  {0}Testing settings{1}".format(BColours.SUBHEADER, BColours.ENDC))
            errors, plugin_settings = plugin_executor.test_plugin_settings(plugin_id)
            if errors:
                for error in errors:
                    print("    - {1}FAILED: {0}{2}".format(error, BColours.FAIL, BColours.ENDC))
            else:
                formatted_plugin_settings = json.dumps(plugin_settings, indent=1)
                formatted_plugin_settings = formatted_plugin_settings.replace('\n', '\n' + '                    ')
                print("        - {1}Settings: {0}{2}".format(formatted_plugin_settings, BColours.RESULTS, BColours.ENDC))
                print("    - {}PASSED{}".format(BColours.OKGREEN, BColours.ENDC))
            print()

    def main(self, arg):
        switcher = {
            'Test installed plugins': 'test_installed_plugins',
            'List installed plugins': 'list_installed_plugins',
            'Create new plugin':      'create_new_plugins',
        }
        function = switcher.get(arg, None)
        if function:
            getattr(self, function)()
        else:
            self._log("Invalid selection")
            return

    def run(self):
        while True:
            selection = inquirer.prompt(menus.get('main'))
            self.main(selection.get('cli_action'))
            if selection.get('cli_action') == "Exit":
                break
