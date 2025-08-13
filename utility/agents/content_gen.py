
import os
import re
from datetime import datetime
from typing import Dict, Any, List
import logging
from .step_gen import StepGenerator


class ContentGenAgent:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.step_generator = StepGenerator()

    def _normalize_step(self, phrase: str) -> str:
        # Replace parameters like '{recipient}' with '{}'
        return re.sub(r"\{[^}]+\}", "{}", phrase.strip().lower())
        
    def _extract_steps_from_feature(self, feature_path: str) -> List[str]:
        """Extract step phrases from feature file"""
        steps = []
        step_keywords = ["Given", "When", "Then", "And", "But"]
        with open(feature_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if any(line.startswith(k) for k in step_keywords):
                    steps.append(line)
        return steps
        
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run content generation"""
        orchestrator = state["orchestrator"]
        user_story = state["user_story"]
        
        # Generate feature file
        feature_path = await orchestrator.generate_from_user_story(user_story)
        
        # Extract steps and generate step definitions
        timestamp = os.path.basename(feature_path).split('_')[2].split('.')[0]
        steps_path = os.path.join(os.path.dirname(feature_path), "..", "steps", f"test_steps_{timestamp}.py")
        
        # Extract steps from feature file
        steps = self._extract_steps_from_feature(feature_path)
        
        # Generate step definitions
        os.makedirs(os.path.dirname(steps_path), exist_ok=True)
        self.step_generator.generate_step_file(steps, steps_path)
        
        self.logger.info(f"Generated step definitions in {steps_path}")
        
        state["feature_path"] = feature_path
        state["step_definitions_path"] = steps_path
        state["missing_steps"] = []
        return state