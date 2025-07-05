import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class ConfigRepository:
    """Manages loading and accessing task configurations from YAML files."""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.configs: Dict[str, Any] = self._load_configs()

    def _load_configs(self) -> Dict[str, Any]:
        """Loads all task configurations from a directory of YAML files."""
        if not self.config_path.is_dir():
            logger.error(f"Configuration directory not found: {self.config_path}")
            return {}

        configs = {}
        for config_file in self.config_path.glob('*.yaml'):
            task_name = config_file.stem
            try:
                with config_file.open('r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if not isinstance(data, dict):
                        logger.warning(f"Config file {config_file} is not a dictionary. Skipping.")
                        continue
                    configs[task_name] = data
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML from {config_file}: {e}")
            except Exception as e:
                logger.error(f"Error reading file {config_file}: {e}")

        logger.info(f"Successfully loaded {len(configs)} task configurations from {self.config_path}.")
        return configs

    def get_task_config(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves the configuration for a specific task."""
        task_config = self.configs.get(task_name)
        if not task_config:
            logger.warning(f"Configuration for task '{task_name}' not found.")
        return task_config

    def list_tasks(self) -> List[str]:
        """Returns a list of all task names defined in the configuration."""
        return list(self.configs.keys()) 