import json

class PromptBuilder:
    """Constructs the deterministic prompts for the LLM Brain."""
    
    @staticmethod
    def build_market_prompt(market_state: dict) -> str:
        return f"""
        You are the OpenClaw-Class Autonomous Execution Agent.
        Your logic is strictly governed by the provided institutional execution guide.
        
        CORE AXIOM: A POI without Liquidity offers zero mathematical edge. 
        Prioritize capital preservation over frequency of trades.
        
        Current Quantitative Market State:
        {json.dumps(market_state, indent=2)}
        
        Evaluate this state. Are the time filters valid? Is there a valid MSS with an FVG/BPR/VI? 
        Is there clear target liquidity?
        
        Output ONLY valid JSON in the exact following format. No extra text.
        {{
            "action": "LONG" | "SHORT" | "WAIT",
            "confidence": <integer 0-100>,
            "reasoning": "<Reference the POI, FVG, and Target Liquidity. Max 2 sentences.>",
            "entry_poi": "<price float or null>",
            "target_liquidity": "<price float or null>",
            "stop_reference": "<price float or null>"
        }}
        """
