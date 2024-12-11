function checkExistingIndex(table, indexName) {
  const existingIndex = table.indexFiles.some(index => index.indexName === indexName);
  if (existingIndex) return `ERROR: Index with the name ${indexName} already exists on table ${table.tableName}`;
}

async function validateDuplicatePK(collection, tableName, pkValue) {
  const existingDocument = await collection.findOne({_id: pkValue});
  if (existingDocument) {
    return `ERROR: Duplicate primary key ${pkValue} in table ${tableName}`;
  }
}

async function checkExistingUniqueIndex(table, fields, databaseName, client) {
  const db = client.db(databaseName);
  const collections = await db.listCollections().toArray();
  const indexCollections = collections.filter(collection =>
    collection.name.includes(`${table.tableName}_idx_`)
  );

  for (const indexCollection of indexCollections) {
    const match = indexCollection.name.match(/idx_(.+)$/);
    const indexName = match ? match[1] : null;

    const index = table.indexFiles.find(index => index.indexName === indexName);
    const indexCollectionData = db.collection(indexCollection.name);

    if (index && index.isUnique) {
      const indexAttributes = index.indexAttributes;

      const compositeKey = indexAttributes.length === 1
        ? fields[indexAttributes[0]]
        : indexAttributes.map(attr => fields[attr]).join('$');

      const existingIndex = await indexCollectionData.findOne({_id: compositeKey});
      if (existingIndex) {
        return `ERROR: Unique index ${indexName} already contains the value ${compositeKey}`;
      }
    }
  }

  return null;
}

module.exports = {checkExistingIndex, validateDuplicatePK, checkExistingUniqueIndex};
