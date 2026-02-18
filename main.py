from Classes.WeatherDataSetup import WeatherDataSetup

if __name__ == '__main__':
    weatherSetup = WeatherDataSetup(42.817816, -80.633052, 100, 2, 10, True)
    grid = weatherSetup.CreateGrid()
    print("done")

