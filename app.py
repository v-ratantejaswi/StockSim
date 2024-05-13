from flask import Flask, render_template, request, jsonify, url_for, redirect, flash, session
import os
from pymongo import MongoClient, ReturnDocument
import yfinance as yf
import datetime
import bcrypt
from flask_mail import Mail, Message
import random
from bson.objectid import ObjectId
import time

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

# def get_stock_data(symbol, period):
#     x = symbol.split('-')
#     stock = yf.Ticker(x[0])
#     historical_prices = stock.history(period='1d', interval='1m')
#     data = {
#         "times": historical_prices.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
#         "prices": historical_prices['Close'].tolist()  # Assuming you want to plot the closing prices
#     }

#     return data

# @app.route('/stock_data', methods=['GET'])
# def stock_data():
#     symbol = request.args.get('symbol', default='', type=str)
#     period = request.args.get('period', default='1d', type=str)  # '1d', '1wk', '1mo', '1yr'

#     # Assume function `get_stock_data` fetches data according to period
#     data = get_stock_data(symbol, period)
#     return jsonify(data)

def get_stock_data(symbol, period):
    x = symbol.split('-')[0]
    stock = yf.Ticker(x)
    if period == '1d':
        historical_prices = stock.history(period='1d', interval='1m')
    elif period == '1mo':
        historical_prices = stock.history(period='1mo', interval='1d')
    elif period == '1y':
        historical_prices = stock.history(period='1y', interval='1wk')  # adjusted to '1wk'
    elif period == '5y':
        historical_prices = stock.history(period='5y', interval='1mo')  # matches requirement
    else:
        return {"error": "Invalid period"}

    data = {
        "times": historical_prices.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
        "prices": historical_prices['Close'].tolist()
    }
    return data

@app.route('/stock_data', methods=['GET'])
def stock_data():
    symbol = request.args.get('symbol', default='', type=str)
    period = request.args.get('period', default='1d', type=str)
    
    if symbol:
        data = get_stock_data(symbol, period)
        if "error" in data:
            return jsonify({"error": "Invalid period selected"}), 400
        return jsonify(data)
    return jsonify({"error": "Symbol not provided"}), 400

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
        new_user = {"name": name, "email": email, "password": hashed_password, "balance": 20000}
        users_collection.insert_one(new_user)

        # Success message and redirect to login
        flash("User created successfully. Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')




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
    else:
        flash("Please log in to access this feature.", "info")
        return redirect(url_for('login'))

@app.route('/get_stock_ownership', methods=['GET'])
def get_stock_ownership():
    if 'user_id' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    symbol = request.args.get('symbol', default='', type=str)
    print("symbol is"+symbol)
    if not symbol:
        return jsonify({"error": "No symbol provided"}), 400

    user_id = session['user_id']
    portfolio_item = portfolio_collection.find_one({"user_id": ObjectId(user_id), "symbol": symbol})

    if portfolio_item:
        return jsonify({"owned_stocks": portfolio_item['quantity']})
    else:
        return jsonify({"owned_stocks": 0})





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

    if amount < 1:
        return jsonify({"error": "Invalid purchase quantity. Please enter a value above or equal to 1."}), 400

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

    if amount < 1:
        return jsonify({"error": "Invalid sell quantity. Please enter a value above or equal to 1."}), 400

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


# @app.route('/portfolio')
# def portfolio():
#     if 'user_id' not in session:
#         flash("Please log in to view your portfolio", "info")
#         return redirect(url_for('login'))

#     user_id = session['user_id']
#     portfolio = portfolio_collection.find({"user_id": ObjectId(user_id)})

#     stocks = []
#     total_pl = 0
#     for item in portfolio:
#         symbol = item['symbol']
#         stock_data = get_stock_info(symbol + "-SomeName")  # Update this to your actual method for fetching stock data
#         current_price = stock_data['ltp'] if 'ltp' in stock_data else 0
#         formatted_buy_price = float("{:.2f}".format(item['buy_price']))
#         formatted_current_price = float("{:.2f}".format(current_price))
#         total_value = item['quantity'] * current_price
#         pl = (current_price - item['buy_price']) * item['quantity']
#         formatted_total_value = float("{:.2f}".format(total_value))
#         formatted_pl = float("{:.2f}".format(pl))
#         total_pl += float(pl)
#         stocks.append({
#             "symbol": symbol,
#             "quantity": item['quantity'],
#             "buy_price": formatted_buy_price,
#             "current_price": formatted_current_price,
#             "total_value": formatted_total_value,
#             "pl": formatted_pl
#         })

#     user = users_collection.find_one({"_id": ObjectId(session['user_id'])})
#     balance = user['balance'] if user else None
#     return render_template('portfolio.html', stocks=stocks, balance=balance, total_pl=(total_pl))

# @app.route('/api/update_portfolio')
# def update_portfolio():
#     if 'user_id' not in session:
#         return jsonify({"error": "User not logged in"}), 401

#     user_id = session['user_id']
#     portfolio_items = portfolio_collection.find({"user_id": ObjectId(user_id)})
#     updated_stocks = []
#     total_pl = 0

#     for item in portfolio_items:
#         symbol = item['symbol']
#         stock_info = get_stock_info(symbol)
#         if 'ltp' in stock_info:
            
#             current_price = float("{:.2f}".format(stock_info['ltp']))
#             buy_price = float("{:.2f}".format(item['buy_price']))
#             quantity = item['quantity']
#             current_total_value = current_price * quantity
#             pl = (current_price - buy_price) * quantity

#             updated_stocks.append({
#                 "symbol": symbol,
#                 "quantity": quantity,
#                 "buy_price": buy_price,
#                 "current_price": current_price,
#                 "total_value": current_total_value,
#                 "pl": pl
#             })

#             total_pl += pl

#     return jsonify({"stocks": updated_stocks, "total_pl": total_pl})


def calculate_portfolio_values(user_id):
    portfolio_items = portfolio_collection.find({"user_id": ObjectId(user_id)})
    stocks = []
    total_pl = 0
    port_value = 0

    for item in portfolio_items:
        stock_info = get_stock_info(item['symbol'])
        if 'ltp' in stock_info:
            current_price = float("{:.2f}".format(stock_info['ltp']))
            buy_price = float("{:.2f}".format(item['buy_price']))
            quantity = item['quantity']
            current_total_value = float("{:.2f}".format(current_price * quantity))
            pl = float("{:.2f}".format((current_price - buy_price) * quantity))
            stocks.append({
                "symbol": item['symbol'],
                "quantity": quantity,
                "buy_price": buy_price,
                "current_price": current_price,
                "total_value": current_total_value,
                "pl": pl
            })
            port_value += current_total_value
            total_pl += pl

    return stocks, total_pl, port_value

@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session:
        flash("Please log in to view your portfolio", "info")
        return redirect(url_for('login'))

    user_id = session['user_id']
    stocks, total_pl, port_value = calculate_portfolio_values(user_id)
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    balance = user['balance'] if user else None

    return render_template('portfolio.html', stocks=stocks, balance=balance, total_pl=total_pl, port_value=port_value)

@app.route('/api/update_portfolio')
def update_portfolio():
    if 'user_id' not in session:
        return jsonify({"error": "User not logged in"}), 401

    user_id = session['user_id']
    stocks, total_pl, port_value = calculate_portfolio_values(user_id)

    return jsonify({"stocks": stocks, "total_pl": total_pl, "port_value": port_value})

@app.route('/about')
def about():
    return render_template('about.html')

def send_password_email(email, password):
    msg = Message('Your Password for StockSim', sender='stock-sim@outlook.com', recipients=[email])
    msg.body = f'Your current password is: {password}\n\nPlease log in and change your password immediately for your security.'
    mail.send(msg)


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = users_collection.find_one({"email": email})
        if user:
            # Generate OTP
            otp = random.randint(100000, 999999)
            session['otp'] = otp  # Store OTP in session
            session['email_for_reset'] = email  # Store email to verify later

            # Send OTP via email
            msg = Message("Your OTP for Password Reset", sender='stock-sim@outlook.com', recipients=[email])
            msg.body = f"Your OTP for resetting your password is {otp}. Please enter this code to proceed with setting a new password."
            mail.send(msg)

            flash('An OTP has been sent to your email. Please check your email to proceed with resetting your password.', 'info')
            return redirect(url_for('verify_otp_for_reset'))
        else:
            flash('Email address not found. Please sign up.', 'danger')
            return redirect(url_for('signup'))
    return render_template('forgot-password.html')

@app.route('/verify_otp_for_reset', methods=['GET', 'POST'])
def verify_otp_for_reset():
    if request.method == 'POST':
        user_otp = request.form['otp']
        if 'otp' in session and int(user_otp) == session['otp']:
            return render_template('reset-password.html')  # A form to enter new password
        else:
            flash('Invalid OTP', 'danger')
            return redirect(url_for('forgot_password'))
    return render_template('verify-otp-for-reset.html')  # A simple form to enter OTP


@app.route('/reset-password', methods=['POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form['new_password']
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Ensure the email collected earlier is valid and set the new password
        if 'email_for_reset' in session:
            users_collection.update_one(
                {"email": session['email_for_reset']},
                {"$set": {"password": hashed_password}}
            )
            session.pop('email_for_reset', None)  # Clean up session
            session.pop('otp', None)  # Clean up session
            flash('Your password has been reset successfully. Please login with your new password.', 'success')
            return redirect(url_for('login'))
    return render_template('reset-password.html')  # Form to enter new password



if __name__ == '__main__':
    app.run(debug=True)