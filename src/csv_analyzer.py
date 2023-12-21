import constants as c
import csv
from datetime import datetime

def is_valid_timestamp(date_to_check : str) -> bool:
    '''Function used to check if the given string is compliant to the correct time format'''
    expected_format = "%d/%m/%Y %H:%M:%S"
    try:
        datetime_check = datetime.strptime(date_to_check, expected_format)
        return True
    except ValueError:
        return False 

# TODO fix function
def count_types_of_mobile(types : dict, current : str):
    '''Function that counts how many types of mobile are in the dataset. Automatically updates the dictionary if new types are found'''
    if current not in types.values():
        types[current] = 1
    else:
         types[current] += 1


FILE_NAME = "aisdk_20060401.csv"
typesDict = {}

# Quicky extract the number of attributes of the csv
with open(c.ROOT_FOLDER_PATH + FILE_NAME) as cf:
     myReader = csv.reader(cf)
     row1 = next(myReader)
     attributesNames = [str(x) for x in row1]
     results = [0 for x in attributesNames]
print(attributesNames)

with open(c.ROOT_FOLDER_PATH + FILE_NAME) as cf:
        myReader = csv.reader(cf)
        next(myReader) # skip the first row (with the names of the attributes)

        for row in myReader:
            for index, col in enumerate(row):
                match index:
                    case c.CsvColumns.Timestamp.value:
                        if not(is_valid_timestamp(col)):
                            results[index] += 1
                    case c.CsvColumns.Type_of_mobile.value:
                          typesDict.count_types_of_mobile(col)

print(typesDict)



