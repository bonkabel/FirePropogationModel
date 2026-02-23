import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
# city = input("What is the name of the city?")
# country = input("What is the name of the country")
city = "Miami"
country = "FL"
name = requests.get(f"https://geocode.maps.co/search?q={city},{country}&api_key={api_key}")
data = name.json()
lat = data[0].get('lat')
lon = data[0].get('lon')
