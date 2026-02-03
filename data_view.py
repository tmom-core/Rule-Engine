import pandas as pd

def main():
    df = pd.read_csv("market_data.csv")
    print(df.columns)
    print(df["timestamp_server"])

if __name__ == "__main__":
    main()
    