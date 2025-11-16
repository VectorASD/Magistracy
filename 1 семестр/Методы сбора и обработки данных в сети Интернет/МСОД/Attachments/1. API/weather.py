# e5e4cd692a72b0b66ea0a6b80255d1c3
import requests
from pprint import pprint

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}
params = {'q': 'Chelyabinsk',
          'appid': 'e5e4cd692a72b0b66ea0a6b80255d1c3'}
url = 'https://api.openweathermap.org/data/2.5/weather'

response = requests.get(url, headers=headers, params=params)
j_data = response.json()
print(j_data) # {'cod': 401, 'message': 'Invalid API key. Please see https://openweathermap.org/faq#error401 for more info.'}
pprint(f"В городе {j_data.get('name')} температура {round(j_data.get('main').get('temp') - 273.15, 2)} градусов")




