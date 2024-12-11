# miniDBMS Setup Guide

## Install MongoDB on macOS

### Install Homebrew (if not installed)

Run the following command to install Homebrew if you don't have it installed:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Start MongoDB:

```
brew services start mongodb/brew/mongodb-community
```

This will start MongoDB as a background service, so it will continue running even after you close the terminal.

### To stop MongoDB:

```
brew services stop mongodb/brew/mongodb-community
```

If you want to run MongoDB without starting it as a background service, you can run it manually:

```
mongod --config /usr/local/etc/mongod.conf --fork
```

This will start MongoDB manually, and it will run until you close the terminal or stop it.

<details>

<summary>Database Example Commands</summary>

### Database creation

```
create database Hospital
use Hospital
drop database Hospital
```

### Table creation and deletion

```
create table Doctors id int primary, name varchar 255, specialty varchar 255, cnp int
create table Patients id int primary, name varchar 255, cnp int, doctor_id int foreign=Doctors.id
create table Appointments patient_id int primary foreign=Patients.id, doctor_id int primary foreign=Doctors.id
```

```
drop table Appointments
drop table Patients
drop table Doctors
```

### Index creation

```
create unique index cnp_name on Patients cnp, name
create index specialty on Doctors specialty
```

### Insert data and delete data

```
insert into Doctors id = 1, name = 'John', specialty = 'Cardiology', cnp = 1234567890123
insert into Patients id = 1, name = 'Alice', cnp = 1234567890123, doctor_id = 1
insert into Appointments patient_id = 1, doctor_id = 1
```

```
delete from Appointments where patient_id = 1 and doctor_id = 1
delete from Patients where id = 1
delete from Doctors where id = 1
```

</details>

### Use Mongo with CLI

1. Start MongoDB

```
mongosh
```

2. Show databases

```
show dbs
```

3. Use a database

```
use Hospital
```

4. Show database's collections

```
show collections
```

<details>
<summary>5. Show entries in a collection</summary>

```
db.Hospital_Doctors.find()
db.Hospital_Patients.find()
db.Hospital_Patients_fk_Doctors_doctor_id.find()
db.Hospital_Patients_idx_cnp_name.find()
db.Hospital_Doctors_idx_specialty.find()

db.Hospital_Appointments.find()
db.Hospital_Appointments_fk_Patients_patient_id.find()
db.Hospital_Appointments_fk_Doctors_doctor_id.find()
```

</details>

<details>
<summary>6. Show index/table collection of indexes</summary>

```
db.getCollection('Hospital_Doctors').getIndexes()
db.getCollection('Hospital_Patients').getIndexes()
db.getCollection('Hospital_Patients_fk_Doctors_doctor_id').getIndexes()
db.getCollection('Hospital_Patients_idx_cnp_name').getIndexes()

db.getCollection('Hospital_Appointments').getIndexes()
db.getCollection('Hospital_Appointments_fk_Patients_patient_id').getIndexes()
db.getCollection('Hospital_Appointments_fk_Doctors_doctor_id').getIndexes()
```

</details>

## Setting Up a Node.js Project with Separate Server and Client Folders

### Create Project Structure

Install server dependencies:

```
npm init -y
```

Create 2 terminals and run the following commands in each:

```
node server/server.js
node client/client.js
```

## For Windows Users

### Install MongoDB on Windows

1. Download MongoDB from the official site: [MongoDB Download Center](https://www.mongodb.com/try/download/community).
2. Run the installer and follow the installation instructions.

### Start MongoDB as a service:

```
net start MongoDB
```

If you want to run MongoDB manually, open a Command Prompt as Administrator and run:

```
mongod --dbpath "C:\path\to\your\db\folder"
```

### Setting Up a Node.js Project with Server and Client on Windows

1. Install [Node.js](https://nodejs.org/en).
2. Open Command Prompt or PowerShell and follow the same steps as on macOS to create the project structure and run the server/client.

For more database examples, check the [databases.txt](https://github.com/hognogicristina/miniDBMS/blob/main/databases.txt) file.