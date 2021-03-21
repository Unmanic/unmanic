# Development



## Database

This project uses Peewee migrations for managing the sqlite database.
`devops/migrations.sh` provides a small wrapper for the cli tool. To get started, run:
```
devops/migrations.sh --help
```


-----------------------------------------------------------


## Running a dev environment

### Docker:

The project runs best with docker. 
`devops/run_docker.sh` runs this development environment within the project's root folder.
The following folders are generated:

  - `/dev_environment/config` - Contains the containers mutable config data
  - `/dev_environment/library` - A library in which media files can be placed for testing
  - `/dev_environment/cache` - The temporary location used by ffmpeg for converting file formats

By default debugging is disabled when running a dev environment with `devops/run_docker.sh`. If you
wish to enable debugging, run:
```
devops/run_docker.sh --debug
```


### Py Module:

Install dependencies:
```
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-dev.txt
```

Install package link:
```
python3 ./setup.py develop --user
```

To later uninstall the development symlink, run:
```
python3 ./setup.py develop --user --uninstall
```

You should now be able to run unmanic from the commandline:
```
unmanic --version
```