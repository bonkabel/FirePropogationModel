from Classes.WeatherDataSetup import WeatherDataSetup

# Just for testing purposes

if __name__ == '__main__':
    weatherSetup = WeatherDataSetup(42.817816, -80.633052, 100, 2, 10, True)
    grid = weatherSetup.CreateWeatherLayers()
    temp = grid['temperature'][0][1][1]
    print(f"{temp}")

