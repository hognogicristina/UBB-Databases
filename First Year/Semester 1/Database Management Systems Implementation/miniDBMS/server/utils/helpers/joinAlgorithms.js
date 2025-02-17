const {client} = require("../../db/mongoConnection");
const {fetchDocuments} = require("./indexOptimization");
const {findTable} = require("../validators/tableValidation");

async function applyRemainingJoins(initialJoinResult, joinRemainingClause, currentDatabase) {
  let currentResult = initialJoinResult;

  for (const joinClause of joinRemainingClause) {
    const {joinType, joinTable, onConditions} = joinClause;
    const [joinTableName, joinAlias] = joinTable.split(/\s+/);
    const tableRemaining = findTable(joinTableName);

    const joinTableData = await fetchDocuments(
      tableRemaining,
      [],
      currentDatabase
    );

    const joinResults = [];
    const [onCondition] = onConditions;
    const {left, right} = onCondition;
    const rightColumnName = right.split('.').pop();

    currentResult.forEach((row) => {
      const leftValue = row[left];
      let matched = false;

      joinTableData.forEach((joinRow) => {
        const joinParsedRow = extractFullRow(
          joinRow,
          tableRemaining,
          joinAlias || joinTableName
        );
        const rightValue = joinParsedRow[`${joinAlias || joinTableName}.${rightColumnName}`];

        if (leftValue === rightValue) {
          joinResults.push({...row, ...joinParsedRow});
          matched = true;
        }
      });

      if (!matched && (joinType === 'left' || joinType === 'full')) {
        joinResults.push({
          ...row,
          ...getNullFilledRow(tableRemaining, joinAlias || joinTableName),
        });
      }
    });

    if (joinType === 'right' || joinType === 'full') {
      const unmatchedJoinRows = joinTableData.filter((joinRow) => {
        const joinParsedRow = extractFullRow(
          joinRow,
          tableRemaining,
          joinAlias || joinTableName
        );

        return !joinResults.some(
          (resultRow) => resultRow[`${joinAlias || joinTableName}.${rightColumnName}`] === joinParsedRow[`${joinAlias || joinTableName}.${rightColumnName}`]
        );
      });

      unmatchedJoinRows.forEach((row) => {
        joinResults.push({
          ...getNullFilledRow(
            tableRemaining,
            Object.keys(currentResult[0])[0]
          ),
          ...row,
        });
      });
    }

    currentResult = joinResults;
  }

  return currentResult;
}

async function performJoin(mainTableData, joinTableData, joinType, onConditions, mainTable, joinTable, currentDatabase, mainAlias, joinAlias) {
  let result;

  const [onCondition] = onConditions;
  const {left, right} = onCondition;

  const mainColumnName = left.split('.').pop();
  const joinColumnName = right.split('.').pop();

  const mainIsIndexed = mainTable.indexFiles.find((index) => index.indexAttributes.includes(mainColumnName));
  const joinIsIndexed = joinTable.indexFiles.find((index) => index.indexAttributes.includes(joinColumnName));

  if (mainIsIndexed && joinIsIndexed) {
    result = await indexedNestedLoopJoin(
      mainTableData,
      joinTableData,
      mainTable,
      joinTable,
      mainColumnName,
      joinColumnName,
      mainAlias,
      joinAlias,
      currentDatabase,
      joinType
    );
  } else {
    result = sortMergeJoin(
      mainTableData,
      joinTableData,
      mainTable,
      joinTable,
      mainColumnName,
      joinColumnName,
      mainAlias,
      joinAlias,
      joinType
    );
  }

  return result;
}

async function indexedNestedLoopJoin(
  mainTableData,
  joinTableData,
  mainTable,
  joinTable,
  mainColumnName,
  joinColumnName,
  mainAlias,
  joinAlias,
  currentDatabase,
  joinType
) {
  const joinResults = [];
  const db = client.db(currentDatabase);
  const joinCollection = db.collection(joinTable.fileName);

  const mainParsedData = mainTableData.map((row) => extractFullRow(row, mainTable, mainAlias));

  for (const mainParsedRow of mainParsedData) {
    const mainValue = mainParsedRow[`${mainAlias}.${mainColumnName}`];
    const joinRows = await joinCollection.find({}).toArray();
    let matched = false;

    for (const joinRow of joinRows) {
      const joinParsedRow = extractFullRow(joinRow, joinTable, joinAlias);
      const joinValue = joinParsedRow[`${joinAlias}.${joinColumnName}`];

      if (mainValue === joinValue) {
        const mergedRow = {...mainParsedRow, ...joinParsedRow};
        joinResults.push(mergedRow);
        matched = true;
      }
    }

    if (!matched && (joinType === 'left' || joinType === 'full')) {
      joinResults.push({...mainParsedRow, ...getNullFilledRow(joinTable, joinAlias)});
    }
  }

  if (joinType === 'right' || joinType === 'full') {
    const joinParsedData = joinTableData.map((row) => extractFullRow(row, joinTable, joinAlias));
    const matchedSet = new Set(joinResults.map((row) => row[`${joinAlias}.${joinColumnName}`]));

    joinParsedData.forEach((joinRow) => {
      if (!matchedSet.has(joinRow[`${joinAlias}.${joinColumnName}`])) {
        joinResults.push({...getNullFilledRow(mainTable, mainAlias), ...joinRow});
      }
    });
  }

  return joinResults;
}

function sortMergeJoin(
  mainTableData,
  joinTableData,
  mainTable,
  joinTable,
  mainColumnName,
  joinColumnName,
  mainAlias,
  joinAlias,
  joinType
) {
  const joinResults = [];
  const unmatchedMain = [];
  const unmatchedJoin = [];

  const mainParsedData = mainTableData.map((row) => extractFullRow(row, mainTable, mainAlias));
  const joinParsedData = joinTableData.map((row) => extractFullRow(row, joinTable, joinAlias));

  mainParsedData.sort((a, b) => (a[`${mainAlias}.${mainColumnName}`] || '').localeCompare(b[`${mainAlias}.${mainColumnName}`] || ''));
  joinParsedData.sort((a, b) => (a[`${joinAlias}.${joinColumnName}`] || '').localeCompare(b[`${joinAlias}.${joinColumnName}`] || ''));

  let i = 0, j = 0;

  while (i < mainParsedData.length && j < joinParsedData.length) {
    const mainValue = mainParsedData[i][`${mainAlias}.${mainColumnName}`];
    const joinValue = joinParsedData[j][`${joinAlias}.${joinColumnName}`];

    if (mainValue === joinValue) {
      joinResults.push({...mainParsedData[i], ...joinParsedData[j]});
      i++;
      j++;
    } else if (mainValue < joinValue) {
      if (joinType === 'left' || joinType === 'full') {
        unmatchedMain.push(mainParsedData[i]);
      }
      i++;
    } else {
      if (joinType === 'right' || joinType === 'full') {
        unmatchedJoin.push(joinParsedData[j]);
      }
      j++;
    }
  }

  if (joinType === 'left' || joinType === 'full') {
    unmatchedMain.forEach((row) => joinResults.push({...row, ...getNullFilledRow(joinTable, joinAlias)}));
  }

  if (joinType === 'right' || joinType === 'full') {
    unmatchedJoin.forEach((row) => joinResults.push({...getNullFilledRow(mainTable, mainAlias), ...row}));
  }

  return joinResults;
}

function getNullFilledRow(table, alias) {
  const row = {};
  table.structure.attributes.forEach((attr) => {
    row[`${alias}.${attr.attributeName}`] = null;
  });
  return row;
}

function extractFullRow(document, table, alias) {
  const attributes = table.structure.attributes.map((attr) => attr.attributeName);
  const pkAttributes = table.primaryKey.pkAttributes;

  const pkValues = document._id.split('$');
  const valueParts = document.value.split('#');

  const row = {};
  let valueIndex = 0;

  attributes.forEach((attr, idx) => {
    const prefixedAttr = `${alias}.${attr}`;
    if (pkAttributes.includes(attr)) {
      row[prefixedAttr] = pkValues[pkAttributes.indexOf(attr)];
    } else {
      row[prefixedAttr] = valueParts[valueIndex];
      valueIndex++;
    }
  });

  return row;
}

module.exports = {performJoin, applyRemainingJoins};