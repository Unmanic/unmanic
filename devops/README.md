# Development



## Database

This project uses Peewee migrations for managing the sqlite database.
`devops/migrations.sh` provides a small wrapper for the cli tool. To get started, run:
```
devops/migrations.sh --help
```


-----------------------------------------------------------


## Running a dev environment

The project runs best with docker. 
`devops/run_docker.sh` runs this development environment within the project's root folder.
The following folders are generated:

  - /config - Contains the containers mutable config data
  - /library - A library in which media files can be placed for testing
  - /cache - The temporary location used by ffmpeg for converting file formats

By default debugging is disabled when running a dev environment with `devops/run_docker.sh`. If you
wish to enable debugging, run:
```
devops/run_docker.sh --debug
```

