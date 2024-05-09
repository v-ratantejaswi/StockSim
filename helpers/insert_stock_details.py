import pandas as pd
import os
from pymongo import MongoClient

stock_data = pd.read_csv('all_stocks.csv')
mongo_conn_string =  os.getenv("MONGO_STOCKS_URI")
# Create a new MongoClient instance
client = MongoClient(mongo_conn_string)

# Access the 'stocks' database
db = client['StockDB']

# Access the 'stock_data' collection
collection = db['stock_details']

stock_data_df = stock_data[['Symbol', 'Name', 'Market Cap', 'Country', 'IPO Year', 'Volume', 'Sector', 'Industry']]
collection.insert_many(stock_data_df.to_dict('records'))