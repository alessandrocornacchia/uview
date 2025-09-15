import pyverbs.enums as e

print("All symbols in pyverbs.enums:")
symbols = dir(e)
for symbol in sorted(symbols):
    if not symbol.startswith('_'):  # Skip private attributes
        try:
            value = getattr(e, symbol)
            print(f"{symbol} = {value}")
        except Exception as ex:
            print(f"{symbol} = <error: {ex}>")
