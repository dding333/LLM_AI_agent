import tiktoken
import openai
from tool import *
from gptLearning import *
from chatmessage import ChatMessages
from availablefunctions import AvailableFunctions
from planning import *
from response import *
encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
with open('telco_data_dictionary.md', 'r', encoding='utf-8') as f:
    data_dictionary = f.read()

with open('DA instruct.md', 'r', encoding='utf-8') as f:
    DA_instruct = f.read()

# functions_list = [sql_inter]
# functions = auto_functions(functions_list)
#
# response = openai.ChatCompletion.create(
#         model="gpt-4-0613",
#         messages=[
#             {"role": "system", "content": md_content},
#             {"role": "user", "content": "user_demographics数据表的主键和user_services数据表的主键是否完全一致？"}
#         ],
#         functions=functions,
#         function_call="auto",
#     )
# print(response["choices"][0]["message"])
# messages = [
#     {"role": "system", "content": md_content},
#     {"role": "user", "content": "请问user_demographics数据表的主键和user_services数据表的主键是否完全一致？"}
# ]
# response1 = run_conversation(messages, functions_list=functions_list, model="gpt-4-0613", function_call="auto")
# print(response1)

# messages = [
#     {"role": "system", "content": md_content},
#     {"role": "user", "content": "请问user_demographics的第10条数据内容是？"}
# ]
#
# response2=check_code_run(messages,
#                functions_list=functions_list,
#                model="gpt-4-0613",
#                function_call="auto",
#                auto_run = False)
# print(response2)

#
# msg1 = ChatMessages()
# print(msg1.system_messages)
# print(msg1.history_messages)
# msg1.messages_append({"role":"user","content":"nihao, can i help"})
# print(msg1.history_messages)
# print(msg1.tokens_count)
# msg1.messages_pop()
# print(msg1.history_messages)
# msg1.messages_pop(manual=True, index=-1)
# print(msg1.history_messages)
# print(msg1.tokens_count)
# msg2 = ChatMessages(system_content_list=[data_dictionary, DA_instruct])
# print(msg2.system_messages)
# print(msg2.history_messages)
# msg3 = msg2.copy()
# print(msg3.messages)
# print(msg3.tokens_count)
# msg4 = ChatMessages(system_content_list=[data_dictionary, DA_instruct],tokens_thr=2000)
# print(msg4.messages)

# g = globals()
# a = sql_inter(sql_query='SELECT COUNT(*) FROM user_demographics;', g=globals())
# print(a)
# extract_data(sql_query = 'SELECT * FROM user_demographics;',
#              df_name = 'user_demographics_df',
#              g = globals())
# code_str1 = '2 + 5'
# a = python_inter(py_code = code_str1, g=globals())
# print(a)
#
# code_str1 = 'a = 10'
# python_inter(py_code = code_str1, g=globals())
# print(a)

# msg1 = ChatMessages(system_content_list=[data_dictionary], question="请帮我查看user_demographics数据表中总共有多少条数据？")
# msg2 = msg1.copy()
# msg1_get_decomposition = add_task_decomposition_prompt(messages=msg1)
# print(msg1_get_decomposition.history_messages)
# print(msg2.history_messages)
# msg2_COT = modify_prompt(messages=msg2, action='add', enable_md_output=False, enable_COT=True)
# print(msg2_COT.messages[-1])
# print(msg2_COT.history_messages)
# msg2 = modify_prompt(messages=msg2_COT, action='remove', enable_md_output=False, enable_COT=True)
# print(msg2.history_messages)
af = AvailableFunctions(functions_list=[sql_inter, extract_data, python_inter, fig_inter])
# msg1 = ChatMessages(system_content_list=[data_dictionary], question="请帮我简单介绍下telco_db数据库中的这四张表")
# msg1_response = get_gpt_response(model='gpt-4-0613',
#                                  messages=msg1,
#                                  available_functions=None,
#                                  is_developer_mode=False,
#                                  is_enhanced_mode=False)
# print(msg1_response.content)
# msg2 = ChatMessages(system_content_list=[data_dictionary], question="请帮我查看user_demographics数据表中总共有多少条数据。")
# msg2_response = get_gpt_response(model='gpt-4-0613',
#                                  messages=msg2,
#                                  available_functions=af,
#                                  is_developer_mode=False,
#                                  is_enhanced_mode=False)
# print(msg2_response)
# msg5 = ChatMessages(system_content_list=[data_dictionary], question="分析telco_db数据库中的这四张表，帮我梳理一个数据分析的基本思路")
# msg5_response = get_gpt_response(model='gpt-4-0613',
#                                  messages=msg5,
#                                  available_functions=af,
#                                  is_developer_mode=False,
#                                  is_enhanced_mode=True)
# print(msg5_response.content)
# msg4 = ChatMessages(system_content_list=[data_dictionary], question="请帮我查询telco_db数据库中四张表数据量是否一致。")
# msg_response4 = get_chat_response(model='gpt-3.5-turbo-16k-0613',
#                                   messages=msg4,
#                                   available_functions=af)
# print(msg_response4.history_messages)
msg7 = ChatMessages(system_content_list=[data_dictionary], question="请帮我将user_demographics数据表读取到Python环境中，并对其进行缺失值分析。")
msg_response7 = get_chat_response(model='gpt-3.5-turbo-16k-0613',
                                  messages=msg7,
                                  available_functions=af,
                                  is_developer_mode=True)
print(msg_response7.history_messages)