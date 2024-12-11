const {client} = require("../../db/mongoConnection");

async function deleteForeignKeyEntries(table, pkValue, databaseName, client) {
  const db = client.db(databaseName);
  const collections = await db.listCollections().toArray();

  const fkCollections = collections.filter(collection => collection.name.includes(`${table.fileName}_fk_`));
  const indexCollections = collections.filter(collection => collection.name.includes(`${table.tableName}_idx_`));

  const removePkFromValue = (value, pkValue) => {
    const parts = value.split('#').filter(val => val !== pkValue);
    return parts.join('#');
  };

  for (const indexCollection of indexCollections) {
    const indexCollectionData = db.collection(indexCollection.name);
    const entries = await indexCollectionData.find().toArray();

    for (const entry of entries) {
      if (entry.value === pkValue) {
        await indexCollectionData.deleteOne({ _id: entry._id });
      } else if (entry.value.includes('#')) {
        const updatedValue = removePkFromValue(entry.value, pkValue);

        if (updatedValue) {
          await indexCollectionData.updateOne(
            { _id: entry._id },
            { $set: { value: updatedValue } }
          );
        } else {
          await indexCollectionData.deleteOne({ _id: entry._id });
        }
      }
    }
  }

  for (const fkCollection of fkCollections) {
    const indexCollection = db.collection(fkCollection.name);
    const entries = await indexCollection.find().toArray();

    for (const entry of entries) {
      if (entry.value === pkValue) {
        await indexCollection.deleteOne({ _id: entry._id });
      } else if (entry.value.includes('#')) {
        const updatedValue = removePkFromValue(entry.value, pkValue);

        if (updatedValue) {
          await indexCollection.updateOne(
            { _id: entry._id },
            { $set: { value: updatedValue } }
          );
        } else {
          await indexCollection.deleteOne({ _id: entry._id });
        }
      }
    }
  }

  return null;
}

async function dropTable(table, databaseName) {
  const db = client.db(databaseName);
  const collections = await db.listCollections().toArray();
  const fkCollections = collections.filter(collection => collection.name.includes(`${table.fileName}_fk_`));
  const indexCollections = collections.filter(collection => collection.name.includes(`${table.tableName}_idx_`));

  for (const indexCollection of indexCollections) {
    const indexCollectionData = db.collection(indexCollection.name);
    await indexCollectionData.drop();
  }

  for (const fkCollection of fkCollections) {
    const indexCollection = db.collection(fkCollection.name);
    await indexCollection.drop();
  }

  return null;
}

module.exports = {deleteForeignKeyEntries, dropTable};