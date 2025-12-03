# -*- coding: utf-8 -*-
# reasoning_engine.py v3.2
# -------------------------------------------------------
# Generates thoughts and reasoning inputs for ReflectionLayer
# Uses light contextual recall from MemoryFusion memory
# -------------------------------------------------------

import random
from datetime import datetime
from MemoryFusion import MemoryFusion


class ReasoningEngine:
    def __init__(self):
        self.memory = MemoryFusion("long_term_memory.json")
        self.engine_tag = "ReasoningEngine_v3.2"

    # ====================================================
    # THOUGHT GENERATION
    # ====================================================
    def generate_thought(self) -> str:
        """
        Generates a contextual 'thought' for the Thinking Engine.
        Combines prior reflections, emotional cues, and random inspiration.
        """
        try:
            base_thoughts = [
                "Why do certain goals feel harder to achieve?",
                "How can patience improve long-term outcomes?",
                "What if consistency mattered more than motivation?",
                "When does ambition become self-pressure?",
                "How can reflection guide better daily focus?",
            ]

            # Pull last few reflections for inspiration
            reflections = self.memory.long_term_memory.get("reflections", [])
            if reflections:
                recent = reflections[-1]["reflection"]
                seed_thought = f"Building on prior reflection: {recent}"
                combined = random.choice([seed_thought, random.choice(base_thoughts)])
            else:
                combined = random.choice(base_thoughts)

            # Inject time and mood for realism
            timestamp = datetime.now().strftime("%H:%M:%S")
            return f"[{timestamp}] {combined}"

        except Exception as e:
            return f"[Reasoning Error] {e}"

    # ====================================================
    # OPTIONAL UTILITIES
    # ====================================================
    def inject_prompt(self, user_input: str) -> str:
        """
        Allows manual override: user can input a specific topic
        or phrase to seed the reasoning process.
        """
        return f"User-driven thought: {user_input}"

    def recall_recent_memory(self) -> str:
        """Recall a recent reflection for continuity."""
        reflections = self.memory.long_term_memory.get("reflections", [])
        if not reflections:
            return "No prior reflections available."
        last_ref = reflections[-1]
        return f"Recalling last reflection ({last_ref['timestamp']}): {last_ref['reflection']}"