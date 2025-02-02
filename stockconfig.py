import requests
import argparse
import json
from typing import Dict, List, Tuple
import re
import sys

try:
# Import configuration from config.py
    from config import (
        API_CONFIG,
        SKU_CHECK_API_CONFIG,
    )
except ModuleNotFoundError:
    print("config.py DOES NOT EXIST. Rename example_config.py to config.py to begin.")
    sys.exit(1)


def load_locales() -> List[Tuple[str, str, str]]:
    """
    Load locales from locales.txt file.
    Returns list of tuples containing (country, locale_code, currency).
    """
    try:
        with open('locales.txt', 'r', encoding='utf-8') as f:
            locales = []
            for line in f:
                if line.strip():  # Skip empty lines
                    country, locale, currency = line.strip().split(',')
                    locales.append((country, locale, currency))
            return locales
    except FileNotFoundError:
        print("Warning: locales.txt not found. Using default locale.")
        return [("United Kingdom", "en-gb", "£")]
    except Exception as e:
        print(f"Error loading locales: {e}")
        return [("United Kingdom", "en-gb", "£")]

def get_locale_choice() -> tuple[str, str]:
    """
    Prompt user for locale choice.
    Returns tuple of (locale, currency_symbol)
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
                return custom_locale, currency
            elif 1 <= choice_num <= len(locales):
                _, locale, currency = locales[choice_num - 1]
                return locale, currency
            else:
                print(f"Please enter a number between 1 and {len(locales) + 1}")
        except ValueError:
            print("Invalid input. Please try again.")

def update_locale_config(config_content: str, locale: str, currency: str) -> str:
    """
    Update the LOCALE_CONFIG section in the config file content.
    """
    # Find the LOCALE_CONFIG section
    locale_pattern = r'("locale":\s*")[^"]+(")'
    currency_pattern = r'("currency":\s*")[^"]+(")'
    
    # Update locale and currency
    updated_content = re.sub(locale_pattern, f'\\1{locale}\\2', config_content)
    updated_content = re.sub(currency_pattern, f'\\1{currency}\\2', updated_content)
    
    return updated_content

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

def read_config_file() -> str:
    """Read the entire config.py file."""
    with open('config.py', 'r', encoding='utf-8') as f:
        return f.read()

def update_product_config(config_content: str, products: List[Dict[str, str]], product_choices: Dict[str, bool]) -> str:
    """
    Update the PRODUCT_CONFIG_CARDS section in the config file content.
    Preserves file structure and comments.
    """
    # Find the start and end of the PRODUCT_CONFIG_CARDS section
    start_pattern = r"PRODUCT_CONFIG_CARDS = {"
    start_match = re.search(start_pattern, config_content)
    
    if not start_match:
        raise ValueError("Could not find PRODUCT_CONFIG_CARDS in config file")
        
    start_pos = start_match.start()
    
    # Find the matching closing brace
    opening_count = 1
    closing_pos = start_pos + len(start_pattern)
    
    for i in range(start_pos + len(start_pattern), len(config_content)):
        if config_content[i] == '{':
            opening_count += 1
        elif config_content[i] == '}':
            opening_count -= 1
            if opening_count == 0:
                closing_pos = i + 1
                break
    
    # Create new config string
    new_config = "PRODUCT_CONFIG_CARDS = {\n"
    for i, product in enumerate(products):
        enabled = product_choices.get(product['name'], False)
        new_config += f'    "{product["name"]}": {{\n'
        new_config += f'        "enabled": {str(enabled)}\n'
        new_config += '    }'
        if i < len(products) - 1:  # Add comma only if not the last item
            new_config += ','
        new_config += '\n'
    new_config += "}"
    
    # Replace the old config with the new one
    updated_content = (
        config_content[:start_pos] +
        new_config +
        config_content[closing_pos:]
    )
    
    return updated_content

def prompt_for_products(products: List[Dict[str, str]]) -> Dict[str, bool]:
    """
    Prompt user for which products they want to monitor.
    Returns a dictionary of product names and their enabled status.
    """
    choices = {}
    for product in products:
        while True:
            response = input(f"\nMonitor {product['name']}? (y/n): ").lower()
            if response in ['y', 'n']:
                choices[product['name']] = (response == 'y')
                break
            print("Please enter 'y' or 'n'")
    return choices

def save_config(content: str):
    """Save the updated config back to config.py."""
    with open('config.py', 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    parser = argparse.ArgumentParser(description='List NVIDIA SKUs for a specific locale')
    parser.add_argument('--json', action='store_true', 
                       help='Output in JSON format')
    
    args = parser.parse_args()
    
    # Get locale choice from user
    locale, currency = get_locale_choice()
    print(f"\nFetching SKUs for locale: {locale}")
    products = get_skus(locale)
    
    if args.json:
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
            while True:
                update_response = input("\nWould you like to update the product configuration? (y/n): ").lower()
                if update_response in ['y', 'n']:
                    break
                print("Please enter 'y' or 'n'")
            
            if update_response == 'y':
                try:
                    # Get user choices for each product
                    product_choices = prompt_for_products(products)
                    
                    # Update configuration files
                    config_content = read_config_file()
                    
                    # Update product config
                    updated_content = update_product_config(config_content, products, product_choices)
                    
                    # Update locale config
                    updated_content = update_locale_config(updated_content, locale, currency)
                    
                    # Save updated config
                    save_config(updated_content)
                    print("\nConfiguration updated successfully!")
                
                except Exception as e:
                    print(f"\nError updating configuration: {e}")
        else:
            print("No products found or error occurred")

if __name__ == "__main__":
    main()