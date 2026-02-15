from __future__ import annotations

import json
import logging
from pathlib import Path

import aiohttp

from ai.parser import JSONParser
from core.config import settings
from models.schemas import AIDecision, MarketState

logger = logging.getLogger("openclaw.llm_brain")


class DecisionEngine:
    """
    LLM policy evaluator against the master execution guide.
    """

    def __init__(self):
        self.model_name = settings.OLLAMA_MODEL
        self.ollama_url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
        self.system_prompt = self._load_execution_guide()

    def _load_execution_guide(self) -> str:
        guide_path = Path(__file__).resolve().parents[1] / "knowledge_base" / "master_desk_manual_v4.txt"
        if not guide_path.exists():
            logger.critical("Execution guide not found at %s", guide_path)
            raise FileNotFoundError("Missing master_desk_manual_v4.txt")
        return guide_path.read_text(encoding="utf-8")

    def _build_prompt(self, market_state: MarketState) -> str:
        market_json = market_state.model_dump_json(indent=2)
        return f"""
You are the OpenClaw-Class Autonomous Execution Agent.
Your logic is strictly governed by the provided institutional execution guide.

CORE AXIOM: A POI without Liquidity offers zero mathematical edge.
Prioritize capital preservation over frequency of trades.

Current Quantitative Market State:
{market_json}

Evaluate the state and respond ONLY as JSON in the exact shape below:
{{
  "action": "LONG" | "SHORT" | "WAIT",
  "confidence": <int 0-100>,
  "reasoning": "<max 2 concise sentences>",
  "entry_poi": <float or null>,
  "target_liquidity": <float or null>,
  "stop_reference": <float or null>
}}
"""

    async def evaluate_market(self, market_state: MarketState) -> AIDecision:
        payload = {
            "model": self.model_name,
            "system": self.system_prompt,
            "prompt": self._build_prompt(market_state),
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.0, "num_ctx": 4096},
        }

        try:
            timeout = aiohttp.ClientTimeout(total=settings.OLLAMA_TIMEOUT_SECS)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.ollama_url, json=payload) as response:
                    if response.status != 200:
                        logger.error("Ollama status=%s", response.status)
                        return self._default_wait_state("LLM API Error", market_state.stop_reference)

                    data = await response.json()
                    raw_response = data.get("response", "{}")
                    parsed = JSONParser.parse_ai_decision(raw_response)
                    decision = AIDecision(**parsed)
                    if decision.stop_reference is None:
                        decision.stop_reference = market_state.stop_reference
                    logger.info("AI decision: %s", json.dumps(decision.model_dump(mode="json")))
                    return decision
        except Exception as exc:
            logger.error("Failed to evaluate market via Ollama: %s", exc)
            return self._default_wait_state("Connection Failure", market_state.stop_reference)

    def _default_wait_state(self, reason: str, stop_reference: float | None) -> AIDecision:
        return AIDecision(
            action="WAIT",
            confidence=0,
            reasoning=f"System defaulted to WAIT: {reason}.",
            entry_poi=None,
            target_liquidity=None,
            stop_reference=stop_reference,
        )
