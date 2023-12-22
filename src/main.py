import constants as c
import csv_analyzer as csva
import os

def main():
    for file in os.listdir(c.ROOT_FOLDER_PATH + "csv/test/"):
        if file.endswith(".csv"):
            print("Creating output file " + str(file.split('.')[0]) + ".txt")
            tempResults = csva.analyze(c.ROOT_FOLDER_PATH + "/csv/test/" +str(file))
            with open(c.ROOT_FOLDER_PATH + "output/test/" + str(file.split(".")[0]) + ".txt", 'w') as f:
                for index, item in enumerate(tempResults):
                    f.write(str(c.CsvColumns(index).name) + " -> " + str(item) + "\n")
                print("File " + str(file.split('.')[0]) + ".txt" + " completed!" )

    

if __name__ == "__main__":
    main()