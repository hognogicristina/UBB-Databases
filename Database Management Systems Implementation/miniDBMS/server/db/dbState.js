let currentDatabase = null;

function setCurrentDatabase(dbName) {
  currentDatabase = dbName;
}

function getCurrentDatabase() {
  return currentDatabase;
}

module.exports = {setCurrentDatabase, getCurrentDatabase};
