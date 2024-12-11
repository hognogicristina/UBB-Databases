const readline = require('readline');
const {faker} = require('@faker-js/faker');
const {client} = require('./server/db/mongoConnection');
const {catalog} = require('./server/db/catalog');
const {handleUse} = require('./server/handlers/database/useHandler');
const {handleInsert} = require('./server/handlers/operations/insertHandler');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function promptUser(query) {
  return new Promise(resolve => rl.question(query, answer => resolve(answer.trim())));
}

function getTableSchema(dbName, tableName) {
  const database = catalog.databases.find(db => db.dataBaseName === dbName);
  if (!database) throw new Error(`Database "${dbName}" does not exist`);

  const table = database.tables.find(tbl => tbl.tableName === tableName);
  if (!table) throw new Error(`Table "${tableName}" does not exist in database "${dbName}"`);

  return table;
}

function generateRandomData(column, rowIndex) {
  if (column.isUnique && column.attributeName === 'StudID') {
    return rowIndex;
  }

  switch (column.attributeName) {
    case 'Name':
      return `'${faker.person.firstName()}'`;
    case 'Tel':
      return `'${faker.phone.number()}'`;
    case 'email':
      return generateCustomEmail();
    case 'mark':
      return Math.floor(Math.random() * 10) + 1;
    case 'GroupID':
      return Math.floor(Math.random() * 51) + 200;
    default:
      switch (column.type.toUpperCase()) {
        case 'INT':
          return Math.floor(Math.random() * 1000);
        case 'FLOAT':
          return (Math.random() * 100).toFixed(2);
        case 'BOOL':
          return Math.random() < 0.5 ? 'true' : 'false';
        case 'DATE':
          return `'${faker.date.past().toISOString().split('T')[0]}'`;
        case 'VARCHAR':
        case 'CHAR':
          return `'${faker.string.alphanumeric(column.length || 10)}'`;
        default:
          return `'N/A'`;
      }
  }
}

function generateCustomEmail() {
  const domains = [
    'gmail.com',
    'gmail.ro',
    'yahoo.com',
    'yahoo.ro',
    'hotmail.com',
    'hotmail.ro',
    'outlook.com',
    'protonmail.com',
    'icloud.com',
    'customdomain.org',
    'example.net',
    'randommail.co'
  ];

  const randomChars = faker.string.alphanumeric(10 + Math.floor(Math.random() * 15));
  const domain = domains[Math.floor(Math.random() * domains.length)];
  return `'${randomChars}@${domain}'`;
}

async function fetchStudentIds(dbName) {
  const studentTable = getTableSchema(dbName, "Students");
  const collectionName = `${dbName}_${studentTable.tableName}`;
  const studentCollection = client.db(dbName).collection(collectionName);

  const students = await studentCollection.find({}).toArray();
  return students.map(student => student._id);
}

async function insertRowsBatch(dbName, tableName, rowCount) {
  try {
    handleUse(['USE', dbName], {write: console.log});
    const table = getTableSchema(dbName, tableName);
    const columns = table.structure.attributes;

    if (tableName.includes("Student")) {
      for (let i = 1; i <= rowCount; i++) {
        const fields = columns
          .map(col => `${col.attributeName}=${generateRandomData(col, i)}`)
          .join(", ");

        const command = `INSERT INTO ${tableName} ${fields}`.split(" ");
        await handleInsert(command, {write: console.log});
      }
      console.log(`Inserted ${rowCount} rows into table "${tableName}".`);
    } else if (tableName.includes("Grades")) {
      const studentIds = await fetchStudentIds(dbName);

      if (studentIds.length === 0) {
        throw new Error("No records found in table 'Students'. Cannot insert into 'Grades'.");
      }

      for (let i = 1; i <= rowCount; i++) {
        const gradeData = {
          GDate: `'${faker.date.past().toISOString().split("T")[0]}'`,
          StudID: studentIds[Math.floor(Math.random() * studentIds.length)],
          DiscID: `'${faker.string.alphanumeric(8)}'`,
          Grade: Math.floor(Math.random() * 10) + 1,
        };

        const fields = Object.entries(gradeData)
          .map(([key, value]) => `${key}=${value}`)
          .join(", ");

        const command = `INSERT INTO ${tableName} ${fields}`.split(" ");
        await handleInsert(command, {write: console.log});
      }
      console.log(`Inserted ${rowCount} rows into table "${tableName}".`);
    } else {
      console.log(`Table "${tableName}" is not recognized for this operation.`);
    }
  } catch (error) {
    console.error(error.message);
  } finally {
    rl.close();
    await client.close();
  }
}

(async () => {
  try {
    const dbName = "School";
    const tableName = await promptUser("Enter table name: ");
    const rowCount = parseInt(await promptUser("Enter number of rows to insert: "), 10);

    if (isNaN(rowCount) || rowCount <= 0) {
      throw new Error("Invalid row count. Please enter a positive integer.");
    }

    await insertRowsBatch(dbName, tableName, rowCount);
  } catch (error) {
    console.error("An error occurred:", error.message);
  }
})();
