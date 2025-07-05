import logging
import json
import os
from typing import Dict, List, Optional, Union

import yaml
from dotenv import load_dotenv
from openai import OpenAI
import ollama

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class LLMResponse:
    """A simple dataclass to structure the response from an LLM call."""
    def __init__(self, success: bool, content: Optional[str] = None, error: Optional[str] = None):
        self.success = success
        self.content = content
        self.error = error

    def __repr__(self) -> str:
        if self.success:
            return f"LLMResponse(success=True, content='{self.content[:50]}...')"
        return f"LLMResponse(success=False, error='{self.error}')"


class LLMProvider:
    """Provides an interface for interacting with different LLM backends (OpenAI, Ollama)."""

    def __init__(self, model_name: str, temperature: float = 0.1):
        self.model_name = model_name
        self.temperature = temperature
        self.use_openai = model_name.startswith("openai-")
        self.client = None

        if self.use_openai:
            self._setup_openai()
        else:
            self._setup_ollama()

    def _setup_openai(self):
        """Initializes the OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set for OpenAI models.")
        self.client = OpenAI(api_key=api_key)
        logger.info(f"Using OpenAI model: {self.model_name}")

    def _setup_ollama(self):
        """Verifies that the specified Ollama model is available."""
        try:
            ollama.show(self.model_name)
            logger.info(f"Using Ollama model: {self.model_name}")
        except ollama.ResponseError as e:
            logger.error(f"Ollama model '{self.model_name}' not found. Please pull it first.")
            raise ValueError(f"Ollama model '{self.model_name}' not found.") from e

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """
        Generates a response from the configured LLM.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            if self.use_openai:
                return self._generate_openai(messages)
            else:
                return self._generate_ollama(messages)
        except Exception as e:
            logger.error(f"An unexpected error occurred during LLM generation: {e}", exc_info=True)
            return LLMResponse(success=False, error=str(e))

    def _generate_openai(self, messages: List[Dict[str, str]]) -> LLMResponse:
        """Sends a request to the OpenAI API."""
        if not self.client:
            return LLMResponse(success=False, error="OpenAI client not initialized.")
            
        # Extract the model name without the 'openai-' prefix for the API call
        actual_model = self.model_name.replace("openai-", "")
        response = self.client.chat.completions.create(
            model=actual_model,
            messages=messages,
            temperature=self.temperature,
        )
        content = response.choices[0].message.content
        return LLMResponse(success=True, content=content)

    def _generate_ollama(self, messages: List[Dict[str, str]]) -> LLMResponse:
        """Sends a request to the Ollama backend."""
        response = ollama.chat(
            model=self.model_name,
            messages=messages,
            options={"temperature": self.temperature},
        )
        content = response["message"]["content"]
        return LLMResponse(success=True, content=content) 