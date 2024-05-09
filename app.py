from flask import Flask, render_template, request, jsonify
import os
from pymongo import MongoClient
import yfinance as yf
import time

app = Flask(__name__)
mongo_conn_string = os.getenv("MONGO_STOCKS_URI")
client = MongoClient(mongo_conn_string)
db = client['StockDB']
collection = db['stock_details']

def get_stock_info(symbol):
    res = {}
    print(symbol)
    x = symbol.split('-')
    stock = yf.Ticker(x[0])
    res['symbol'] = x[0]
    res['name'] = x[1]
    res['ltp'] = stock.basic_info['lastPrice']
    res['open'] = stock.basic_info['open']
    res['dayHigh'] = stock.basic_info['dayHigh']
    res['dayLow'] = stock.basic_info['dayLow']
    res['volume'] = stock.history(period='1d', interval='1m').iloc[-2]['Volume']
    res['yearHigh'] = stock.basic_info['yearHigh']
    res['summary'] = stock.info['longBusinessSummary']
    res['yearLow'] = stock.basic_info['yearLow']
    yearopen = stock.history(period='1y', interval='1d').iloc[0]['Open']
    res['yearChange'] = (res['ltp'] - yearopen) / yearopen * 100
    return res

def get_stock_data(symbol, period):
    x = symbol.split('-')
    stock = yf.Ticker(x[0])
    historical_prices = stock.history(period='1d', interval='1m')
    data = {
        "times": historical_prices.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
        "prices": historical_prices['Close'].tolist()  # Assuming you want to plot the closing prices
    }

    return data

@app.route('/stock_info', methods=['GET'])
def stock_info():
    field = request.args.get('symbol', default='', type=str)
    if field:
        info = get_stock_info(field)
        return jsonify(info)
    return jsonify({"error": "Symbol not provided"})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stock_data', methods=['GET'])
def stock_data():
    symbol = request.args.get('symbol', default='', type=str)
    period = request.args.get('period', default='1d', type=str)  # '1d', '1wk', '1mo', '1yr'

    # Assume function `get_stock_data` fetches data according to period
    data = get_stock_data(symbol, period)
    return jsonify(data)


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    results = collection.find({"$or": [{"Symbol": {"$regex": f'^{query}', "$options": "i"}}, {"Name": {"$regex": f'^{query}', "$options": "i"}}]}).limit(5)
    matches = [{"symbol": result['Symbol'], "name": result['Name']} for result in results]
    return jsonify(matches)



if __name__ == '__main__':
    app.run(debug=True)