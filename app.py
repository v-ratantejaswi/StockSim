from flask import Flask, render_template, request, jsonify, url_for, redirect, flash, session
import os
from pymongo import MongoClient, ReturnDocument
import yfinance as yf
import datetime
import bcrypt
from flask_mail import Mail, Message
import random
from bson.objectid import ObjectId


app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']
mongo_conn_string = os.getenv("MONGO_STOCKS_URI")
client = MongoClient(mongo_conn_string)
db = client['StockDB']
users_collection = db['users']
collection = db['stock_details']
transactions_collection = db['transactions']
portfolio_collection = db['portfolio']


app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
mail = Mail(app)


def get_stock_info(symbol):
    res = {}
    print(symbol)
    x = symbol.split('-')
    stock = yf.Ticker(x[0])
    print(x)
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
    if 'user_id' in session:
        user = users_collection.find_one({"_id": ObjectId(session['user_id'])})
        balance = user['balance'] if user else None
        return render_template('index.html', balance=balance)
    return render_template('index.html', balance=None)

@app.route('/explore')
def explore():
    if 'user_id' in session:
        user = users_collection.find_one({"_id": ObjectId(session['user_id'])})
        balance = user['balance'] if user else None
        return render_template('explore.html', balance=balance)
    return render_template('explore.html', balance=None)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Retrieve user details from the form
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Check if a user with this email already exists
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            # User already exists
            flash("An account with this email already exists.", "danger")
            return redirect(url_for('signup'))

        # Encrypt the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Insert new user into the database
        new_user = {"name": name, "email": email, "password": hashed_password, "balance": 10000}
        users_collection.insert_one(new_user)

        # Success message and redirect to login
        flash("User created successfully. Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')




# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']
#         user = users_collection.find_one({"email": email})

#         if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
#             # Password matches, start session
#             session['user_id'] = str(user['_id'])  # Use the user's ID from the database
#             session['user_name'] = user['name']  # Store the user's name in session for personalization
#             return redirect(url_for('index'))
#         else:
#             flash('Invalid email/password combination', 'danger')
#             return redirect(url_for('login'))
#     return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({"email": email})

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            # Generate OTP
            otp = random.randint(100000, 999999)
            session['otp'] = otp  # Temporarily store OTP in session
            session['email'] = email  # Temporarily store email to verify later

            # Send OTP via email
            msg = Message("Your OTP", sender='stock-sim@outlook.com', recipients=[email])
            msg.body = f"Thank you for being a supporter of the StockSim app. The OTP for your current login session is {otp}"
            mail.send(msg)

            return redirect(url_for('verify_otp'))  # Redirect to OTP verification page
        else:
            flash('Invalid email/password combination', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']
        if 'otp' in session and session['otp'] == int(user_otp):
            # Correct OTP
            session['user_id'] = str(users_collection.find_one({"email": session['email']})['_id'])
            session['user_name'] = users_collection.find_one({"email": session['email']})['name']
            session.pop('otp', None)  # Remove OTP from session after successful verification
            session.pop('email', None)  # Remove email used for OTP
            return redirect(url_for('index'))
        else:
            flash('Invalid OTP', 'danger')
            return redirect(url_for('verify_otp'))

    return render_template('verify-otp.html')  # A simple form to enter OTP


@app.route('/logout')
def logout():
    session.clear()  # Clears all data from session
    return redirect(url_for('index'))


@app.route('/trade')
def trade():
    if 'user_id' in session:
        user = users_collection.find_one({"_id": ObjectId(session['user_id'])})
        balance = user['balance'] if user else None
        return render_template('trade.html', balance=balance)
    return render_template('trade.html', balance=None)



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


@app.route('/buy_stock', methods=['POST'])
def buy_stock():
    if 'user_id' not in session:
        return jsonify({"error": "User not logged in"}), 401

    user_id = session['user_id']
    symbol = request.json.get('symbol')
    transaction_type = request.json.get('type')  # 'dollars' or 'shares'
    amount = float(request.json.get('amount'))

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404

    stock_data = get_stock_info(symbol)
    if 'ltp' not in stock_data:
        return jsonify({"error": "Stock information is currently unavailable"}), 503
    ltp = float(stock_data['ltp'])

    if transaction_type == 'dollars':
        quantity = amount / ltp
    elif transaction_type == 'shares':
        quantity = amount
        amount = quantity * ltp  # Calculate the total cost

    amount = round(amount, 2)  # Ensure the amount is rounded to two decimal places

    if user['balance'] < amount:
        return jsonify({"error": "Insufficient balance"}), 400

    # Update the user's balance
    new_balance = round(user['balance'] - amount, 2)
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"balance": new_balance}}
    )

    # Record the transaction
    transaction = {
        "user_id": ObjectId(user_id),
        "symbol": symbol,
        "quantity": quantity,
        "transaction_price": ltp,
        "total_cost": amount,
        "type": "buy",
        "date": datetime.datetime.now()
    }
    transactions_collection.insert_one(transaction)

    # Update the portfolio
    portfolio_item = portfolio_collection.find_one({"user_id": ObjectId(user_id), "symbol": symbol})
    if portfolio_item:
        # Calculate the new weighted average price
        total_quantity = portfolio_item['quantity'] + quantity
        total_spent = portfolio_item['buy_price'] * portfolio_item['quantity'] + amount
        new_buy_price = round(total_spent / total_quantity, 2)

        portfolio_collection.update_one(
            {"_id": portfolio_item['_id']},
            {"$set": {"quantity": total_quantity, "buy_price": new_buy_price}}
        )
    else:
        # Insert new document with initial quantity and price
        portfolio_collection.insert_one({
            "user_id": ObjectId(user_id),
            "symbol": symbol,
            "buy_price": ltp,
            "quantity": quantity
        })

    return jsonify({"message": "Stock purchased successfully", "new_balance": new_balance}), 200




@app.route('/sell_stock', methods=['POST'])
def sell_stock():
    if 'user_id' not in session:
        return jsonify({"error": "User not logged in"}), 401

    user_id = session['user_id']
    symbol = request.json.get('symbol')
    transaction_type = request.json.get('type')
    amount = float(request.json.get('amount'))

    portfolio_item = portfolio_collection.find_one({"user_id": ObjectId(user_id), "symbol": symbol})
    if not portfolio_item:
        return jsonify({"error": "Stock not owned"}), 404

    stock_data = get_stock_info(symbol)
    if 'ltp' not in stock_data:
        return jsonify({"error": "Stock information is currently unavailable"}), 503
    ltp = float(stock_data['ltp'])

    if transaction_type == 'dollars':
        quantity = amount / ltp
    elif transaction_type == 'shares':
        quantity = amount

    # Check if the user has enough shares to sell
    if quantity > portfolio_item['quantity']:
        return jsonify({"error": "Insufficient shares to sell"}), 400

    sell_total = round(quantity * ltp, 2)
    new_balance = round(users_collection.find_one({"_id": ObjectId(user_id)})['balance'] + sell_total, 2)

    # Update user's balance
    users_collection.update_one({"_id": ObjectId(user_id)}, {"$inc": {"balance": sell_total}})

    # Record the transaction
    transactions_collection.insert_one({
        "user_id": ObjectId(user_id),
        "symbol": symbol,
        "quantity": -quantity,
        "transaction_price": ltp,
        "total_cost": sell_total,
        "type": "sell",
        "date": datetime.datetime.now()
    })

    # Update the portfolio entry
    new_quantity = portfolio_item['quantity'] - quantity
    if new_quantity > 0:
        portfolio_collection.update_one(
            {"user_id": ObjectId(user_id), "symbol": symbol},
            {"$set": {"quantity": new_quantity}}
        )
    else:
        # If no shares left, delete the portfolio entry
        portfolio_collection.delete_one({"user_id": ObjectId(user_id), "symbol": symbol})

    return jsonify({"message": "Stock sold successfully", "new_balance": new_balance}), 200


@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session:
        flash("Please log in to view your portfolio", "info")
        return redirect(url_for('login'))

    user_id = session['user_id']
    portfolio = portfolio_collection.find({"user_id": ObjectId(user_id)})

    stocks = []
    for item in portfolio:
        symbol = item['symbol']
        stock_data = get_stock_info(symbol + "-SomeName")  # Update this to your actual method for fetching stock data
        current_price = stock_data['ltp'] if 'ltp' in stock_data else 0
        formatted_buy_price = "{:.2f}".format(item['buy_price'])
        formatted_current_price = "{:.2f}".format(current_price)
        total_value = item['quantity'] * current_price
        pl = (current_price - item['buy_price']) * item['quantity']
        formatted_total_value = "{:.2f}".format(total_value)
        formatted_pl = "{:.2f}".format(pl)

        stocks.append({
            "symbol": symbol,
            "quantity": item['quantity'],
            "buy_price": formatted_buy_price,
            "current_price": formatted_current_price,
            "total_value": formatted_total_value,
            "pl": formatted_pl
        })

    user = users_collection.find_one({"_id": ObjectId(session['user_id'])})
    balance = user['balance'] if user else None
    return render_template('portfolio.html', stocks=stocks, balance=balance)



if __name__ == '__main__':
    app.run(debug=True)