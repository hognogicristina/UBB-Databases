const {TableClient} = require("@azure/data-tables");

const connectionString = process.env.AzureWebJobsStorage;
const tableName = "BookFeedback";

module.exports = async function (context, req) {
  try {
    const {rowKey, title, author, feedback} = req.body;

    if (!rowKey || !title || !author || !feedback) {
      context.res = {
        status: 400,
        body: "Missing required fields",
      };
      return;
    }

    const client = TableClient.fromConnectionString(connectionString, tableName);
    const existing = await client.getEntity("books", rowKey);

    const updated = {
      ...existing,
      title,
      author,
      feedback,
      updatedAt: new Date().toISOString(),
    };

    await client.updateEntity(updated, "Replace");

    context.res = {
      status: 200,
      headers: {
        "Content-Type": "application/json"
      },
      body: {message: "Entry updated", rowKey}
    };
  } catch (err) {
    context.res = {
      status: 500,
      body: `Server error: ${err.message}`
    };
  }
};