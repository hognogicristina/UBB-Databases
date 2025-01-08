async function updateIndexes(table, fields, currentDatabase, client) {
  const primaryKey = table.primaryKey.pkAttributes;
  const pkValue = primaryKey.map(attr => fields[attr]).join("$");
  const indexes = table.indexFiles;

  for (const index of indexes) {
    const collectionName = `${currentDatabase}_${table.tableName}_idx_${index.indexName}`;

    const collections = await client.db(currentDatabase).listCollections().toArray();
    const hasFkCollection = collections.some((col) => col.name.includes("_fk_"));
    if (hasFkCollection) continue;

    const collection = client.db(currentDatabase).collection(collectionName);
    const indexKey = index.indexAttributes
      .map(attr => fields[attr] || '')
      .join("$");

    if (index.isUnique) {
      await collection.insertOne({_id: indexKey, value: pkValue});
    } else {
      const existingEntry = await collection.findOne({_id: indexKey});

      if (!existingEntry) {
        await collection.insertOne({_id: indexKey, value: pkValue});
      } else {
        const updatedValue = `${existingEntry.value}#${pkValue}`;
        await collection.updateOne(
          {_id: indexKey},
          {$set: {value: updatedValue}}
        );
      }
    }
  }
}

async function updateIndexFK(table, fields, currentDatabase, client) {
  const primaryKey = table.primaryKey.pkAttributes;
  const pkValue = primaryKey.map(attr => fields[attr]).join("$");

  for (const foreignKey of table.foreignKeys) {
    const refTable = foreignKey.references.refTable;
    const indexName = `${table.fileName}_fk_${refTable}_${foreignKey.fkAttributes.join('_')}.ind`;

    const collections = await client.db(currentDatabase).listCollections().toArray();
    const hasIdxCollection = collections.some((col) => col.name.includes("_idx_"));
    if (hasIdxCollection) continue;

    const collectionsList = await client.db(currentDatabase).listCollections({name: indexName}).toArray();
    if (collectionsList.length === 0) continue;

    const indexCollection = client.db(currentDatabase).collection(indexName);
    const nonUniqKey = foreignKey.fkAttributes.map(attr => fields[attr] || '').join("$");
    const existingEntry = await indexCollection.findOne({_id: nonUniqKey});

    if (!existingEntry) {
      await indexCollection.insertOne({
        _id: nonUniqKey,
        value: pkValue
      });
    } else {
      const updatedValue = `${existingEntry.value}#${pkValue}`;
      await indexCollection.updateOne(
        {_id: nonUniqKey},
        {$set: {value: updatedValue}}
      );
    }
  }
}

module.exports = {updateIndexes, updateIndexFK};