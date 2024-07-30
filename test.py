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
#             {"role": "user", "content": "Do the primary keys of the user_demographics table match exactly with the primary keys of the user_services table?"}
#         ],
#         functions=functions,
#         function_call="auto",
#     )
# print(response["choices"][0]["message"])
# messages = [
#     {"role": "system", "content": md_content},
#     {"role": "user", "content": "Could you please confirm if the primary keys of the user_demographics table are identical to the primary keys of the user_services table?"}
# ]
# response1 = run_conversation(messages, functions_list=functions_list, model="gpt-4-0613", function_call="auto")
# print(response1)

# messages = [
#     {"role": "system", "content": md_content},
#     {"role": "user", "content": "What is the content of the 10th record in the user_demographics table?"}
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

# msg1 = ChatMessages(system_content_list=[data_dictionary], question="Can you help me check how many records there are in the user_demographics table?")
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
# msg1 = ChatMessages(system_content_list=[data_dictionary], question="Could you provide a brief introduction to these four tables in the telco_db database?")
# msg1_response = get_gpt_response(model='gpt-4-0613',
#                                  messages=msg1,
#                                  available_functions=None,
#                                  is_developer_mode=False,
#                                  is_enhanced_mode=False)
# print(msg1_response.content)
# msg2 = ChatMessages(system_content_list=[data_dictionary], question=""Please help me check how many records there are in the user_demographics table.")
# msg2_response = get_gpt_response(model='gpt-4-0613',
#                                  messages=msg2,
#                                  available_functions=af,
#                                  is_developer_mode=False,
#                                  is_enhanced_mode=False)
# print(msg2_response)
# msg5 = ChatMessages(system_content_list=[data_dictionary], question="Analyze these four tables in the telco_db database and help me outline a basic data analysis approach.")
# msg5_response = get_gpt_response(model='gpt-4-0613',
#                                  messages=msg5,
#                                  available_functions=af,
#                                  is_developer_mode=False,
#                                  is_enhanced_mode=True)
# print(msg5_response.content)
# msg4 = ChatMessages(system_content_list=[data_dictionary], question="Please help me check if the data volume is consistent across the four tables in the telco_db database.")
# msg_response4 = get_chat_response(model='gpt-3.5-turbo-16k-0613',
#                                   messages=msg4,
#                                   available_functions=af)
# print(msg_response4.history_messages)
msg7 = ChatMessages(system_content_list=[data_dictionary], question="Please help me load the user_demographics table into the Python environment and perform a missing value analysis.")
msg_response7 = get_chat_response(model='gpt-3.5-turbo-16k-0613',
                                  messages=msg7,
                                  available_functions=af,
                                  is_developer_mode=True)
print(msg_response7.history_messages)
