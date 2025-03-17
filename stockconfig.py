import requests
import argparse
import json
from typing import Dict, List, Tuple
import re
import sys
import os

# Default filename for the configuration JSON
DEFAULT_CONFIG_FILENAME = "products.json"

try:
    # Import configuration from config.py
    from config import (
        API_CONFIG,
        SKU_CHECK_API_CONFIG,
    )
except ModuleNotFoundError:
    print("Error: config.py not found. Rename example_config.py to config.py to begin.")
    sys.exit(1)


def load_locales() -> List[Tuple[str, str, str]]:
    """
    Load locales from locales.json file.
    Returns list of tuples containing (country, locale_code, currency).
    """
    try:
        with open('locales.json', 'r', encoding='utf-8') as f:
            locale_data = json.load(f)
            locales = []
            for item in locale_data:
                country = item["country"]
                locale = item["locale"]
                currency = item["currency"]
                locales.append((country, locale, currency))
            return locales
    except FileNotFoundError:
        print("Warning: locales.json not found. Using default locale.")
        return [("United Kingdom", "en-gb", "£")]
    except Exception as e:
        print(f"Error loading locales: {e}")
        return [("United Kingdom", "en-gb", "£")]

def get_locale_choice() -> tuple[str, str, str]:
    """
    Prompt user for locale choice.
    Returns tuple of (locale, currency_symbol, country)
    """
    locales = load_locales()
    
    print("\nAvailable locales:")
    for idx, (country, _, _) in enumerate(locales, 1):
        print(f"{idx}. {country}")
    print(f"{len(locales) + 1}. Custom locale")
    
    while True:
        try:
            choice = input(f"\nSelect locale (1-{len(locales) + 1}): ")
            choice_num = int(choice)
            
            if choice_num == len(locales) + 1:
                custom_locale = input("Enter custom locale (e.g., en-us): ").lower()
                currency = input("Enter currency symbol: ")
                country = input("Enter country name: ")
                return custom_locale, currency, country
            elif 1 <= choice_num <= len(locales):
                country, locale, currency = locales[choice_num - 1]
                return locale, currency, country
            else:
                print(f"Please enter a number between 1 and {len(locales) + 1}")
        except ValueError:
            print("Invalid input. Please try again.")

def get_skus(locale: str) -> List[Dict[str, str]]:
    """
    Fetch available SKUs from NVIDIA's API for a given locale.
    Returns a list of dictionaries containing product info.
    """
    url = SKU_CHECK_API_CONFIG["url"]
    headers = API_CONFIG["headers"]
    
    params = {
        "locale": locale,
        "page": 1,
        "limit": 100,
        "manufacturer": "NVIDIA",
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        products = []
        if "searchedProducts" in data and "productDetails" in data["searchedProducts"]:
            for product in data["searchedProducts"]["productDetails"]:
                if "displayName" in product and "productSKU" in product:
                    products.append({
                        "name": product["displayName"],
                        "sku": product["productSKU"]
                    })
        
        return products
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching SKUs: {e}")
        return []

def prompt_for_products(products: List[Dict[str, str]]) -> Dict[str, Dict[str, any]]:
    """
    Prompt user for which products they want to monitor.
    Returns a dictionary of product configurations.
    """
    product_config = {}
    for product in products:
        while True:
            response = input(f"\nMonitor {product['name']} (SKU: {product['sku']})? (y/n): ").lower()
            if response in ['y', 'n']:
                product_config[product['name']] = {
                    "enabled": (response == 'y'),
                    "sku": product['sku']
                }
                break
            print("Please enter 'y' or 'n'")
    return product_config

def create_config_json(locale: str, currency: str, country: str, product_config: Dict[str, Dict[str, any]]) -> Dict:
    """
    Create a configuration dictionary to be saved as JSON.
    """
    config = {
        "locale_config": {
            "locale": locale,
            "currency": currency,
            "country": country
        },
        "product_config_cards": product_config
    }
    return config

def save_config_json(config: Dict, filename: str = DEFAULT_CONFIG_FILENAME):
    """Save the configuration to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print(f"\nConfiguration saved to {filename} successfully!")
    except Exception as e:
        print(f"\nError saving configuration to {filename}: {e}")

def check_config_exists(filename: str = DEFAULT_CONFIG_FILENAME) -> bool:
    """Check if the configuration file exists."""
    return os.path.exists(filename)

def main():
    parser = argparse.ArgumentParser(description='List NVIDIA SKUs for a specific locale')
    parser.add_argument('--json', action='store_true', 
                       help='Output raw SKU list in JSON format')
    parser.add_argument('--output', type=str, default=DEFAULT_CONFIG_FILENAME,
                       help=f'Specify the output JSON file (default: {DEFAULT_CONFIG_FILENAME})')
    
    args = parser.parse_args()
    output_file = args.output
    
    # Get the absolute path for more informative messages
    abs_path = os.path.abspath(output_file)
    
    # Check if the configuration file exists
    if check_config_exists(output_file):
        print(f"\nConfiguration file '{output_file}' already exists.")
        while True:
            response = input("Would you like to update the existing configuration? (y/n): ").lower()
            if response == 'n':
                print("Exiting without making changes.")
                return
            elif response == 'y':
                break
            print("Please enter 'y' or 'n'")
    else:
        print(f"\nConfiguration file '{output_file}' does not exist at {abs_path}")
        print("You will be guided through creating a new configuration file.")
    
    # Get locale choice from user
    locale, currency, country = get_locale_choice()
    print(f"\nFetching SKUs for locale: {locale}")
    products = get_skus(locale)
    
    if args.json:
        # Just output the raw product list if --json is specified
        print(json.dumps(products, indent=2))
    else:
        if products:
            print("\nAvailable Products:")
            print("-" * 50)
            for product in products:
                print(f"Name: {product['name']}")
                print(f"SKU:  {product['sku']}")
                print("-" * 50)
            
            # Prompt for configuration update
            try:
                # Get user choices for each product
                product_config = prompt_for_products(products)
                
                # Create configuration dictionary
                config = create_config_json(locale, currency, country, product_config)
                
                # Save configuration to JSON file
                save_config_json(config, args.output)
                                
            except Exception as e:
                print(f"\nError creating configuration: {e}")
        else:
            print("No products found or error occurred")

if __name__ == "__main__":
    main()