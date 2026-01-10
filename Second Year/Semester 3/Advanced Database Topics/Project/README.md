# Documentație Proiect  
## CDC MySQL → Kafka (Debezium) → PostgreSQL

---

## 1. Scopul proiectului

Acest proiect implementează o **replicare în timp real** a modificărilor dintr-o bază de date **MySQL** către **PostgreSQL**, folosind:

- **Debezium** (pentru CDC din binlog-ul MySQL)
- **Apache Kafka** (ca bus de evenimente)
- **Kafka Connect** (pentru rularea conectorilor)
- **Confluent JDBC Sink Connector** (pentru scrierea în PostgreSQL)
- **Kafka UI** (pentru vizualizarea topic-urilor și mesajelor)

**Obiectiv:**  
Orice `INSERT`, `UPDATE` și `DELETE` făcut în MySQL să apară automat în PostgreSQL.

---

## 2. Arhitectură și flux de date

- **MySQL** – sursa. Debezium citește schimbările din *binlog*.
- **Debezium MySQL Connector (Source)** – transformă schimbările din binlog în mesaje Kafka.
- **Kafka** – transportă evenimentele CDC în topic-uri.
- **JDBC Sink Connector (Postgres)** – consumă topic-urile și aplică schimbările în PostgreSQL.
- **Kafka UI** – interfață web pentru inspectarea topic-urilor și mesajelor.
- **PostgreSQL** – destinația (replica).

---

## 3. Tehnologii folosite

- Docker / Docker Compose  
- Kafka + Zookeeper (Confluent images)  
- Debezium Connect: `quay.io/debezium/connect:3.3.2.Final`  
- Confluent JDBC Sink Connector (instalat în imaginea Connect)  
- MySQL `8.0.36`  
- PostgreSQL `16`  
- Kafka UI: `provectuslabs/kafka-ui`

---

## 4. Configurarea mediului (Docker Compose)

```bash
docker compose down -v
docker compose build
docker compose up -d
````

---

## 5. Configurarea MySQL pentru Debezium

MySQL trebuie să aibă:

* `binlog-format=ROW`
* `log-bin` activ
* `server-id` setat

Acestea sunt configurate în `docker-compose.yml` în secțiunea `command:`.

Debezium are nevoie să poată citi poziția binlog-ului și metadatele pentru snapshot.

Intră în MySQL ca `root` și acordă privilegiile necesare:

```powershell
Get-Content .\mysql_grants.sql | docker exec -i cdc-mysql-1 mysql -u root -proot
```

---

## 6. Crearea schemelor (tabele) în MySQL și PostgreSQL

> **Important:** Debezium nu creează tabele.
> Conectorii replică **doar modificări de date**, nu migrează schema.

Tabelele trebuie create **manual** în ambele baze de date.

### MySQL (source)

```powershell
Get-Content .\create_database.sql | docker exec -i cdc-mysql-1 mysql -u root -proot
```

### PostgreSQL (destination)

```powershell
Get-Content .\schema_postgres.sql -Raw | docker exec -i cdc-postgres-1 psql -U debezium_user -d debezium_postgres
```

---

## 7. Crearea conectorilor Kafka Connect

### Conector MySQL Source

Creează fișierul `mysql-source.json`, apoi rulează:

```powershell
Invoke-RestMethod `
  -Uri http://localhost:8083/connectors `
  -Method Post `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body (Get-Content .\mysql-source.json -Raw)
```

Acest conector:

* face snapshot inițial (opțional),
* publică evenimente CDC în topic-uri de forma:

```
mysql.<db>.<table>
```

---

## 8. Vizualizarea mesajelor în Kafka UI

Kafka UI rulează la:
👉 [http://localhost:8081](http://localhost:8081)

### Pași:

1. Selectezi clusterul local
2. Meniul **Topics**
3. Cauți topic-ul:

   ```
   mysql.library.AUTHORS
   ```
4. Intri pe tab-ul **Messages**
5. Selectezi:

   * partition: `0`
   * offset: `0`
   * limit: `50`
6. Click pe **Search**

---

## 9. JDBC Sink către PostgreSQL

Creează conectorul PostgreSQL:

```powershell
Invoke-RestMethod `
  -Uri http://localhost:8083/connectors `
  -Method Post `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body (Get-Content .\postgres-sink-authors.json -Raw)
```

---

## 10. Testare end-to-end

### Insert în MySQL

```bash
docker exec -i cdc-mysql-1 mysql -u root -proot -D library \
  -e "INSERT INTO AUTHORS (AUTHOR_ID, AUTHOR_NAME, NATIONALITY) VALUES (1, 'J.K.Rowling', 'UK');"
```

### Verificare în Kafka

* Topic: `mysql.library.AUTHORS`
* Trebuie să apară un eveniment nou în tab-ul **Messages**

### Verificare în PostgreSQL

```bash
docker exec -it cdc-postgres-1 psql -U debezium_user -d debezium_postgres \
  -c "SELECT * FROM authors;"
```
