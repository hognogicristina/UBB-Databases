const {TableClient} = require("@azure/data-tables");

const connectionString = process.env.AzureWebJobsStorage;
const tableName = "BookFeedback";

module.exports = async function (context, req) {
  try {
    const rowKey = req.query.rowKey || (req.body && req.body.rowKey);

    if (!rowKey) {
      context.res = {
        status: 400,
        body: "Missing rowKey",
      };
      return;
    }

    const client = TableClient.fromConnectionString(connectionString, tableName);
    await client.deleteEntity("books", rowKey);

    context.res = {
      status: 200,
      headers: {
        "Content-Type": "application/json"
      },
      body: {message: `Entry ${rowKey} deleted`}
    };
  } catch (err) {
    context.res = {
      status: 500,
      body: `Server error: ${err.message}`
    };
  }
};
