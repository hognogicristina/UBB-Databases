const {TableClient} = require("@azure/data-tables");

const connectionString = process.env.AzureWebJobsStorage;
const tableName = "BookFeedback";

module.exports = async function (context, req) {
  try {
    const client = TableClient.fromConnectionString(connectionString, tableName);
    const results = [];
    const entities = client.listEntities({
      queryOptions: {filter: `PartitionKey eq 'books'`},
    });

    for await (const entity of entities) {
      results.push({
        rowKey: entity.rowKey,
        title: entity.title || "Unknown",
        author: entity.author || "Unknown",
        feedback: entity.feedback || "",
        createdAt: entity.createdAt || null,
        updatedAt: entity.updatedAt || null
      });
    }

    results.sort((a, b) => {
      const dateA = new Date(a.updatedAt || a.createdAt);
      const dateB = new Date(b.updatedAt || b.createdAt);
      return dateB - dateA;
    });

    context.res = {
      status: 200,
      headers: {"Content-Type": "application/json"},
      body: results
    };
  } catch (err) {
    context.log.error("getEntries failed:", err.message, err.stack);
    context.res = {
      status: 500,
      body: `Server error: ${err.message}`
    };
  }
};