#!/usr/bin/env python3
"""
Simple Google Forms Extractor Script

This script extracts form data from a Google Forms URL and returns
the form structure in entry format, mapping to existing entry IDs.

Usage:
    python extract_form.py <google_forms_url>

Example:
    python extract_form.py "https://docs.google.com/forms/d/1ABC123.../viewform"

Output format:
    {
        "entry.2027499558": {"Option 1": 0, "Option 2": 0, ...},
        "entry.856881664": {"options": {"Option A": 0, "Option B": 0, ...}},
        ...
    }
"""

import sys
import os
import json
from typing import Dict, Any, Optional

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from core.form_extractor import FormExtractor
from models import Form, Question, AnswerConfig, AnswerOption


def load_entry_structure() -> Dict[str, Any]:
    """
    Load the existing entry structure from extracted_form_data.json.
    
    Returns:
        Dict[str, Any]: Dictionary with entry structure
    """
    try:
        if os.path.exists("extracted_form_data.json"):
            with open("extracted_form_data.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print("Warning: extracted_form_data.json not found. Creating empty entry structure.")
            return {}
    except Exception as e:
        print(f"Warning: Could not load extracted_form_data.json: {e}")
        return {}


def form_to_dict(form: Form, entry_structure: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a Form object to the required dictionary format using entry structure.
    
    Args:
        form (Form): The Form object to convert
        entry_structure (Dict[str, Any]): Existing entry structure to map to
        
    Returns:
        Dict[str, Any]: Dictionary with entry structure and extracted options
    """
    result = entry_structure.copy()
    
    if not form.response_config or not form.response_config.pages:
        return result
    
    # Get list of entry keys for mapping
    entry_keys = list(entry_structure.keys())
    entry_index = 0
    
    for page in form.response_config.pages:
        if not page.questions:
            continue
            
        for question in page.questions:
            # Map to next available entry if we have one
            if entry_index < len(entry_keys):
                entry_key = entry_keys[entry_index]
                
                # Handle questions with options (multiple choice, checkbox, etc.)
                if question.answer_config and question.answer_config.options:
                    options_dict = {}
                    for option in question.answer_config.options:
                        options_dict[option.text] = 0
                    
                    # For checkbox questions, wrap in "options" key
                    if question.type == "checkbox":
                        result[entry_key] = {"options": options_dict}
                    else:
                        result[entry_key] = options_dict
                else:
                    # For text-based questions, create empty structure
                    result[entry_key] = {"answer": ""}
                
                entry_index += 1
    
    return result


def extract_form_data(url: str, headless: bool = True) -> Dict[str, Any]:
    """
    Extract form data from a Google Forms URL.
    
    Args:
        url (str): Google Forms URL
        headless (bool): Run browser in headless mode
        
    Returns:
        Dict[str, Any]: Form structure in entry format
        
    Raises:
        ValueError: If URL is invalid or extraction fails
    """
    try:
        # Load existing entry structure
        entry_structure = load_entry_structure()
        
        # Initialize the form extractor
        extractor = FormExtractor(
            chromebinary_path="D:/application/chrome-win64/chrome-win64/chrome.exe",  # Use system Chrome
            chromedriver_path="D:/application/chromedriver-win64/chromedriver-win64/chromedriver.exe",  # Use system ChromeDriver
            headless=headless
        )
        
        # Extract the form data
        form = extractor.extract_form_data(url)
        
        # Convert to dictionary format using entry structure
        result = form_to_dict(form, entry_structure)
        
        return result
        
    except Exception as e:
        raise ValueError(f"Failed to extract form data: {str(e)}")


def main():
    """
    Main function to run the form extractor from command line.
    """
    if len(sys.argv) < 2:
        print("Usage: python extract_form.py <google_forms_url> [--visible]")
        print("Example: python extract_form.py 'https://docs.google.com/forms/d/1ABC123.../viewform'")
        print("Add --visible flag to show browser window (for debugging)")
        sys.exit(1)
    
    url = sys.argv[1]
    headless = "--visible" not in sys.argv
    
    # Validate URL
    if not url.startswith('https://docs.google.com/forms/'):
        print("Error: Please provide a valid Google Forms URL")
        print("URL should start with: https://docs.google.com/forms/")
        sys.exit(1)
    
    try:
        print(f"Extracting form data from: {url}")
        print(f"Running in {'headless' if headless else 'visible'} mode...")
        
        # Extract form data
        form_dict = extract_form_data(url, headless=headless)
        
        # Print results
        print("\n" + "="*50)
        print("EXTRACTED FORM DATA:")
        print("="*50)
        print(json.dumps(form_dict, indent=2, ensure_ascii=False))
        
        # Save to file
        output_file = "extracted_form_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(form_dict, f, indent=2, ensure_ascii=False)
        
        print(f"\nForm data saved to: {output_file}")
        print(f"Total entries processed: {len(form_dict)}")
        print(f"Entries with extracted data: {len([k for k, v in form_dict.items() if v])}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
