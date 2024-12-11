const {catalog} = require("../../db/catalog");
const {getCurrentDatabase} = require("../../db/dbState");

function checkDatabase(dbName) {
  if (!dbName) return `ERROR: Database name required`;
  if (catalog.databases.find(db => db.dataBaseName === dbName)) return `ERROR: Database ${dbName} already exists`;
  return null;
}

function checkDatabaseExists(dbName) {
  const dbIndex = catalog.databases.findIndex(db => db.dataBaseName === dbName);
  return dbIndex === -1 ? `ERROR: Database ${dbName} does not exist` : dbIndex;
}

function checkDatabaseSelection() {
  const currentDatabase = getCurrentDatabase();
  if (!currentDatabase) return `ERROR: No database selected`;
}

module.exports = {checkDatabase, checkDatabaseExists, checkDatabaseSelection};