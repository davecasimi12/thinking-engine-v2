# -*- coding: utf-8 -*-
# reflection_layer.py v6.0
# -------------------------------------------------------
# Automated reflection with self-evaluation (no user input)
# Compatible with MemoryFusion v6.0 + ThinkingEngine v6.0
# -------------------------------------------------------

import json
import random
from datetime import datetime
from typing import Dict, Any
from MemoryFusion import MemoryFusion


class ReflectionLayer:
    def __init__(self, memory: MemoryFusion):
        self.memory = memory
        self.correction_log_file = "corrections.log"

    # ====================================================
    # CORE REFLECTION
    # ====================================================
    def process_thought(self, thought: str) -> str:
        """Process a thought into a reflection with auto-evaluation."""
        try:
            # Step 1: Analyze
            emotion = self._detect_emotion(thought)
            reasoning = self._analyze_reasoning(thought)

            # Step 2: Compose reflection
            reflection = (
                f"Insight → {reasoning}\n"
                f"Emotion detected → {emotion}\n"
                f"Reflection saved successfully."
            )

            # Step 3: Evaluate reflection quality automatically
            confidence = self._auto_evaluate_reflection(reflection)

            # Step 4: Store reflection and confidence
            self._store_reflection(thought, reflection, emotion, confidence)

            # Return formatted reflection text
            return f"{reflection}\n(Self-evaluated confidence: {confidence}/5)"

        except Exception as e:
            error_message = f"[Reflection Error] {e}"
            self._log_correction(error_message)
            return error_message

    # ====================================================
    # EMOTION + REASONING ANALYSIS
    # ====================================================
    def _detect_emotion(self, text: str) -> str:
        """Detect emotion based on simple keyword mapping."""
        keywords = {
            "happy": "positive",
            "excited": "motivated",
            "angry": "frustrated",
            "sad": "reflective",
            "confused": "uncertain",
            "tired": "fatigued",
            "focused": "determined",
        }
        for k, v in keywords.items():
            if k in text.lower():
                return v
        return random.choice(["neutral", "curious", "inspired", "reflective"])

    def _analyze_reasoning(self, text: str) -> str:
        """Generate reasoning classification."""
        if "why" in text.lower():
            return "Explores motivation and cause."
        elif "how" in text.lower():
            return "Focuses on logical method or execution."
        elif "what if" in text.lower():
            return "Considers alternate possibilities."
        else:
            return "Processes direct or factual reasoning."

    # ====================================================
    # SELF-EVALUATION
    # ====================================================
    def _auto_evaluate_reflection(self, reflection: str) -> int:
        """Rate reflection based on its clarity and structure."""
        length = len(reflection.split())
        clarity_score = 5 if "Insight" in reflection and "Emotion" in reflection else 3
        length_score = 5 if length > 40 else 4 if length > 25 else 3
        emotion_bonus = 1 if "Emotion detected" in reflection else 0

        raw_score = clarity_score + length_score + emotion_bonus
        normalized = max(2, min(5, round(raw_score / 3)))
        return normalized

    # ====================================================
    # STORAGE + LOGGING
    # ====================================================
    def _store_reflection(self, thought: str, reflection: str, emotion: str, confidence: int):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "thought": thought,
            "reflection": reflection,
            "emotion": emotion,
            "self_confidence": confidence,
        }
        self.memory.long_term_memory.setdefault("reflections", []).append(entry)
        self.memory.update_confidence_trend(confidence)
        self.memory._save()

    def _log_correction(self, message: str):
        """Log internal reflection errors."""
        log_entry = {"timestamp": datetime.now().isoformat(), "message": message}
        try:
            with open(self.correction_log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass