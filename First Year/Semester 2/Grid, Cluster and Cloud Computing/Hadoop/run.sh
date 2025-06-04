DOCKER_NETWORK=hadoop-proj_default
ENV_FILE=hadoop.env

docker build -t hadoop-wordcounter ./submit --platform=linux/amd64
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-base hdfs namenode -format
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-base hdfs dfs -rm -r -f /output
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-base hdfs dfs -mkdir -p /books
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -copyFromLocal -f /opt/hadoop/book1.txt /books
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -copyFromLocal -f /opt/hadoop/book2.txt /books
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -copyFromLocal -f /opt/hadoop/book3.txt /books
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -copyFromLocal -f /opt/hadoop/book4.txt /books
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -copyFromLocal -f /opt/hadoop/book5.txt /books
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -copyFromLocal -f /opt/hadoop/book6.txt /books
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -copyFromLocal -f /opt/hadoop/book7.txt /books
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -copyFromLocal -f /opt/hadoop/book8.txt /books
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -copyFromLocal -f /opt/hadoop/book9.txt /books
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -copyFromLocal -f /opt/hadoop/book10.txt /books
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -ls /
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -stat %o /books/book1.txt
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -stat %o /books/book2.txt
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -stat %o /books/book3.txt
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -stat %o /books/book4.txt
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -stat %o /books/book5.txt
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -stat %o /books/book6.txt
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -stat %o /books/book7.txt
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -stat %o /books/book8.txt
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -stat %o /books/book9.txt
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter hdfs dfs -stat %o /books/book10.txt
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-wordcounter
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-base hdfs dfs -cat /output/* > result.txt
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-base hdfs dfs -rm -r /output
docker run --platform linux/amd64 --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} hadoop-base hdfs dfs -rm -r /books