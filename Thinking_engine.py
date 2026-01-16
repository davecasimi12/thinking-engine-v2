# -*- coding: utf-8 -*-
"""
Thinking_engine_core_v6 (Stable Build)

Multi-cycle adaptive reasoning + reflection engine.
Works with MemoryFusion + ReflectionLayer + ReasoningEngine.

This file is NOT the FastAPI entrypoint.
FastAPI entrypoint is: thinking_engine.py
"""

import json
import time
from datetime import datetime

from MemoryFusion import MemoryFusion
from reflection_layer import ReflectionLayer
from reasoning_engine import ReasoningEngine


class ThinkingEngine:
    def __init__(self):
        # Initialize subsystems
        self.memory = MemoryFusion("long_term_memory.json")
        self.reasoning = ReasoningEngine()
        self.reflection = ReflectionLayer(self.memory)

        # Identity
        self.engine_name = "Nivora Thinking Engine v6.0"
        print(f"\n🧠 {self.engine_name} online.")
        print("--------------------------------------------------")

        # Pre-flight check
        if not self.memory.verify_integrity():
            print("⚠️ Memory structure incomplete — attempting auto-repair...")
            self.memory.save()
            print("✅ Memory file repaired.")
        else:
            print("✅ Memory verified and loaded successfully.\n")

    # ==========================
    # MAIN LOOP
    # ==========================
    def run(self, cycles: int = 3):
        """Run multiple reasoning-reflection cycles automatically."""
        print(f"Session started ({cycles} cycles).")
        print("--------------------------------------------------")

        for i in range(1, cycles + 1):
            print(f"\n🔁 Cycle {i}/{cycles}")

            # 1) Generate a thought
            thought = self.reasoning.generate_thought()
            print(f"💭 Thought: {thought}")

            # 2) Reflect on it
            reflection_output = self.reflection.process_thought(thought)
            print("\n🪞 Reflection Output:")
            print(reflection_output)

            # 3) Auto self-evaluate reflection quality (1-5)
            auto_confidence = self._auto_confidence_estimate(reflection_output)
            self.memory.update_confidence_trend(auto_confidence)
            print(f"✅ Auto-confidence recorded: {auto_confidence}/5")

            # brief pause between cycles
            time.sleep(1)

        print("\n--------------------------------------------------")
        self._end_session()

    # ==========================
    # SUPPORT METHODS
    # ==========================
    def _auto_confidence_estimate(self, reflection_text: str) -> int:
        """
        Simple automatic confidence estimation.
        Longer reflections = higher confidence tendency.
        """
        words = (reflection_text or "").split()
        length_factor = len(words)

        if length_factor > 35:
            return 5
        elif length_factor > 25:
            return 4
        elif length_factor > 15:
            return 3
        else:
            return 2

    def _end_session(self):
        """Wrap-up summary + memory persistence."""
        try:
            summary = self.memory.get_reinforcement_summary()
            self.memory.save()
            print("💾 Memory persisted to long_term_memory.json")
            print(f"📌 Summary:\n{summary}")
            print("✅ Session complete.\n")
        except Exception as e:
            print(f"❌ Error saving session: {e}")

    # ==========================
    # UTILITIES
    # ==========================
    def export_summary(self, filename: str = "session_summary.json"):
        """Export a summary file for analytics."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "engine": self.engine_name,
            "summary": self.memory.get_reinforcement_summary(),
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"📦 Session summary exported to {filename}")


if __name__ == "__main__":
    engine = ThinkingEngine()
    engine.run(cycles=3) 