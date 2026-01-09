import talib, json

print(json.dumps(talib.get_function_groups(), indent=4))