const {getCurrentDatabase} = require("../../db/dbState");
const {checkDatabaseSelection} = require("../../utils/validators/databaseValidation");
const {findTable, validateWhereColumns} = require("../../utils/validators/tableValidation");
const {parseSelectCommand} = require("../../utils/validators/commandValidation");
const {
  fetchDocuments,
  mergeJoinResults,
  applyProjection,
  removeDuplicates,
  writeResultsToFile
} = require("../../utils/helpers/indexOptimization");

async function handleSelect(command, socket) {
  const currentDatabase = getCurrentDatabase();
  const dbError = checkDatabaseSelection();
  if (dbError) return socket.write(dbError);

  try {
    const parsedCommand = parseSelectCommand(command);
    if (typeof parsedCommand === 'string') {
      return socket.write(parsedCommand);
    }

    const {tables, columns, whereConditions, distinct} = parsedCommand;
    const tablesData = tables.map(findTable);
    if (tablesData.some(table => typeof table === 'string')) {
      return socket.write(tablesData.find(table => typeof table === 'string'));
    }

    const validationError = validateWhereColumns(whereConditions, tablesData[0]);
    if (validationError) {
      return socket.write(validationError);
    }

    const tableResults = await Promise.all(
      tablesData.map((table) => fetchDocuments(table, whereConditions, currentDatabase))
    );

    let result = tableResults.length > 1 ? mergeJoinResults(tableResults) : tableResults[0];
    const selectedColumns = columns.includes('*')
      ? tablesData[0].structure.attributes.map(attr => attr.attributeName)
      : columns;

    let projectedResults = await applyProjection(result, selectedColumns, tablesData[0], whereConditions, currentDatabase);
    if (distinct) {
      projectedResults = removeDuplicates(projectedResults);
    }

    if (projectedResults.length === 0) {
      return socket.write('No results found.');
    }

    writeResultsToFile(projectedResults, selectedColumns, currentDatabase, tablesData[0].tableName);
    socket.write('check select.txt');
  } catch (error) {
    socket.write("ERROR: Failed to execute SELECT command");
  }
}

module.exports = {handleSelect};
