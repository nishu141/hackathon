from typing import Dict, Any


class ContentGenAgent:
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        orchestrator = state["orchestrator"]
        user_story = state.get("user_story", "As a user I want to test the API")

        feature_path = await orchestrator.generate_from_user_story(user_story)
        steps_path = await orchestrator.generate_step_definitions(user_story)

        state["feature_path"] = feature_path
        state["step_definitions_path"] = steps_path
        return state