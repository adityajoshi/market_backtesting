import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_name TEXT NOT NULL,
            buy_date TEXT NOT NULL,
            sell_date TEXT NOT NULL,
            buy_price INTEGER NOT NULL,
            sell_price INTEGER NOT NULL,
            strategy_name TEXT NOT NULL
        )
    ''')

    # Pre-populate Nifty 50 stocks (sample list)
    nifty_stocks = [
        'RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK', 'HUL', 'INFY', 'ITC',
        'SBIN', 'BHARTIARTL', 'KOTAKBANK', 'BAJFINANCE', 'LT', 'ASIANPAINT',
        'AXISBANK', 'MARUTI', 'SUNPHARMA', 'TITAN', 'ULTRACEMCO', 'BAJAJFINSV',
        'WIPRO', 'TATASTEEL', 'M&M', 'HCLTECH', 'ADANIENT', 'ADANIPORTS',
        'NTPC', 'POWERGRID', 'ONGC', 'TATAMOTORS', 'NESTLEIND', 'TECHM',
        'GRASIM', 'JSWSTEEL', 'HINDALCO', 'DIVISLAB', 'INDUSINDBK', 'CIPLA',
        'DRREDDY', 'BRITANNIA', 'SBILIFE', 'EICHERMOT', 'COALINDIA', 'APOLLOHOSP',
        'BAJAJ-AUTO', 'TATACONSUM', 'HEROMOTOCO', 'UPL', 'BPCL', 'HDFCLIFE', 'LTIM'
    ]

    # Insert only if empty
    c.execute('SELECT count(*) FROM stocks')
    count = c.fetchone()[0]
    if count == 0:
        for stock in nifty_stocks:
            c.execute('INSERT INTO stocks (symbol) VALUES (?)', (stock,))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
