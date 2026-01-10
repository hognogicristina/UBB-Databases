FROM quay.io/debezium/connect:3.3.2.Final

USER root

RUN microdnf -y install unzip && microdnf clean all

COPY confluentinc-kafka-connect-jdbc-*.zip /tmp/jdbc.zip
RUN mkdir -p /kafka/connect/jdbc \
 && unzip -q /tmp/jdbc.zip -d /kafka/connect/jdbc \
 && rm -f /tmp/jdbc.zip

COPY mysql-connector-j-8.4.0.jar /kafka/libs/mysql-connector-j.jar

USER kafka