import pymysql
import pandas as pd
import os
mysql_pw = os.getenv("MYSQL_PW")
print(mysql_pw)
connection = pymysql.connect(
    host='localhost',  
    user='root',  
    passwd=mysql_pw,  
    db='telco_db',  
    charset='utf8' 
)
print(connection)
cursor = connection.cursor()
sql_query = "SELECT * FROM user_demographics LIMIT 10"
cursor.execute(sql_query)
results = cursor.fetchall()
print(results)
column_names = [desc[0] for desc in cursor.description]


df = pd.DataFrame(results, columns=column_names)
print(df)
cursor.close()
