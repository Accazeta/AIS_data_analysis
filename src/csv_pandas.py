import pandas as pd
import constants as c



df1 = pd.read_csv(c.ROOT_FOLDER_PATH + c.FILENAME1)

ships = {}


for MMSI in df1['MMSI'].unique():
    # each key-value pair of the "ships" dictionary represents the data produced by a given ship inside the csv
    ships[MMSI] = df1[df1['MMSI'] == MMSI]
    #
    ships[MMSI].to_csv(c.ROOT_FOLDER_PATH + "output/pandas/" + c.FILENAME1.split('/')[2] + "_" + str(MMSI))

#print(ships)