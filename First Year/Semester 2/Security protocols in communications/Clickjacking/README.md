# Clickjacking Demo: The Invisible Threat Behind a Simple Click

This project demonstrates a **Clickjacking attack** through a simulated shopping web application and a malicious attacker page. It shows how a user's actions can be invisibly hijacked to perform unintended operations — like transferring their entire fund balance — without their knowledge.

## Project Purpose

This educational demo is intended to:

- Simulate a realistic login and shopping flow for a fake e-commerce platform.
- Demonstrate a clickjacking exploit via a transparent iframe.
- Visualize fund theft and reflect it in real-time using WebSocket updates.
- Showcase authentication via JWT, simple session handling, and front-end manipulation.

## Features

### Legitimate Site (`localhost:3000`)
- User **registration**, **login**, and **logout**
- Fund tracking with an initial **fund trust** of €1000
- Real-time **WebSocket updates** when funds are modified
- A `Claim Prize` button that triggers a hidden transfer to the attacker

### Attacker Page (`attacker.html`)
- Invisible iframe points to the `/claim.html` route
- Triggers a **hidden click** on the prize button
- Steals funds by calling the backend `/claimPrize` route on behalf of the user

### Backend (Node.js + Express)
- Secure authentication using **JWT**
- Simulated **fund storage** using `users.json`
- WebSocket (`ws`) server broadcasts fund updates
- Routes protected by token middleware

## Project Structure

```
clickjacking/
├── public/
│   ├── login.html
│   ├── register.html
│   ├── shopping.html
│   ├── attacker.html
│   ├── claim.html
│   ├── style.css
│   └── images/
├── server.js
├── users.json
├── .env
├── package.json
└── README.md
````

## Installation & Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/clickjacking-demo.git
   cd clickjacking-demo

2. **Install dependencies:**

   ```bash
   npm install
   ```

3. **Create a `.env` file:**

   ```env
   SESSION_SECRET=yourSecretSessionKey
   JWT_SECRET=yourSecretJWTKey
   ```

4. **Start the server:**

   ```bash
   npm start
   ```

5. **Open your browser:**

   ```
   http://localhost:3000/login.html
   ```

## Authentication Flow

* On login, the server issues a **JWT token** valid for 1 hour.
* This token is stored in `localStorage` on the client.
* All protected routes use the token via `Authorization: Bearer <token>` header.
* WebSocket is used to update client-side UI when funds are stolen.

## The Attack Explained

1. **Victim logs into the shopping site and is authenticated via JWT.**
2. **Attacker tricks victim into visiting `attacker.html`.**
3. `attacker.html` loads an **invisible iframe** over the malicious `Transfer Trust Fund` button.
4. When the user clicks, they **actually click the iframe**, which calls `/claimPrize`.
5. Server drains victim's funds and transfers them to the `attacker` account.
6. Victim’s UI is updated after 10 seconds with a "Your funds have been stolen!" message.

## Default Users

The `users.json` file contains:

```json
[
  {
    "username": "attacker",
    "password": "1",
    "fundTrust": 0
  },
  {
    "username": "a",
    "password": "a",
    "fundTrust": 10000
  }
]
```

You can register new users through the UI or edit `users.json` manually.

## WebSocket Usage

WebSocket is used to notify the frontend when a fund transfer occurs. This simulates real-time updates that would occur in a real banking/shopping app.

* The server sends `{ type: 'updateFunds' }` to all clients upon `/claimPrize`.

## Security Discussion

### The Clickjacking Attack Works Because:

* No `X-Frame-Options` or `Content-Security-Policy` headers are set.
* The `claim.html` route is iframe-able by default.
* Buttons are predictable and placed in known positions.
* There's no confirmation or CAPTCHA on critical actions.

### How to Prevent It:

* Add `X-Frame-Options: DENY` or `SAMEORIGIN` header.
* Use Content Security Policy (`Content-Security-Policy: frame-ancestors 'none'`).
* Implement UI confirmation for sensitive operations.
* Use **double-submit cookies**, **same-site cookies**, and **CSP** for extra protection.

## Possible Improvements

* Save transaction history (e.g. fund transfers) to `transactions.json`.
* Add CAPTCHA or 2FA for critical routes.
* Implement CSRF tokens in addition to JWT.
* Add WebSocket-based real-time attacker/victim UI for more dramatic demos.
* Extend the attacker page with visual decoys (e.g. fake "Win an iPhone!" ad).
