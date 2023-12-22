from enum import Enum

ROOT_FOLDER_PATH = "/home/accazeta/Scrivania/Unibg/ZTesi Magistrale/"

# https://en.wikipedia.org/wiki/Automatic_identification_system
class CsvColumns(Enum):
    '''Enum per gestire le colonne dei file csv'''

    Timestamp = 0 
    """Timestamp from the AIS basestation. Format: dd/mm/yyyy hh:mm:ss"""

    Type_of_mobile = 1
    '''Describes what type of target this message is received from (class A AIS Vessel, Class B AIS vessel, etc)
        Class A are the most common (AIS is mandatory on them), while class B are less common because it's optional on them
        There might be other classes, such as "base station" or "Buoy"
        Further explanation: https://www.svb-marine.it/it/guida/tutto-cio-che-devi-sapere-sugli-ais.html
        Note: class B units, as per wikipedia (https://en.wikipedia.org/wiki/Automatic_identification_system) transmit less info
        with different transmission intervals'''

    MMSI = 2
    '''MMSI number of vessel. 9 digits. Unique value for each vessel. No alphabetical or special characters allowed'''
    
    Latitude = 3
    '''Latitude of message report (e.g. 57,8794)
        Accepted values from -90 to +90, with some exceptions (ex: sometimes 91 is used as a placeholder when there is no data)
        Resolution: 0.0001 arcminutes'''
    
    Longitude = 4
    '''Longitude of message report (e.g. 17,9125)
        Accepted values from -180 to +180, with some exceptions (ex: sometimes 181 is used as a placeholder when there is no data)
        Resolution: 0.0001 arcminutes'''
    
    NavStatus = 5
    '''Navigational status from AIS message if available, e.g.: 'Engaged in fishing', 'Under way using engine', mv.
        More detailed description can be found at: https://api.vtexplorer.com/docs/ref-navstat.html'''
    
    ROT = 6
    '''Rate of turn from AIS message if available. (=Tasso di variazione rotta)
        Can be right or left, with accepted values (float) ranging from 0 to +/-720 (deg/min)'''
    
    SOG = 7
    '''Speed over ground from AIS message if available
        Represents the instant speed of the vessel
        Accepted values (float) from 0 to 102 with a resolution of 0.1 (knots)'''
    
    COG = 8
    '''Course over ground from AIS message if available.
        Relative to true north with a 0.1 deg precions
        Accepted values 0 to 360 -> [0,360)'''
    
    Heading = 9
    '''Heading from AIS message if available
        In navigation is called "true heading"
        Accepted values: 0 to 359 (degrees)'''
    
    IMO = 10
    '''IMO number of the vessel.
        seven  digit number that remains unchanged upon transfer of the ship's registration to another country'''
    
    Callsign = 11
    '''International radio callsign, up to 7 characters, assigned to the vessel by its country of registry
        Used by other ship to address the vessel via radio'''
    
    Name = 12
    '''Name of the vessel
        20 alphanumerical characters used to represent the name of the vessel'''
    
    ShipType = 13
    '''Describes the AIS ship type of this vessel
    More details: https://unstats.un.org/wiki/display/AIS/Overview+of+AIS+dataset?preview=/57999709/72777792/VesselTypeCodes2018.pdf''' 
    
    CargoType = 14
    '''Type of cargo from the AIS message''' 
    
    Width = 15
    '''Width of the vessel, to the nearest meter (positive integer value)'''
    
    Length = 16
    '''Lenght of the vessel, to the nearest meter (positive integer value)''' 
    
    AISPosition = 17
    '''Type of positional fixing device from the AIS message.
    Position of the AIS antenna with respect to the ship (in metri a poppa della prua e metri a babordo o a tribordo)''' 
    
    Draught = 18
    '''Draugth field from AIS message. Float value between 0.1 and 25.5 included'''
    
    Destination = 19
    '''Destination from AIS message. Max 20 alphanumerical characters'''
    
    ETA = 20
    '''Estimated Time of Arrival, if available. Format: dd/mm/yyyy hh:mm:ss'''  
    
    DataSourceType = 21
    '''Data source type, e.g. AIS'''
    
    SizeA = 22
    '''Length from GPS to the bow. Often missing'''
    
    SizeB = 23
    '''ength from GPS to the stern. Often missing'''
    
    SizeC = 24
    '''Length from GPS to starboard side. Often missing'''
    
    SizeD = 25
    '''Length from GPS to port side. Often missing'''
    