# views.py

from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import StockData


import os 
import databento as db
import pandas as pd

from dotenv import load_dotenv

load_dotenv()

APIKEY = os.getenv("APIKEY")

# First, create a historical client
client = db.Historical(APIKEY)

DATABASE_ACCESS = True 
#if False, the app will always query the Alpha Vantage APIs regardless of whether the stock data for a given ticker is already in the local database


#view function for rendering home.html
def home(request):
    return render(request, 'home.html', {})

def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

@csrf_exempt
def get_stock_data(request):
    if is_ajax(request=request):
        #get ticker from the AJAX POST request
        ticker = request.POST.get('ticker', 'null')
        ticker = ticker.upper()

        #StockData.objects.filter(symbol=ticker).delete()

        if DATABASE_ACCESS == True:
            #checking if the database already has data stored for this ticker before querying the Alpha Vantage API
            if StockData.objects.filter(symbol=ticker).exists(): 
                #We have the data in our database! Get the data from the database directly and send it back to the frontend AJAX call
                entry = StockData.objects.filter(symbol=ticker)[0]
                return HttpResponse(entry.data, content_type='application/json')
            
        data = client.timeseries.get_range(
        dataset="DBEQ.BASIC",
        start="2024-10-15T09:30:00",
        end="2024-10-15T21:00:00",
        symbols= [ticker],
        stype_in="raw_symbol",
        schema="ohlcv-1m",
        )

        # Then, convert the DBNStore to a pandas DataFrame
        trades_df = data.to_df()

        resampled_df = (
        trades_df.groupby([trades_df.index.to_period("1 min"), "symbol"])
        .agg({"open": "first", 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'})
        .reset_index("symbol")
        )
        resampled_df.index = resampled_df.index.to_timestamp().tz_localize("UTC")
        resampled_df.index.names = ["ts_event"]
        resampled_df.columns = ["symbol", "open", "high", "low", "close", "volume"]

        # Finally, print the reconstructed bars
        print(resampled_df)

        #StockData.objects.filter(symbol=ticker).delete()
    
        #save the dictionary to database
        #temp = StockData(symbol=ticker, data=json.dumps(resampled_df))
        #temp.save()
        resampled_df_json = resampled_df.reset_index().to_json(orient="records", date_format="iso")

        #return the data back to the frontend AJAX call 
        return HttpResponse(resampled_df_json, content_type='application/json')

    else:
        message = "Not Ajax"
        return HttpResponse(message)
