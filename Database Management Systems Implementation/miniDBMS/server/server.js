const net = require('net');
const {handleCommand} = require('./handlers/commandHandler');
const {connectMongo} = require('./db/mongoConnection');
const config = require('./config');

connectMongo();

const server = net.createServer((socket) => {
  socket.on('data', (data) => {
    const command = data.toString().trim().split(' ');
    handleCommand(command, socket);
  });
  socket.on('end', () => {
    console.log(`Client disconnected`);
  });
});

server.listen(config.port, '127.0.0.1', () => {
  console.log(`Server listening on port ${config.port}`);
});
