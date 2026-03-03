import os
import json
import talib
from talib import abstract

def generate_talib_metadata(output_path: str):
    """
    Generates a comprehensive JSON dictionary of all TA-Lib metrics,
    including their required inputs, optimal parameters (with defaults), and outputs.
    """
    functions = talib.get_functions()
    metadata = {}
    
    for func_name in functions:
        try:
            func = abstract.Function(func_name)
            info = func.info
            
            # Extract relevant information
            metadata[func_name] = {
                "group": info.get("group", "Unknown"),
                "display_name": info.get("display_name", func_name),
                "inputs": info.get("inputs", {}), # usually {'price': ['high', 'low', 'close']} or similar
                "parameters": info.get("parameters", {}), # optional params with default values e.g. {'timeperiod': 14}
                "outputs": info.get("outputs", []) # returned arrays e.g. ['macd', 'macdsignal', 'macdhist']
            }
        except Exception as e:
            print(f"Failed to extract info for {func_name}: {e}")
            
    with open(output_path, 'w') as f:
        json.dump(metadata, f, indent=2)
        
    print(f"Successfully generated metadata for {len(metadata)} TA-Lib functions at {output_path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(current_dir, "talib_metadata.json")
    generate_talib_metadata(output_file)
