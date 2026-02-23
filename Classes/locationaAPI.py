import os
import requests
from dotenv import load_dotenv
load_dotenv()

class Location():
    def __init__(self, city, country):

        self.api_key = os.getenv("API_KEY")
        self.city = city
        self.country = country

    def coordinates(self):
        name = requests.get(f"https://geocode.maps.co/search?q={self.city},{self.country}&api_key={self.api_key}")
        data = name.json()
        lat = data[0].get('lat')
        lon = data[0].get('lon')
        return lat, lon
