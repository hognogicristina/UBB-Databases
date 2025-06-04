#!/bin/bash

docker build -t hadoop-compiler .
docker run --rm -it --name hadoop-compiler -v "$(pwd)/hadoop-data:/hadoop-data" -p 9871:9870 -p 8089:8088 hadoop-compiler bash
