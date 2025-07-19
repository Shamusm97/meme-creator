from google import genai
from google.genai import types
import os
import argparse
from typing import Optional

class GoogleLLMClient:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Google LLM client using the new google-genai SDK.
        
        Args:
            api_key: Google API key. If None, will try to get from environment variable.
        """
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            # Will automatically pick up GEMINI_API_KEY or GOOGLE_API_KEY from environment
            self.client = genai.Client()
    
    def generate_script(self, system_prompt: str, user_prompt: str, 
                       temperature: float = 0.7, max_tokens: int = 2048,
                       direct_output: bool = True, thinking_config: Optional[types.ThinkingConfig] = None,
                       model: str = "gemini-2.5-flash") -> str:
        """
        Generate a script using system and user prompts.
        
        Args:
            system_prompt: System instructions/context
            user_prompt: User's specific request
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens in response
            direct_output: If True, instructs model to be direct without explanation
            thinking_config: Optional thinking configuration for the model
            model: Model to use for generation (default: "gemini-2.5-flash")
            
        Returns:
            Generated script text
        """
        try:
            # Modify prompt to encourage direct output if requested
            if direct_output:
                final_user_prompt = f"""{user_prompt}

IMPORTANT: Provide only the requested script content. Do not include explanations, reasoning, or meta-commentary. Output the script directly."""
            else:
                final_user_prompt = user_prompt
            
            # Configure generation parameters
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                thinking_config=thinking_config,
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=0.9,
                top_k=40,
                stop_sequences=["Explanation:", "Note:", "Analysis:", "Here's the script:"]
            )
            
            # Generate response
            response = self.client.models.generate_content(
                model=model,
                contents=final_user_prompt,
                config=config
            )
            
            return response.text
            
        except Exception as e:
            raise Exception(f"Error generating content: {str(e)}")

def save_script(content: str, filename: str) -> None:
    """Save script content to file."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Script saved to: {filename}")

def load_template(template_file: str) -> str:
    """Load system prompt template from file."""
    with open(template_file, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    parser = argparse.ArgumentParser(description='Generate scripts using Google LLM API (new SDK)')
    parser.add_argument('--system-prompt', '-s', required=True, 
                       help='System prompt or path to system prompt file')
    parser.add_argument('--user-prompt', '-u', required=True,
                       help='User prompt or request')
    parser.add_argument('--output', '-o', default='generated_script.txt',
                       help='Output filename (default: generated_script.txt)')
    parser.add_argument('--temperature', '-t', type=float, default=0.7,
                       help='Generation temperature (default: 0.7)')
    parser.add_argument('--max-tokens', '-m', type=int, default=2048,
                       help='Maximum tokens (default: 2048)')
    parser.add_argument('--api-key', '-k', 
                       help='Google API key (or set GEMINI_API_KEY env var)')
    parser.add_argument('--direct', action='store_true',
                       help='Use direct output mode')
    parser.add_argument('--model', '-M', default='gemini-2.5-flash',
                       help='Model to use for generation (default: gemini-2.5-flash)')
    parser.add_argument('--thinking-budget', type=int, default=0,
                       help='Thinking budget for the model (default: 0)')
    
    args = parser.parse_args()
    
    try:
        # Initialize client
        client = GoogleLLMClient(api_key=args.api_key)
        
        # Check if system prompt is a file
        if os.path.exists(args.system_prompt):
            system_prompt = load_template(args.system_prompt)
        else:
            system_prompt = args.system_prompt
        user_prompt = args.user_prompt
        
        print("Generating script...")
        print(f"System prompt: {system_prompt[:100]}...")
        print(f"User prompt: {user_prompt}")
        print("-" * 50)

        # Configure thinking budget if provided
        thinking_config = None
        if args.thinking_budget > 0:
            thinking_config = types.ThinkingConfig(
                thinking_budget=args.thinking_budget,
                include_thoughts=False  # Set to True if you want to include model's reasoning
            )
        
        # Generate script
        script = client.generate_script(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            direct_output=args.direct,
            thinking_config=thinking_config,
            model=args.model
        )
        
        # Display result
        print("Generated Script:")
        print("=" * 50)
        print(script)
        print("=" * 50)
        
        # Save to file
        save_script(script, args.output)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0