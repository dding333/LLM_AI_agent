import pymysql
import pandas as pd
import os
mysql_pw = os.getenv("MYSQL_PW")
print(mysql_pw)
connection = pymysql.connect(
    host='localhost',  # 数据库地址
    user='root',  # 数据库用户名
    passwd=mysql_pw,  # 数据库密码
    db='telco_db',  # 数据库名
    charset='utf8'  # 字符集选择utf8
)
print(connection)
cursor = connection.cursor()
sql_query = "SELECT * FROM user_demographics LIMIT 10"
cursor.execute(sql_query)
results = cursor.fetchall()
print(results)
column_names = [desc[0] for desc in cursor.description]

# 使用results和column_names创建DataFrame
df = pd.DataFrame(results, columns=column_names)
print(df)
cursor.close()