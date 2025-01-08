const {getCurrentDatabase} = require("../../db/dbState");
const {checkDatabaseSelection} = require("../../utils/validators/databaseValidation");
const {findTable, validateWhereColumns} = require("../../utils/validators/tableValidation");
const {parseSelectCommand} = require("../../utils/validators/commandValidation");
const {
  fetchDocuments,
  applyProjection,
  removeDuplicates,
  writeResultsToFile,
  whereCond
} = require("../../utils/helpers/indexOptimization");
const {performJoin, applyRemainingJoins} = require("../../utils/helpers/joinAlgorithms");

async function handleSelect(command, socket) {
  const currentDatabase = getCurrentDatabase();
  const dbError = checkDatabaseSelection();
  if (dbError) return socket.write(dbError);

  try {
    const parsedCommand = parseSelectCommand(command);
    if (typeof parsedCommand === 'string') {
      return socket.write(parsedCommand);
    }

    const {tables, columns, whereConditions, distinct, joinClause, joinRemainingClause} = parsedCommand;

    const tableAliasMap = {};
    for (const tableEntry of tables) {
      const [tableName, alias] = tableEntry.split(/\s+/);
      const tableData = findTable(tableName);

      if (typeof tableData === 'string') {
        return socket.write(tableData);
      }

      tableAliasMap[alias || tableName] = tableData;
    }

    const isJoinOperation = Boolean(joinClause);

    const validationError = validateWhereColumns(whereConditions, tableAliasMap, isJoinOperation);
    if (validationError) {
      return socket.write(validationError);
    }

    let result;
    if (isJoinOperation) {
      const {joinType, onConditions} = joinClause;
      const [mainTableAlias] = Object.keys(tableAliasMap);
      const joinAlias = Object.keys(tableAliasMap).find(
        (alias) => alias !== mainTableAlias
      );

      const mainTableData = await fetchDocuments(
        tableAliasMap[mainTableAlias],
        whereConditions,
        currentDatabase
      );

      const joinTableData = await fetchDocuments(
        tableAliasMap[joinAlias],
        [],
        currentDatabase
      );

      result = await performJoin(
        mainTableData,
        joinTableData,
        joinType,
        onConditions,
        tableAliasMap[mainTableAlias],
        tableAliasMap[joinAlias],
        currentDatabase,
        mainTableAlias,
        joinAlias
      );

      if (whereConditions.length > 0) {
        result = whereCond(result, whereConditions);
      }

      if (joinRemainingClause && joinRemainingClause.length > 0) {
        result = await applyRemainingJoins(
          result,
          joinRemainingClause,
          currentDatabase
        );
      }
    } else {
      const mainTableAlias = Object.keys(tableAliasMap)[0];
      result = await fetchDocuments(
        tableAliasMap[mainTableAlias],
        whereConditions,
        currentDatabase
      );
    }

    const selectedColumns = columns.includes('*')
      ? Object.values(tableAliasMap).flatMap((table) =>
        table.structure.attributes.map((attr) => `${tableAliasMap[table.tableName].alias}.${attr.attributeName}`)
      )
      : columns;

    let projectedResults = await applyProjection(
      result,
      selectedColumns,
      tableAliasMap[Object.keys(tableAliasMap)[0]],
      whereConditions,
      currentDatabase,
      isJoinOperation
    );

    if (distinct) {
      projectedResults = removeDuplicates(projectedResults);
    }

    if (projectedResults.length === 0) {
      return socket.write('No results found.');
    }

    writeResultsToFile(
      projectedResults,
      selectedColumns,
      currentDatabase,
      tableAliasMap[Object.keys(tableAliasMap)[0]].tableName
    );
    socket.write('check select.txt');
  } catch (error) {
    console.error("ERROR:", error);
    socket.write("ERROR: Failed to execute SELECT command");
  }
}

module.exports = {handleSelect};
