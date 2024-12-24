import requests
from datetime import datetime, timedelta
from config import API_KEY


def get_location_key(location):

    location_url = 'http://dataservice.accuweather.com/locations/v1/cities/autocomplete'
    params = {
        'apikey': API_KEY,
        'q': location,
        'language': 'ru-ru'
    }
    try:
        response = requests.get(location_url, params=params)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]['Key']
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f'Ошибка при запросе локации: {e}')
        return None


def get_weather(location_key, days):

    weather_url = f'http://dataservice.accuweather.com/forecasts/v1/daily/5day/{location_key}'
    params = {
        'apikey': API_KEY,
        'language': 'ru-ru',
        'details': 'true',
        'metric': 'true'
    }
    try:
        response = requests.get(weather_url, params=params)
        response.raise_for_status()
        data = response.json()
        if data and 'DailyForecasts' in data:
            forecasts = []
            dates = []
            temps = []
            for forecast in data['DailyForecasts'][:days]:
                date = forecast['Date'][:10]  # Берем только дату (без времени)
                temp = forecast['Temperature']['Maximum']['Value']
                humidity = forecast['Day']['RelativeHumidity']
                wind = forecast['Day']['Wind']['Speed']['Value']
                precipitation = forecast['Day']['PrecipitationProbability']
                description = forecast['Day']['LongPhrase']

                forecasts.append({
                    'date': date,
                    'temp': temp,
                    'humidity': humidity,
                    'wind': wind,
                    'precipitation': precipitation,
                    'description': description
                })
                dates.append(date)
                temps.append(temp)
            return forecasts, dates, temps
        else:
            return None, None, None
    except requests.exceptions.RequestException as e:
        print(f'Ошибка при запросе погоды: {e}')
        return None, None, None
