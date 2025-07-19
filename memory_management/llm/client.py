"""Ollama LLM client for structured data extraction."""

import json
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM API call."""
    content: str
    model: str
    success: bool
    error: Optional[str] = None
    tokens_used: Optional[int] = None


class LLMClient:
    """Client for communicating with Ollama API."""
    
    # Supported models for different tasks
    MODELS = {
        'qwq:32b': 'qwq:32b',
        'gemma3:27b': 'gemma3:27b'
    }
    
    def __init__(self, 
                 base_url: str = "http://localhost:11434",
                 timeout: int = 120,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        """
        Initialize Ollama LLM client.
        
        Args:
            base_url: Ollama server URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP request to Ollama API with error handling.
        
        Args:
            endpoint: API endpoint
            data: Request payload
            
        Returns:
            Response data
            
        Raises:
            requests.RequestException: On API communication failure
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = self.session.post(
                url, 
                json=data, 
                headers=headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout after {self.timeout}s for {url}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to Ollama server at {url}")
            raise
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            else:
                logger.error(f"HTTP error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama API: {str(e)}")
            raise
    
    def generate(self, 
                 prompt: str, 
                 model: str = 'qwq:32b',
                 system_prompt: Optional[str] = None,
                 temperature: float = 0.1,
                 max_tokens: Optional[int] = None) -> LLMResponse:
        """
        Generate text using Ollama model.
        
        Args:
            prompt: Input prompt
            model: Model name to use
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse with generated content
        """
        if model not in self.MODELS:
            raise ValueError(f"Unsupported model: {model}. Supported: {list(self.MODELS.keys())}")
        
        data = {
            'model': self.MODELS[model],
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': temperature,
            }
        }
        
        if system_prompt:
            data['system'] = system_prompt
        
        if max_tokens:
            data['options']['num_predict'] = max_tokens
        
        try:
            logger.info(f"Generating text with model {model}")
            response_data = self._make_request('api/generate', data)
            
            return LLMResponse(
                content=response_data.get('response', ''),
                model=model,
                success=True,
                tokens_used=response_data.get('eval_count')
            )
            
        except Exception as e:
            logger.error(f"Text generation failed: {str(e)}")
            return LLMResponse(
                content='',
                model=model,
                success=False,
                error=str(e)
            )
    
    def extract_structured_data(self, 
                               prompt: str, 
                               expected_schema: Dict[str, Any],
                               model: str = 'qwq:32b',
                               system_prompt: Optional[str] = None) -> LLMResponse:
        """
        Extract structured data using LLM with JSON schema validation.
        
        Args:
            prompt: Input prompt for data extraction
            expected_schema: Expected JSON schema for validation
            model: Model name to use
            system_prompt: Optional system prompt
            
        Returns:
            LLMResponse with structured JSON data
        """
        # Add JSON formatting instruction to prompt
        json_prompt = f"""{prompt}

Please respond with valid JSON only, following this structure:
{json.dumps(expected_schema, indent=2)}

Response:"""
        
        if not system_prompt:
            system_prompt = "You are a data extraction assistant. Extract information and respond with valid JSON only."
        
        response = self.generate(
            prompt=json_prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=0.1  # Low temperature for consistent structured output
        )
        
        if not response.success:
            return response
        
        # Try to parse and validate JSON response
        try:
            # Clean the response content by removing <think>...</think> blocks
            cleaned_content = self._clean_llm_response(response.content)
            
            parsed_json = json.loads(cleaned_content.strip())
            # Basic schema validation - check if required keys exist
            if isinstance(expected_schema, dict):
                for key in expected_schema.keys():
                    if key not in parsed_json:
                        logger.warning(f"Missing expected key '{key}' in LLM response")
            
            # Update response with validated JSON
            response.content = json.dumps(parsed_json, indent=2)
            return response
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {str(e)}")
            logger.error(f"Raw response: {response.content}")
            return LLMResponse(
                content='',
                model=model,
                success=False,
                error=f"Invalid JSON response: {str(e)}"
            )
    
    def check_health(self) -> bool:
        """
        Check if Ollama server is healthy and models are available.
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            # Check server health
            response = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            
            # Check if required models are available
            models_data = response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]
            
            for model_key, model_name in self.MODELS.items():
                if model_name not in available_models:
                    logger.warning(f"Model {model_name} not found in Ollama")
                    return False
            
            logger.info("Ollama server health check passed")
            return True
            
        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
            return False
    
    def list_models(self) -> List[str]:
        """
        List available models on Ollama server.
        
        Returns:
            List of available model names
        """
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            models_data = response.json()
            return [model['name'] for model in models_data.get('models', [])]
        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
            return []
    
    def _clean_llm_response(self, content: str) -> str:
        """
        Clean LLM response by removing <think>...</think> blocks and other artifacts.
        
        Args:
            content: Raw LLM response content
            
        Returns:
            Cleaned content ready for JSON parsing
        """
        import re
        
        # Remove <think>...</think> blocks (case insensitive, multiline)
        cleaned = re.sub(r'<think>.*?</think>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove any other common LLM artifacts
        cleaned = re.sub(r'<reasoning>.*?</reasoning>', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r'<analysis>.*?</analysis>', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up extra whitespace
        cleaned = cleaned.strip()
        
        # If the response starts with "Response:" or similar, try to extract just the JSON part
        if cleaned.lower().startswith('response:'):
            cleaned = cleaned[9:].strip()
        
        return cleaned
    
    def _clean_llm_response(self, content: str) -> str:
        """
        Clean LLM response by removing <think>...</think> blocks and other artifacts.
        
        Args:
            content: Raw LLM response content
            
        Returns:
            Cleaned content ready for JSON parsing
        """
        import re
        
        # Remove <think>...</think> blocks (case insensitive, multiline)
        cleaned = re.sub(r'<think>.*?</think>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove any other common LLM artifacts
        cleaned = re.sub(r'<reasoning>.*?</reasoning>', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r'<analysis>.*?</analysis>', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up extra whitespace
        cleaned = cleaned.strip()
        
        # If the response starts with "Response:" or similar, try to extract just the JSON part
        if cleaned.lower().startswith('response:'):
            cleaned = cleaned[9:].strip()
        
        return cleaned