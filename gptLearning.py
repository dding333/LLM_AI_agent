import os
import openai
import glob
import shutil
openai.api_key = os.getenv("OPENAI_API_KEY")

import numpy as np
import pandas as pd

import json
import io
import inspect
import requests
import re

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import base64
import email
from email import policy
from email.parser import BytesParser
from email.mime.text import MIMEText

from bs4 import BeautifulSoup
import dateutil.parser as parser

import sys
sys.path.insert(0, '.\\functions\\untested functions')
sys.path.insert(0, '.\\functions\\tested functions')


def extract_sql(json_str):
    # 解码JSON字符串
    data = json.loads(json_str)

    # 提取并返回'sql_query'的值
    return data.get('sql_query', None)

def check_code_run(messages,
                   functions_list=None,
                   model="gpt-4-0613",
                   function_call="auto",
                   auto_run=True):
    """
    能够自动执行外部函数调用的Chat对话模型，专门用于代码解释器的构建过程，可以通过auto_run参数设置，决定是否自动执行代码
    :param messages: 必要参数，字典类型，输入到Chat模型的messages参数对象
    :param functions_list: 可选参数，默认为None，可以设置为包含全部外部函数的列表对象
    :param model: Chat模型，可选参数，默认模型为gpt-4
    :auto_run：在调用外部函数的情况下，是否自动进行Second Response。该参数只在外部函数存在时起作用
    :return：Chat模型输出结果
    """

    # 如果没有外部函数库，则执行普通的对话任务
    if functions_list == None:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
        )
        response_message = response["choices"][0]["message"]
        final_response = response_message["content"]

    # 若存在外部函数库，则需要灵活选取外部函数并进行回答
    else:
        print("正在调用外部函数回答该问题")
        # 创建functions对象
        functions = auto_functions(functions_list)
        # 创建外部函数库字典
        available_functions = {func.__name__: func for func in functions_list}

        # first response
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            functions=functions,
            function_call=function_call)
        response_message = response["choices"][0]["message"]

        # 判断返回结果是否存在function_call，即判断是否需要调用外部函数来回答问题
        if response_message.get("function_call"):
            # 需要调用外部函数
            # 获取函数名
            function_name = response_message["function_call"]["name"]
            # 获取函数对象
            fuction_to_call = available_functions[function_name]
            # 获取函数参数
            function_args = json.loads(response_message["function_call"]["arguments"])
            if auto_run == False:
                sql_query = extract_sql(response_message["function_call"]["arguments"])

                res = input('即将执行以下代码：%s。是否确认并继续执行（1），或者退出本次运行过程（2）' % sql_query)
                if res == '2':
                    print("终止运行")
                    return None
                else:
                    print("正在执行代码，请稍后...")

            # 将函数参数输入到函数中，获取函数计算结果
            function_response = fuction_to_call(**function_args)

            # messages中拼接first response消息
            messages.append(response_message)
            # messages中拼接函数输出结果
            messages.append(
                {
                    "role": "function",
                    "name": function_name,
                    "content": function_response,
                }
            )
            # 第二次调用模型
            second_response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
            )
            # 获取最终结果
            final_response = second_response["choices"][0]["message"]["content"]
        else:
            final_response = response_message["content"]

    del messages

    return final_response
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
            if attempts == max_attempts:
                print("已达到最大尝试次数，程序终止。")
                raise  # 重新引发最后一个异常
            else:
                print("正在重新运行...")
    return functions



def run_conversation(messages, functions_list=None, model="gpt-4-0613", function_call="auto"):
    """
    能够自动执行外部函数调用的Chat对话模型
    :param messages: 必要参数，字典类型，输入到Chat模型的messages参数对象
    :param functions_list: 可选参数，默认为None，可以设置为包含全部外部函数的列表对象
    :param model: Chat模型，可选参数，默认模型为gpt-4
    :return：Chat模型输出结果
    """
    # 如果没有外部函数库，则执行普通的对话任务
    if functions_list == None:
        response = openai.ChatCompletion.create(
                        model=model,
                        messages=messages,
                        )
        response_message = response["choices"][0]["message"]
        final_response = response_message["content"]
        
    # 若存在外部函数库，则需要灵活选取外部函数并进行回答
    else:
        # 创建functions对象
        functions = auto_functions(functions_list)
        # 创建外部函数库字典
        available_functions = {func.__name__: func for func in functions_list}

        # first response
        response = openai.ChatCompletion.create(
                        model=model,
                        messages=messages,
                        functions=functions,
                        function_call=function_call)
        response_message = response["choices"][0]["message"]

        # 判断返回结果是否存在function_call，即判断是否需要调用外部函数来回答问题
        if response_message.get("function_call"):
            # 需要调用外部函数
            # 获取函数名
            function_name = response_message["function_call"]["name"]
            # 获取函数对象
            fuction_to_call = available_functions[function_name]
            # 获取函数参数
            function_args = json.loads(response_message["function_call"]["arguments"])
            # 将函数参数输入到函数中，获取函数计算结果
            function_response = fuction_to_call(**function_args)

            # messages中拼接first response消息
            messages.append(response_message)  
            # messages中拼接函数输出结果
            messages.append(
                {
                    "role": "function",
                    "name": function_name,
                    "content": function_response,
                }
            )  
            # 第二次调用模型
            second_response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
            )  
            # 获取最终结果
            final_response = second_response["choices"][0]["message"]["content"]
        else:
            final_response = response_message["content"]
            
    del messages
    
    return final_response


def chat_with_model(functions_list=None, 
                    prompt="你好呀", 
                    model="gpt-4-0613", 
                    system_message=[{"role": "system", "content": "你是一位乐于助人的助手。"}]):
    
    messages = system_message
    messages.append({"role": "user", "content": prompt})
    
    while True:           
        answer = run_conversation(messages=messages, 
                                    functions_list=functions_list, 
                                    model=model)
        
        
        print(f"模型回答: {answer}")

        # 询问用户是否还有其他问题
        user_input = input("您还有其他问题吗？(输入退出以结束对话): ")
        if user_input == "退出":
            del messages
            break

        # 记录用户回答
        messages.append({"role": "user", "content": user_input})
        
        
def extract_function_code(s, detail=0, tested=False, g=globals()):
    """
    函数提取函数，同时执行函数内容，可以选择打印函数信息，并选择代码保存的地址
    """
    def extract_code(s):
        """
        如果输入的字符串s是一个包含Python代码的Markdown格式字符串，提取出代码部分。
        否则，返回原字符串。

        参数:
        s: 输入的字符串。

        返回:
        提取出的代码部分，或原字符串。
        """
        # 判断字符串是否是Markdown格式
        if '```python' in s or 'Python' in s or'PYTHON' in s:
            # 找到代码块的开始和结束位置
            code_start = s.find('def')
            code_end = s.find('```\n', code_start)
            # 提取代码部分
            code = s[code_start:code_end]
        else:
            # 如果字符串不是Markdown格式，返回原字符串
            code = s

        return code
    
    # 提取代码字符串
    code = extract_code(s)
    
    # 提取函数名称
    match = re.search(r'def (\w+)', code)
    function_name = match.group(1)
    
    # 在untested文件夹内创建函数同名文件夹
    directory = './functions/untested functions/%s' % function_name
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # 将函数写入本地
    if tested == False:
        with open('./functions/untested functions/%s/%s_module.py' % (function_name, function_name), 'w', encoding='utf-8') as f:
            f.write(code)
    else:
        # 调用remove_to_test函数将函数文件夹转移至tested文件夹内
        remove_to_tested(function_name)
        with open('./functions/tested functions/%s/%s_module.py' % (function_name, function_name), 'w', encoding='utf-8') as f:
            f.write(code)
    
    # 执行该函数
    try:
        exec(code, g)
    except Exception as e:
        print("An error occurred while executing the code:")
        print(e)
    
    # 打印函数名称
    if detail == 0:
        print("The function name is:%s" % function_name)
    
    if detail == 1:
        if tested == False:
            with open('./functions/untested functions/%s/%s_module.py' % (function_name, function_name), 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            with open('./functions/tested functions/%s/%s_module.py' % (function_name, function_name), 'r', encoding='utf-8') as f:   
                content = f.read()
                
        print(content)
        
    return function_name
        

def remove_to_tested(function_name):
    """
    将函数同名文件夹由untested文件夹转移至tested文件夹内。\
    完成转移则说明函数通过测试，可以使用。此时需要将该函数的源码写入gptLearning.py中方便下次调用。
    """

    # 将函数代码写入gptLearning.py文件中
    with open('./functions/untested functions/%s/%s_module.py' % (function_name, function_name), encoding='utf-8') as f:
        function_code = f.read()

    with open('gptLearning.py', 'a', encoding='utf-8') as f:
        f.write("\n" + function_code)

    # 源文件夹路径
    src_dir = './functions/untested functions/%s' % function_name

    # 目标文件夹路径
    dst_dir = './functions/tested functions/%s' % function_name

    # 移动文件夹
    shutil.move(src_dir, dst_dir)

def show_functions(tested=False, if_print=False):
    """
    打印tested或untested文件夹内全部函数
    """
    current_directory = os.getcwd()
    if tested == False:
        directory = current_directory + '\\functions\\untested functions'
    else:
        directory = current_directory + '\\functions\\tested functions'
    files_and_directories = os.listdir(directory)
    # 过滤结果，只保留.py文件和非__pycache__文件夹
    files_and_directories = files_and_directories = [name for name in files_and_directories if (os.path.splitext(name)[1] == '.py' or os.path.isdir(os.path.join(directory, name))) and name != "__pycache__"]
    
    if if_print != False:
        for name in files_and_directories:
            print(name)
    
    return files_and_directories

def code_generate(req, few_shot='all', model='gpt-4-0613', g=globals(), detail=0):
    """
    Function calling外部函数自动创建函数，可以根据用户的需求，直接将其翻译为Chat模型可以直接调用的外部函数代码。
    :param req: 必要参数，字符串类型，表示输入的用户需求；
    :param few_shot: 可选参数，默认取值为字符串all，用于描述Few-shot提示示例的选取方案，当输入字符串all时，则代表提取当前外部函数库中全部测试过的函数作为Few-shot；\
    而如果输入的是一个包含了多个函数名称的list，则表示使用这些函数作为Few-shot。
    :param model: 可选参数，表示调用的Chat模型，默认选取gpt-4-0613；
    :param g: 可选参数，表示extract_function_code函数作用域，默认为globals()，即在当前操作空间全域内生效；
    :param detail: 可选参数，默认取值为0，还可以取值为1，表示extract_function_code函数打印新创建的外部函数细节；
    :return：新创建的函数名称。需要注意的是，在函数创建时，该函数也会在当前操作空间被定义，后续可以直接调用；
    """
    
    # 提取提示示例的函数名称
    if few_shot == 'all':
        few_shot_functions_name = show_functions(tested=True)
    elif type(few_shot) == list:
        few_shot_functions_name = few_shot
    # few_shot_functions = [globals()[name] for name in few_shot_functions_name]
    
    # 读取各阶段系统提示
    with open('./functions/tested functions/system_messages.json', 'r') as f:
        system_messages = json.load(f)
        
    # 各阶段提示message对象
    few_shot_messages_CM = []
    few_shot_messages_CD = []
    few_shot_messages = []
    
    # 先保存第一条消息，也就是system message
    few_shot_messages_CD += system_messages["system_message_CD"]
    few_shot_messages_CM += system_messages["system_message_CM"]
    few_shot_messages += system_messages["system_message"]

    # 创建不同阶段提示message
    for function_name in few_shot_functions_name:
        with open('./functions/tested functions/%s/%s_prompt.json' % (function_name, function_name), 'r') as f:
            msg = json.load(f)
        few_shot_messages_CD += msg["stage1_CD"]
        few_shot_messages_CM += msg["stage1_CM"]
        few_shot_messages += msg['stage2']
        
    # 读取用户需求，作为第一阶段CD环节User content
    new_req_CD_input = req
    few_shot_messages_CD.append({"role": "user", "content": new_req_CD_input})
    
    print('第一阶段CD环节提示创建完毕，正在进行CD提示...')
    
    # 第一阶段CD环节Chat模型调用过程
    response = openai.ChatCompletion.create(
                  model=model,
                  messages=few_shot_messages_CD
                )
    new_req_pi = response.choices[0].message['content']
    
    print('第一阶段CD环节提示完毕')
    
    # 第一阶段CM环节Messages创建
    new_req_CM_input = new_req_CD_input + new_req_pi
    few_shot_messages_CM.append({"role": "user", "content": new_req_CM_input})
    
    print('第一阶段CM环节提示创建完毕，正在进行第一阶段CM提示...')
    # 第一阶段CM环节Chat模型调用过程
    response = openai.ChatCompletion.create(
                      model=model,
                      messages=few_shot_messages_CM
                    )
    new_req_description = response.choices[0].message['content']
    
    print('第一阶段CM环节提示完毕')
    
    # 第二阶段Messages创建过程
    few_shot_messages.append({"role": "user", "content": new_req_description})
    
    print('第二阶段提示创建完毕，正在进行第二阶段提示...')
    
    # 第二阶段Chat模型调用过程
    response = openai.ChatCompletion.create(
                  model=model,
                  messages=few_shot_messages
                )
    new_req_function = response.choices[0].message['content']
    
    print('第二阶段提示完毕，准备运行函数并编写提示示例')
    
    # 提取函数并运行，创建函数名称对象，统一都写入untested文件夹内
    function_name = extract_function_code(s=new_req_function, detail=detail, g=g)
    
    print('新函数保存在./functions/untested functions/%s/%s_module.py文件中' % (function_name, function_name))
    
    # 创建该函数提示示例
    new_req_messages_CD = [
                          {"role": "user", "content": new_req_CD_input},
                          {"role": "assistant", "content": new_req_pi}
                         ]
    new_req_messages_CM = [
                          {"role": "user", "content": new_req_CM_input},
                          {"role": "assistant", "content":new_req_description}
                         ]
    
    with open('./functions/untested functions/%s/%s_module.py' % (function_name, function_name), encoding='utf-8') as f:
        new_req_function = f.read()
    
    new_req_messages = [
                       {"role": "user", "content": new_req_description},
                       {"role": "assistant", "content":new_req_function}
                      ] 
    
    new_req_prompt = {
                     "stage1_CD": new_req_messages_CD,
                     "stage1_CM": new_req_messages_CM,
                     "stage2": new_req_messages
                    }   
    
    with open('./functions/untested functions/%s/%s_prompt.json' % (function_name, function_name), 'w') as f:
        json.dump(new_req_prompt, f)
        
    print('新函数提示示例保存在./functions/untested functions/%s/%s_prompt.json文件中' % (function_name, function_name))
    print('done')
    return function_name

def prompt_modified(function_name, system_content='推理链修改.md', model="gpt-4-0613", g=globals()):
    """
    智能邮件项目的外部函数审查函数，用于审查外部函数创建流程提示是否正确以及最终创建的代码是否正确
    :param function_name: 必要参数，字符串类型，表示审查对象名称；
    :param system_content: 可选参数，默认取值为字符串推理链修改.md，表示此时审查函数外部挂载文档名称，需要是markdwon格式文档；
    :param model: 可选参数，表示调用的Chat模型，默认选取gpt-4-0613；
    :param g: 可选参数，表示extract_function_code函数作用域，默认为globals()，即在当前操作空间全域内生效；
    :return：审查结束后新创建的函数名称
    """
    print("正在执行审查函数，审查对象：%s" % function_name)
    with open(system_content, 'r', encoding='utf-8') as f:
        md_content = f.read()
        
    # 读取原函数全部提示内容
    with open('./functions/untested functions/%s/%s_prompt.json' % (function_name, function_name), 'r') as f:
        msg = json.load(f)
    
    # 将其保存为字符串
    msg_str = json.dumps(msg)
    
    # 进行审查
    response = openai.ChatCompletion.create(
                    model=model,
                    messages=[
                    {"role": "system", "content": md_content},
                    {"role": "user", "content": '以下是一个错误的智能邮件项目的推理链，请你按照要求对其进行修改：%s' % msg_str}
                    ]
                )
    
    modified_result = response.choices[0].message['content']
    
    def extract_json(s):
        pattern = r'```[jJ][sS][oO][nN]\s*({.*?})\s*```'
        match = re.search(pattern, s, re.DOTALL)
        if match:
            return match.group(1)
        else:
            return s
    
    modified_json = extract_json(modified_result)
    
    # 提取函数源码
    code = json.loads(modified_json)['stage2'][1]['content']
    
    # 提取函数名
    match = re.search(r'def (\w+)', code)
    function_name = match.group(1)
    
    print("审查结束，新的函数名称为：%s。\n正在运行该函数定义过程，并保存函数源码与prompt" % function_name)
    
    exec(code, g)
    
    # 在untested文件夹内创建函数同名文件夹
    directory = './functions/untested functions/%s' % function_name
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    # 写入函数
    with open('./functions/untested functions/%s/%s_module.py' % (function_name, function_name), 'w', encoding='utf-8') as f:
        f.write(code)
        
    # 写入提示
    with open('./functions/untested functions/%s/%s_prompt.json' % (function_name, function_name), 'w') as f:
        json.dump(json.loads(modified_json), f)
    
    print('新函数提示示例保存在./functions/untested functions/%s/%s_prompt.json文件中' % (function_name, function_name))
    print("%s函数已在当前操作空间定义，可以进行效果测试" % function_name)
    
    return function_name

def function_test(function_name, req, few_shot, model="gpt-4-0613", g=globals()):

    def test_messages(ueser_content):
        messages = [{"role": "system", "content": "端木天的邮箱地址是:2323365771@qq.com"},
                    {"role": "system", "content": "我的邮箱地址是:ksken166@gmail.com"},
                    {"role": "user", "content": ueser_content}]
        return messages
            
    messages = test_messages(req)
    
    new_function = globals()[function_name]
    functions_list = [new_function]
    
    print("根据既定用户需求req进行%s函数功能测试，请确保当该函数已经在当前操作空间定义..." % function_name)
    
    # 有可能在run_conversation环节报错
    # 若没报错，则运行：
    try:
        final_response = run_conversation(messages=messages, functions_list=functions_list, model=model)
        print("当前函数运行结果：'%s'" % final_response)
        
        feedback = input("函数功能是否满足要求 (yes/no)? ")
        if feedback.lower() == 'yes':
            print("函数功能通过测试，正在将函数写入tested文件夹")
            remove_to_tested(function_name)
            print('done')
        else:
            next_step = input("函数功能未通过测试，是1.需要再次进行测试，还是2.进入debug流程？")
            if next_step == '1':
                print("准备再次测试...")
                function_test(function_name, req, few_shot)
            else:
                solution = input("请选择debug方案：\n1.再次执行函数创建流程，并测试结果；\n2.执行审查函数\
                \n3.重新输入用户需求；\n4.退出程序，进行手动尝试")
                if solution == '1':
                    # 再次运行函数创建过程
                    print("好的，正在尝试再次创建函数，请稍等...")
                    few_shot_str = input("准备再次测试，请问是1.采用此前Few-shot方案，还是2.带入全部函数示例进行Few-shot？")
                    if few_shot_str == '1':
                        function_name = code_generate(req=req, few_shot=few_shot, model=model, g=g)
                    else:
                        function_name = code_generate(req=req, few_shot='all', model=model, g=g)
                    function_test(function_name=function_name, req=req, few_shot=few_shot, g=g)
                elif solution == '2':
                    # 执行审查函数
                    print("好的，执行审查函数，请稍等...")
                    function_name = prompt_modified(function_name=function_name, model="gpt-3.5-turbo-16k-0613", g=g)
                    # 接下来带入进行测试
                    print("新函数已创建，接下来带入进行测试...")
                    function_test(function_name=function_name, req=req, few_shot=few_shot, g=g)
                elif solution == '3':
                    new_req = input("好的，请再次输入用户需求，请注意，用户需求描述方法将极大程度影响最终函数创建结果。")
                    few_shot_str = input("接下来如何运行代码创建函数？1.采用此前Few-shot方案；\n2.使用全部外部函数作为Few-shot")
                    if few_shot_str == '1':
                        function_name = code_generate(req=new_req, few_shot=few_shot, model=model, g=g)
                    else:
                        function_name = code_generate(req=new_req, few_shot='all', model=model, g=g)
                    function_test(function_name=function_name, req=new_req, few_shot=few_shot, g=g)
                elif solution == '4':
                    print("好的，预祝debug顺利~")
        
    # run_conversation报错时则运行：
    except Exception as e:
        next_step = input("run_conversation无法正常运行，接下来是1.再次运行运行run_conversation，还是2.进入debug流程？")
        if next_step == '1':
            function_test(function_name, req, few_shot)
        else:
            solution = input("请选择debug方案：\n1.再次执行函数创建流程，并测试结果；\n2.执行审查函数\
            \n3.重新输入用户需求；\n4.退出程序，进行手动尝试")
            if solution == '1':
                # 再次运行函数创建过程
                print("好的，正在尝试再次创建函数，请稍等...")
                few_shot_str = input("准备再次测试，请问是1.采用此前Few-shot方案，还是2.带入全部函数示例进行Few-shot？")
                if few_shot_str == '1':
                    function_name = code_generate(req=req, few_shot=few_shot, model=model, g=g)
                else:
                    function_name = code_generate(req=req, few_shot='all', model=model, g=g)
                function_test(function_name=function_name, req=req, few_shot=few_shot, g=g)
            elif solution == '2':
                # 执行审查函数
                print("好的，执行审查函数，请稍等...")
                max_attempts = 3
                attempts = 0

                while attempts < max_attempts:
                    try:
                        function_name = prompt_modified(function_name=function_name, model="gpt-3.5-turbo-16k-0613", g=g)
                        break  # 如果代码成功执行，跳出循环
                    except Exception as e:
                        attempts += 1  # 增加尝试次数
                        print("发生错误：", e)
                        if attempts == max_attempts:
                            print("已达到最大尝试次数，程序终止。")
                            raise  # 重新引发最后一个异常
                        else:
                            print("正在重新运行审查程序...")
                # 接下来带入进行测试
                print("新函数已创建，接下来带入进行测试...")
                function_test(function_name=function_name, req=req, few_shot=few_shot, g=g)
            elif solution == '3':
                new_req = input("好的，请再次输入用户需求，请注意，用户需求描述方法将极大程度影响最终函数创建结果。")
                few_shot_str = input("接下来如何运行代码创建函数？1.采用此前Few-shot方案；\n2.使用全部外部函数作为Few-shot")
                if few_shot_str == '1':
                    function_name = code_generate(req=new_req, few_shot=few_shot, model=model, g=g)
                else:
                    function_name = code_generate(req=new_req, few_shot='all', model=model, g=g)
                function_test(function_name=function_name, req=new_req, few_shot=few_shot, g=g)
            elif solution == '4':
                print("好的，预祝debug顺利~")
                
def Gmail_auto_func(req, few_shot='all', model='gpt-4-0613', g=globals(), detail=0):
    function_name = code_generate(req, few_shot=few_shot, model=model, g=g, detail=detail)
    function_test(function_name=function_name, req=req, few_shot=few_shot, model=model, g=g)

################################
# 外部函数部分
def get_email_counts(userId='me'):
    """
    查询Gmail邮箱中邮件总数
    :param userId: 必要参数，字符串类型，用于表示需要查询的邮箱ID，\
    注意，当查询我的邮箱时，userId需要输入'me'；
    :return：邮件总数，返回结果本身必须是一个json格式对象
    """
    # 从本地文件中加载凭据
    creds = Credentials.from_authorized_user_file('token.json')

    # 创建 Gmail API 客户端
    service = build('gmail', 'v1', credentials=creds)

    # 列出用户的所有邮件
    results = service.users().messages().list(userId=userId).execute()
    messages = results.get('messages', [])

    # 获得邮件数量
    email_counts = len(messages)

    return json.dumps({"email_counts": email_counts})
def get_latest_email(userId):
    """
    查询Gmail邮箱中最后一封邮件信息
    :param userId: 必要参数，字符串类型，用于表示需要查询的邮箱ID，\
    注意，当查询我的邮箱时，userId需要输入'me'；
    :return：包含最后一封邮件全部信息的对象，该对象由Gmail API创建得到，且保存为JSON格式
    """
    # 从本地文件中加载凭据
    creds = Credentials.from_authorized_user_file('token.json')
    
    # 创建 Gmail API 客户端
    service = build('gmail', 'v1', credentials=creds)
    
    # 列出用户的一封最新邮件
    results = service.users().messages().list(userId=userId, maxResults=1).execute()
    messages = results.get('messages', [])

    # 遍历邮件
    for message in messages:
        # 获取邮件的详细信息
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        
    return json.dumps(msg)
def retrieve_emails(n, user_id='me'):
    """
    获取指定数量的最近邮件。

    参数:
    n: 要检索的邮件的数量。这应该是一个整数。
    user_id: 要检索邮件的用户的ID。默认值是'me'，表示当前授权的用户。

    返回:
    一个列表，其中每个元素都是一个字典，表示一封邮件。每个字典包含以下键：
    'From': 发件人的邮箱地址。
    'Date': 邮件的发送日期。
    'Subject': 邮件的主题。
    'Snippet': 邮件的摘要（前100个字符）。
    """
    # 从本地文件中加载凭据
    creds = Credentials.from_authorized_user_file('token.json')

    # 创建 Gmail API 客户端
    service = build('gmail', 'v1', credentials=creds)

    # 获取邮件列表
    results = service.users().messages().list(userId=user_id).execute()
    messages = results.get('messages', [])[:n]

    emails = []
    for message in messages:
        msg = service.users().messages().get(userId=user_id, id=message['id']).execute()

        # 解码邮件内容
        payload = msg['payload']
        headers = payload.get("headers")
        parts = payload.get("parts")

        data = {}

        if headers:
            for d in headers:
                name = d.get("name")
                if name.lower() == "from":
                    data['From'] = d.get("value")
                if name.lower() == "date":
                    data['Date'] = parser.parse(d.get("value")).strftime('%Y-%m-%d %H:%M:%S')
                if name.lower() == "subject":
                    data['Subject'] = d.get("value")

        if parts:
            for part in parts:
                mimeType = part.get("mimeType")
                body = part.get("body")
                data_decoded = base64.urlsafe_b64decode(body.get("data")).decode()
                if mimeType == "text/plain":
                    data['Snippet'] = data_decoded
                elif mimeType == "text/html":
                    soup = BeautifulSoup(data_decoded, "html.parser")
                    data['Snippet'] = soup.get_text()

        emails.append(data)

    # 返回邮件列表
    return json.dumps(emails, indent=2)
def send_email(to, subject, message_text):
    """
    借助Gmail API创建并发送邮件函数
    :param to: 必要参数，字符串类型，用于表示邮件发送的目标邮箱地址；
    :param subject: 必要参数，字符串类型，表示邮件主题；
    :param message_text: 必要参数，字符串类型，表示邮件全部正文；
    :return：返回发送结果字典，若成功发送，则返回包含邮件ID和发送状态的字典。
    """
    
    creds_file='token_send.json'
    
    def create_message(to, subject, message_text):
        """创建一个MIME邮件"""
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = 'me'
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_string().encode('utf-8')).decode('utf-8')
        return {
            'raw': raw_message
        }

    def send_message(service, user_id, message):
        """发送邮件"""
        try:
            sent_message = service.users().messages().send(userId=user_id, body=message).execute()
            print(f'Message Id: {sent_message["id"]}')
            return sent_message
        except Exception as e:
            print(f'An error occurred: {e}')
            return None

    # 从本地文件中加载凭据
    creds = Credentials.from_authorized_user_file(creds_file)

    # 创建 Gmail API 客户端
    service = build('gmail', 'v1', credentials=creds)

    message = create_message(to, subject, message_text)
    res = send_message(service, 'me', message)

    return json.dumps(res)

def get_oldest_email(userId='me'):
    """
    根据给定的userId，查询Gmail邮箱中最早一封邮件的发件人和邮件主要内容
    :param userId: 非必要参数，默认为'me'，表示查询调用此函数的用户在Gmail中最早的一封邮件
    :return 其结果是一个json对象，包含最早一封邮件的发件人和邮件内容
    """
    # 从本地文件中加载凭据
    creds = Credentials.from_authorized_user_file('token.json')

    # 创建 Gmail API 的 service 客户对象
    service = build('gmail', 'v1', credentials=creds)

    # 列出用户邮件
    results = service.users().messages().list(userId=userId).execute()
    messages = results.get('messages', [])
    
    # 判断邮件是否存在，取最早的一封邮件
    if not messages:
        return json.dumps({"error":"No emails found."})
    else:
        message = messages[-1]
        #获取邮件详情
        msg = service.users().messages().get(userId=userId, id=message['id']).execute()
        
    # 解析邮件内容
    headers = msg['payload']['headers']
    snippet = msg['snippet']
    for d in headers:
        if d['name'] == 'From':
            sender = d['value']

    return json.dumps({"Sender": sender, "Content": snippet})

def get_emails_by_sender(sender, userId='me'):
    """
    根据发件人查询Gmail邮箱中的邮件列表

    参数:
    sender: 邮件的发送者
    userId: 要检索邮件的用户的ID，默认值是'me'。

    返回:
    包含所有从特定发送者收到的邮件的列表，每个邮件都表示为一个字典，包含邮件的id和主题。
    """

    # 从本地文件中加载凭据
    creds = Credentials.from_authorized_user_file('token.json')

    # 创建 Gmail API 的 service 客户对象
    service = build('gmail', 'v1', credentials=creds)

    # 获取特定发件人的专门邮件列表
    results = service.users().messages().list(userId=userId, q=f"from:{sender}").execute()

    messages = results.get('messages', [])

    emails = []
    if len(messages):
        for message in messages:
            msg = service.users().messages().get(userId=userId, id=message['id']).execute()
            email_data = msg['payload']['headers']
            for values in email_data:
                name = values['name']
                if name == 'Subject':
                    sub = values['value']
            emails.append({"id": message['id'], "subject": sub})
    else:
        print(f"No emails found from {sender}")

    return json.dumps(emails)

def count_emails_from_sender(sender, userId='me'):
    """
    根据发件人查询Gmail邮箱中的邮件列表并计数。

    参数:
    sender: 邮件的发送者
    userId: 要计数邮件的用户的ID，默认值是'me'。

    返回:
    包含了邮件总数的json对象
    """
    # 从本地文件中加载凭据
    creds = Credentials.from_authorized_user_file('token.json')

    # 创建 Gmail API 的 service 客户对象
    service = build('gmail', 'v1', credentials=creds)

    # 获取指定发送者的邮件列表
    try:
        request = service.users().messages().list(userId=userId, q=f"from:{sender}")
        response = request.execute()
    except Exception as error:
        print(f"An error occurred: {error}")
        return None

    # 计算邮件总数
    email_count = len(response['messages'])

    # 返回邮件总数
    return json.dumps({'count': email_count})

def count_emails_before_date(date, userId='me'):
    """
    查询在指定日期之前收到的邮件数量。

    参数:
    date: 指定的日期，格式为'yyyy/mm/dd'。将统计在这个日期之前收到的邮件数目。
    userId: 查询邮件的用户ID，默认值是'me'。

    返回:
    在指定日期之前收到的邮件数量，结果会返回为json对象。
    """
    # 从本地文件中加载凭据
    creds = Credentials.from_authorized_user_file('token.json')

    # 创建 Gmail API 的 service 客户对象
    service = build('gmail', 'v1', credentials=creds)

    # 列出用户的邮件
    results = service.users().messages().list(userId=userId).execute()
    messages = results.get('messages', [])

    # 计数器
    count = 0

    # 遍历每封邮件
    for message in messages:
        msg = service.users().messages().get(userId=userId, id=message['id']).execute()

        # 获取邮件的收到日期
        headers = msg['payload']['headers']
        for header in headers:
            if header['name'] == 'Date':
                msg_date = parser.parse(header['value']).strftime('%Y/%m/%d')
                if msg_date < date:
                    count += 1

    # 返回邮件数量
    return json.dumps({"count": count})

def get_unread_email_count(userId='me'):
    """
    获取Gmail邮箱中未读邮件的数量。

    参数:
    userId: 访问gmail账户的用户ID，该参数是字符串类型，默认值为'me'，表示当前授权的用户。

    返回:
    返回未读邮件的数量，结果会以json格式对象返回。
    """
    # 从本地文件中加载凭据
    creds = Credentials.from_authorized_user_file('token.json')

    # 创建 Gmail API 客户对象
    service = build('gmail', 'v1', credentials=creds)

    # 查找未读邮件
    results = service.users().messages().list(userId=userId, q='is:unread').execute()
    messages = results.get('messages', [])

    # 获取未读邮件的数量
    unread_count = len(messages)

    return json.dumps({"unread_email_count": unread_count})

def count_emails_with_query(query, userId='me'):
    """
    查询包含指定内容的邮件数量。

    参数:
    query: 要查询的邮件内容。
    userId: 查询邮件的用户ID，默认值是'me'。

    返回:
    包含查询内容的邮件数量，结果会返回为json对象。
    """
    # 从本地文件中加载凭据
    creds = Credentials.from_authorized_user_file('token.json')

    # 创建 Gmail API 的 service 客户对象
    service = build('gmail', 'v1', credentials=creds)

    # 获取指定内容的邮件列表
    try:
        request = service.users().messages().list(userId=userId, q=query)
        response = request.execute()
    except Exception as error:
        print(f"An error occurred: {error}")
        return None

    # 计算邮件总数
    email_count = len(response['messages'])

    # 返回邮件总数
    return json.dumps({'count': email_count})

def count_emails_from_sender_in_period(sender, date_range, userId='me'):
    """
    查询在指定日期范围内由特定发件人发送的邮件数量。

    参数:
    sender: 邮件的发送者。
    date_range: 邮件的接收日期范围，日期格式为'yyyy-mm-dd to yyyy-mm-dd'。
    userId: 查询邮件的用户ID，默认值是'me'。

    返回:
    在指定日期范围内由特定发件人发送的邮件数量，结果会返回为json对象。
    """

    # 从本地文件中加载凭据
    creds = Credentials.from_authorized_user_file('token.json')

    # 创建 Gmail API 的 service 客户对象
    service = build('gmail', 'v1', credentials=creds)

    try:
        # 查询在指定日期范围内由特定发件人发送的邮件
        request = service.users().messages().list(userId=userId, q=f"from:{sender} after:{date_range.split(' to ')[0]} before:{date_range.split(' to ')[1]}")
        response = request.execute()
    except Exception as e:
        print(f'An error occurred: {e}')
        return None

    # 计算邮件总数
    email_count = len(response['messages'])

    # 返回邮件数量
    return json.dumps({'count': email_count})

if __name__ == '__main__':
    print("this file contains assist functions")