import json
import asyncio
import websockets

async def trigger_dashboard():
    # Connect to the live WebSocket tunnel we just opened
    uri = "ws://localhost:8000/ws/ai-feed"
    
    # The exact JSON structure your Next.js frontend is waiting for
    fake_trade = {
        "type": "trade_execution",
        "symbol": "BTC/USDT",
        "action": "BUY",
        "price": 69420.50,
        "size": 0.05,
        "reasoning": "AI Brain Analysis: Detected strong Fair Value Gap (FVG) and swept local liquidity on the 5m timeframe. Risk/Reward ratio is 1:3. Executing optimal long entry.",
        "status": "SUCCESS",
        "pnl": "+0.00"
    }

    try:
        async with websockets.connect(uri) as websocket:
            # Transmit the payload as a frame-based message
            await websocket.send(json.dumps(fake_trade))
            print("🚀 FAKE TRADE INJECTED SUCCESSFULLY! Check your browser.")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(trigger_dashboard())