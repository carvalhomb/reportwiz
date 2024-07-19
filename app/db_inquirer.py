import os
import dotenv

from langchain.agents import tool
from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_community.agent_toolkits import SQLDatabaseToolkit




dotenv.load_dotenv()



@tool
def db_inquirer():
    """
    Tool to query the database about the weather in the following cities in Croatia: 
    Zagreb, Split, Rijeka, Dubrovnik, Vukovar, Osijek
    """
    return 'I don\'t know'