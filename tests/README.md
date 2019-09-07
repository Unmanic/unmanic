# Unit Testing



## Setup

Before any tests can be run, you need to execute
```
tests/scripts/setup_tests.sh
```


-----------------------------------------------------------


## Python unit tests

To run all tests execute from the project directory root:
```
pytest --log-cli-level=INFO
```

You can also specify the files to run individual. Eg.
```
pytest --log-cli-level=INFO lib/common.py
```


-----------------------------------------------------------


## WebUI unit tests

This is still a WIP but the idea will be to have a series of API calls to determine successful functionality of the Web API

To run the test first run a docker environment. You can do this by running
```
tests/scripts/library_scan.sh
```
You can export the following variables to configure the test container:
```
DEBUGGING=true
NUMBER_OF_WORKERS=1
SCHEDULE_FULL_SCAN_MINUTES=1
RUN_FULL_SCAN_ON_START=true
```
To clean the config run 
```
tests/scripts/library_scan.sh --clean
```