# Unmanic Docker Image


### Building the Source
Before building the image, you need to have built the unmanic python package:
```bash
rm -rfv ./build && rm -fv ./dist/unmanic-*
python3 ./setup.py sdist bdist_wheel
```


### Building the image
Simply run this command from the root of the project:
```bash
docker build -f ./docker/Dockerfile -t josh5/unmanic:latest .
```