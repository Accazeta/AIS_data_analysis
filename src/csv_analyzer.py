import constants as c
import csv                      # for reading csv files
from datetime import datetime   # for checking time format
import re                       # for regex

def analyze(csvFilePath) -> list:

    def count_types(types : dict, current : str):
        '''Function that counts how many types of mobile are in the dataset. Automatically updates the dictionary if new types are found'''
        if current in types.keys():
            types[current] += 1
        else:
             types[current] = 1

    def check_value_formality(valuesDict : dict, value : str, type : str, min : float = 0, 
                              max : float = 0, regex : str = "") -> bool:
        if value == "":
            valuesDict['nulls'] += 1
            return False
        else:
            match type:
                case "Timestamp":
                    expected_format = "%d/%m/%Y %H:%M:%S"
                    try:
                        datetime_check = datetime.strptime(value, expected_format)
                        valuesDict['stdvalues'] += 1
                        return True
                    except ValueError:
                        valuesDict['errors'] += 1
                        return False
                case "Interval":
                    floatValue = float(value)
                    if min <= floatValue <= max:
                        valuesDict['stdvalues'] += 1
                        return True
                    else:
                        valuesDict['errors'] += 1
                        return False
                case "Regex":
                    if re.match(regex, value):
                        valuesDict['stdvalues'] += 1
                    else:
                        valuesDict['errors'] += 1
                    None
                case _:
                    try:
                        raise ValueError("Wrong type of check")
                    except:
                        return False

    TimestampDict =     {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    AIStypes =          {}
    MMSIDict =          {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    LatDict =           {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    LongDict =          {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    NavStatusDict =     {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    ROTdict =           {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    SOGdict =           {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    COGdict =           {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    HeadingDict =       {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    IMODict =           {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    CallSignDict =      {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    NamesDict =         {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    ShipTypes =         {}
    CargoTypes =        {}
    WidthDict =         {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    LengthDict =        {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    AISpositionTypes =  {}
    DraughtDict =       {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    DestinationsDict =  {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    EtaDict =           {"stdvalues" : 0, "nulls" : 0, "errors" : 0}
    DataSourceTypes =   {}
    results = []

    # Quicky extract the number of attributes of the csv
    with open(csvFilePath) as cf:
         myReader = csv.reader(cf)
         row1 = next(myReader)
         attributesNames = [str(x) for x in row1]
         results = [0 for x in attributesNames]

    try:
        with open(csvFilePath) as cf:
            myReader = csv.reader(cf)
            next(myReader) # skip the first row (with the names of the attributes)

            for row in myReader:
                for index, col in enumerate(row):
                    match index:
                        case c.CsvColumns.Timestamp.value:
                            check_value_formality(TimestampDict, col, "Timestamp")
                        case c.CsvColumns.Type_of_mobile.value:
                            count_types(AIStypes, col)
                        case c.CsvColumns.MMSI.value:
                            # Checks if the MMSI is a [1-9] digit number
                            check_value_formality(MMSIDict, col, "Regex", regex="^\d{1,9}$")
                        case c.CsvColumns.Latitude.value:
                            check_value_formality(LatDict, col, "Interval", 0.1, 90)
                        case c.CsvColumns.Longitude.value:
                            check_value_formality(LongDict, col, "Interval", 0.1, 180)
                        case c.CsvColumns.NavStatus.value:
                            if col == "":
                                NavStatusDict['nulls'] += 1
                            elif col == "Unknown value":
                                NavStatusDict['errors'] += 1
                            else:
                                NavStatusDict['stdvalues'] += 1
                        case c.CsvColumns.ROT.value:
                            check_value_formality(ROTdict, col, "Interval", -720, 720)
                        case c.CsvColumns.SOG.value:
                            check_value_formality(SOGdict, col, "Interval", 0, 102)
                        case c.CsvColumns.COG.value:
                            check_value_formality(COGdict, col, "Interval", 0, 359.9)
                        case c.CsvColumns.Heading.value:
                            check_value_formality(HeadingDict, col, "Interval", 0, 359)
                        case c.CsvColumns.IMO.value:
                            if col == "Unknown":
                                IMODict['nulls'] += 1
                            else:
                                check_value_formality(IMODict, col, "Regex", regex="^\d{1,7}$")
                        case c.CsvColumns.Callsign.value:
                            check_value_formality(CallSignDict, col, "Regex", regex="^[a-zA-Z0-9]{1,7}$")
                        case c.CsvColumns.Name.value:
                            check_value_formality(NamesDict, col, "Regex", regex="^[a-zA-Z0-9]{1,20}$")
                        case c.CsvColumns.ShipType.value:
                            count_types(ShipTypes, col)
                        case c.CsvColumns.CargoType.value:
                            count_types(CargoTypes, col)
                        case c.CsvColumns.Width.value:
                            check_value_formality(WidthDict, col, "Interval", 1, 500)
                        case c.CsvColumns.Length.value:
                            check_value_formality(LengthDict, col,"Interval", 1, 5000)
                        case c.CsvColumns.AISPosition.value:
                            count_types(AISpositionTypes, col)
                        case c.CsvColumns.Draught.value:
                            check_value_formality(DraughtDict, col, "Interval", 0.1, 25.5)
                        case c.CsvColumns.Destination.value:
                            check_value_formality(DestinationsDict, col, "Regex", regex="^[a-zA-Z0-9]{1,20}$")
                        case c.CsvColumns.ETA.value:
                            check_value_formality(EtaDict, col, "Timestamp")
                        case c.CsvColumns.DataSourceType.value:
                            count_types(DataSourceTypes, col)
                        case c.CsvColumns.SizeA.value:
                            None
                        case c.CsvColumns.SizeB.value:
                            None
                        case c.CsvColumns.SizeC.value:
                            None
                        case c.CsvColumns.SizeD.value:
                            None
                        case _:
                            raise ValueError("Unexpected Error")
        
            results[c.CsvColumns.Timestamp.value] = TimestampDict
            results[c.CsvColumns.Type_of_mobile.value] = AIStypes
            results[c.CsvColumns.MMSI.value] = MMSIDict
            results[c.CsvColumns.Latitude.value] = LatDict
            results[c.CsvColumns.Longitude.value] = LongDict
            results[c.CsvColumns.NavStatus.value] = NavStatusDict
            results[c.CsvColumns.ROT.value] = ROTdict
            results[c.CsvColumns.SOG.value] = SOGdict
            results[c.CsvColumns.COG.value] = COGdict
            results[c.CsvColumns.Heading.value] = HeadingDict
            results[c.CsvColumns.IMO.value] = IMODict
            results[c.CsvColumns.Callsign.value] = CallSignDict
            results[c.CsvColumns.Name.value] = NamesDict
            results[c.CsvColumns.ShipType.value] = ShipTypes
            results[c.CsvColumns.CargoType.value] = CargoTypes
            results[c.CsvColumns.Width.value] = WidthDict
            results[c.CsvColumns.Length.value] = LengthDict
            results[c.CsvColumns.AISPosition.value] = AISpositionTypes
            results[c.CsvColumns.Draught.value] = DraughtDict
            results[c.CsvColumns.Destination.value] = DestinationsDict
            results[c.CsvColumns.ETA.value] = EtaDict
            results[c.CsvColumns.DataSourceType.value] = DataSourceTypes
    except Exception:
        None
    return results

   



