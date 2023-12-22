import constants as c
import csv                      # for reading csv file
from datetime import datetime   # for checking time format
import re                       # for regex

def is_valid_timestamp(date_to_check : str) -> bool:
    '''Function used to check if the given string is compliant to the correct time format'''
    expected_format = "%d/%m/%Y %H:%M:%S"
    try:
        datetime_check = datetime.strptime(date_to_check, expected_format)
        return True
    except ValueError:
        return False 

def count_types_of_mobile(types : dict, current : str):
    '''Function that counts how many types of mobile are in the dataset. Automatically updates the dictionary if new types are found'''
    if current in types.keys():
        types[current] += 1
    else:
         types[current] = 1

def is_float_in_interval(min : float, max : float, to_check : str) -> bool:
    '''Function used to check if a given string represents a float value greater than min and less than max'''
    # checks if the given string is represents a float
    regex = r'^[-+]?(\d+\.\d*|\.\d+)?$'
    testResult = re.search(regex, to_check)
    if testResult is None:
        return False
    else:
        value = float(testResult.group(0))
        return min <= value <= max

def check_value_formality(valuesDict : dict, value : str, max : float) -> bool:
    '''Function used for the ROT, SOG, COG, Heading attributes in order to check if a value from the csv is null, valid or an error'''
    if value == "":
        valuesDict['nulls'] += 1
        return True
    else:
        floatValue = float(value)
        if 0 <= abs(floatValue) <= max:
            valuesDict['stdvalues'] += 1
            return True
        else:
            valuesDict['errors'] += 1
            return False


typesDict = {}
ROTdict =       {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
SOGdict =       {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
COGdict =       {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
HeadingDict =   {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
results = []

# Quicky extract the number of attributes of the csv
with open(c.ROOT_FOLDER_PATH + c.FILENAME1) as cf:
     myReader = csv.reader(cf)
     row1 = next(myReader)
     attributesNames = [str(x) for x in row1]
     results = [0 for x in attributesNames]
print(attributesNames)

with open(c.OUTPUTFILE, 'w') as f:
    None 
    # This is used to delete the output file in case it already exists
    # If it doesn't exists, creates a new one
    

with open(c.ROOT_FOLDER_PATH + c.FILENAME1) as cf:
        myReader = csv.reader(cf)
        next(myReader) # skip the first row (with the names of the attributes)

        for row in myReader:
            for index, col in enumerate(row):
                match index:
                    case c.CsvColumns.Timestamp.value:
                        if not(is_valid_timestamp(col)):
                            results[index] += 1
                    case c.CsvColumns.Type_of_mobile.value:
                        count_types_of_mobile(typesDict, col)
                    case c.CsvColumns.MMSI.value:
                        # Checks if the MMSI is a [1-9] digit number
                        if re.match(r'^\d{1,9}$', col) is None: # ^ -> starts with, $ -> ends with, \d -> digit, {1,9} -> min-max
                            results[index] += 1
                    case c.CsvColumns.Latitude.value:
                        if is_float_in_interval(-90, 90, col) is False or float(col) == 0:
                            results[index] += 1
                    case c.CsvColumns.Longitude.value:
                        if is_float_in_interval(-180, 180, col) is False or float(col) == 0:
                            results[index] += 1
                    case c.CsvColumns.NavStatus.value:
                       if re.match('Unknown value', col):
                           results[index] += 1
                    case c.CsvColumns.ROT.value:
                        if not(check_value_formality(ROTdict, col, 720)):
                            with open(OUTPUTFILE, 'a') as file:
                                file.write("ROT -> " + str(row[0:3]) + " "  + row[index] + "\n")
                    case c.CsvColumns.SOG.value:
                        if not(check_value_formality(SOGdict, col, 102)):
                            with open(OUTPUTFILE, 'a') as file:
                                file.write("SOG -> " + str(row[0:3]) + " "  + row[index]+ "\n")
                    case c.CsvColumns.COG.value:
                        if not(check_value_formality(COGdict, col, 360)):
                            with open(OUTPUTFILE, 'a') as file:
                                file.write("COG -> " + str(row[0:3]) + " "  + row[index] + "\n")
                    case c.CsvColumns.Heading.value:
                        if not(check_value_formality(HeadingDict, col, 360)):
                            with open(OUTPUTFILE, 'a') as file:
                                file.write("Heading -> "+ str(row[0:3]) + " " + row[index] + "\n")
                        

        
        results[c.CsvColumns.Type_of_mobile.value] = typesDict
        results[c.CsvColumns.ROT.value] = ROTdict
        results[c.CsvColumns.SOG.value] = SOGdict
        results[c.CsvColumns.COG.value] = COGdict
        results[c.CsvColumns.Heading.value] = HeadingDict

print(typesDict)
print(results)



