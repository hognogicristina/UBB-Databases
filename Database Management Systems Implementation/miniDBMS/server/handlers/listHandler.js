const {catalog} = require('../db/catalog');
const {getCurrentDatabase} = require('../db/dbState');

function listDatabases(socket) {
  const dbNames = catalog.databases.map(db => db.dataBaseName);
  if (dbNames.length === 0) {
    socket.write(`No databases available.`);
  } else {
    socket.write(`Databases:\n${dbNames.join('\n')}`);
  }
}

function listTables(socket) {
  const currentDatabase = getCurrentDatabase();
  if (currentDatabase) {
    const db = catalog.databases.find(db => db.dataBaseName === currentDatabase);
    const tableNames = db.tables.map(t => t.tableName);
    if (tableNames.length === 0) {
      socket.write(`No tables in database ${currentDatabase}.`);
    } else {
      socket.write(`Tables in database ${currentDatabase}:\n${tableNames.join('\n')}`);
    }
  } else {
    socket.write(`ERROR: No database selected.`);
  }
}


module.exports = {listDatabases, listTables};
