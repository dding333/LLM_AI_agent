import os
import json
import pymysql
import pandas as pd
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
import matplotlib
import seaborn as sns
import numpy as np
import inspect
import openai
import time

def sql_inter(sql_query, g='globals()'):
    """
    This function is used to execute a segment of SQL code and ultimately retrieve the result of the SQL code execution. The core functionality is to transmit the input SQL code to a MySQL environment for execution and return the results. Note that this function uses pymysql to connect to the MySQL database.
    sql_query: A string containing the SQL query to be executed. This query will be used to perform operations on tables within the telco_db database in MySQL and retrieve various related information from these tables.
    g: A variable of type string, representing the environment variable. It does not need to be set; the default parameter is sufficient.
    Returns: The result of executing sql_query in MySQL.
    """

    mysql_pw = os.getenv('MYSQL_PW')

    connection = pymysql.connect(
            host='localhost', 
            user='root', 
            passwd=mysql_pw, 
            db='telco_db', 
            charset='utf8'
        )

    try:
        with connection.cursor() as cursor:

            sql = sql_query
            cursor.execute(sql)

            results = cursor.fetchall()

    finally:
        connection.close()


    return json.dumps(results)

def extract_data(sql_query,df_name,g='globals()'):
    """
    This function uses pymysql to read a table from MySQL and save it to the local Python environment.
    sql_query: A string containing the SQL query used to extract a specific table from MySQL.
    df_name: The variable name, in string format, under which the extracted table from the MySQL database will be saved locally.
    g: A variable of type string, representing the environment variable. It does not need to be set; the default parameter is sufficient.
    Returns: The result of reading and saving the table.
    """

    mysql_pw = os.getenv('MYSQL_PW')

    connection = pymysql.connect(
            host='localhost', 
            user='root',
            passwd=mysql_pw, 
            db='telco_db', 
            charset='utf8'
        )


    g[df_name] = pd.read_sql(sql_query, connection)

    return "Successfully completed the creation of the %s variable." % df_name

def python_inter(py_code, g='globals()'):
    """
    Specifically used to execute non-plotting Python code and obtain the final query or processing result. For Python code related to designing plots, you should use the `fig_inter` function.
    :param py_code: A string representing the Python code to be executed for operations on various data tables in the `telco_db` database.
    :param g: `g`, a string variable representing the environment variable, which does not need to be set; keep the default parameter as is.
    :return: The final result of the code execution.
    """

    global_vars_before = set(g.keys())
    try:
        exec(py_code, g)
    except Exception as e:
        return f"An error occurred during code execution: {e}"
    
    global_vars_after = set(g.keys())
    new_vars = global_vars_after - global_vars_before
    
    # If there are new variables
    if new_vars:
        result = {var: g[var] for var in new_vars}
        return str(result)
    
    # If there are no new variables, which could mean the code is an expression or the code reassigns the same variables
    else:
        try:
            # Try returning the result if it is an expression
            return str(eval(py_code, g))
        # If there is an error, test if it is due to reassigning the same variables
        except Exception as e:
            try:
                exec(py_code, g)
                return "Code executed successfully"
            except Exception as e:
                pass
            # If it is not due to reassigning variables, return the error
            return f"An error occurred during code execution: {e}"



def upload_image_to_drive(figure, folder_id = '1YstWRU-78JwTEQQA3vJokK3OF_F0djRH'):
    """
    upload the fig to google drive
    """
    folder_id = folder_id       
    creds = Credentials.from_authorized_user_file('token.json')
    drive_service = build('drive', 'v3', credentials=creds)

    # 1. Save image to Google Drive
    buf = BytesIO()
    figure.savefig(buf, format='png')
    buf.seek(0)
    media = MediaIoBaseUpload(buf, mimetype='image/png', resumable=True)
    file_metadata = {
        'name': 'YourImageName.png',
        'parents': [folder_id],
        'mimeType': 'image/png'
    }
    image_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id,webContentLink'  # Specify the fields to be returned
    ).execute()

    return image_file["webContentLink"]


def fig_inter(py_code, fname, g='globals()'):
    """
    Used to execute a segment of Python code that includes visualization and plotting, and ultimately obtain an image-type object.
    :param py_code: A string containing Python code for creating plots as needed. The code must include the process of creating a Figure object.
    :param fname: The variable name of the Figure created in the py_code, represented as a string.
    :param g: g, a string variable representing the environment, which does not need to be set and can remain as the default parameter.
    :return: The final result of executing the code.

    """

    current_backend = matplotlib.get_backend()

    # set agg backend 
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    # create a python dict 
    local_vars = {"plt": plt, "pd": pd, "sns": sns}

    try:
        exec(py_code, g, local_vars)
    except Exception as e:
        return f"code excution with error{e}"

    # reply to backend
    matplotlib.use(current_backend)

    # get the fig object
    fig = local_vars[fname]

    # upload fig 
    try:
        fig_url = upload_image_to_drive(fig)
        res = f"The code has been successfully executed, and the image created by the code has been stored at: {fig_url}"
    
    except Exception as e:
        res = "Unable to upload the image to Google Drive. Please check the Google Drive folder ID and the current network conditions."


    print(res)
    return res
def auto_functions(functions_list):
    """
    Function to create the functions parameter for the Chat model
    :param functions_list: A list containing one or more function objects;
    :return: A functions object that meets the requirements for the Chat model's functions parameter
    """
    def functions_generate(functions_list):
        # Create an empty list to store the description dictionaries for each function
        functions = []

        def chen_ming_algorithm(data):
            """
            Chen Ming algorithm function, which defines a special dataset calculation process
            :param data: Required parameter, represents the data table used for calculations, represented as a string
            :return: The result of the Chen Ming function calculation, returned as a DataFrame object in JSON format
            """
            df_new = pd.read_json(data)
            res = np.sum(df_new, axis=1) - 1
            return res.to_json(orient='records')

        chen_ming_function_description = inspect.getdoc(chen_ming_algorithm)

        chen_ming_function_name = chen_ming_algorithm.__name__

        chen_ming_function = {
            "name": "chen_ming_algorithm",
            "description": "Function for executing the Chen Ming algorithm, which defines a special dataset calculation process",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "string",
                        "description": "Dataset for executing the Chen Ming algorithm"
                    },
                },
                "required": ["data"],
            },
        }




        for function in functions_list:
            # read the documents of a function 
            function_description = inspect.getdoc(function)
            function_name = function.__name__
            
            # comment out the user_message before using
            # user_message1 = 'Here is the description of a function: %s.' % chen_ming_function_description
            #                 "Based on this function description, please help me create a function object to describe the basic details of this function. This function object should be a JSON-formatted dictionary with the following 5 requirements:\
            #                 1. The dictionary should contain three key-value pairs;\
            #                 2. The first key-value pair should have the key "name" with the value being the function name: %s, which should also be a string;\
            #                 3. The second key-value pair should have the key "description" with the value being the function's functionality description, which should also be a string;\
            #                 4. The third key-value pair should have the key "parameters" with the value being a JSON Schema object that describes the function's parameter input specifications;\
            #                 5. The output must be a JSON-formatted dictionary, and only this dictionary should be output, without any additional statements or explanations." % chen_ming_function_name


            assistant_message1 = json.dumps(chen_ming_function)
            
            user_prompt = 'Now there is another function, with the function name: %s; and the function description: %s;\
                          Please help me create a function object for this current function in a similar format.' % (function_name, function_description)


            response = openai.ChatCompletion.create(
                              model="gpt-4-0613",
                              messages=[
                                {"role": "user", "name":"example_user", "content": user_message1},
                                {"role": "assistant", "name":"example_assistant", "content": assistant_message1},
                                {"role": "user", "name":"example_user", "content": user_prompt}]
                            )
            functions.append(json.loads(response.choices[0].message['content']))
        return functions

    max_attempts = 3
    attempts = 0
    
    while attempts < max_attempts:
        try:
            functions = functions_generate(functions_list)
            break  # Exit the loop if the code executes successfully
        except Exception as e:
            attempts += 1  # Increment the attempt count
            print("An error occurred:", e)
            print("Due to a model limit rate error, pausing for 1 minute. The model will be retried after 1 minute.")
            time.sleep(60)
    
            if attempts == max_attempts:
                print("Maximum number of attempts reached, terminating the program.")
                raise  # Re-raise the last exception
            else:
                print("Retrying...")
    return functions



if __name__ == '__main__':
    print("this file contains functions to connect Mysql")
