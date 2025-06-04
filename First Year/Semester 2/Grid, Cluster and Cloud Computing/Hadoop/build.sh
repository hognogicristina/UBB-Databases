docker build -t hadoop-base ./base --platform=linux/amd64
docker build -t hadoop-namenode ./namenode --platform=linux/amd64
docker build -t hadoop-datanode ./datanode --platform=linux/amd64
docker build -t hadoop-resourcemanager ./resourcemanager --platform=linux/amd64
docker build -t hadoop-nodemanager ./nodemanager --platform=linux/amd64
docker build -t hadoop-historyserver ./historyserver --platform=linux/amd64
docker build -t hadoop-submit ./submit --platform=linux/amd64
