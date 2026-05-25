from pathlib import Path
from string import Template
from typing import Dict

from loguru import logger


class PromptManager:

    def __init__(self, prompts_dir: str = "prompts") -> None:
        self.prompts_dir = Path(prompts_dir)
        self.templates: Dict[str, Template] = {}
        self.status = "initializing"

    async def load_templates(self) -> None:
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")
            self.prompts_dir.mkdir(parents=True, exist_ok=True)
        for file_path in self.prompts_dir.glob("*.txt"):
            content = file_path.read_text(encoding="utf-8")
            self.templates[file_path.stem] = Template(content)
        self.status = "loaded"
        logger.info(f"Loaded {len(self.templates)} prompt templates")

    def get_prompt(self, agent_name: str, **kwargs) -> str:
        if agent_name not in self.templates:
            raise KeyError(f"Prompt template not found: {agent_name}")
        return self.templates[agent_name].safe_substitute(**kwargs)

    def list_templates(self) -> list[str]:
        return sorted(self.templates.keys())
