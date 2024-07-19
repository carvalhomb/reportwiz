from sqlite_utils.utils import rows_from_file
import io
from sqlite_utils import Database
#import sqlite3
import pandas as pd
import json


# Which DB to use

db_path = "database.db"
#db_path = "../app/data/databases/database.db"
db = Database(db_path)



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

temperatures_dubrovnik = ('dubrovniktempdatabase.json', 'nasa_meteo_data', 'Dubrovnik')
temperatures_osijek = ('osijektempdatabase.json', 'nasa_meteo_data', 'Osijek')
temperatures_rijeka = ('rijekatempdatabase.json', 'nasa_meteo_data', 'Rijeka')
temperatures_split = ('splittempdatabase.json', 'nasa_meteo_data', 'Split')
temperatures_vukovar = ('vukovartempdatabase.json', 'nasa_meteo_data', 'Vukovar')
temperatures_hvar = ('hvartempdatabase.json', 'nasa_meteo_data', 'Hvar')
temperatures_zagreb = ('zagrebtempdatabase.json', 'nasa_meteo_data', 'Zagreb')

temp_dbs = [
    temperatures_dubrovnik, 
    temperatures_osijek, 
    temperatures_rijeka, 
    temperatures_split, 
    temperatures_vukovar,
    temperatures_hvar,
    temperatures_zagreb,
]

def create_temp_table_from_json(filepath, db, table_name, city):
    print(f'\nInserting from file {filepath} into table {table_name}')
    with open(filepath, "rb") as f:
        rows, format_ = rows_from_file(f)
    
    cols = rows[0].keys()
    coordinates = str(rows[0]['geometry']['coordinates'])
    print(coordinates)
    print(rows[0]['type'])

    params = rows[0]['properties']['parameter']
    print(params)
    df = pd.DataFrame.from_dict(params)
    # Get the col names before adding extra stuff
    cols = list(df.columns)
    df['coordinates'] = coordinates
    df['city'] = city
    df['country'] = 'Croatia'
    df = df.reset_index(drop=False, names=['date'])
    cols_new_order = ['date', 'country', 'city', 'coordinates'] + cols
    df = df.loc[:, cols_new_order]
    print(df.head())

    # Insert pandas table to SQL
    tbl = db[table_name]

    for index, row in df.iterrows():
        #print(row.to_dict())
        tbl.insert(row.to_dict())

    # tbl_metadata = {}
    # tbl_metadata['table_info'] = rows[0]['header']
    # tbl_metadata['parameters_info'] = rows[0]['parameters']
    # print(tbl_metadata)

    # with open('tables_metadata.md', 'w') as f:
    #     f.write(json.dumps(tbl_metadata))


    print('Done\n\n')

#for t in temp_dbs:
#    create_temp_table_from_json(t[0], db, t[1], t[2])

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
                    "Predano_vs_Utroseno": values["Predano/Utroseno"]
                }
                rows.append(row)
    df = pd.DataFrame(rows)
    print(df.head())

    # Insert pandas table to SQL
    tbl = db[table_name]

    for index, row in df.iterrows():
        #print(row.to_dict())
        tbl.insert(row.to_dict())


ee = ('EEFinal.json', 'electricity_input_output_aggregated')
#create_ee_table_from_json(ee[0], db, ee[1])


######################################################
# HEP final database


# def create_hepfinal_table_from_json(filepath, db, table_name):

#     print(f'\nInserting from file {filepath} into table {table_name}')    
    
#     with open(filepath, "rb") as f:
#         content = json.load(f)
#         #print(content)
    
#     # Flatten the JSON data
#     rows = []
#     for year, months in content.items():
#         for month, days in months.items():
#             for day, values in days.items():
#                 print(year + ' ' + month +' ' + day)
#                 row = {
#                     "year": year,
#                     "month": month,
#                     "day": day,
#                     "Nocna_Poslano": values.get("Nocna", {}).get("Poslano prema HEP-u", pd.NA),
#                     "Nocna_Preuzeto": values.get("Nocna", {}).get("Preuzeto od HEP-a", pd.NA),
#                     "Dnevna_Preuzeto": values.get("Dnevna", {}).get("Preuzeto od HEP-a", pd.NA),
#                     "Dnevna_Poslano": values.get("Dnevna", {}).get("Poslano prema HEP-u", pd.NA),
#                 }
#                 rows.append(row)
#     df = pd.DataFrame(rows)
#     print(df.head())

#     # Insert pandas table to SQL
#     tbl = db[table_name]

#     for index, row in df.iterrows():
#         #print(row.to_dict())
#         tbl.insert(row.to_dict())

# hep_final = ('HEPfinal.json', 'hep_final')
# #create_hepfinal_table_from_json(hep_final[0], db, hep_final[1])



#################################

print(db.table_names())


