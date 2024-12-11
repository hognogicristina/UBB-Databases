const fs = require('fs');
const catalogFile = 'Catalog.json';

let catalog = {};
if (fs.existsSync(catalogFile)) {
  catalog = JSON.parse(fs.readFileSync(catalogFile));
} else {
  catalog = {databases: []};
  saveCatalog();
}

function saveCatalog() {
  fs.writeFileSync(catalogFile, JSON.stringify(catalog, null, 4));
}

module.exports = {catalog, saveCatalog};
