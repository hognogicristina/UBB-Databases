const {client} = require('../../db/mongoConnection');
const fs = require("fs");
const path = require("path");
const SELECT_FILE_PATH = path.join(process.cwd(), 'select.txt');

function useIndexes(table, whereConditions) {
  if (!Array.isArray(whereConditions)) {
    if (whereConditions && typeof whereConditions === 'object') {
      whereConditions = [whereConditions];
    } else {
      return [];
    }
  }

  if (whereConditions.length === 0) {
    return [];
  }
  return whereConditions.map((cond) => {
    if (!cond || !cond.attribute) return null;

    const compositeIndex = table.indexFiles.find((index) => index.indexAttributes.length > 1 && index.indexAttributes.includes(cond.attribute));
    if (compositeIndex) {
      const relevantConditions = whereConditions.filter((wc) => compositeIndex.indexAttributes.includes(wc.attribute));
      const canUseCompositeIndex = relevantConditions.every((cond) =>
        compositeIndex.indexAttributes.includes(cond.attribute)
      );
      if (canUseCompositeIndex) {
        return {
          indexName: compositeIndex.indexName, conditions: relevantConditions, isComposite: true,
        };
      }
    }

    const singleIndex = table.indexFiles.find((index) => index.indexAttributes.includes(cond.attribute));

    if (singleIndex) {
      return {
        indexName: singleIndex.indexName, value: cond.value, operator: cond.operator,
      };
    }

    return null;
  }).filter(Boolean);
}

async function indexConditionQuery(indexCond, indexCollection, query) {
  if (indexCond.operator === '=') {
    query = {_id: indexCond.value};
  } else if (indexCond.operator === 'LIKE') {
    const value = indexCond.value.replace(/'/g, '');
    let regex;
    if (value.startsWith('%') && value.endsWith('%')) {
      regex = new RegExp(value.slice(1, -1), 'i');
    } else if (value.startsWith('%')) {
      regex = new RegExp(`${value.slice(1)}$`, 'i');
    } else if (value.endsWith('%')) {
      regex = new RegExp(`^${value.slice(0, -1)}`, 'i');
    } else {
      regex = new RegExp(`^${value}$`, 'i');
    }
    query = {_id: {$regex: regex}};
  }
  return await indexCollection.find(query).toArray();
}

async function fetchDocuments(table, whereConditions, currentDatabase) {
  const db = client.db(currentDatabase);
  const collection = db.collection(table.fileName);
  whereConditions = Array.isArray(whereConditions) ? whereConditions : [whereConditions];
  const indexedConditions = useIndexes(table, whereConditions);

  let pkSets = [];
  for (const indexCond of indexedConditions) {
    const indexCollection = db.collection(`${currentDatabase}_${table.tableName}_idx_${indexCond.indexName}`);

    if (indexCond.isComposite) {
      const compositeAttributes = table.indexFiles.find(
        (index) => index.indexName === indexCond.indexName
      ).indexAttributes;

      const relevantConditions = indexCond.conditions
        .filter((cond) => compositeAttributes.includes(cond.attribute))
        .sort((a, b) => compositeAttributes.indexOf(a.attribute) - compositeAttributes.indexOf(b.attribute));

      const compositeResults = await indexCollection.find().toArray();
      const filteredPrimaryKeys = compositeResults
        .filter((doc) => {
          const compositeValues = doc._id.split('$');
          return relevantConditions.every((cond) => {
            const attrIndex = compositeAttributes.indexOf(cond.attribute);
            if (attrIndex === -1) return false;

            const value = compositeValues[attrIndex];
            if (cond.operator === '=') return value === cond.value;
            if (cond.operator === '>') return parseFloat(value) > parseFloat(cond.value);
            if (cond.operator === '>=') return parseFloat(value) >= parseFloat(cond.value);
            if (cond.operator === '<') return parseFloat(value) < parseFloat(cond.value);
            if (cond.operator === '<=') return parseFloat(value) <= parseFloat(cond.value);

            if (cond.operator === 'LIKE') {
              const likeValue = cond.value.replace(/'/g, '');
              let regex;

              if (likeValue.startsWith('%') && likeValue.endsWith('%')) {
                regex = new RegExp(likeValue.slice(1, -1), 'i');
              } else if (likeValue.startsWith('%')) {
                regex = new RegExp(`${likeValue.slice(1)}$`, 'i');
              } else if (likeValue.endsWith('%')) {
                regex = new RegExp(`^${likeValue.slice(0, -1)}`, 'i');
              } else {
                regex = new RegExp(`^${likeValue}$`, 'i');
              }

              return regex.test(value);
            }

            return false;
          });
        })
        .map((doc) => doc.value.split('#'))
        .flat();

      if (filteredPrimaryKeys.length > 0) {
        pkSets.push(new Set(filteredPrimaryKeys));
      }
    } else {
      const indexResults = await indexConditionQuery(indexCond, indexCollection, {});
      if (indexResults.length > 0) {
        const primaryKeys = indexResults
          .map((doc) => {
            if (typeof doc.value === 'string') {
              return doc.value.includes('#') ? doc.value.split('#') : [doc.value];
            }
            return [];
          })
          .flat();
        pkSets.push(new Set(primaryKeys));
      }
    }

    if (['>', '>=', '<', '<='].includes(indexCond.operator)) {
      const allIndexResults = await indexCollection.find().toArray();

      const filteredPrimaryKeys = allIndexResults
        .filter((doc) => {
          const value = parseFloat(doc._id);
          const conditionValue = parseFloat(indexCond.value);

          if (indexCond.operator === '=') return value === conditionValue;
          if (indexCond.operator === '>') return value > conditionValue;
          if (indexCond.operator === '>=') return value >= conditionValue;
          if (indexCond.operator === '<') return value < conditionValue;
          if (indexCond.operator === '<=') return value <= conditionValue;

          return false;
        })
        .map((doc) => {
          if (typeof doc.value === 'string') {
            return doc.value.includes('#') ? doc.value.split('#') : [doc.value];
          }
          return [];
        })
        .flat();

      if (filteredPrimaryKeys.length > 0) {
        pkSets.push(new Set(filteredPrimaryKeys));
      }
    }
  }

  let commonPrimaryKeys = [];
  if (pkSets.length > 0) {
    commonPrimaryKeys = Array.from(
      pkSets.reduce((acc, set) => {
        if (acc === null) return set;
        return new Set([...acc].filter((key) => set.has(key)));
      }, null)
    );
  }


  let results = [];
  if (commonPrimaryKeys.length > 0) {
    results = await collection.find({_id: {$in: commonPrimaryKeys}}).toArray();
  } else if (indexedConditions.length === 0) {
    results = await collection.find().toArray();
  }

  return results;
}

async function applyProjection(results, columns, table, whereConditions, currentDatabase, isJoinOperation) {
  const attributeNames = table.structure.attributes.map(attr => attr.attributeName);
  const primaryKeys = table.primaryKey.pkAttributes;

  const db = client.db(currentDatabase);
  const collection = db.collection(table.fileName);

  whereConditions = Array.isArray(whereConditions) ? whereConditions : [whereConditions];
  const nonIndexedConditions = whereConditions.filter(
    (cond) => !table.indexFiles.some((index) => index.indexAttributes.includes(cond.attribute))
  );

  if (nonIndexedConditions.length > 0 && !isJoinOperation) {
    const allDocuments = await collection.find({}, {projection: {_id: 1, value: 1}}).toArray();

    const parsedDocuments = allDocuments.map((doc) => {
      const attributeMap = {};
      const pkValues = doc._id.split('$');
      primaryKeys.forEach((pkAttr, idx) => {
        if (columns.includes(pkAttr) || columns.includes('*')) {
          attributeMap[pkAttr] = pkValues[idx];
        }
      });

      const values = doc.value.split('#');
      primaryKeys.forEach((pkAttr, idx) => {
        values.unshift(pkValues[idx]);
      });

      attributeNames.forEach((attr, idx) => {
        attributeMap[attr] = values[idx];
      });

      return {
        _id: doc._id,
        ...attributeMap,
      }
    });

    const filteredDocuments = parsedDocuments.filter((doc) =>
      nonIndexedConditions.every((cond) => {
        const attrValue = doc[cond.attribute];
        if (cond.operator === '=') return attrValue == cond.value;
        if (cond.operator === '>') return attrValue > cond.value;
        if (cond.operator === '>=') return attrValue >= cond.value;
        if (cond.operator === '<') return attrValue < cond.value;
        if (cond.operator === '<=') return attrValue <= cond.value;
        if (cond.operator === 'LIKE') {
          const value = cond.value.replace(/'/g, '');
          if (value.startsWith('%') && value.endsWith('%')) {
            return new RegExp(value.slice(1, -1), 'i').test(attrValue);
          } else if (value.startsWith('%')) {
            return new RegExp(`${value.slice(1)}$`, 'i').test(attrValue);
          } else if (value.endsWith('%')) {
            return new RegExp(`^${value.slice(0, -1)}`, 'i').test(attrValue);
          } else {
            return new RegExp(`^${value}$`, 'i').test(attrValue);
          }
        }
        return false;
      })
    );

    if (results.length > 0) {
      const indexedIds = new Set(results.map((doc) => doc._id));
      results = filteredDocuments.filter((doc) => indexedIds.has(doc._id));
    } else if (results.length === 0) {
      results = filteredDocuments;
    }
  }

  return results.map(result => {
    const projected = {};
    if (nonIndexedConditions.length === 0 && !isJoinOperation) {
      const pkValues = result._id.split('$');
      primaryKeys.forEach((pkAttr, idx) => {
        if (columns.includes(pkAttr) || columns.includes('*')) {
          projected[pkAttr] = pkValues[idx];
        }
      });

      const values = result.value.split('#');
      primaryKeys.forEach((pkAttr, idx) => {
        values.unshift(pkValues[idx]);
      });

      const attributeMap = {};
      attributeNames.forEach((attr, idx) => {
        attributeMap[attr] = values[idx];
      });

      columns.forEach(col => {
        if (primaryKeys.includes(col) && !columns.includes('*')) return;
        if (col in attributeMap || columns.includes('*')) {
          projected[col] = attributeMap[col];
        }
      });
    } else {
      columns.forEach(col => {
        if (col in result || columns.includes('*')) {
          projected[col] = result[col] !== undefined ? result[col] : null;
        }
      });
    }

    return projected;
  });
}

function removeDuplicates(results) {
  const uniqueResults = [];
  const seen = new Set();

  results.forEach(row => {
    const rowString = JSON.stringify(row);
    if (!seen.has(rowString)) {
      seen.add(rowString);
      uniqueResults.push(row);
    }
  });

  return uniqueResults;
}

function writeResultsToFile(results, columns, databaseName, tableName) {
  fs.writeFileSync(SELECT_FILE_PATH, '', 'utf8');
  const fileStream = fs.createWriteStream(SELECT_FILE_PATH, {flags: 'a'});

  fileStream.write(`For ${databaseName} table ${tableName}:\n`);
  results.forEach(result => {
    const row = columns.map(col => `"${result[col] || ''}"`).join(', ');
    fileStream.write(`${row}\n`);
  });

  fileStream.end();
}

function whereCond(result, whereConditions) {
  return result.filter((row) =>
    whereConditions.every((cond) => {
      const columnNameWithAlias = Object.keys(row).find((key) =>
        key.endsWith(`.${cond.attribute}`)
      );
      const value = row[columnNameWithAlias]?.replace(/'/g, '').trim();

      switch (cond.operator) {
        case '=':
          return value === cond.value;
        case '>':
          return value > cond.value;
        case '>=':
          return value >= cond.value;
        case '<':
          return value < cond.value;
        case '<=':
          return value <= cond.value;
        case 'LIKE': {
          const likeValue = cond.value.replace(/'/g, '');
          if (likeValue.startsWith('%') && likeValue.endsWith('%')) {
            return new RegExp(likeValue.slice(1, -1), 'i').test(value);
          } else if (likeValue.startsWith('%')) {
            return new RegExp(`${likeValue.slice(1)}$`, 'i').test(value);
          } else if (likeValue.endsWith('%')) {
            return new RegExp(`^${likeValue.slice(0, -1)}`, 'i').test(value);
          } else {
            return new RegExp(`^${likeValue}$`, 'i').test(value);
          }
        }
        default:
          return false;
      }
    })
  );
}

module.exports = {
  fetchDocuments,
  applyProjection,
  removeDuplicates,
  writeResultsToFile,
  whereCond
};
