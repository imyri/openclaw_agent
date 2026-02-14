import asyncio
import logging
from strategy.data_feed import LiveDataFeed
from strategy.market_structure import QuantitativeEngine
from ai.decision_engine import DecisionEngine
from execution.position_manager import PositionManager
from execution.risk_guard import RiskGuard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openclaw.worker")

# Initialize Microservices
data_feed = LiveDataFeed(symbol="BTC/USDT", timeframe="5m")
ai_brain = DecisionEngine()
risk_guard = RiskGuard()
position_manager = PositionManager(api_key="YOUR_API_KEY", secret="YOUR_SECRET")

async def process_closed_candle(locked_df):
    """
    The Core Pipeline. Triggered every 5 minutes when a candle locks.
    """
    # 1. Check Global Risk Kill-Switch
    if not risk_guard.check_daily_killswitch():
        logger.warning("Daily -2R limit reached. Processing bypassed.")
        return

    # 2. Quantitative Engine: Calculate FVG & MSS Math
    quant_engine = QuantitativeEngine(locked_df)
    market_state_json = quant_engine.run_execution_checklist()

    # If no math-verified POI exists, we stop here and save LLM compute.
    if not market_state_json.get("valid_poi_found"):
        logger.info("No valid mathematical setup found. Waiting for next candle.")
        return

    # 3. LLM Brain: Evaluate Master Execution Manual against Math
    logger.info("Valid POI detected. Engaging LLM Brain for execution decision...")
    ai_decision = await ai_brain.evaluate_market(market_state_json)

    # 4. Risk Shield: Validate AI decision and execute if 1:3 RR is met
    current_price = locked_df['Close'].iloc[-1]
    account_balance = 10000.0 # Mock balance; fetch from DB in prod
    
    execution_result = position_manager.validate_and_execute(ai_decision, current_price, account_balance)
    logger.info(f"Execution Result: {execution_result}")

async def main():
    """Starts the system."""
    logger.info("Initializing OpenClaw-Class Autonomous Agent...")
    
    # Start the WebSocket stream and bind the processing pipeline
    await data_feed.start_stream(on_candle_close_callback=process_closed_candle)

if __name__ == "__main__":
    asyncio.run(main())