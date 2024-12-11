async function checkExistingFK(table, fields, currentDatabase, client) {
  for (const fk of table.foreignKeys) {
    const refTable = fk.references.refTable;
    const refCollection = client.db(currentDatabase).collection(`${currentDatabase}_${refTable}`);
    const fkValue = fk.fkAttributes.map(attr => fields[attr]).join("$");
    const refDoc = await refCollection.findOne({_id: fkValue});

    if (!refDoc) {
      return `ERROR: Foreign key constraint violation. No record found in table ${refTable}`;
    }
  }
}

async function checkUseOfExistingFK(table, databaseName, client) {
  const db = client.db(databaseName);
  const collections = await db.listCollections().toArray();

  const fkCollections = collections.filter(collection =>
    collection.name.includes(`_fk_${table.tableName}`)
  );

  const referencingTables = fkCollections.map(collection => {
    const match = collection.name.match(new RegExp(`^${databaseName}_(.+?)_fk_`));
    return match ? match[1] : null;
  }).filter(Boolean);

  if (referencingTables.length > 0) {
    return `ERROR: Table '${table.tableName}' is being referenced by the following tables: ${referencingTables.join(', ')}`;
  }

  return null;
}

async function checkForeignKeyReferences(table, pkValue, databaseName, client) {
  const db = client.db(databaseName);
  const collections = await db.listCollections().toArray();
  const fkCollections = collections.filter(collection =>
    collection.name.includes(`_fk_${table.tableName}`)
  );

  const referencedTables = [];

  for (const fkCollection of fkCollections) {
    const indexCollection = db.collection(fkCollection.name);
    const existingReference = await indexCollection.findOne({
      value: {$regex: `(^|[#\$])${pkValue}([#\$]|$)`}
    });

    if (existingReference) {
      const match = fkCollection.name.match(new RegExp(`^${databaseName}_(.+?)_fk_`));
      const referencedTable = match ? match[1] : null;

      if (referencedTable) {
        referencedTables.push(referencedTable);
      }
    }
  }

  if (referencedTables.length > 0) {
    return `ERROR: Table '${table.tableName}' with id '${pkValue}' is referenced in the following tables: ${referencedTables.join(', ')}`;
  }

  return null;
}

module.exports = {checkExistingFK, checkUseOfExistingFK, checkForeignKeyReferences};