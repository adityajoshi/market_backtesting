import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Cache stocks on startup
def load_stocks():
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT symbol FROM stocks')
        stocks = [row[0] for row in c.fetchall()]
        conn.close()
        return stocks
    except sqlite3.OperationalError:
        return []

cached_stocks = load_stocks()

@app.route('/')
def index():
    return render_template('index.html', stocks=cached_stocks)

@app.route('/save', methods=['POST'])
def save_trade():
    data = request.json

    # Validate required fields
    required_fields = ['stock_name', 'buy_date', 'sell_date', 'buy_price', 'sell_price', 'strategy_name']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        buy_price = round(float(data['buy_price']))
        sell_price = round(float(data['sell_price']))
    except ValueError:
        return jsonify({'error': 'Invalid price values'}), 400

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO trades (stock_name, buy_date, sell_date, buy_price, sell_price, strategy_name)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['stock_name'], data['buy_date'], data['sell_date'], buy_price, sell_price, data['strategy_name']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Trade saved successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
