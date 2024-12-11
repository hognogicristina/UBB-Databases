const {client} = require('../../db/mongoConnection');
const {saveCatalog, catalog} = require('../../db/catalog');
const {getCurrentDatabase} = require('../../db/dbState');
const {checkDatabase, checkDatabaseSelection} = require("../../utils/validators/databaseValidation");
const {checkTableName, validateColumnDefinitions} = require("../../utils/validators/tableValidation");

async function handleCreate(command, socket) {
  const type = command[1].toLowerCase();

  try {
    if (type === 'database') {
      const dbName = command[2];
      const errorMessage = checkDatabase(dbName);
      if (errorMessage) return socket.write(errorMessage);

      catalog.databases.push({dataBaseName: dbName, tables: []});
      saveCatalog();
      socket.write(`Database ${dbName} created`);
    } else if (type === 'table') {
      const currentDatabase = getCurrentDatabase();
      const dbError = checkDatabaseSelection();
      if (dbError) return socket.write(dbError);

      const tableName = command[2];
      const columnsData = command.slice(3).join(' ');
      const tableError = checkTableName(currentDatabase, tableName);
      if (tableError) return socket.write(tableError);

      const dbEntry = catalog.databases.find(db => db.dataBaseName === currentDatabase);
      const columnValidation = validateColumnDefinitions(dbEntry, columnsData);
      if (typeof columnValidation === 'string') return socket.write(columnValidation);

      const {columns, primaryKey, foreignKeys = [], uniqueColumns = []} = columnValidation;
      const fileName = `${currentDatabase}_${tableName}`;
      const db = client.db(currentDatabase);
      await db.createCollection(fileName);

      const newTable = {
        tableName,
        fileName,
        structure: {attributes: columns},
        primaryKey: {pkAttributes: primaryKey.length > 0 ? primaryKey : ['_id']},
        foreignKeys,
        indexFiles: [],
      };

      for (const fk of foreignKeys) {
        const refTable = fk.references.refTable;
        const fkName = `${fk.fkAttributes.join('_')}.ind`;
        const fkIndexName = `${fileName}_fk_${refTable}_${fkName}`;
        await db.createCollection(fkIndexName);

        newTable.indexFiles.push({
          indexName: fkName,
          isUnique: 0,
          indexAttributes: fk.fkAttributes,
        });
      }

      for (const uniqueColumn of uniqueColumns) {
        await db.createCollection(`${fileName}_idx_${uniqueColumn}.ind`);
        newTable.indexFiles.push({
          indexName: `${uniqueColumn}.ind`,
          isUnique: 1,
          indexAttributes: [uniqueColumn]
        });
      }

      dbEntry.tables.push(newTable);
      saveCatalog();
      socket.write(`Table ${tableName} created.`);
    }
  } catch (error) {
    socket.write("ERROR: An unexpected error occurred");
  }
}

module.exports = {handleCreate};
