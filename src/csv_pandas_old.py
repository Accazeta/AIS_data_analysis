import pandas as pd
import constants_old as c
from shapely.geometry import Point
import geopandas as gpd
import matplotlib.pyplot as plt




df1 = pd.read_csv(c.ROOT_FOLDER_PATH + c.FILENAME1)

ships = {}
base_stations = {}

all_MMSIs = pd.Series(df1['MMSI'].unique())
#print(all_MMSIs.values[0:10])
ships_MMSIs = pd.Series(df1[(df1['Type of mobile'] != "Base Station")].get("MMSI").unique())
#print(ships_MMSIs.values[0:10])
base_stations_MMSIs = pd.Series(df1[(df1['Type of mobile'] == "Base Station")].get("MMSI").unique())
#print(base_stations_MMSIs.values[0:69])


lengths = {}

for mmsi in list(base_stations_MMSIs):
    if len(str(mmsi)) in lengths.keys():
        lengths[len(str(mmsi))] += 1
    else:
        lengths[len(str(mmsi))] = 1

print(lengths)


for MMSI in ships_MMSIs:
    # each key-value pair of the "ships" dictionary represents the data produced by a given ship inside the csv
    ships[MMSI] = df1[(df1['MMSI'] == MMSI)]
    # saves the track of each ship on a separate file
    ships[MMSI].to_csv(c.ROOT_FOLDER_PATH + "output/pandas/ships/" + c.FILENAME1.split('/')[1] + "_" + str(MMSI) + ".csv")

for MMSI in base_stations_MMSIs:
    # each key-value pair of the "base_stations" dictionary represents the data produced by a given base_station inside the csv
    base_stations[MMSI] = df1[(df1['MMSI'] == MMSI)]
    # saves the record of each base station on a separate file
    base_stations[MMSI].to_csv(c.ROOT_FOLDER_PATH + "output/pandas/base_stations/" + c.FILENAME1.split('/')[1] + "_" + str(MMSI) + ".csv")


# A quanto pare l'ordine con cui vengono passate Longitudine e Latitudine è importante!
# La Danimarca si trova più o meno all'interno di questo range di coordinate:
filtered_df1 = df1[53.5<=df1["Longitude"]<=59]
points = [Point(x,y) for x,y in zip(53.5<=df1["Longitude"]<=59, 5.75<=df1["Latitude"]<=17)]

geodf = gpd.GeoDataFrame(df1,geometry=points, crs="WGS84")

world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
ax = world.plot(figsize=(10,6), color='lightgray')

geodf.plot(ax=ax, color='blue', marker='o', markersize=1)

plt.show()
#print(ships)