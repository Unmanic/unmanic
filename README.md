Unmanic - Library Optimiser  
===========================

![UNMANIC - Library Optimiser](https://github.com/unmanic/unmanic/raw/master/logo.png)

<a href='https://ko-fi.com/I2I21F8E1' target='_blank'><img height='26' style='border:0px;height:26px;' src='https://cdn.ko-fi.com/cdn/kofi1.png?v=2' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

[![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/unmanic/unmanic?color=009dc7&label=latest%20release&logo=github&logoColor=%23403d3d&style=flat-square)](https://github.com/unmanic/unmanic/releases)
[![GitHub issues](https://img.shields.io/github/issues-raw/unmanic/unmanic?color=009dc7&logo=github&logoColor=%23403d3d&style=flat-square)](https://github.com/unmanic/unmanic/issues?q=is%3Aopen+is%3Aissue)
[![GitHub closed issues](https://img.shields.io/github/issues-closed-raw/unmanic/unmanic?color=009dc7&logo=github&logoColor=%23403d3d&style=flat-square)](https://github.com/unmanic/unmanic/issues?q=is%3Aissue+is%3Aclosed)
[![GitHub pull requests](https://img.shields.io/github/issues-pr-raw/unmanic/unmanic?color=009dc7&logo=github&logoColor=%23403d3d&style=flat-square)](https://github.com/unmanic/unmanic/pulls?q=is%3Aopen+is%3Apr)
[![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed-raw/unmanic/unmanic?color=009dc7&logo=github&logoColor=%23403d3d&style=flat-square)](https://github.com/unmanic/unmanic/pulls?q=is%3Apr+is%3Aclosed)

[![Docker Stars](https://img.shields.io/docker/stars/josh5/unmanic?color=009dc7&logo=docker&logoColor=%23403d3d&style=for-the-badge)](https://hub.docker.com/r/josh5/unmanic)
[![Docker Pulls](https://img.shields.io/docker/pulls/josh5/unmanic?color=009dc7&logo=docker&logoColor=%23403d3d&style=for-the-badge)](https://hub.docker.com/r/josh5/unmanic)
[![Docker Image Size (tag)](https://img.shields.io/docker/image-size/josh5/unmanic/latest?color=009dc7&label=docker%20image%20size&logo=docker&logoColor=%23403d3d&style=for-the-badge)](https://hub.docker.com/r/josh5/unmanic)




[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Unmanic/unmanic/python_lint_and_run_unit_tests.yml?branch=master&style=flat-square&logo=github&logoColor=403d3d&label=Unit%20Tests)](https://github.com/Unmanic/unmanic/actions/workflows/python_lint_and_run_unit_tests.yml?query=branch%3Amaster)
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Unmanic/unmanic/integration_test_and_build_all_packages_ci.yml?branch=master&style=flat-square&logo=github&logoColor=403d3d&label=Package%20Build)](https://github.com/Unmanic/unmanic/actions/workflows/integration_test_and_build_all_packages_ci.yml?query=branch%3Amaster)

[![GitHub license](https://img.shields.io/github/license/unmanic/unmanic?color=009dc7&style=flat-square)]()
---

Unmanic is a simple tool for optimising your file library. You can use it to convert your files into a single, uniform format, manage file movements based on timestamps, or execute custom commands against a file based on its file size.

Simply configure Unmanic pointing it at your library and let it automatically manage that library for you.

Unmanic provides you with the following main functions:

- A scheduler built in to scan your whole library for files that do not conform to your configured file presets. Files found requiring processing are then queued.
- A file/directory monitor. When a file is modified, or a new file is added in your library, Unmanic is able to again test that against your configured file presets. Like the first function, if this file requires processing, it is added to a queue for processing.
- A handler to manage running multiple file manipulation tasks at a time.
- A Web UI to easily configure, manage and monitor the progress of your library optimisation.

You choose how you want your library to be.

Some examples of how you may use Unmanic:

- Transcode video or audio files into a uniform format using FFmpeg.
- Identify (and remove if desired) commercials in DVR recordings shortly after they have completed being recorded.
- Move files from one location to another after a configured period of time.
- Automatically execute FileBot rename files in your library as they are added.
- Compress files older than a specified age.
- Run any custom command against files matching a certain extension or above a configured file size.

### Table Of Contents

[Dependencies](#dependencies)

[Screen-shots](#screen-shots)
  * [Dashboard](#dashboard)
  * [File metrics](#file-metrics)
  * [Installed plugins](#installed-plugins)

[Install and Run](#install-and-run)

[License and Contribution](#license-and-contribution)


## Dependencies

 - Python 3.x ([Install](https://www.python.org/downloads/))
 - To install requirements run 'python3 -m pip install -r requirements.txt' from the project root

Since Unmanic can be used for running any commands, you will need to ensure that the required dependencies for those commands are also installed on your system.

## Screen-shots

#### Dashboard:
![Screen-shot - Dashboard](./docs/images/unmanic-dashboard-processing-anime.png)
#### File metrics:
![Screen-shot - Desktop](./docs/images/unmanic-file-size-data-panel-anime.png)
#### Installed plugins:
![Screen-shot - Desktop](./docs/images/unmanic-list-installed-plugins.png)

## Install and Run

For up-to-date installation instructions, follow the [Unmanic documentation](https://docs.unmanic.app/docs/).

To run from source:

1) Install the Python dependencies listed above then run:
2) Run:
    ```
    # Ensure the submodules are checked out
    git submodule update --init --recursive
    
    # Build and install the project into your home directory
    python3 ./setup.py install --user
    
    # Run Unmanic
    unmanic
    ```
3) Open your web browser and navigate to http://localhost:8888/

## License and Contribution

This projected is licensed under the GPL version 3. 

Copyright (C) Josh Sunnex - All Rights Reserved

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
 
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

This project contains libraries imported from external authors.
Please refer to the source of these libraries for more information on their respective licenses.

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) to learn how to contribute to Unmanic.

---
