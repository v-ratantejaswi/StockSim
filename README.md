# StockSim

StockSim is a stock trading simulation web application that allows users to explore, trade, and manage their stock portfolios. The application provides real-time stock data, stock price charts, and a simulated trading environment where users can buy and sell stocks.

## Table of Contents
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Setup and Installation](#setup-and-installation)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Routes](#routes)
- [License](#license)

## Features
- User Authentication
  - Sign Up
  - Log In with OTP Verification
  - Password Reset with Email Verification
- Real-time Stock Data
  - Display of stock information including LTP (Last Traded Price), day high, day low, etc.
  - Stock price chart for different periods (1 Day, 1 Month, 1 Year, 5 Years)
- Simulated Trading
  - Buy and sell stocks using either dollar amounts or share quantities
  - Portfolio management showing current holdings, average buy price, current LTP, total value, and profit/loss
- View Latest Stock News
- Automatic Portfolio Updates
- Responsive design

## Tech Stack
- **Backend**: Flask, MongoDB, yFinance, Flask-Mail, Bcrypt
- **Frontend**: HTML, CSS, JavaScript, jQuery, Bootstrap, Chart.js
- **Other**: Microsoft Azure(deployment), GitHub Actions (for CI/CD)

## Setup and Installation
### Prerequisites
- Python 3.8 or higher
- MongoDB

### Installation Steps
1. **Clone the repository**:
   ```sh
   git clone https://github.com/yourusername/stock-sim.git
   cd stock-sim
   ```
2. **Install backend dependencies**:
   ```sh
   pip install -r requirements.txt
   ```
3. **Set up environment variables**:
   - Create a .env file in the project root directory with the following content:
   ```sh
   SECRET_KEY=your_secret_key
   MONGO_STOCKS_URI=your_mongodb_uri
   MAIL_SERVER=your_mail_server
   MAIL_USERNAME=your_mail_username
   MAIL_PASSWORD=your_mail_password
   ```
4. **Run the Flask application**:
   ```sh
   flask run
   ```
5. **Access the application**:
   - Open your browser and navigate to http://127.0.0.1:5000
  
## Environment Variables
The application uses the following environment variables:

- SECRET_KEY: A secret key for Flask session management
- MONGO_STOCKS_URI: Connection string for MongoDB
- MAIL_SERVER: Mail server address (e.g., smtp.gmail.com)
- MAIL_USERNAME: Mail server username
- MAIL_PASSWORD: Mail server password

## Usage
### User Authentication
- Sign Up: Users can create a new account by providing their name, email, and password.
- Log In: Users can log in with their email and password. An OTP is sent to their email for verification.
- Forgot Password: Users can reset their password by entering their registered email. An OTP is sent for verification.
### Trading
-Explore Stocks: Users can search for stocks and view their real-time data.
- Buy Stocks: Users can buy stocks using either dollar amounts or share quantities.
- Sell Stocks: Users can sell their holdings partially or completely.
### Portfolio Management
- View Portfolio: Users can view their current holdings, average buy price, current LTP, total value, and profit/loss.
- Automatic Updates: The portfolio data is automatically updated every 30 seconds.

### Routes
- /: Home page
- /explore: Explore stocks page
- /signup: User sign-up page
- /login: User log-in page
- /verify_otp: OTP verification page for login
- /logout: User logout
- /trade: Trade stocks page
- /portfolio: User portfolio page
- /stock_data: API endpoint for fetching stock data
- /stock_info: API endpoint for fetching stock information
- /search: API endpoint for searching stocks
- /buy_stock: API endpoint for buying stocks
- /sell_stock: API endpoint for selling stocks
- /forgot-password: Forgot password page
- /verify_otp_for_reset: OTP verification page for password reset
- /reset-password: Reset password page
- /api/update_portfolio: API endpoint for updating portfolio data
- /about: About page

## Contributions
Feel free to contribute to the project by submitting pull requests or opening issues for any bugs or feature requests. For any questions, please contact ratantejaswi@gmail.com.
