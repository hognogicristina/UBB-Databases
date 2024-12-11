const {client} = require('../../db/mongoConnection');
const {getCurrentDatabase} = require("../../db/dbState");
const {checkDatabaseSelection} = require("../../utils/validators/databaseValidation");
const {findTable} = require("../../utils/validators/tableValidation");
const {
  validateInsertCommand,
  checkInsertCommand,
  checkForDuplicateColumns,
  validateEmptyVarcharChar
} = require("../../utils/validators/commandValidation");
const {validateDuplicatePK, checkExistingUniqueIndex} = require("../../utils/validators/indexValidation");
const {updateIndexes, updateIndexFK} = require("../../utils/helpers/updateIndexes");
const {checkExistingFK} = require("../../utils/validators/foreignKeyValidation");

async function handleInsert(command, socket) {
  const currentDatabase = getCurrentDatabase();
  const dbError = checkDatabaseSelection();
  if (dbError) return socket.write(dbError);

  const tableName = command[2];
  const table = findTable(tableName);
  if (typeof table === 'string') return socket.write(table);

  const commandText = command.join(" ");
  const match = commandText.match(/insert\s+into\s+\w+\s+((\w+\s*=\s*[^,]+)(\s*,\s*\w+\s*=\s*[^,]+)*)/i);
  const insertErrorCommand = validateInsertCommand(match, tableName);
  if (insertErrorCommand) return socket.write(insertErrorCommand);

  const fieldPairs = match[1].split(",").map(pair => pair.trim());
  const fields = {};
  const columns = [];

  fieldPairs.forEach(pair => {
    const [col, val] = pair.split("=").map(s => s.trim());
    columns.push(col);
    fields[col] = val.replace(/^'|'$/g, "");
  });

  const duplicateColumnError = checkForDuplicateColumns(columns);
  if (duplicateColumnError) return socket.write(duplicateColumnError);

  const tableColumns = table.structure.attributes.map(attr => attr.attributeName);
  const insertError = checkInsertCommand(command, tableColumns, fields);
  if (insertError) return socket.write(insertError);

  const emptyValueError = validateEmptyVarcharChar(commandText, table);
  if (emptyValueError) return socket.write(emptyValueError);

  const primaryKey = table.primaryKey.pkAttributes;
  const pkValue = primaryKey.map(key => fields[key]).join("$");

  const collection = client.db(currentDatabase).collection(table.fileName);
  const duplicatePKError = await validateDuplicatePK(collection, tableName, pkValue);
  if (duplicatePKError) return socket.write(duplicatePKError);

  const fkError = await checkExistingFK(table, fields, currentDatabase, client);
  if (fkError) return socket.write(fkError);

  const nonPKColumns = tableColumns.filter(col => !primaryKey.includes(col));
  const value = nonPKColumns.map(col => fields[col]).join("#");
  const document = {_id: pkValue, value};

  const indexError = await checkExistingUniqueIndex(table, fields, currentDatabase, client);
  if (indexError) return socket.write(indexError);

  try {
    await collection.insertOne(document);
    await updateIndexes(table, fields, currentDatabase, client);
    await updateIndexFK(table, fields, currentDatabase, client);

    socket.write(`Inserted into table ${tableName}`);
  } catch (error) {
    socket.write("ERROR: Insert operation failed");
  }
}

module.exports = {handleInsert};
