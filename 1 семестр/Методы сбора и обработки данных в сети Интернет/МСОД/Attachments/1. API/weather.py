import requests
from pprint import pprint

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}

# old:
params = {'q': 'Chelyabinsk',
          'appid': 'e5e4cd692a72b0b66ea0a6b80255d1c3'}
url = 'https://api.openweathermap.org/data/2.5/weather'
# {'cod': 401, 'message': 'Invalid API key. Please see https://openweathermap.org/faq#error401 for more info.'}

# new:
url = "https://api.openweathermap.org/data/3.0/onecall/timemachine"
params = {"lat": 39.099724,
          "lon": -94.578331,
          "dt": 1643803200,
          "appid": "7a7bb06364215d01c0b8f9837fc4612d"}
# {'cod': 401, 'message': 'Please note that using One Call 3.0 requires a separate subscription to the One Call by Call plan. Learn more here https://openweathermap.org/price. If you have a valid subscription to the One Call by Call plan, but still receive this error, then please see https://openweathermap.org/faq#error401 for more info.'}

response = requests.get(url, headers=headers, params=params)
j_data = response.json()
print(j_data)
pprint(f"В городе {j_data.get('name')} температура {round(j_data.get('main').get('temp') - 273.15, 2)} градусов")




