# -*- coding: utf-8 -*-
# MemoryFusion.py v6.0
# -------------------------------------------------------
# Adaptive weighted reinforcement + trend normalization
# Supports multi-cycle reflections with memory priority scoring
# -------------------------------------------------------

import json
from statistics import mean
from typing import Dict, Any, List


class MemoryFusion:
    def __init__(self, memory_file: str = "long_term_memory.json"):
        self.memory_file = memory_file
        self.long_term_memory: Dict[str, Any] = {
            "thoughts": {},
            "reflections": [],
            "priorities": {},
            "meta": {
                "confidence_trend": [],
                "reinforcement_log": [],
                "weighted_insights": {},
            },
        }
        self._load()

    # ====================================================
    # CORE OPS
    # ====================================================
    def _load(self):
        try:
            with open(self.memory_file, "r") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.long_term_memory.update(data)
                meta = self.long_term_memory.setdefault("meta", {})
                meta.setdefault("confidence_trend", [])
                meta.setdefault("reinforcement_log", [])
                meta.setdefault("weighted_insights", {})
        except (FileNotFoundError, json.JSONDecodeError):
            self._save()

    def _save(self):
        with open(self.memory_file, "w") as f:
            json.dump(self.long_term_memory, f, indent=4)

    # ====================================================
    # TREND + REINFORCEMENT
    # ====================================================
    def update_confidence_trend(self, conf_value: int):
        """Track confidence trend, trigger reinforcement, and normalize."""
        trend = self.long_term_memory["meta"].setdefault("confidence_trend", [])
        trend.append(conf_value)

        # Keep last 100 entries
        if len(trend) > 100:
            trend.pop(0)

        # Normalize trend around mean
        avg = round(mean(trend), 2) if trend else 0
        self.long_term_memory["meta"]["avg_confidence"] = avg

        # Trigger reinforcement for confident reflections
        if conf_value >= 4:
            self._reinforce_reflection(conf_value)

        self._save()

    def _reinforce_reflection(self, conf_value: int):
        """Log and weight reinforced reflections."""
        reflections = self.long_term_memory.get("reflections", [])
        if not reflections:
            return

        latest = reflections[-1]
        text = latest.get("reflection", "Unknown reflection")

        # Log reinforcement entry
        entry = {"reflection": text, "confidence": conf_value}
        log = self.long_term_memory["meta"].setdefault("reinforcement_log", [])
        log.append(entry)

        # Update weighted score
        weighted = self.long_term_memory["meta"].setdefault("weighted_insights", {})
        if text not in weighted:
            weighted[text] = conf_value
        else:
            weighted[text] = round((weighted[text] + conf_value) / 2, 2)

        # Sort and limit to top 20 strongest insights
        sorted_weights = dict(
            sorted(weighted.items(), key=lambda x: x[1], reverse=True)[:20]
        )
        self.long_term_memory["meta"]["weighted_insights"] = sorted_weights

        self._save()

    # ====================================================
    # RECALL + STATS
    # ====================================================
    def recall_top_insights(self, limit: int = 3) -> List[str]:
        """Return the top insights by weighted confidence."""
        weighted = self.long_term_memory["meta"].get("weighted_insights", {})
        if not weighted:
            return []
        return list(weighted.keys())[:limit]

    def get_reinforcement_summary(self) -> str:
        """Summarize current memory stats."""
        meta = self.long_term_memory["meta"]
        avg_conf = meta.get("avg_confidence", 0)
        log = meta.get("reinforcement_log", [])
        weighted = meta.get("weighted_insights", {})

        return (
            f"{len(log)} reinforced reflections, "
            f"{len(weighted)} weighted insights (avg confidence {avg_conf}/5)."
        )

    # ====================================================
    # STABILITY CHECK
    # ====================================================
    def verify_integrity(self) -> bool:
        """Check that memory schema is intact."""
        required_keys = ["thoughts", "reflections", "priorities", "meta"]
        meta_keys = [
            "confidence_trend",
            "reinforcement_log",
            "weighted_insights",
        ]
        try:
            for key in required_keys:
                if key not in self.long_term_memory:
                    return False
            for mkey in meta_keys:
                if mkey not in self.long_term_memory["meta"]:
                    return False
            return True
        except Exception:
            return False