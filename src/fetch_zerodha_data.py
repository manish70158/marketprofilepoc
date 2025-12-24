# -*- coding: utf-8 -*-
"""
Fetch Historical Data from Zerodha Without API
Based on: https://www.youtube.com/watch?v=x07JVy6DyYk

This script fetches historical candlestick data directly from Zerodha's web interface
without requiring a paid API subscription. It works by using the ENCTOKEN from your 
logged-in Zerodha session.

IMPORTANT: 
- You must be logged into Zerodha in your browser
- Extract ENCTOKEN from browser's Network tab (see instructions below)
- Zerodha limits to 60 days per request, so we fetch in 2-month chunks
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import time
import openpyxl  # Required for Excel export

# =====================================================================
# HOW TO GET YOUR ENCTOKEN:
# =====================================================================
# 1. Login to Zerodha in your browser (https://kite.zerodha.com)
# 2. Open Developer Tools (F12 or Right-click > Inspect)
# 3. Go to Network tab > Fetch/XHR
# 4. Refresh the page or open a chart
# 5. Find any API request and look for "Request Headers" > "Cookie"
# 6. Copy the value after "enctoken=" (everything until the semicolon)
# 7. Paste it below
# =====================================================================

# YOUR ENCTOKEN HERE (Replace with your actual token)
# IMPORTANT: Copy ONLY the enctoken value (before &uid or semicolon)
ENCTOKEN = 'oTEsySq+Ru1lTb9mJLh1Sj3tFQnBF0IpYUuMiT6ztYtmLxn5I35Ae+Qt3ZVhytj+M+tqfbcMEJzdsH/Ea5PTTHDtg1gLfjHZgUQX6zM+IJk9j2eou8hu+A=='

# =====================================================================
# CONFIGURATION
# =====================================================================

class ZerodhaDataFetcher:
    """
    Fetches historical data from Zerodha without API subscription
    """
    
    BASE_URL = "https://kite.zerodha.com/oms/instruments/historical"
    
    def __init__(self, enctoken: str):
        """
        Initialize the data fetcher
        
        Args:
            enctoken: Your Zerodha ENCTOKEN from browser cookies
        """
        self.enctoken = enctoken
        self.session = requests.Session()
        self.headers = {
            "Authorization": f"enctoken {self.enctoken}"
        }
    
    def fetch_data(self, 
                   token: str,
                   timeframe: str = "minute",
                   start_date: datetime = None,
                   end_date: datetime = None,
                   oi: int = 1) -> pd.DataFrame:
        """
        Fetch historical data for a single date range (max 60 days)
        
        Args:
            token: Instrument token (e.g., "738561" for RELIANCE)
            timeframe: minute, 3minute, 5minute, 10minute, 15minute, 30minute, 
                      60minute, day, etc.
            start_date: Start date for data
            end_date: End date for data
            oi: Open Interest flag (1 for F&O, 0 for equity)
        
        Returns:
            DataFrame with OHLCV data
        """
        # Build URL
        url = f"{self.BASE_URL}/{token}/{timeframe}"
        
        # Build parameters
        params = {
            "oi": oi,
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d")
        }
        
        try:
            # Make request
            response = self.session.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            # Extract data
            data = response.json()
            candles = data.get("data", {}).get("candles", [])
            
            if not candles:
                print(f"No data returned for {start_date} to {end_date}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            # Check number of columns (6 for equity, 7 for F&O with OI)
            if len(candles[0]) == 7:
                columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'oi']
            else:
                columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            
            df = pd.DataFrame(candles, columns=columns)
            df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)  # Remove timezone for Excel compatibility
            
            print(f"✓ Fetched {len(df)} candles from {df['date'].min()} to {df['date'].max()}")
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()
    
    def fetch_bulk_data(self,
                       token: str,
                       timeframe: str = "minute",
                       start_date: datetime = None,
                       end_date: datetime = None,
                       oi: int = 1,
                       chunk_days: int = 60) -> pd.DataFrame:
        """
        Fetch historical data for extended periods by breaking into chunks
        
        Zerodha limits each request to 60 days, so we split the date range
        into 2-month chunks and combine the results.
        
        Args:
            token: Instrument token
            timeframe: Candle timeframe
            start_date: Start date
            end_date: End date
            oi: Open Interest flag
            chunk_days: Days per chunk (default 60, don't exceed this)
        
        Returns:
            Combined DataFrame with all data
        """
        if start_date is None:
            start_date = datetime(2015, 1, 1)
        
        if end_date is None:
            end_date = datetime.now()
        
        print(f"\n{'='*70}")
        print(f"Fetching {timeframe} data for token {token}")
        print(f"Date range: {start_date.date()} to {end_date.date()}")
        print(f"{'='*70}\n")
        
        all_data = []
        current_start = start_date
        
        while current_start < end_date:
            # Calculate chunk end date
            current_end = min(current_start + timedelta(days=chunk_days), end_date)
            
            # Fetch data for this chunk
            df = self.fetch_data(
                token=token,
                timeframe=timeframe,
                start_date=current_start,
                end_date=current_end,
                oi=oi
            )
            
            if not df.empty:
                all_data.append(df)
            
            # Move to next chunk
            current_start = current_end
            
            # Sleep to avoid rate limiting
            time.sleep(0.5)
        
        # Combine all chunks
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            final_df = final_df.drop_duplicates(subset=['date'])
            final_df = final_df.sort_values('date').reset_index(drop=True)
            
            print(f"\n{'='*70}")
            print(f"✓ COMPLETE: Fetched {len(final_df)} total candles")
            print(f"Date range: {final_df['date'].min()} to {final_df['date'].max()}")
            print(f"{'='*70}\n")
            
            return final_df
        else:
            print("No data fetched!")
            return pd.DataFrame()


# =====================================================================
# INSTRUMENT TOKENS (Common stocks/indices)
# =====================================================================
# You can find token by:
# 1. Open Zerodha chart for the instrument
# 2. Check Network tab, look at the API URL
# 3. The number after "/historical/" is the token

INSTRUMENTS = {
    "RELIANCE": "738561",
    "NIFTY BANK": "260105",  # Nifty Bank Index
    "NIFTY 50": "256265",    # Nifty 50 Index
    "TCS": "2953217",
    "INFY": "408065",
    "SBIN": "779521",
    "HDFCBANK": "341249",
    # Add more as needed
}


# =====================================================================
# USAGE EXAMPLES
# =====================================================================

def example_1_fetch_recent_data():
    """Example 1: Fetch recent 1-minute data"""
    
    fetcher = ZerodhaDataFetcher(ENCTOKEN)
    
    # Fetch last 30 days of 1-minute data for RELIANCE
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    df = fetcher.fetch_data(
        token=INSTRUMENTS["RELIANCE"],
        timeframe="minute",
        start_date=start_date,
        end_date=end_date,
        oi=0  # 0 for equity, 1 for F&O
    )
    
    print(df.head())
    print(f"\nTotal candles: {len(df)}")
    
    # Save to Excel
    filename = "reliance_recent_1min.xlsx"
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"\n✓ Data saved to {filename}")


def example_2_fetch_10_years():
    """Example 2: Fetch 10 years of data (any timeframe)"""
    
    fetcher = ZerodhaDataFetcher(ENCTOKEN)
    
    # Fetch 10 years of 5-minute data for Nifty Bank
    df = fetcher.fetch_bulk_data(
        token=INSTRUMENTS["NIFTY BANK"],
        timeframe="5minute",
        start_date=datetime(2015, 1, 1),
        end_date=datetime(2025, 12, 24),
        oi=1  # Use 1 for indices/F&O
    )
    
    print(df.head())
    print(df.tail())
    print(f"\nTotal candles: {len(df)}")
    
    # Save to Excel
    df.to_excel("nifty_bank_5min_10years.xlsx", index=False, engine='openpyxl')
    print("\n✓ Data saved to nifty_bank_5min_10years.xlsx")


def example_3_multiple_timeframes():
    """Example 3: Fetch same instrument with different timeframes"""
    
    fetcher = ZerodhaDataFetcher(ENCTOKEN)
    
    timeframes = ["minute", "5minute", "15minute", "day"]
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2025, 12, 24)
    
    for tf in timeframes:
        print(f"\nFetching {tf} data...")
        df = fetcher.fetch_bulk_data(
            token=INSTRUMENTS["RELIANCE"],
            timeframe=tf,
            start_date=start_date,
            end_date=end_date,
            oi=0
        )
        
        filename = f"reliance_{tf}_data.xlsx"
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"✓ Saved to {filename}")


# =====================================================================
# MAIN EXECUTION
# =====================================================================

if __name__ == "__main__":
    # Check if ENCTOKEN is set
    if ENCTOKEN == "your_enctoken_here":
        print("\n" + "="*70)
        print("ERROR: Please set your ENCTOKEN first!")
        print("="*70)
        print("\nSteps to get ENCTOKEN:")
        print("1. Login to https://kite.zerodha.com")
        print("2. Open Developer Tools (F12)")
        print("3. Go to Network tab > Fetch/XHR")
        print("4. Refresh page or open a chart")
        print("5. Find any API request > Request Headers > Cookie")
        print("6. Copy value after 'enctoken=' (before semicolon)")
        print("7. Replace ENCTOKEN variable in this script")
        print("="*70 + "\n")
    else:
        # Run example
        print("Select example to run:")
        print("1. Fetch recent 30 days of 1-minute data")
        print("2. Fetch 10 years of 5-minute data for Nifty Bank")
        print("3. Fetch multiple timeframes for RELIANCE")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            example_1_fetch_recent_data()
        elif choice == "2":
            example_2_fetch_10_years()
        elif choice == "3":
            example_3_multiple_timeframes()
        else:
            print("Invalid choice. Running example 1...")
            example_1_fetch_recent_data()
