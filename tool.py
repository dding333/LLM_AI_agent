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
    用于执行一段SQL代码，并最终获取SQL代码执行结果，\
    核心功能是将输入的SQL代码传输至MySQL环境中进行运行，\
    并最终返回SQL代码运行结果。需要注意的是，本函数是借助pymysql来连接MySQL数据库。
    :param sql_query: 字符串形式的SQL查询语句，用于执行对MySQL中telco_db数据库中各张表进行查询，并获得各表中的各类相关信息
    :param g: g，字符串形式变量，表示环境变量，无需设置，保持默认参数即可
    :return：sql_query在MySQL中的运行结果。
    """

    mysql_pw = os.getenv('MYSQL_PW')

    connection = pymysql.connect(
            host='localhost',  # 数据库地址
            user='root',  # 数据库用户名
            passwd=mysql_pw,  # 数据库密码
            db='telco_db',  # 数据库名
            charset='utf8'  # 字符集选择utf8
        )

    try:
        with connection.cursor() as cursor:
            # SQL查询语句
            sql = sql_query
            cursor.execute(sql)

            # 获取查询结果
            results = cursor.fetchall()

    finally:
        connection.close()


    return json.dumps(results)

def extract_data(sql_query,df_name,g='globals()'):
    """
    借助pymysql将MySQL中的某张表读取并保存到本地Python环境中。
    :param sql_query: 字符串形式的SQL查询语句，用于提取MySQL中的某张表。
    :param df_name: 将MySQL数据库中提取的表格进行本地保存时的变量名，以字符串形式表示。
    :param g: g，字符串形式变量，表示环境变量，无需设置，保持默认参数即可
    :return：表格读取和保存结果
    """

    mysql_pw = os.getenv('MYSQL_PW')

    connection = pymysql.connect(
            host='localhost',  # 数据库地址
            user='root',  # 数据库用户名
            passwd=mysql_pw,  # 数据库密码
            db='telco_db',  # 数据库名
            charset='utf8'  # 字符集选择utf8
        )


    g[df_name] = pd.read_sql(sql_query, connection)

    return "已成功完成%s变量创建" % df_name

def python_inter(py_code, g='globals()'):
    """
    专门用于执行非绘图类python代码，并获取最终查询或处理结果。若是设计绘图操作的Python代码，则需要调用fig_inter函数来执行。
    :param py_code: 字符串形式的Python代码，用于执行对telco_db数据库中各张数据表进行操作
    :param g: g，字符串形式变量，表示环境变量，无需设置，保持默认参数即可
    :return：代码运行的最终结果
    """

    global_vars_before = set(g.keys())
    try:
        exec(py_code, g)
    except Exception as e:
        return f"代码执行时报错{e}"
    global_vars_after = set(g.keys())
    new_vars = global_vars_after - global_vars_before
    # 若存在新变量
    if new_vars:
        result = {var: g[var] for var in new_vars}
        return str(result)
    # 若不存在新变量，即有可能是代码是表达式，也有可能代码对相同变量重复赋值
    else:
        try:
            # 尝试如果是表达式，则返回表达式运行结果
            return str(eval(py_code, g))
        # 若报错，则先测试是否是对相同变量重复赋值
        except Exception as e:
            try:
                exec(py_code, g)
                return "已经顺利执行代码"
            except Exception as e:
                pass
            # 若不是重复赋值，则报错
            return f"代码执行时报错{e}"


def upload_image_to_drive(figure, folder_id = '1YstWRU-78JwTEQQA3vJokK3OF_F0djRH'):
    """
    将指定的fig对象上传至谷歌云盘
    """
    folder_id = folder_id        # 此处需要改为自己的谷歌云盘文件夹ID
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
    用于执行一段包含可视化绘图的Python代码，并最终获取一个图片类型对象
    :param py_code: 字符串形式的Python代码，用于根据需求进行绘图，代码中必须包含Figure对象创建过程
    :param fname: py_code代码中创建的Figure变量名，以字符串形式表示。
    :param g: g，字符串形式变量，表示环境变量，无需设置，保持默认参数即可
    :return：代码运行的最终结果
    """
    # 保存当前的后端
    current_backend = matplotlib.get_backend()

    # 设置为Agg后端
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    # 创建一个字典，用于存储本地变量
    local_vars = {"plt": plt, "pd": pd, "sns": sns}

    try:
        exec(py_code, g, local_vars)
    except Exception as e:
        return f"代码执行时报错{e}"

    # 回复默认后端
    matplotlib.use(current_backend)

    # 根据图片名称，获取图片对象
    fig = local_vars[fname]

    # 上传图片
    try:
        fig_url = upload_image_to_drive(fig)
        res = f"已经成功运行代码，并已将代码创建的图片存储至：{fig_url}"

    except Exception as e:
        res = "无法上传图片至谷歌云盘，请检查谷歌云盘文件夹ID，并检查当前网络情况"

    print(res)
    return res
def auto_functions(functions_list):
    """
    Chat模型的functions参数编写函数
    :param functions_list: 包含一个或者多个函数对象的列表；
    :return：满足Chat模型functions参数要求的functions对象
    """
    def functions_generate(functions_list):
        # 创建空列表，用于保存每个函数的描述字典
        functions = []

        def chen_ming_algorithm(data):
            """
            陈明算法函数，该函数定义了一种特殊的数据集计算过程
            :param data: 必要参数，表示带入计算的数据表，用字符串进行表示
            :return：陈明函数计算后的结果，返回结果为表示为JSON格式的Dataframe类型对象
            """
            df_new = pd.read_json(data)
            res = np.sum(df_new, axis=1) - 1
            return res.to_json(orient='records')

        chen_ming_function_description = inspect.getdoc(chen_ming_algorithm)

        chen_ming_function_name = chen_ming_algorithm.__name__

        chen_ming_function = {"name": "chen_ming_algorithm",
                              "description": "用于执行陈明算法的函数，定义了一种特殊的数据集计算过程",
                              "parameters": {"type": "object",
                                             "properties": {"data": {"type": "string",
                                                                     "description": "执行陈明算法的数据集"},
                                                           },
                                             "required": ["data"],
                                            },
                             }


        # 对每个外部函数进行循环
        for function in functions_list:
            # 读取函数对象的函数说明
            function_description = inspect.getdoc(function)
            # 读取函数的函数名字符串
            function_name = function.__name__

            user_message1 = '以下是某的函数说明：%s。' % chen_ming_function_description +\
                            '根据这个函数的函数说明，请帮我创建一个function对象，用于描述这个函数的基本情况。这个function对象是一个JSON格式的字典，\
                            这个字典有如下5点要求：\
                            1.字典总共有三个键值对；\
                            2.第一个键值对的Key是字符串name，value是该函数的名字：%s，也是字符串；\
                            3.第二个键值对的Key是字符串description，value是该函数的函数的功能说明，也是字符串；\
                            4.第三个键值对的Key是字符串parameters，value是一个JSON Schema对象，用于说明该函数的参数输入规范。\
                            5.输出结果必须是一个JSON格式的字典，只输出这个字典即可，前后不需要任何前后修饰或说明的语句' % chen_ming_function_name


            assistant_message1 = json.dumps(chen_ming_function)

            user_prompt = '现在有另一个函数，函数名为：%s；函数说明为：%s；\
                          请帮我仿造类似的格式为当前函数创建一个function对象。' % (function_name, function_description)

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
            break  # 如果代码成功执行，跳出循环
        except Exception as e:
            attempts += 1  # 增加尝试次数
            print("发生错误：", e)
            print("由于模型limit rate导致报错，即将暂停1分钟，1分钟后重新尝试调用模型")
            time.sleep(60)

            if attempts == max_attempts:
                print("已达到最大尝试次数，程序终止。")
                raise  # 重新引发最后一个异常
            else:
                print("正在重新运行...")
    return functions


if __name__ == '__main__':
    print("this file contains functions to connect Mysql")