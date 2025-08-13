
import re
from typing import Dict, Any, List
import logging
import os
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
                    phrase = re.sub(r'^(Given|When|Then|And|But)\s+', '', line)
                    steps.append(self._normalize_step(phrase))
        return steps

    def _extract_step_definitions(self, steps_path: str) -> List[str]:
        """Extract step definition phrases from step file"""
        phrases = []
        pattern = re.compile(r"@(given|when|then)\(['\"](.*?)['\"]\)")
        with open(steps_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    phrases.append(self._normalize_step(match.group(2)))
        return phrases

    def _generate_stub(self, phrase: str) -> str:
        """Generate a stub step definition for a missing step phrase"""
        # Guess the decorator type based on original phrase
        phrase_lower = phrase.lower()
        if phrase_lower.startswith("given "):
            decorator = "@given"
        elif phrase_lower.startswith("when "):
            decorator = "@when"
        elif phrase_lower.startswith("then ") or phrase_lower.startswith("and ") or phrase_lower.startswith("but ") or phrase_lower.startswith("the ") or phrase_lower.startswith("i should"):
            decorator = "@then"
        elif phrase_lower.startswith("i send") or phrase_lower.startswith("i "):
            decorator = "@when"
        else:
            decorator = "@given"
        # Use double quotes if single quote is present in phrase
        if "'" in phrase:
            quote = '"'
        else:
            quote = "'"
        return f"\n{decorator}({quote}{phrase}{quote})\ndef step_{re.sub(r'[^a-zA-Z0-9]', '_', phrase_lower)}(context, *args, **kwargs):\n    # TODO: Implement step\n    pass\n"

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio
        orchestrator = state["orchestrator"]
        user_story = state.get("user_story", "As a user I want to test the API")

        # Always generate feature file
        feature_path = await orchestrator.generate_from_user_story(user_story)

        # Create step definition file with matching timestamp from feature file
        steps_dir = os.path.join(os.path.dirname(feature_path), "..", "steps")
        steps_dir = os.path.abspath(steps_dir)
        os.makedirs(steps_dir, exist_ok=True)
        # Extract timestamp from feature file name
        feature_timestamp = os.path.basename(feature_path).split('_')[2].split('.')[0]
        steps_path = os.path.join(steps_dir, f"test_steps_{feature_timestamp}.py")

        # Extract all unique step phrases from feature file
        feature_steps_raw = []
        step_keywords = ["Given", "When", "Then", "And", "But"]
        with open(feature_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if any(line.startswith(k) for k in step_keywords):
                    phrase = re.sub(r'^(Given|When|Then|And|But)\s+', '', line)
                    feature_steps_raw.append(phrase)

        # Deduplicate while preserving order
        seen = set()
        unique_steps = []
        for phrase in feature_steps_raw:
            norm = self._normalize_step(phrase)
            if norm not in seen:
                seen.add(norm)
                unique_steps.append(phrase)

        # Generate complete step definitions using StepGenerator
        self.step_generator.generate_step_file(unique_steps, steps_path)
        self.logger.info(f"Generated step definitions in {steps_path}")

        self.logger.info(f"Step definitions written to: {steps_path}")

        state["feature_path"] = feature_path
        state["step_definitions_path"] = steps_path
        state["missing_steps"] = []
        return state