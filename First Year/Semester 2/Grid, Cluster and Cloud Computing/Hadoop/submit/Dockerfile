FROM hadoop-base:latest

COPY index.jar /opt/hadoop/applications/app.jar
COPY book1.txt /opt/hadoop/book1.txt
COPY book2.txt /opt/hadoop/book2.txt
COPY book3.txt /opt/hadoop/book3.txt
COPY book4.txt /opt/hadoop/book4.txt
COPY book5.txt /opt/hadoop/book5.txt
COPY book6.txt /opt/hadoop/book6.txt
COPY book7.txt /opt/hadoop/book7.txt
COPY book8.txt /opt/hadoop/book8.txt
COPY book9.txt /opt/hadoop/book9.txt
COPY book10.txt /opt/hadoop/book10.txt

ENV JAR_FILEPATH="/opt/hadoop/applications/app.jar"
ENV CLASS_TO_RUN="WordCounter"
ENV PARAMS="hdfs:///books /output"

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]