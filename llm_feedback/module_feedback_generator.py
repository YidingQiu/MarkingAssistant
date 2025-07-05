import logging
import json
from typing import Type, Optional
from pydantic import ValidationError

from .llm_deployment import LLMDeployment, LLMResponse
from .output_models import OUTPUT_MODEL_REGISTRY, BaseFeedbackOutput # Import Pydantic models

logger = logging.getLogger(__name__)

def generate_feedback_for_module(
    system_prompt: str,
    user_prompt: str,
    model_name: str,
    module_id: str,
    user_name: str,
    task_name: str,
    output_model_name: Optional[str] = "TextFeedback", # Default to simple text output
    max_tokens: int = 2000, # Increased default for potentially larger JSON
    temperature: float = 0.1 # Default from previous step
) -> str: # For now, still returns a string, but it will be structured text or error.
    """
    Generates feedback for a single module using an LLM, with structured output.

    Args:
        system_prompt: The populated system prompt for the LLM.
        user_prompt: The populated user-specific prompt/content for the LLM.
        model_name: The name of the LLM model to use.
        module_id: Identifier for the module being processed.
        user_name: Name of the user for logging/context.
        task_name: Name of the task for logging/context.
        output_model_name: Name of the Pydantic model to structure the output (from OUTPUT_MODEL_REGISTRY).
        max_tokens: Maximum tokens for the LLM response.
        temperature: Temperature setting for the LLM.

    Returns:
        A string representing the structured feedback (e.g., specific field or formatted model),
        or an error message string if generation or parsing fails.
    """
    logger.info(f"Generating LLM feedback for module: {module_id} (Task: {task_name}, User: {user_name}, Model: {model_name}, OutputModel: {output_model_name})")

    # Get the Pydantic model class from the registry
    output_model_class: Type[BaseFeedbackOutput] = OUTPUT_MODEL_REGISTRY.get(output_model_name, BaseFeedbackOutput)
    if not output_model_class:
        error_msg = f"Error: Pydantic output model '{output_model_name}' not found in registry for module {module_id}."
        logger.error(error_msg)
        return error_msg

    # Enhance prompts to request JSON output matching the Pydantic model's schema
    # This is a crucial step and might need model-specific instructions.
    json_schema_description = output_model_class.model_json_schema()
    
    # Simplified instruction to output JSON. More robust prompting might be needed.
    system_prompt_with_json_instruction = (
        f"{system_prompt}\n\n"
        f"IMPORTANT: Your response MUST be a single, valid JSON object that conforms to the following JSON schema. "
        f"Do not include any explanatory text or markdown formatting before or after the JSON object itself.\n"
        f"JSON Schema:\n{json.dumps(json_schema_description, indent=2)}"
    )

    logger.debug(f"LLM System Prompt (with JSON instruction) for module {module_id}:\n{system_prompt_with_json_instruction}")
    logger.debug(f"LLM User Prompt for module {module_id}:\n{user_prompt}")

    try:
        llm_client = LLMDeployment(model_name=model_name)
        messages = [{"role": "user", "content": user_prompt}]

        llm_response: LLMResponse = llm_client._safe_chat(
            messages=messages, 
            system_prompt=system_prompt_with_json_instruction, # Use enhanced system prompt
            temperature=temperature
        )

        if llm_response.success:
            raw_llm_text = llm_response.content
            logger.info(f"Successfully received LLM output for module: {module_id}. Attempting to parse as {output_model_name}.")
            logger.debug(f"Raw LLM output for module {module_id}:\n{raw_llm_text}")
            
            # Attempt to parse the LLM output string as JSON into the Pydantic model
            try:
                # Clean the output if necessary (e.g., remove markdown code block fences)
                cleaned_llm_text = raw_llm_text.strip()
                if cleaned_llm_text.startswith("```json"):
                    cleaned_llm_text = cleaned_llm_text[len("```json"):].strip()
                if cleaned_llm_text.startswith("```"):
                     cleaned_llm_text = cleaned_llm_text[len("```"):].strip()
                if cleaned_llm_text.endswith("```"):
                    cleaned_llm_text = cleaned_llm_text[:-len("```")].strip()
                
                parsed_output = output_model_class.model_validate_json(cleaned_llm_text)
                parsed_output.raw_llm_output = raw_llm_text # Store raw output for reference
                
                # Decide what to return. For now, return a formatted string representation or a key field.
                # This can be customized based on how modules_pipeline.py consumes the output.
                if hasattr(parsed_output, 'feedback_text'): # For TextFeedbackOutput
                    return parsed_output.feedback_text
                else:
                    # Return a pretty JSON representation for other structured models
                    return parsed_output.model_dump_json(indent=2)

            except json.JSONDecodeError as e:
                error_msg = f"Error: LLM output for module {module_id} was not valid JSON. Details: {e}. Output: {raw_llm_text[:500]}..."
                logger.error(error_msg)
                # Optionally, save the failed output for debugging
                return f"{error_msg}\nRaw LLM Output:\n{raw_llm_text}" # Return error and raw output
            except ValidationError as e:
                error_msg = f"Error: LLM output for module {module_id} did not match schema {output_model_name}. Details: {e}. Output: {raw_llm_text[:500]}..."
                logger.error(error_msg)
                return f"{error_msg}\nRaw LLM Output:\n{raw_llm_text}"
        else:
            error_message = f"Error from LLM for module {module_id} (User: {user_name}): {llm_response.error}"
            logger.error(error_message)
            if llm_response.raw_response:
                logger.error(f"Raw LLM response (error): {llm_response.raw_response}")
            return f"Error: LLM generation failed for module {module_id}. Details: {llm_response.error}"

    except RuntimeError as e:
        logger.error(f"RuntimeError during LLMDeployment for module {module_id}: {e}")
        logger.exception("Detailed LLMDeployment RuntimeError traceback:")
        return f"Error: LLM setup failed for module {module_id}. Details: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error calling LLM for module {module_id} (User: {user_name}): {e}")
        logger.exception("Detailed LLM call error traceback:")
        return f"Error: LLM generation failed unexpectedly for module {module_id}. Details: {str(e)}" 