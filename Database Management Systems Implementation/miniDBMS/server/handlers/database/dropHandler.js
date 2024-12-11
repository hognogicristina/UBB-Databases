const {client} = require('../../db/mongoConnection');
const {saveCatalog, catalog} = require('../../db/catalog');
const {getCurrentDatabase} = require('../../db/dbState');
const {checkDatabaseExists, checkDatabaseSelection} = require('../../utils/validators/databaseValidation');
const {checkTableExists} = require('../../utils/validators/tableValidation');
const {checkUseOfExistingFK} = require('../../utils/validators/foreignKeyValidation');
const {dropTable} = require('../../utils/helpers/deleteIndex');

async function handleDrop(command, socket) {
  const type = command[1].toLowerCase();

  try {
    if (type === 'database') {
      const dbName = command[2];
      const dbIndex = checkDatabaseExists(dbName);
      if (typeof dbIndex === 'string') return socket.write(dbIndex);

      const db = client.db(dbName);
      await db.dropDatabase();
      catalog.databases.splice(dbIndex, 1);
      saveCatalog();
      socket.write(`Database ${dbName} dropped`);

    } else if (type === 'table') {
      const currentDatabase = getCurrentDatabase();
      const tableName = command[2];

      const dbError = checkDatabaseSelection();
      if (dbError) return socket.write(dbError);

      const db = catalog.databases.find(db => db.dataBaseName === currentDatabase);
      const tableIndex = checkTableExists(currentDatabase, tableName);
      if (typeof tableIndex === 'string') return socket.write(tableIndex);

      const table = db.tables[tableIndex];
      const fkError = await checkUseOfExistingFK(table, currentDatabase, client);
      if (fkError) return socket.write(fkError);

      try {
        await dropTable(table, currentDatabase);
        const tableCollection = client.db(currentDatabase).collection(table.fileName);
        await tableCollection.drop();
      } catch (error) {
        return socket.write(`ERROR: Could not drop table collection ${table.fileName}`);
      }

      db.tables.splice(tableIndex, 1);
      saveCatalog();
      socket.write(`Table ${tableName} dropped`);
    }
  } catch (error) {
    socket.write("ERROR: An unexpected error occurred");
  }
}

module.exports = {handleDrop};
