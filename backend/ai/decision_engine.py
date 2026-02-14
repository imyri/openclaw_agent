import json
import aiohttp
import logging
from typing import Dict, Any

logger = logging.getLogger("openclaw.llm_brain")

class DecisionEngine:
    """
    The LLM Brain for OpenClaw-Class.
    Acts as a strict probabilistic engine evaluating quantitative data against the master execution manual.
    """
    def __init__(self, model_name: str = "deepseek-r1:7b"):
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/generate"
        self.system_prompt = self._load_execution_guide()
        
    def _load_execution_guide(self) -> str:
        """
        Loads the institutional rules. This acts as the unshakeable daily checklist for the AI.
        """
        try:
            with open("knowledge_base/master_desk_manual_v4.txt", "r") as f:
                return f.read()
        except FileNotFoundError:
            logger.critical("master_desk_manual_v4.txt not found! Halting execution capability.")
            raise FileNotFoundError("The AI cannot operate without its institutional knowledge base.")

    def _build_prompt(self, market_state: Dict[str, Any]) -> str:
        """
        Constructs the strict, JSON-enforced prompt for the LLM.
        """
        return f"""
        You are the OpenClaw-Class Autonomous Execution Agent.
        Your logic is strictly governed by the provided institutional execution guide.
        
        CORE AXIOM: A POI without Liquidity offers zero mathematical edge. 
        Prioritize capital preservation over frequency of trades.
        
        Current Quantitative Market State:
        {json.dumps(market_state, indent=2)}
        
        Evaluate this state against your daily execution checklist. 
        Are the time filters valid? Is there a valid MSS with an FVG? Is there clear target liquidity?
        
        Output ONLY valid JSON in the exact following format. Do not include markdown formatting or extra text.
        {{
            "action": "LONG" | "SHORT" | "WAIT",
            "confidence": <int 0-100>,
            "reasoning": "<Strictly reference the POI, FVG, and Target Liquidity. Max 2 sentences.>",
            "entry_poi": "<price level or null>",
            "target_liquidity": "<price level or null>"
        }}
        """

    async def evaluate_market(self, market_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends the market state to the local LLM and parses the JSON decision.
        Runs asynchronously to prevent blocking the live price feed.
        """
        prompt = self._build_prompt(market_state)
        
        payload = {
            "model": self.model_name,
            "system": self.system_prompt,
            "prompt": prompt,
            "format": "json",  # Forces Ollama to strictly output valid JSON
            "stream": False,
            "options": {
                "temperature": 0.0, # Complete determinism; no creative hallucinations allowed
                "num_ctx": 4096     # Ensure enough context window for the master manual
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.ollama_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        raw_response = data.get("response", "{}")
                        decision = json.loads(raw_response)
                        
                        logger.info(f"AI Decision Output: {json.dumps(decision)}")
                        return decision
                    else:
                        logger.error(f"Ollama API returned status: {response.status}")
                        return self._default_wait_state("LLM API Error")
        except Exception as e:
            logger.error(f"Failed to connect to local LLM: {e}")
            return self._default_wait_state("Connection Failure")
            
    def _default_wait_state(self, reason: str) -> Dict[str, Any]:
        """Fail-safe state. If anything breaks, we default to capital preservation."""
        return {
            "action": "WAIT",
            "confidence": 0,
            "reasoning": f"System default to WAIT due to: {reason}. Prioritizing capital preservation.",
            "entry_poi": None,
            "target_liquidity": None
        }