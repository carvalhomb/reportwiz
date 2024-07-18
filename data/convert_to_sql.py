from sqlite_utils.utils import rows_from_file
import io
from sqlite_utils import Database
#import sqlite3
import pandas as pd
import json


# Which DB to use

db = Database("database.db")



#########################################################################
# HEP measurements

hep = ('hepdatabase.json', 'hep')

def create_table_from_json(filepath, db, table_name):
    print(f'\nInserting from file {filepath} into table {table_name}')
    with open(filepath, "rb") as f:
        rows, format = rows_from_file(f)
    
    cols = rows[0].keys()
    print(cols)

    # Create table
    new_tbl = db[table_name]

    for idx, row in enumerate(rows):
        if idx % 1000 == 0:
            print(idx)
        new_tbl.insert(row)

    print('Done\n\n')

#create_table_from_json(hep[0], db, hep[1])

######################################################
# NASA temperature databases

temperatures_dubrovnik = ('dubrovniktempdatabase.json', 'temperatures', 'Dubrovnik')
temperatures_osijek = ('osijektempdatabase.json', 'temperatures', 'Osijek')
temperatures_rijeka = ('rijekatempdatabase.json', 'temperatures', 'Rijeka')
temperatures_split = ('splittempdatabase.json', 'temperatures', 'Split')
temperatures_vukovar = ('vukovartempdatabase.json', 'temperatures', 'Vukovar')

temp_dbs = [temperatures_dubrovnik, temperatures_osijek, temperatures_rijeka, temperatures_split, temperatures_vukovar]

def create_temp_table_from_json(filepath, db, table_name, city):
    print(f'\nInserting from file {filepath} into table {table_name}')
    with open(filepath, "rb") as f:
        rows, format_ = rows_from_file(f)
    
    cols = rows[0].keys()
    coordinates = str(rows[0]['geometry']['coordinates'])
    print(coordinates)
    print(rows[0]['type'])

    params = rows[0]['properties']['parameter']
    df = pd.DataFrame.from_dict(params)
    df['coordinates'] = coordinates
    df['city'] = city
    df['country'] = 'Croatia'
    print(df.head())

    # Insert pandas table to SQL
    tbl = db[table_name]

    for index, row in df.iterrows():
        #print(row.to_dict())
        tbl.insert(row.to_dict())

    tbl_metadata = {}
    tbl_metadata['table_info'] = rows[0]['header']
    tbl_metadata['parameters_info'] = rows[0]['parameters']
    print(tbl_metadata)

    with open('tables_metadata.md', 'w') as f:
        f.write(json.dumps(tbl_metadata))

    # Create table
    # new_tbl = db[table_name]

    # for idx, row in enumerate(rows):
    #     if idx % 1000 == 0:
    #         print(idx)
    #     new_tbl.insert(row)

    print('Done\n\n')

# for t in temp_dbs:
#     create_temp_table_from_json(t[0], db, t[1], t[2])

######################################################
# EE database

def create_ee_table_from_json(filepath, db, table_name):

    print(f'\nInserting from file {filepath} into table {table_name}')    
    
    with open(filepath, "rb") as f:
        content = json.load(f)
        #print(content)
    
    # Flatten the JSON data
    rows = []
    for year, months in content.items():
        for month, days in months.items():
            for day, values in days.items():
                #print(year + ' ' + month +' ' + day)
                row = {
                    "year": year,
                    "month": month,
                    "day": day,
                    "SolarPower": values["SolarPower"],
                    "Nocna_Poslano": values["HEP"]["Nocna"].get("Poslano prema HEP-u", pd.NA),
                    "Nocna_Preuzeto": values["HEP"]["Nocna"].get("Preuzeto od HEP-a", pd.NA),
                    "Dnevna_Preuzeto": values["HEP"]["Dnevna"].get("Preuzeto od HEP-a", pd.NA),
                    "Dnevna_Poslano": values["HEP"]["Dnevna"].get("Poslano prema HEP-u", pd.NA),
                    "Preuzeto_total": values["Preuzeto od HEP-a (total)"],
                    "Poslano_total": values["Poslano prema HEP-u (total)"],
                    "UkupnaPotrosnja": values["UkupnaPotrosnja"],
                    "Predano/Utroseno": values["Predano/Utroseno"]
                }
                rows.append(row)
    df = pd.DataFrame(rows)
    print(df.head())

    # Insert pandas table to SQL
    tbl = db[table_name]

    for index, row in df.iterrows():
        #print(row.to_dict())
        tbl.insert(row.to_dict())


ee = ('EEFinal.json', 'ee', 'energy')
#create_ee_table_from_json(ee[0], db, ee[1])


######################################################
# HEP final database


def create_hepfinal_table_from_json(filepath, db, table_name):

    print(f'\nInserting from file {filepath} into table {table_name}')    
    
    with open(filepath, "rb") as f:
        content = json.load(f)
        #print(content)
    
    # Flatten the JSON data
    rows = []
    for year, months in content.items():
        for month, days in months.items():
            for day, values in days.items():
                print(year + ' ' + month +' ' + day)
                row = {
                    "year": year,
                    "month": month,
                    "day": day,
                    "Nocna_Poslano": values.get("Nocna", {}).get("Poslano prema HEP-u", pd.NA),
                    "Nocna_Preuzeto": values.get("Nocna", {}).get("Preuzeto od HEP-a", pd.NA),
                    "Dnevna_Preuzeto": values.get("Dnevna", {}).get("Preuzeto od HEP-a", pd.NA),
                    "Dnevna_Poslano": values.get("Dnevna", {}).get("Poslano prema HEP-u", pd.NA),
                }
                rows.append(row)
    df = pd.DataFrame(rows)
    print(df.head())

    # Insert pandas table to SQL
    tbl = db[table_name]

    for index, row in df.iterrows():
        #print(row.to_dict())
        tbl.insert(row.to_dict())

hep_final = ('HEPfinal.json', 'hep_final')
#create_hepfinal_table_from_json(hep_final[0], db, hep_final[1])



#################################

print(db.table_names())


