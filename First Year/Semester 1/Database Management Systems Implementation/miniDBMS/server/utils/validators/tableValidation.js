const {catalog} = require("../../db/catalog");
const {isValidDataType, isValidColumnModifier, isUnique} = require("./dataValidation");
const {getCurrentDatabase} = require("../../db/dbState");

function checkTableName(currentDatabase, tableName) {
  if (!tableName) return `ERROR: Table name required`;
  const dbEntry = catalog.databases.find(db => db.dataBaseName === currentDatabase);
  if (!dbEntry) return `ERROR: No database selected`;
  if (dbEntry.tables.find(table => table.tableName === tableName)) return `ERROR: Table ${tableName} already exists in database ${currentDatabase}`;
  return null;
}

function checkTableExists(currentDatabase, tableName) {
  const db = catalog.databases.find(db => db.dataBaseName === currentDatabase);
  if (!db) return `ERROR: No database selected`;
  const tableIndex = db.tables.findIndex(t => t.tableName === tableName);
  return tableIndex === -1 ? `ERROR: Table ${tableName} does not exist in database ${currentDatabase}` : tableIndex;
}

function validateColumnDefinitions(dbEntry, columnDefinitions) {
  const columns = [];
  const primaryKey = [];
  const foreignKeys = [];
  const uniqueColumns = [];
  const columnNames = new Set();

  const primaryCount = columnDefinitions.split(',').filter(def => def.includes('primary')).length;
  const hasMultiplePrimaryKeys = primaryCount > 1;

  for (const definition of columnDefinitions.split(',')) {
    const parts = definition.trim().split(' ');
    const columnName = parts[0];
    const columnType = parts[1];
    const columnLength = parts[2] ? parseInt(parts[2], 10) : null;

    if (columnNames.has(columnName)) return `ERROR: Duplicate column name ${columnName}`;
    columnNames.add(columnName);

    if (!isValidDataType(columnType, columnLength)) return `ERROR: Invalid data type for column ${columnName}`;
    let isUniqueColumn = isUnique(parts);

    let isPrimary = parts.includes('primary');
    if (hasMultiplePrimaryKeys && isPrimary) {
      isUniqueColumn = false;
    }

    for (const part of parts) {
      if (part !== columnName && part !== columnType && !Number.isInteger(columnLength) && part !== 'unique') {
        if (part.startsWith('foreign=')) {
          const [refTable, refColumn] = part.split('=')[1].split('.');
          const referencedTable = dbEntry.tables.find(t => t.tableName === refTable);
          if (!referencedTable) return `ERROR: Referenced table ${refTable} does not exist`;
          if (!referencedTable.structure.attributes.some(attr => attr.attributeName === refColumn)) {
            return `ERROR: Referenced column ${refColumn} does not exist in table ${refTable}`;
          }
          foreignKeys.push({fkAttributes: [columnName], references: {refTable, refAttributes: [refColumn]}});
        } else if (!isValidColumnModifier(part)) {
          return `ERROR: Invalid column modifier "${part}" in column ${columnName}`;
        }
      }
    }

    if (isPrimary) {
      primaryKey.push(columnName);
      if (!hasMultiplePrimaryKeys) {
        isUniqueColumn = true;
      }
    }

    const column = {
      attributeName: columnName,
      type: columnType,
      length: columnLength,
      isUnique: isUniqueColumn,
    };

    if (isUniqueColumn && !isPrimary) {
      uniqueColumns.push(columnName);
    }

    columns.push(column);
  }

  if (columns.length === 0) return `ERROR: At least one column is required`;
  if (primaryKey.length === 0) primaryKey.push('_id');

  return {columns, primaryKey, foreignKeys, uniqueColumns};
}

function findTable(tableName) {
  const currentDatabase = getCurrentDatabase();
  const db = catalog.databases.find(db => db.dataBaseName === currentDatabase);
  const table = db.tables.find(t => t.tableName === tableName);

  if (!table) {
    return `ERROR: Table ${tableName} does not exist in database ${currentDatabase}`;
  } else {
    return table;
  }
}

function checkColumnExists(table, tableName, columnName) {
  const columnExists = table.structure.attributes.some(attr => attr.attributeName === columnName);
  if (!columnExists) {
    return `ERROR: Column ${columnName} does not exist in table ${tableName}`;
  }
}

function validateWhereColumns(whereConditions, tableAliasMap, isJoinOperation = false) {
  const invalidColumns = [];

  whereConditions.forEach((condition) => {
    let {attribute} = condition;

    if (isJoinOperation) {
      const aliasMatch = attribute.match(/^(\w+)\.(\w+)$/);
      if (aliasMatch) {
        const [_, alias, columnName] = aliasMatch;
        const table = tableAliasMap[alias];

        if (!table) {
          invalidColumns.push(`${alias}.${columnName} (invalid alias)`);
        } else {
          const tableColumns = table.structure.attributes.map((attr) => attr.attributeName);
          if (!tableColumns.includes(columnName)) {
            invalidColumns.push(columnName);
          }
          condition.attribute = columnName;
        }
      } else {
        invalidColumns.push(`${attribute} (missing alias for join)`);
      }
    } else {
      const table = tableAliasMap[Object.keys(tableAliasMap)[0]];
      const tableColumns = table.structure.attributes.map((attr) => attr.attributeName);

      if (!tableColumns.includes(attribute)) {
        invalidColumns.push(attribute);
      }
    }
  });

  if (invalidColumns.length > 0) {
    const tableNames = Object.values(tableAliasMap)
      .map((table) => `"${table.tableName}"`)
      .join(", ");
    return `ERROR: The following columns do not exist in table(s) ${tableNames}: ${invalidColumns.join(", ")}`;
  }

  return null;
}

module.exports = {
  checkTableName,
  checkTableExists,
  validateColumnDefinitions,
  findTable,
  checkColumnExists,
  validateWhereColumns
};