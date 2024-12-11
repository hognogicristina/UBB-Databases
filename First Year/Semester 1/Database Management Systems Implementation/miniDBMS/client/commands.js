function processCommand(command, client, rl) {
  if (command === 'exit') {
    client.write(command);
    client.end();
    rl.close();
  } else {
    client.write(command);
  }
}

module.exports = {processCommand};
