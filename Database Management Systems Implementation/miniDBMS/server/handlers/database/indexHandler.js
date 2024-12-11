const {client} = require('../../db/mongoConnection');
const {saveCatalog} = require('../../db/catalog');
const {checkDatabaseSelection} = require('../../utils/validators/databaseValidation');
const {checkExistingIndex} = require('../../utils/validators/indexValidation');
const {findTable, checkColumnExists} = require('../../utils/validators/tableValidation');
const {getCurrentDatabase} = require("../../db/dbState");
const {parseCommandIndex} = require('../../utils/validators/commandValidation');

async function handleCreateIndex(command, socket) {
  const dbError = checkDatabaseSelection();
  if (dbError) {
    socket.write(dbError);
    return;
  }

  const commandText = command.join(' ');
  const regex = /create\s+(unique\s+)?index\s+(\w+)\s+on\s+(\w+)\s+([\w,\s]+)/i;
  const match = commandText.match(regex);

  const indexErrorCmd = parseCommandIndex(match);
  if (indexErrorCmd) {
    socket.write(indexErrorCmd);
    return;
  }

  const isUnique = !!match[1];
  const indexName = match[2] + '.ind';
  const tableName = match[3];
  const columns = match[4].split(',').map(col => col.trim());

  const table = findTable(tableName);
  if (typeof table === 'string') {
    socket.write(table);
    return;
  }

  for (const column of columns) {
    const columnError = checkColumnExists(table, tableName, column);
    if (columnError) {
      socket.write(columnError);
      return;
    }
  }

  const indexError = checkExistingIndex(table, indexName);
  if (indexError) {
    socket.write(indexError);
    return;
  }

  const currentDatabase = getCurrentDatabase();
  const collectionName = `${currentDatabase}_${tableName}_idx_${indexName}`;

  try {
    await client.db(currentDatabase).createCollection(collectionName);
    const indexEntry = {
      indexName: indexName,
      isUnique: isUnique ? 1 : 0,
      indexAttributes: columns
    };

    table.indexFiles.push(indexEntry);
    saveCatalog();

    socket.write(
      `Index ${indexName} created on columns ${columns.join(', ')} in table ${tableName} (Unique: ${isUnique})`
    );
  } catch (error) {
    socket.write(`ERROR: Could not create index ${indexName} on columns ${columns.join(', ')} in table ${tableName}`);
  }
}

module.exports = {handleCreateIndex};
