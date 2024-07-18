from planning import *
import openai
import time
import json
from IPython.display import display, Code, Markdown
from openai.error import APIConnectionError
from gptLearning import *


def function_to_call(available_functions, function_call_message):
    """
    根据一条函数调用消息function_call_message，返回一条函数运行结果消息function_response_messages。
    :param available_functions: 必要参数，要求输入一个AvailableFunctions对象，以说明当前外部函数基本情况
    :param function_call_message: 必要参数，要求输入一条外部函数调用的message
    :return: function_response_messages，输出又外部函数运行结果所组成的message
    """

    # 获取调用外部函数的函数名称
    function_name = function_call_message["function_call"]["name"]

    # 根据函数名称获取对应的外部函数对象
    fuction_to_call = available_functions.functions_dic[function_name]

    # 提取function_call_message中调用外部函数的函数参数
    # 即大模型编写的SQL或者Python代码
    function_args = json.loads(function_call_message["function_call"]["arguments"])

    # 将参数带入到外部函数中并运行
    try:
        # 将当前操作空间中的全局变量添加到外部函数中
        function_args['g'] = globals()

        # 运行外部函数
        function_response = fuction_to_call(**function_args)

    # 若外部函数运行报错，则提取报错信息
    except Exception as e:
        function_response = "函数运行报错如下:" + str(e)
        # print(function_response)

    # 创建function_response_messages
    # 该message包含外部函数顺利运行或报错信息

    function_response_messages = {
        "role": "function",
        "name": function_name,
        "content": function_response,
    }

    return function_response_messages
def get_gpt_response(model,
                     messages,
                     available_functions=None,
                     is_developer_mode=False,
                     is_enhanced_mode=False):
    """
    负责调用Chat模型并获得模型回答函数，并且当在调用GPT模型时遇到Rate limit时可以选择暂时休眠1分钟后再运行。\
    同时对于意图不清的问题，会提示用户修改输入的prompt，以获得更好的模型运行结果。
    :param model: 必要参数，表示调用的大模型名称
    :param messages: 必要参数，ChatMessages类型对象，用于存储对话消息
    :param available_functions: 可选参数，AvailableFunctions类型对象，用于表示开启对话时外部函数基本情况。\
    默认为None，表示没有外部函数
    :param is_developer_mode: 表示是否开启开发者模式，默认为False。\
    开启开发者模式时，会自动添加提示词模板，并且会在每次执行代码前、以及返回结果之后询问用户意见，并会根据用户意见进行修改。
    :param is_enhanced_mode: 可选参数，表示是否开启增强模式，默认为False。\
    开启增强模式时，会自动启动复杂任务拆解流程，并且在进行代码debug时会自动执行deep debug。
    :return: 返回模型返回的response message
    """

    # 如果开启开发者模式，则进行提示词修改，首次运行是增加提示词
    if is_developer_mode:
        messages = modify_prompt(messages, action='add')

    # 如果是增强模式，则增加复杂任务拆解流程
    if is_enhanced_mode:
        messages = add_task_decomposition_prompt(messages)

    # 考虑到可能存在通信报错问题，因此循环调用Chat模型进行执行
    while True:
        try:
            # 若不存在外部函数
            if available_functions == None:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages.messages)

                # 若存在外部函数，此时functions和function_call参数信息都从AvailableFunctions对象中获取
            else:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages.messages,
                    functions=available_functions.functions,
                    function_call=available_functions.function_call
                )
            break  # 如果成功获取响应，退出循环

        except APIConnectionError as e:
            # APIConnectionError默认是用户需求不清导致无法返回结果
            # 若开启增强模式，此时提示用户重新输入需求
            if is_enhanced_mode:
                # 创建临时消息列表
                msg_temp = messages.copy()
                # 获取用户问题
                question = msg_temp.messages[-1]["content"]
                # 提醒用户修改提问的提示模板
                new_prompt = "以下是用户提问：%s。该问题有些复杂，且用户意图并不清晰。\
                请编写一段话，来引导用户重新提问。" % question
                # 修改msg_temp并重新提问
                try:
                    msg_temp.messages[-1]["content"] = new_prompt
                    # 修改用户问题并直接提问
                    response = openai.ChatCompletion.create(
                        model=model,
                        messages=msg_temp.messages)

                    # 打印gpt返回的提示修改原问题的描述语句
                    display(Markdown(response["choices"][0]["message"]["content"]))
                    # 引导用户重新输入问题或者退出
                    user_input = input("请重新输入问题，输入“退出”可以退出当前对话")
                    if user_input == "退出":
                        print("当前模型无法返回结果，已经退出")
                        return None
                    else:
                        # 修改原始问题
                        messages.history_messages[-1]["content"] = user_input

                        # 再次进行提问
                        response_message = get_gpt_response(model=model,
                                                            messages=messages,
                                                            available_functions=available_functions,
                                                            is_developer_mode=is_developer_mode,
                                                            is_enhanced_mode=is_enhanced_mode)

                        return response_message
                # 若在提示用户修改原问题时遇到链接错误，则直接暂停1分钟后继续执行While循环
                except APIConnectionError as e:
                    print(f"当前遇到了一个链接问题: {str(e)}")
                    print("由于Limit Rate限制，即将等待1分钟后继续运行...")
                    time.sleep(60)  # 等待1分钟
                    print("已等待60秒，即将开始重新调用模型并进行回答...")

            # 若未开启增强模式
            else:
                # 打印错误的核心信息
                print(f"当前遇到了一个链接问题: {str(e)}")
                # 如果是开发者模式
                if is_developer_mode:
                    # 选择等待、更改模型或者直接报错退出
                    user_input = input("请选择等待1分钟（1），或者更换模型（2），或者报错退出（3）")
                    if user_input == '1':
                        print("好的，将等待1分钟后继续运行...")
                        time.sleep(60)  # 等待1分钟
                        print("已等待60秒，即将开始新的一轮问答...")
                    elif user_input == '2':
                        model = input("好的，请输出新模型名称")
                    else:
                        # if modify:
                        #     messages = modify_prompt(messages, action='remove', enable_md_output=md_output,
                        #                              enable_COT=COT)
                        raise e  # 如果用户选择退出，恢复提示并抛出异常
                # 如果不是开发者模式
                else:
                    print("由于Limit Rate限制，即将等待1分钟后继续运行...")
                    time.sleep(60)  # 等待1分钟
                    print("已等待60秒，即将开始重新调用模型并进行回答...")

    # 还原原始的msge对象
    if is_developer_mode:
        messages = modify_prompt(messages, action='remove')

    return response["choices"][0]["message"]


def get_chat_response(model,
                      messages,
                      available_functions=None,
                      is_developer_mode=False,
                      is_enhanced_mode=False,
                      delete_some_messages=False,
                      is_task_decomposition=False):
    """
    负责完整执行一次对话的最高层函数，需要注意的是，一次对话中可能会多次调用大模型，而本函数则是完成一次对话的主函数。\
    要求输入的messages中最后一条消息必须是能正常发起对话的消息。\
    该函数通过调用get_gpt_response来获取模型输出结果，并且会根据返回结果的不同，例如是文本结果还是代码结果，\
    灵活调用不同函数对模型输出结果进行后处理。\
    :param model: 必要参数，表示调用的大模型名称
    :param messages: 必要参数，ChatMessages类型对象，用于存储对话消息
    :param available_functions: 可选参数，AvailableFunctions类型对象，用于表示开启对话时外部函数基本情况。\
    默认为None，表示没有外部函数
    :param is_developer_mode: 表示是否开启开发者模式，默认为False。\
    开启开发者模式时，会自动添加提示词模板，并且会在每次执行代码前、以及返回结果之后询问用户意见，并会根据用户意见进行修改。
    :param is_enhanced_mode: 可选参数，表示是否开启增强模式，默认为False。\
    开启增强模式时，会自动启动复杂任务拆解流程，并且在进行代码debug时会自动执行deep debug。
    :param delete_some_messages: 可选参数，表示在拼接messages时是否删除中间若干条消息，默认为Fasle。
    :param is_task_decomposition: 可选参数，是否是当前执行任务是否是审查任务拆解结果，默认为False。
    :return: 拼接本次问答最终结果的messages
    """

    # 当且仅当围绕复杂任务拆解结果进行修改时，才会出现is_task_decomposition=True的情况
    # 当is_task_decomposition=True时，不再重新创建response_message
    if not is_task_decomposition:
        # 先获取单次大模型调用结果
        # 此时response_message是大模型调用返回的message
        response_message = get_gpt_response(model=model,
                                            messages=messages,
                                            available_functions=available_functions,
                                            is_developer_mode=is_developer_mode,
                                            is_enhanced_mode=is_enhanced_mode)

    # 复杂条件判断，若is_task_decomposition = True，
    # 或者是增强模式且是执行function response任务时
    # （需要注意的是，当is_task_decomposition = True时，并不存在response_message对象）
    if is_task_decomposition or (is_enhanced_mode and response_message.get("function_call")):
        # 将is_task_decomposition修改为True，表示当前执行任务为复杂任务拆解
        is_task_decomposition = True
        # 在拆解任务时，将增加了任务拆解的few-shot-message命名为text_response_messages
        task_decomp_few_shot = add_task_decomposition_prompt(messages)
        # print("正在进行任务分解，请稍后...")
        # 同时更新response_message，此时response_message就是任务拆解之后的response
        response_message = get_gpt_response(model=model,
                                            messages=task_decomp_few_shot,
                                            available_functions=available_functions,
                                            is_developer_mode=is_developer_mode,
                                            is_enhanced_mode=is_enhanced_mode)
        # 若拆分任务的提示无效，此时response_message有可能会再次创建一个function call message
        if response_message.get("function_call"):
            print("当前任务无需拆解，可以直接运行。")

    # 若本次调用是由修改对话需求产生，则按照参数设置删除原始message中的若干条消息
    # 需要注意的是，删除中间若干条消息，必须在创建完新的response_message之后再执行
    if delete_some_messages:
        for i in range(delete_some_messages):
            messages.messages_pop(manual=True, index=-1)

    # 注意，执行到此处时，一定会有一个response_message
    # 接下来分response_message不同类型，执行不同流程
    # 若是文本响应类任务（包括普通文本响应和和复杂任务拆解审查两种情况，都可以使用相同代码）
    if not response_message.get("function_call"):
        # 将message保存为text_answer_message
        text_answer_message = response_message
        # 并带入is_text_response_valid对文本内容进行审查
        messages = is_text_response_valid(model=model,
                                          messages=messages,
                                          text_answer_message=text_answer_message,
                                          available_functions=available_functions,
                                          is_developer_mode=is_developer_mode,
                                          is_enhanced_mode=is_enhanced_mode,
                                          delete_some_messages=delete_some_messages,
                                          is_task_decomposition=is_task_decomposition)



    # 若是function response任务
    elif response_message.get("function_call"):
        # 创建调用外部函数的function_call_message
        # 在当前Agent中，function_call_message是一个包含SQL代码或者Python代码的JSON对象
        function_call_message = response_message
        # 将function_call_message带入代码审查和运行函数is_code_response_valid
        # 并最终获得外部函数运行之后的问答结果
        messages = is_code_response_valid(model=model,
                                          messages=messages,
                                          function_call_message=function_call_message,
                                          available_functions=available_functions,
                                          is_developer_mode=is_developer_mode,
                                          is_enhanced_mode=is_enhanced_mode,
                                          delete_some_messages=delete_some_messages)

    return messages


def is_code_response_valid(model,
                           messages,
                           function_call_message,
                           available_functions=None,
                           is_developer_mode=False,
                           is_enhanced_mode=False,
                           delete_some_messages=False):
    """
    负责完整执行一次外部函数调用的最高层函数，要求输入的msg最后一条消息必须是包含function call的消息。\
    函数的最终任务是将function call的消息中的代码带入外部函数并完成代码运行，并且支持交互式代码编写或自动代码编写运行不同模式。\
    当函数运行得到一条包含外部函数运行结果的function message之后，会继续将其带入check_get_final_function_response函数，\
    用于最终将function message转化为assistant message，并完成本次对话。
    :param model: 必要参数，表示调用的大模型名称
    :param messages: 必要参数，ChatMessages类型对象，用于存储对话消息
    :param function_call_message: 必要参数，用于表示上层函数创建的一条包含function call消息的message
    :param available_functions: 可选参数，AvailableFunctions类型对象，用于表示开启对话时外部函数基本情况。\
    默认为None，表示没有外部函数
    :param is_developer_mode: 表示是否开启开发者模式，默认为False。\
    开启开发者模式时，会自动添加提示词模板，并且会在每次执行代码前、以及返回结果之后询问用户意见，并会根据用户意见进行修改。
    :param is_enhanced_mode: 可选参数，表示是否开启增强模式，默认为False。\
    开启增强模式时，会自动启动复杂任务拆解流程，并且在进行代码debug时会自动执行deep debug。
    :param delete_some_messages: 可选参数，表示在拼接messages时是否删除中间若干条消息，默认为Fasle。
    :return: message，拼接了最新大模型回答结果的message
    """

    # 为打印代码和修改代码（增加创建图像对家部分代码）做准备
    # 创建字符串类型json格式的message对象
    code_json_str = function_call_message["function_call"]["arguments"]
    # 将json转化为字典
    try:
        code_dict = json.loads(code_json_str)
    except Exception as e:
        print("json字符解析错误，正在重新创建代码...")
        # 递归调用上层函数get_chat_response，并返回最终message结果
        # 需要注意的是，如果上层函数再次创建了function_call_message
        # 则会再次调用is_code_response_valid，而无需在当前函数中再次执行
        messages = get_chat_response(model=model,
                                     messages=messages,
                                     available_functions=available_functions,
                                     is_developer_mode=is_developer_mode,
                                     is_enhanced_mode=is_enhanced_mode,
                                     delete_some_messages=delete_some_messages)

        return messages

    # 若顺利将json转化为字典，则继续执行以下代码
    # 创建convert_to_markdown内部函数，用于辅助打印代码结果
    def convert_to_markdown(code, language):
        return f"```{language}\n{code}\n```"

    # 提取代码部分参数
    # 如果是SQL，则按照Markdown中SQL格式打印代码
    if code_dict.get('sql_query'):
        code = code_dict['sql_query']
        markdown_code = convert_to_markdown(code, 'sql')
        print("即将执行以下代码：")

    # 如果是Python，则按照Markdown中Python格式打印代码
    elif code_dict.get('py_code'):
        code = code_dict['py_code']
        markdown_code = convert_to_markdown(code, 'python')
        print("即将执行以下代码：")

    else:
        markdown_code = code_dict

    display(Markdown(markdown_code))

    # 若是开发者模式，则提示用户先对代码进行审查然后再运行
    if is_developer_mode:
        user_input = input("是直接运行代码（1），还是反馈修改意见，并让模型对代码进行修改后再运行（2）")
        if user_input == '1':
            print("好的，正在运行代码，请稍后...")

        else:
            modify_input = input("好的，请输入修改意见：")
            # 记录模型当前创建的代码
            messages.messages_append(function_call_message)
            # 记录修改意见
            messages.messages_append({"role": "user", "content": modify_input})

            # 调用get_chat_response函数并重新获取回答结果
            # 需要注意，此时需要设置delete_some_messages=2，删除中间对话结果以节省token
            messages = get_chat_response(model=model,
                                         messages=messages,
                                         available_functions=available_functions,
                                         is_developer_mode=is_developer_mode,
                                         is_enhanced_mode=is_enhanced_mode,
                                         delete_some_messages=2)

            return messages

    # 若不是开发者模式，或者开发者模式下user_input == '1'
    # 则调用function_to_call函数，并获取最终外部函数运行结果
    # 在当前Agent中，外部函数运行结果就是SQL或者Python运行结果，或代码运行报错结果
    function_response_message = function_to_call(available_functions=available_functions,
                                                 function_call_message=function_call_message)

    # 将function_response_message带入check_get_final_function_response进行审查
    messages = check_get_final_function_response(model=model,
                                                 messages=messages,
                                                 function_call_message=function_call_message,
                                                 function_response_message=function_response_message,
                                                 available_functions=available_functions,
                                                 is_developer_mode=is_developer_mode,
                                                 is_enhanced_mode=is_enhanced_mode,
                                                 delete_some_messages=delete_some_messages)

    return messages


# 判断代码输出结果是否符合要求，输入function response message，输出基于外部函数运行结果的message
def check_get_final_function_response(model,
                                      messages,
                                      function_call_message,
                                      function_response_message,
                                      available_functions=None,
                                      is_developer_mode=False,
                                      is_enhanced_mode=False,
                                      delete_some_messages=False):
    """
    负责执行外部函数运行结果审查工作。若外部函数运行结果消息function_response_message并不存在报错信息，\
    则将其拼接入message中，并将其带入get_chat_response函数并获取下一轮对话结果。而如果function_response_message中存在报错信息，\
    则开启自动debug模式。本函数将借助类似Autogen的模式，复制多个Agent，并通过彼此对话的方式来完成debug。
    :param model: 必要参数，表示调用的大模型名称
    :param messages: 必要参数，ChatMessages类型对象，用于存储对话消息
    :param function_call_message: 必要参数，用于表示上层函数创建的一条包含function call消息的message
    :param function_response_message: 必要参数，用于表示上层函数创建的一条包含外部函数运行结果的message
    :param available_functions: 可选参数，AvailableFunctions类型对象，用于表示开启对话时外部函数基本情况。\
    默认为None，表示没有外部函数
    :param is_developer_mode: 表示是否开启开发者模式，默认为False。\
    开启开发者模式时，会自动添加提示词模板，并且会在每次执行代码前、以及返回结果之后询问用户意见，并会根据用户意见进行修改。
    :param is_enhanced_mode: 可选参数，表示是否开启增强模式，默认为False。\
    开启增强模式时，会自动启动复杂任务拆解流程，并且在进行代码debug时会自动执行deep debug。
    :param delete_some_messages: 可选参数，表示在拼接messages时是否删除中间若干条消息，默认为Fasle。
    :return: message，拼接了最新大模型回答结果的message
    """

    # 获取外部函数运行结果内容
    fun_res_content = function_response_message["content"]

    # 若function_response中包含错误
    if "报错" in fun_res_content:
        # 打印报错信息
        print(fun_res_content)

        # 根据是否是增强模式，选择执行高效debug或深度debug
        # 高效debug和深度debug区别只在于提示内容和提示流程的不同
        # 高效debug只包含一条提示，只调用一次大模型即可完成自动debug工作
        # 而深度debug则包含三次提示，需要调用三次大模型进行深度总结并完成debug工作
        # 先创建不同模式bubug的不同提示词
        if not is_enhanced_mode:
            # 执行高效debug
            display(Markdown("**即将执行高效debug，正在实例化Efficient Debug Agent...**"))
            debug_prompt_list = ['你编写的代码报错了，请根据报错信息修改代码并重新执行。']

        else:
            # 执行深度debug
            display(Markdown(
                "**即将执行深度debug，该debug过程将自动执行多轮对话，请耐心等待。正在实例化Deep Debug Agent...**"))
            display(Markdown("**正在实例化deep debug Agent...**"))
            debug_prompt_list = ["之前执行的代码报错了，你觉得代码哪里编写错了？",
                                 "好的。那么根据你的分析，为了解决这个错误，从理论上来说，应该如何操作呢？",
                                 "非常好，接下来请按照你的逻辑编写相应代码并运行。"]

        # 复制msg，相当于创建一个新的Agent进行debug
        # 需要注意的是，此时msg最后一条消息是user message，而不是任何函数调用相关message
        msg_debug = messages.copy()
        # 追加function_call_message
        # 当前function_call_message中包含编错的代码
        msg_debug.messages_append(function_call_message)
        # 追加function_response_message
        # 当前function_response_message包含错误代码的运行报错信息
        msg_debug.messages_append(function_response_message)

        # 依次输入debug的prompt，来引导大模型完成debug
        for debug_prompt in debug_prompt_list:
            msg_debug.messages_append({"role": "user", "content": debug_prompt})
            display(Markdown("**From Debug Agent:**"))
            display(Markdown(debug_prompt))

            # 再次调用get_chat_response，在当前debug的prompt下，get_chat_response会返回修改意见或修改之后的代码
            # 打印提示信息
            display(Markdown("**From MateGen:**"))
            msg_debug = get_chat_response(model=model,
                                          messages=msg_debug,
                                          available_functions=available_functions,
                                          is_developer_mode=is_developer_mode,
                                          is_enhanced_mode=False,
                                          delete_some_messages=delete_some_messages)

        messages = msg_debug.copy()

        # 若function message不包含报错信息
    # 需要将function message传递给模型
    else:
        print("外部函数已执行完毕，正在解析运行结果...")
        messages.messages_append(function_call_message)
        messages.messages_append(function_response_message)
        messages = get_chat_response(model=model,
                                     messages=messages,
                                     available_functions=available_functions,
                                     is_developer_mode=is_developer_mode,
                                     is_enhanced_mode=is_enhanced_mode,
                                     delete_some_messages=delete_some_messages)

    return messages

def is_text_response_valid(model,
                           messages,
                           text_answer_message,
                           available_functions=None,
                           is_developer_mode=False,
                           is_enhanced_mode=False,
                           delete_some_messages=False,
                           is_task_decomposition=False):
    """
    负责执行文本内容创建审查工作。运行模式可分为快速模式和人工审查模式。在快速模式下，模型将迅速创建文本并保存至msg对象中，\
    而如果是人工审查模式，则需要先经过人工确认，函数才会保存大模型创建的文本内容，并且在这个过程中，\
    也可以选择让模型根据用户输入的修改意见重新修改文本。
    :param model: 必要参数，表示调用的大模型名称
    :param messages: 必要参数，ChatMessages类型对象，用于存储对话消息
    :param text_answer_message: 必要参数，用于表示上层函数创建的一条包含文本内容的message
    :param available_functions: 可选参数，AvailableFunctions类型对象，用于表示开启对话时外部函数基本情况。\
    默认为None，表示没有外部函数
    :param is_developer_mode: 表示是否开启开发者模式，默认为False。\
    开启开发者模式时，会自动添加提示词模板，并且会在每次执行代码前、以及返回结果之后询问用户意见，并会根据用户意见进行修改。
    :param is_enhanced_mode: 可选参数，表示是否开启增强模式，默认为False。\
    开启增强模式时，会自动启动复杂任务拆解流程，并且在进行代码debug时会自动执行deep debug。
    :param delete_some_messages: 可选参数，表示在拼接messages时是否删除中间若干条消息，默认为Fasle。
    :param is_task_decomposition: 可选参数，是否是当前执行任务是否是审查任务拆解结果，默认为False。
    :return: message，拼接了最新大模型回答结果的message
    """

    # 从text_answer_message中获取模型回答结果并打印
    answer_content = text_answer_message["content"]

    print("模型回答：\n")
    display(Markdown(answer_content))

    # 创建指示变量user_input，用于记录用户修改意见，默认为None
    user_input = None

    # 若是开发者模式，或者是增强模式下任务拆解结果，则引导用户对其进行审查
    # 若是开发者模式而非任务拆解
    if not is_task_decomposition and is_developer_mode:
        user_input = input("请问是否记录回答结果（1），\
        或者对当前结果提出修改意见（2），\
        或者重新进行提问（3），\
        或者直接退出对话（4）")
        if user_input == '1':
            # 若记录回答结果，则将其添加入msg对象中
            messages.messages_append(text_answer_message)
            print("本次对话结果已保存")

    # 若是任务拆解
    elif is_task_decomposition:
        user_input = input("请问是否按照该流程执行任务（1），\
        或者对当前执行流程提出修改意见（2），\
        或者重新进行提问（3），\
        或者直接退出对话（4）")
        if user_input == '1':
            # 任务拆解中，如果选择执行该流程
            messages.messages_append(text_answer_message)
            print("好的，即将逐步执行上述流程")
            messages.messages_append({"role": "user", "content": "非常好，请按照该流程逐步执行。"})
            is_task_decomposition = False
            is_enhanced_mode = False
            messages = get_chat_response(model=model,
                                         messages=messages,
                                         available_functions=available_functions,
                                         is_developer_mode=is_developer_mode,
                                         is_enhanced_mode=is_enhanced_mode,
                                         delete_some_messages=delete_some_messages,
                                         is_task_decomposition=is_task_decomposition)

    if user_input != None:
        if user_input == '1':
            pass
        elif user_input == '2':
            new_user_content = input("好的，输入对模型结果的修改意见：")
            print("好的，正在进行修改。")
            # 在messages中暂时记录上一轮回答的内容
            messages.messages_append(text_answer_message)
            # 记录用户提出的修改意见
            messages.messages_append({"role": "user", "content": new_user_content})

            # 再次调用主函数进行回答，为了节省token，可以删除用户修改意见和第一版模型回答结果
            # 因此这里可以设置delete_some_messages=2
            # 此外，这里需要设置is_task_decomposition=is_task_decomposition
            # 当需要修改复杂任务拆解结果时，会自动带入is_task_decomposition=True
            messages = get_chat_response(model=model,
                                         messages=messages,
                                         available_functions=available_functions,
                                         is_developer_mode=is_developer_mode,
                                         is_enhanced_mode=is_enhanced_mode,
                                         delete_some_messages=2,
                                         is_task_decomposition=is_task_decomposition)

        elif user_input == '3':
            new_user_content = input("好的，请重新提出问题：")
            # 修改问题
            messages.messages[-1]["content"] = new_user_content
            # 再次调用主函数进行回答
            messages = get_chat_response(model=model,
                                         messages=messages,
                                         available_functions=available_functions,
                                         is_developer_mode=is_developer_mode,
                                         is_enhanced_mode=is_enhanced_mode,
                                         delete_some_messages=delete_some_messages,
                                         is_task_decomposition=is_task_decomposition)

        else:
            print("好的，已退出当前对话")

    # 若不是开发者模式
    else:
        # 记录返回消息
        messages.messages_append(text_answer_message)

    return messages

if __name__ == '__main__':
    print("this file contains functions to get responses from llm")