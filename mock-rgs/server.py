"""Mock RGS Server - Bridge between web-sdk and math-sdk."""

import sys
import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add math-sdk to path
MATH_SDK_PATH = os.path.join(os.path.dirname(__file__), '..', 'math-sdk')
GAME_ID = os.getenv('MATH_SDK_GAME_ID', 'lexlooter')
GAME_PATH = os.path.join(MATH_SDK_PATH, 'games', GAME_ID)
sys.path.insert(0, MATH_SDK_PATH)
sys.path.insert(0, GAME_PATH)

# Import math-sdk game engine
try:
    from game_config import GameConfig
    from gamestate import GameState
    print("✅ Successfully imported math-sdk GameState")
except ImportError as e:
    print(f"❌ Failed to import math-sdk: {e}")
    GameConfig = None
    GameState = None

app = Flask(__name__)
CORS(app)  # Enable CORS for web-sdk frontend

# In-memory session storage
sessions = {}
game_instances = {}
INITIAL_BALANCE = 1000000000  # $1000 with 6 decimal precision


class Session:
    """Game session with real math-sdk integration."""
    
    def __init__(self, session_id):
        self.session_id = session_id
        self.balance = INITIAL_BALANCE
        self.currency = "USD"
        self.language = "en"
        self.current_bet_amount = None
        self.current_book = None
        self.current_book_raw = None
        self.round_active = False
        self.round_id = None
        self.win_amount = 0
        self.current_event_index = 0
        self.current_mode = 'BASE'
        self.game_state = None
        self.config = None
        
    def initialize_game(self):
        """Initialize math-sdk game instance."""
        if GameConfig and GameState and not self.config:
            try:
                self.config = GameConfig()
                self.game_state = GameState(self.config)
                print(f"✅ Initialized game for session {self.session_id}")
            except Exception as e:
                print(f"❌ Failed to initialize game: {e}")
    
    def run_game_round(self, sim_number=None, mode='base'):
        """Run actual game round using math-sdk."""
        if not self.game_state:
            self.initialize_game()
        
        if not self.game_state:
            return None
            
        try:
            import random as rnd
            if sim_number is None:
                sim_number = rnd.randint(1, 1000000)
            
            # Set betmode based on requested mode
            # Maps frontend mode names → math-sdk betmode names
            mode_map = {
                'base': 'base',
                'BASE': 'base',
                'low': 'low',
                'LOW': 'low',
                'medium': 'medium',
                'MEDIUM': 'medium',
                'high': 'high',
                'HIGH': 'high',
                'extreme': 'extreme',
                'EXTREME': 'extreme',
                # Buy bonus modes
                'arcane_ascension': 'arcane_ascension',
                'ARCANE_ASCENSION': 'arcane_ascension',
                'overlord_enhancement': 'overlord_enhancement',
                'OVERLORD_ENHANCEMENT': 'overlord_enhancement',
            }
            # Fall back to first available betmode if unknown
            available_betmodes = [bm.get_name() for bm in self.game_state.config.bet_modes]
            desired = mode_map.get(mode, mode.lower())
            self.game_state.betmode = desired if desired in available_betmodes else available_betmodes[0]
            
            # Apply per-betmode wincap (mirrors run_sims.py behaviour)
            betmode_obj = self.game_state.get_current_betmode()
            self.game_state.config.wincap = betmode_obj.get_wincap()
            
            # Pick criteria based on distribution quotas
            distributions = betmode_obj.get_distributions()
            roll = rnd.random()
            cumulative = 0
            for dist in distributions:
                if dist._quota is None:
                    continue
                cumulative += dist._quota
                if roll < cumulative:
                    self.game_state.criteria = dist._criteria
                    break
            else:
                self.game_state.criteria = distributions[-1]._criteria
            
            # Run the actual game simulation
            self.game_state.run_spin(sim_number)
            
            # Get the book data
            book_data = self.game_state.book.to_json()
            
            return book_data
            
        except Exception as e:
            print(f"❌ Error running game round: {e}")
            import traceback
            traceback.print_exc()
            return None


@app.route('/wallet/authenticate', methods=['POST'])
def authenticate():
    """Authenticate endpoint - initialize or resume session."""
    data = request.json
    session_id = data.get('sessionID') or data.get('playerID')
    language = data.get('language', 'en')
    currency = data.get('currency', 'USD')
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    if session_id not in sessions:
        sessions[session_id] = Session(session_id)
        sessions[session_id].initialize_game()
    
    session = sessions[session_id]
    session.language = language
    session.currency = currency
    
    response = {
        "sessionID": session_id,
        "balance": {
            "amount": session.balance,
            "currency": session.currency
        },
        "config": {
            "minBet": 100000,  # $0.10
            "maxBet": 1000000000,  # $1000
            "stepBet": 10000,
            "defaultBetLevel": 1000000,
            "betLevels": [100000, 200000, 400000, 600000, 800000, 1000000],
            "jurisdiction": {
                "socialCasino": False,
                "disabledFullscreen": False,
                "disabledTurbo": False
            }
        }
    }
    
    # Resume active round if exists
    if session.round_active and session.current_book:
        response["round"] = {
            "roundID": session.round_id,
            "amount": session.current_bet_amount,
            "payout": session.win_amount,
            "payoutMultiplier": session.current_book.get('payoutMultiplier', 0),
            "active": True,
            "mode": session.current_mode or "BASE",
            "event": str(session.current_event_index or 0),
            "state": session.current_book.get('events', []),  # web-sdk expects 'state'
        }
    
    print(f"✅ Authenticated: {session_id}, Balance: ${session.balance/1000000}")
    return jsonify(response)


@app.route('/wallet/play', methods=['POST'])
def play():
    """Place a bet and start a round - uses real math-sdk game engine."""
    data = request.json
    session_id = data.get('sessionID')
    amount = int(data.get('amount', 1000000))
    mode = data.get('mode', 'BASE')

    # Buy-bonus cost multipliers: portal expects base bet and applies multiplier internally.
    # Mock-rgs mirrors this: receive base bet, compute total_debit = base_bet * multiplier.
    _BUY_BONUS_COST = {
        'arcane_ascension': 50, 'ARCANE_ASCENSION': 50,
        'overlord_enhancement': 100, 'OVERLORD_ENHANCEMENT': 100,
    }
    _cost_mult = _BUY_BONUS_COST.get(mode, 1)
    total_debit = amount * _cost_mult

    if session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400

    session = sessions[session_id]

    # Check balance against TOTAL cost (base bet × cost multiplier)
    if session.balance < total_debit:
        return jsonify({"error": "ERR_IPB", "message": "Insufficient balance"}), 400

    # Deduct total cost
    session.balance -= total_debit
    session.current_bet_amount = total_debit
    session.round_id = str(uuid.uuid4())
    session.round_active = True
    session.current_mode = mode.upper()
    session.current_event_index = 0
    
    # Run actual game round using math-sdk
    book = session.run_game_round(
        mode=mode
    )
    
    if not book:
        # Restore balance if game failed
        session.balance += total_debit
        return jsonify({"error": "Game engine error"}), 500
    
    # Keep events as-is (web-sdk expects 'events' not 'state')
    session.current_book = book
    
    # Calculate win amount from actual game result
    # payoutMultiplier in book is in basis points (100 = 1x)
    payout_multiplier_raw = book.get('payoutMultiplier', 0)
    payout_multiplier_decimal = payout_multiplier_raw / 100.0

    # For buy-bonus modes, amount = base_bet (portal/mock applies the cost multiplier).
    # For standard modes, amount = base_bet = total_debit.
    is_buy_bonus_mode = mode in {'arcane_ascension', 'ARCANE_ASCENSION',
                                  'overlord_enhancement', 'OVERLORD_ENHANCEMENT'}

    if is_buy_bonus_mode:
        # amount is the base bet; win = base_bet × payoutMultiplier
        base_bet = amount
        win_amount = int(base_bet * payout_multiplier_decimal)
    else:
        # Standard mode: Win = bet × payoutMultiplier
        win_amount = int(amount * payout_multiplier_decimal)
    session.win_amount = win_amount
    
    # Extract item details from the game event for frontend matching
    events = book.get('events', [])
    buy_bonus_modes = {'arcane_ascension', 'overlord_enhancement',
                       'arcane-ascension', 'overlord-enhancement',
                       'ARCANE_ASCENSION', 'OVERLORD_ENHANCEMENT'}
    is_buy_bonus = mode in buy_bonus_modes

    if is_buy_bonus:
        # For buy bonus: read overall payout from multiplierInfo event
        mult_event = next((e for e in events if e.get('type') == 'multiplierInfo'), None)
        win_events = [e for e in events if e.get('type') == 'winInfo']
        # tier/itemName come from the first card for legacy fields
        first_card = win_events[0] if win_events else None
        item_tier = first_card.get('tier', 'common') if first_card else 'common'
        item_name = first_card.get('itemName', '') if first_card else ''
        event_multiplier = mult_event.get('payoutMultiplier', payout_multiplier_raw) if mult_event else payout_multiplier_raw
    else:
        win_event = next((e for e in events if e.get('type') == 'winInfo'), None)
        item_tier = win_event.get('tier', 'common') if win_event else 'common'
        item_name = win_event.get('itemName', '') if win_event else ''
        event_multiplier = win_event.get('payoutMultiplier', payout_multiplier_raw) if win_event else payout_multiplier_raw
    
    # Match math-sdk mock_rgs response format
    # NOTE: 'state' is what the web-sdk expects (contains book events array)
    # 'active' indicates the round is ongoing
    # payoutMultiplier is returned in math/RGS integer format (100 = 1x).
    response = {
        "balance": {
            "amount": session.balance,
            "currency": session.currency
        },
        "round": {
            "roundID": session.round_id,
            "mode": mode.upper(),
            "amount": total_debit,
            "debitAmount": total_debit,
            "payoutMultiplier": payout_multiplier_raw,
            "payout": win_amount,
            "active": True,
            "state": book.get('events', []),  # web-sdk expects 'state' not 'events'
            "tier": item_tier,  # Pass tier for frontend rarity mapping
            "itemName": item_name,  # Pass item name for frontend display
        }
    }
    
    all_events = book.get('events', [])
    event_types = [e.get('type') for e in all_events]
    print(f"🎰 Bet: ${amount/1000000:.2f} | Multiplier: {payout_multiplier_decimal:.2f}x | Win: ${win_amount/1000000:.2f} | Mode: {mode}")
    print(f"   Item: {item_name} ({item_tier}) | Event Mult: {event_multiplier}")
    print(f"📝 Events ({len(event_types)}): {event_types}")
    return jsonify(response)


@app.route('/wallet/end-round', methods=['POST'])
def end_round():
    """End the current round and add winnings from real game result."""
    data = request.json
    session_id = data.get('sessionID')
    
    if session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    session = sessions[session_id]
    
    if not session.round_active:
        return jsonify({"error": "No active round"}), 400
    
    # Add win amount to balance (calculated from actual game)
    session.balance += session.win_amount
    
    session.round_active = False
    session.current_book = None
    session.round_id = None
    session.current_event_index = 0
    session.current_mode = 'BASE'
    
    response = {
        "balance": {
            "amount": session.balance,
            "currency": session.currency
        }
    }
    
    print(f"✅ Round ended | Final Balance: ${session.balance/1000000:.2f}")
    return jsonify(response)


@app.route('/wallet/balance', methods=['POST'])
def balance():
    """Get player's current balance."""
    data = request.json
    session_id = data.get('sessionID')
    
    if session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    session = sessions[session_id]
    
    response = {
        "balance": {
            "amount": session.balance,
            "currency": session.currency
        }
    }
    
    return jsonify(response)


@app.route('/bet/event', methods=['POST'])
def bet_event():
    """Trigger a book event (for features/bonuses) - returns real event from game."""
    data = request.json
    session_id = data.get('sessionID')
    event_index = int(data.get('event', 0))
    
    if session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    session = sessions[session_id]
    session.current_event_index = event_index + 1
    
    if not session.current_book:
        return jsonify({"error": "No active book"}), 400
    
    # Get events array from book
    all_events = session.current_book.get('events', [])
    
    if event_index < len(all_events):
        event = all_events[event_index]
        response = {
            "event": event,
            "eventIndex": event_index
        }
        event_type = event.get('type')
        print(f"📋 Event {event_index}: {event_type}")
        if event_type == 'winInfo':
            import json
            print(f"🔍 winInfo detail: {json.dumps(event, indent=2)}")
        return jsonify(response)
    
    return jsonify({"error": "Invalid event index"}), 400


@app.route('/api/teams/pixefy-gaming/approvals/weapon-ascension', methods=['GET'])
def approvals():
    """Approval check endpoint."""
    return jsonify({
        "status": "APPROVED",
        "team": "pixefy-gaming",
        "game": "weapon-ascension"
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "server": "mock-rgs",
        "sessions": len(sessions),
        "timestamp": datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎰 Mock RGS Server - Bridge to math-sdk")
    print("="*60)
    print(f"Server: http://localhost:3008")
    print(f"web-sdk URL: ?rgs_url=localhost:3008&sessionID=test-123")
    print(f"Math-SDK: {MATH_SDK_PATH}")
    print(f"Game Path: {GAME_PATH}")
    print(f"Game Engine: {'✅ Loaded' if GameState else '❌ Failed'}")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=3008, debug=True)
