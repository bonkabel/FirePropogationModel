import streamlit as st
from geopy.geocoders import Nominatim

st.title("Fire Propagation model")
location_input = st.text_input("Enter a location (e.g., 'San Francisco, CA')", "San Francisco, CA")

if location_input:
    geolocator = Nominatim(user_agent="fire_sim")
    location = geolocator.geocode(location_input)

    if location:
        lat, lon = location.latitude, location.longitude

    else:
        st.error("Location not found")