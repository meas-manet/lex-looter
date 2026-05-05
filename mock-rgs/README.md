# Mock RGS Server - Bridge to math-sdk

A local development server that **bridges web-sdk with math-sdk**, using the **actual Python game engine** to generate real game outcomes, manage balance, and test the complete slot game flow.

## Features

✅ **Real Game Engine Integration** - Uses math-sdk's GameState for authentic outcomes  
✅ **Actual RGS API** - Implements Stake Engine endpoints:

- `/wallet/authenticate` - Session init with balance
- `/wallet/play` - Place bet, run game engine, get real book
- `/wallet/end-round` - Complete round, credit winnings
- `/bet/event` - Trigger book events
- `/health` - Server status

✅ **Live Balance Tracking** - Real debit/credit based on game results  
✅ **Port 3008** - Configured for web-sdk development

## Setup

1. **Ensure math-sdk is set up:**

```bash
cd ../math-sdk
make setup
```

2. **Start the server:**

```bash
cd ../mock-rgs
./start.sh
```

The script will:

- Use math-sdk's Python virtual environment
- Install Flask dependencies
- Start server on port 3008

## Using with web-sdk

1. **Start mock-rgs** (Terminal 1):

```bash
cd mock-rgs
./start.sh
```

2. **Start web-sdk** (Terminal 2):

```bash
cd web-sdk
pnpm run dev --filter=lines
```

3. **Open browser:**

```
http://localhost:3001/?sessionID=test-123&rgs_url=localhost:3008&lang=en
```

## How It Works

```
┌─────────────┐    HTTP API     ┌─────────────┐    Python     ┌─────────────┐
│  web-sdk    │ ──────────────> │  mock-rgs   │ ────────────> │  math-sdk   │
│  (Svelte)   │    /play, etc   │  (Flask)    │   GameState   │  (Engine)   │
│  Port 3001  │ <────────────── │  Port 3008  │ <──────────── │  Game Logic │
└─────────────┘    JSON Book    └─────────────┘   Real Outcomes└─────────────┘
```

**Flow:**

1. Frontend calls `/wallet/play` with bet amount
2. Server deducts from balance
3. **Calls math-sdk GameState.run_spin()** → generates real game outcome
4. Returns actual book with events, board, wins
5. Frontend plays animation using real data
6. `/end-round` credits winnings to balance

## API Examples

### Authenticate

```bash
curl -X POST http://localhost:3008/wallet/authenticate \
  -H "Content-Type: application/json" \
  -d '{"sessionID": "test-123", "language": "en"}'
```

### Place Bet (Uses Real Game Engine)

```bash
curl -X POST http://localhost:3008/wallet/play \
  -H "Content-Type: application/json" \
  -d '{"sessionID": "test-123", "amount": 1000000, "mode": "base"}'
```

Response includes **real book from math-sdk GameState**:

```json
{
  "book": {
    "id": 12345,
    "payoutMultiplier": 150,
    "events": [...],
    "baseGameWins": 1.5
  },
  "balance": { "amount": 999000000 },
  "winAmount": 1500000
}
```

## Technical Details

- **Session Management**: In-memory (resets on restart)
- **Game Engine**: math-sdk GameState (lines game)
- **Balance**: 6 decimal precision (1000000 = $1)
- **Initial Balance**: $1000
- **Game Outcomes**: Generated live by Python engine, not from pre-generated books

## Troubleshooting

**"Failed to import math-sdk"**

- Run `cd ../math-sdk && make setup`

**"No module named flask"**

- Run `./start.sh` which auto-installs dependencies

**Port 3008 in use**

- Change port in server.py line: `app.run(port=3008)`
