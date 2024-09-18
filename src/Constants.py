import datetime as dt                           # datetime module for time intervals

# constants
FOLDER_PATH = "../dataset/2019/"
FILE_NAME = 'cleaned_2019_01-03.csv'
SPEED_THRESHOLD = 0.5 # nautical knots
ABSURD_SPEED_THRESHOLD = 102 # nautical knots
POINTS_THRESHOLD = 50
KNOTS_CONST = 1.943845249221964 # constant used to convert from m/s to nautical knots
EARTH_RADIUS_KM = 6378.137 # average value, taken from WGS-84 standard and used by geopy https://github.com/geopy/geopy/blob/master/geopy/distance.py
EARTH_RADIUS_M = 6378137
LAT_MIN = 18.76651
LAT_MAX = 22.63089
LON_MIN = -160.11085
LON_MAX = -154.38957
LOST_TIME_THRESHOLD_SECONDS = dt.timedelta(seconds=620) # 10 * (62s)
EXIT_TIME_THRESHOLD_HOURS = dt.timedelta(hours=12) # half day