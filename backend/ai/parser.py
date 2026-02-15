import json
import logging
import re

logger = logging.getLogger("openclaw.parser")

class JSONParser:
    """Strips markdown and validates the LLM's strict JSON output."""
    
    @staticmethod
    def parse_ai_decision(raw_response: str) -> dict:
        try:
            # Strip out markdown code blocks if the LLM hallucinates them
            clean_str = re.sub(r"```json\s*", "", raw_response)
            clean_str = re.sub(r"```\s*", "", clean_str).strip()
            
            decision = json.loads(clean_str)
            
            # Validate required keys exist to prevent downstream KeyError
            required_keys = [
                "action",
                "confidence",
                "reasoning",
                "entry_poi",
                "target_liquidity",
                "stop_reference",
            ]
            for key in required_keys:
                if key not in decision:
                    raise ValueError(f"Missing required key: {key}")
                    
            return decision
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode LLM JSON: {e}. Raw Output: {raw_response}")
            return JSONParser.fallback_wait()
        except Exception as e:
            logger.error(f"Validation error in AI output: {e}")
            return JSONParser.fallback_wait()

    @staticmethod
    def fallback_wait() -> dict:
        """The ultimate fail-safe if the AI outputs garbage."""
        return {
            "action": "WAIT",
            "confidence": 0,
            "reasoning": "System parsing failure. Defaulting to WAIT to preserve capital.",
            "entry_poi": None,
            "target_liquidity": None,
            "stop_reference": None,
        }
