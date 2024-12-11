const {MongoClient} = require('mongodb');
const config = require('../config');

const client = new MongoClient(config.mongoUri);

async function connectMongo() {
  try {
    await client.connect();
    console.log(`Connected to MongoDB`);
  } catch (err) {
    console.error('MongoDB connection error:', err);
  }
}

module.exports = {client, connectMongo};
