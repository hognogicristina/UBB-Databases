# Project Documentation  
## CDC MySQL → Kafka (Debezium) → PostgreSQL

---

## 1. Project Purpose

This project implements **real-time replication** of data changes from a **MySQL** database to **PostgreSQL**, using:

- **Debezium** (for CDC from the MySQL binlog)
- **Apache Kafka** (event streaming platform)
- **Kafka Connect** (for running connectors)
- **Confluent JDBC Sink Connector** (for writing data into PostgreSQL)
- **Kafka UI** (for inspecting topics and messages)

**Goal:**  
Any `INSERT`, `UPDATE`, or `DELETE` executed in MySQL should automatically appear in PostgreSQL.

---

## 2. Architecture and Data Flow

- **MySQL** – source database. Debezium reads changes from the binlog.
- **Debezium MySQL Connector (Source)** – converts binlog changes into Kafka messages.
- **Kafka** – transports CDC events through topics.
- **JDBC Sink Connector (PostgreSQL)** – consumes Kafka topics and applies changes to PostgreSQL.
- **Kafka UI** – web interface for inspecting topics and messages.
- **PostgreSQL** – destination database (replica).

---

## 3. Technologies Used

- Docker / Docker Compose  
- Kafka + Zookeeper (Confluent images)  
- Debezium Connect: `quay.io/debezium/connect:3.3.2.Final`  
- Confluent JDBC Sink Connector (installed in the Connect image)  
- MySQL `8.0.36`  
- PostgreSQL `16`  
- Kafka UI: `provectuslabs/kafka-ui`

---

## 4. Environment Setup (Docker Compose)

```bash
docker compose down -v
docker compose build
docker compose up -d
````

---

## 5. MySQL Configuration for Debezium

MySQL must have the following enabled:

* `binlog-format=ROW`
* `log-bin` enabled
* `server-id` configured

These settings are defined in `docker-compose.yml` under the `command:` section.

Debezium needs access to binlog positions and metadata in order to perform snapshots and stream changes.

Log into MySQL as `root` and grant the required privileges:

```powershell
Get-Content .\mysql_grants.sql | docker exec -i cdc-mysql-1 mysql -u root -proot
```

---

## 6. Schema Creation (MySQL and PostgreSQL)

> **Important:** Debezium does **not** create database schemas.
> Connectors replicate **data changes only**, not table structures.

All tables must be created **manually** in both databases.

### MySQL (Source)

```powershell
Get-Content .\create_database.sql | docker exec -i cdc-mysql-1 mysql -u root -proot
```

### PostgreSQL (Destination)

```powershell
Get-Content .\schema_postgres.sql -Raw | docker exec -i cdc-postgres-1 psql -U debezium_user -d debezium_postgres
```

---

## 7. Creating Kafka Connect Connectors

### MySQL Source Connector

Create the `mysql-source.json` file, then register the connector:

```powershell
Invoke-RestMethod `
  -Uri http://localhost:8083/connectors `
  -Method Post `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body (Get-Content .\mysql-source.json -Raw)
```

This connector:

* performs an initial snapshot (optional),
* publishes CDC events to topics with the format:

```
mysql.<database>.<table>
```

---

## 8. Viewing Messages in Kafka UI

Kafka UI is available at:
👉 [http://localhost:8081](http://localhost:8081)

### Steps:

1. Select the local cluster
2. Open the **Topics** menu
3. Search for the topic:

   ```
   mysql.library.AUTHORS
   ```
4. Open the **Messages** tab
5. Select:

   * partition: `0`
   * offset: `0`
   * limit: `50`
6. Click **Search**

---

## 9. JDBC Sink Connector to PostgreSQL

Create the PostgreSQL sink connector:

```powershell
Invoke-RestMethod `
  -Uri http://localhost:8083/connectors `
  -Method Post `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body (Get-Content .\postgres-sink-authors.json -Raw)
```

---

## 10. End-to-End Testing

### Insert Data into MySQL

```bash
docker exec -i cdc-mysql-1 mysql -u root -proot -D library \
  -e "INSERT INTO AUTHORS (AUTHOR_ID, AUTHOR_NAME, NATIONALITY) VALUES (1, 'J.K.Rowling', 'UK');"
```

### Verify in Kafka

* Topic: `mysql.library.AUTHORS`
* A new CDC event should appear in the **Messages** tab

### Verify in PostgreSQL

```bash
docker exec -it cdc-postgres-1 psql -U debezium_user -d debezium_postgres \
  -c "SELECT * FROM authors;"
```