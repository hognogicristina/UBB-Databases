#!/bin/bash

CONTAINER_NAME=hadoop-compiler
SRC_DIR=$(pwd)

docker cp "$SRC_DIR/WordCounter.java" $CONTAINER_NAME:/tmp/
docker cp "$SRC_DIR/stopwords.txt" $CONTAINER_NAME:/tmp/

docker exec -w /tmp $CONTAINER_NAME bash -c '${JAVA_HOME}/bin/javac -encoding UTF-8 -classpath $("${HADOOP_HOME}/bin/hadoop" classpath) WordCounter.java'
docker exec -w /tmp $CONTAINER_NAME bash -c '${JAVA_HOME}/bin/jar cf index.jar WordCounter*.class stopwords.txt'
docker cp $CONTAINER_NAME:/tmp/index.jar "$SRC_DIR/index.jar"

rm ../submit/index.jar
cp "$SRC_DIR/index.jar" ../submit/

echo "index.jar built and copied to host"