const {catalog} = require('../../db/catalog');
const {setCurrentDatabase} = require('../../db/dbState');

function handleUse(command, socket) {
  const dbName = command[1];
  const database = catalog.databases.find(db => db.dataBaseName === dbName);

  if (database) {
    setCurrentDatabase(dbName);
    socket.write(`Using database ${dbName}`);
  } else {
    socket.write(`ERROR: Database ${dbName} does not exist`);
  }
}

module.exports = {handleUse};
