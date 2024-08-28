# Unmanic Docker Image


### Building the Source
Before building the image, you need to have built the unmanic python package:
```bash
rm -rfv ./build && rm -fv ./dist/unmanic-*
git submodule update --init --recursive
python3 -m build --no-isolation --skip-dependency-check --wheel
python3 -m build --no-isolation --skip-dependency-check --sdist
```


### Building the image
Simply run this command from the root of the project:
```bash
docker build -f ./docker/Dockerfile -t josh5/unmanic:latest .
```