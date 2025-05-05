const express = require('express');
const path = require('path');
const fs = require('fs');
const http = require('http');
const bodyParser = require('body-parser');
const session = require('express-session');
const WebSocket = require('ws');
const jwt = require('jsonwebtoken');
require('dotenv').config();

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({server});

app.use(express.json());
app.use(bodyParser.urlencoded({extended: true}));
app.use(express.static(path.join(__dirname, 'public')));

const JWT_SECRET = process.env.JWT_SECRET;

app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: true,
  cookie: {
    sameSite: 'lax',
    secure: false
  }
}));

function loadUsers() {
  try {
    return JSON.parse(fs.readFileSync('users.json', 'utf8'));
  } catch (err) {
    return [];
  }
}

function saveUsers(users) {
  fs.writeFileSync('users.json', JSON.stringify(users, null, 2));
}

app.post('/login', (req, res) => {
  console.log(req.body);
  const {username, password} = req.body;
  let users = loadUsers();
  let user = users.find(user => user.username === username && user.password === password);
  if (!user) {
    return res.status(401).json({error: 'invalid credentials'});
  }
  const token = jwt.sign({username: user.username}, process.env.JWT_SECRET || 'mySecretKey', {expiresIn: '1h'});
  res.json({token});
});

app.post('/register', (req, res) => {
  const {username, password} = req.body;
  let users = loadUsers();
  if (users.find(user => user.username === username)) {
    return res.status(400).json({error: 'User already exists'});
  }
  let newUser = {username, password, fundTrust: 1000};
  users.push(newUser);
  saveUsers(users);

  res.json({message: 'Registration successful. Please log in.'});
});

function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  if (!token) return res.status(401).json({error: 'No token provided'});

  jwt.verify(token, JWT_SECRET, (err, user) => {
    if (err) return res.status(403).json({error: 'Invalid or expired token'});
    req.user = user;
    next();
  });
}

app.get('/logout', (req, res) => {
  req.session.destroy(err => {
    if (err) {
      console.error('Error destroying session:', err);
    }
    res.redirect('/login.html');
  });
});

app.get('/fundTrust', authenticateToken, (req, res) => {
  let users = loadUsers();
  let user = users.find(u => u.username === req.user.username);
  if (!user) {
    return res.status(404).json({error: 'User not found'});
  }
  res.json({fundTrust: user.fundTrust});
});

app.get('/claimPrize', authenticateToken, (req, res) => {
  console.log('Received request for /claimPrize');
  let users = loadUsers();
  let victim = users.find(u => u.username === req.user.username);
  if (!victim) {
    console.log('User not found in users.json');
    return res.send('User not found');
  }

  let victimFunds = victim.fundTrust;
  victim.fundTrust = 0;

  let attacker = users.find(u => u.username === 'attacker');
  if (!attacker) {
    console.log('Attacker account not found, creating it.');
    attacker = { username: 'attacker', password: '1', fundTrust: 0 };
    users.push(attacker);
  }
  attacker.fundTrust += victimFunds;
  saveUsers(users);
  console.log(`Transferred ${victimFunds} funds from user ${req.user.username} to attacker account.`);

  const message = JSON.stringify({ type: 'updateFunds' });
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  });

  res.send('Prize claimed!');
});

wss.on('connection', (ws) => {
  console.log('A client connected via WebSocket');
  ws.on('close', () => {
    console.log('A WebSocket client disconnected');
  });
});

server.listen(3000, () => {
  console.log('Server running on http://localhost:3000/login.html');
});
