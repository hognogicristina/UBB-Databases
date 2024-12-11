const {client} = require("../../db/mongoConnection");
const {getCurrentDatabase} = require("../../db/dbState");
const {checkDatabaseSelection} = require("../../utils/validators/databaseValidation");
const {findTable, checkColumnExists} = require("../../utils/validators/tableValidation");
const {
  checkDeleteSyntax,
  checkDeleteCommand,
  checkDeleteColumn,
  checkForDuplicateColumnsDelete,
  missingPKValueError
} = require("../../utils/validators/commandValidation");
const {checkForeignKeyReferences} = require("../../utils/validators/foreignKeyValidation");
const {deleteForeignKeyEntries} = require("../../utils/helpers/deleteIndex");

async function handleDelete(command, socket) {
  const currentDatabase = getCurrentDatabase();
  const dbError = checkDatabaseSelection();
  if (dbError) return socket.write(dbError);

  const tableName = command[2];
  const table = findTable(tableName);
  if (typeof table === 'string') return socket.write(table);

  const deleteSyntaxError = checkDeleteSyntax(command);
  if (deleteSyntaxError) return socket.write(deleteSyntaxError);

  const deleteCommandError = checkDeleteCommand(command);
  if (deleteCommandError) return socket.write(deleteCommandError);

  const conditionString = command.slice(4).join(" ");
  const conditions = conditionString.split("and").map(cond => cond.trim());

  const duplicateColumnsError = checkForDuplicateColumnsDelete(conditions);
  if (duplicateColumnsError) return socket.write(duplicateColumnsError);

  const primaryKey = table.primaryKey.pkAttributes;
  const conditionMap = {};

  for (let condition of conditions) {
    const [col, val] = condition.split("=").map(s => s.trim());
    conditionMap[col] = val.replace(/^'|'$/g, "");

    const columnExistsError = checkColumnExists(table, tableName, col);
    if (columnExistsError) return socket.write(columnExistsError);

    const deleteColumnError = checkDeleteColumn(primaryKey, col);
    if (deleteColumnError) return socket.write(deleteColumnError);
  }

  const missingError = missingPKValueError(primaryKey, conditionMap);
  if (missingError) return socket.write(missingError);

  const pkValue = primaryKey.map(key => conditionMap[key]).join("$");
  const collection = client.db(currentDatabase).collection(table.fileName);

  const fkReferenceError = await checkForeignKeyReferences(table, pkValue, currentDatabase, client);
  if (fkReferenceError) {
    socket.write(fkReferenceError);
    return;
  }

  try {
    await deleteForeignKeyEntries(table, pkValue, currentDatabase, client);
    const result = await collection.deleteOne({_id: pkValue});
    if (result.deletedCount === 0) {
      socket.write(`ERROR: Record with ${pkValue} not found in table ${tableName}`);
      return;
    }
    socket.write(`Deleted from table ${tableName}`);
  } catch (error) {
    socket.write("ERROR: Delete operation failed");
  }
}

module.exports = {handleDelete};
