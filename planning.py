def add_task_decomposition_prompt(messages):
    """
    当开启增强模式时，任何问题首次尝试作答时都会调用本函数，创建一个包含任务拆解Few-shot的新的message。
    :param model: 必要参数，表示调用的大模型名称
    :param messages: 必要参数，ChatMessages类型对象，用于存储对话消息
    :param available_functions: 可选参数，AvailableFunctions类型对象，用于表示开启对话时外部函数基本情况。\
    默认值为None，表示不存在外部函数。
    :return: task_decomp_few_shot，一个包含任务拆解Few-shot提示示例的message
    """

    # 任务拆解Few-shot
    # 第一个提示示例
    user_question1 = '请问谷歌云邮箱是什么？'
    user_message1_content = "现有用户问题如下：“%s”。为了回答这个问题，总共需要分几步来执行呢？\
    若无需拆分执行步骤，请直接回答原始问题。" % user_question1
    assistant_message1_content = '谷歌云邮箱是指Google Workspace（原G Suite）中的Gmail服务，\
    它是一个安全、智能、易用的电子邮箱，有15GB的免费存储空间，可以直接在电子邮件中接收和存储邮件。\
    Gmail 邮箱会自动过滤垃圾邮件和病毒邮件，并且可以通过电脑或手机等移动设备在任何地方查阅邮件。\
    您可以使用搜索和标签功能来组织邮件，使邮件处理更为高效。'

    # 第二个提示示例
    user_question2 = '请帮我介绍下OpenAI。'
    user_message2_content = "现有用户问题如下：“%s”。为了回答这个问题，总共需要分几步来执行呢？\
    若无需拆分执行步骤，请直接回答原始问题。" % user_question2
    assistant_message2_content = 'OpenAI是一家开发和应用友好人工智能的公司，\
    它的目标是确保人工通用智能（AGI）对所有人都有益，以及随着AGI部署，尽可能多的人都能受益。\
    OpenAI致力在商业利益和人类福祉之间做出正确的平衡，本质上是一家人道主义公司。\
    OpenAI开发了诸如GPT-3这样的先进模型，在自然语言处理等诸多领域表现出色。'

    # 第三个提示示例
    user_question3 = '围绕数据库中的user_payments表，我想要检查该表是否存在缺失值'
    user_message3_content = "现有用户问题如下：“%s”。为了回答这个问题，总共需要分几步来执行呢？\
    若无需拆分执行步骤，请直接回答原始问题。" % user_question3
    assistant_message3_content = '为了检查user_payments数据集是否存在缺失值，我们将执行如下步骤：\
    \n\n步骤1：使用`extract_data`函数将user_payments数据表读取到当前的Python环境中。\
    \n\n步骤2：使用`python_inter`函数执行Python代码检查数据集的缺失值。'

    # 第四个提示示例
    user_question4 = '我想寻找合适的缺失值填补方法，来填补user_payments数据集中的缺失值。'
    user_message4_content = "现有用户问题如下：“%s”。为了回答这个问题，总共需要分几步来执行呢？\
    若无需拆分执行步骤，请直接回答原始问题。" % user_question4
    assistant_message4_content = '为了找到合适的缺失值填充方法，我们需要执行以下三步：\
    \n\n步骤1：分析user_payments数据集中的缺失值情况。通过查看各字段的缺失率和观察缺失值分布，了解其缺失幅度和模式。\
    \n\n步骤2：确定值填补策略。基于观察结果和特定字段的性质确定恰当的填补策略，例如使用众数、中位数、均值或建立模型进行填补等。\
    \n\n步骤3：进行缺失值填补。根据确定的填补策略，执行填补操作，然后验证填补效果。'

    # 在保留原始问题的情况下加入Few-shot
    task_decomp_few_shot = messages.copy()
    task_decomp_few_shot.messages_pop(manual=True, index=-1)
    task_decomp_few_shot.messages_append({"role": "user", "content": user_message1_content})
    task_decomp_few_shot.messages_append({"role": "assistant", "content": assistant_message1_content})
    task_decomp_few_shot.messages_append({"role": "user", "content": user_message2_content})
    task_decomp_few_shot.messages_append({"role": "assistant", "content": assistant_message2_content})
    task_decomp_few_shot.messages_append({"role": "user", "content": user_message3_content})
    task_decomp_few_shot.messages_append({"role": "assistant", "content": assistant_message3_content})
    task_decomp_few_shot.messages_append({"role": "user", "content": user_message4_content})
    task_decomp_few_shot.messages_append({"role": "assistant", "content": assistant_message4_content})

    user_question = messages.history_messages[-1]["content"]

    new_question = "现有用户问题如下：“%s”。为了回答这个问题，总共需要分几步来执行呢？\
    若无需拆分执行步骤，请直接回答原始问题。" % user_question
    question_message = messages.history_messages[-1].copy()
    question_message["content"] = new_question
    task_decomp_few_shot.messages_append(question_message)

    return task_decomp_few_shot


def modify_prompt(messages, action='add', enable_md_output=True, enable_COT=True):
    """
    当开启开发者模式时，会让用户选择是否添加COT提示模板或其他提示模板，并创建一个经过修改的新的message。
    :param messages: 必要参数，ChatMessages类型对象，用于存储对话消息
    :param action: 'add' 或 'remove'，决定是添加还是移除提示
    :param enable_md_output: 是否启用 markdown 格式输出
    :param enable_COT: 是否启用 COT 提示
    :return: messages，一个经过提示词修改的message
    """

    # 思考链提示词模板
    cot_prompt = "请一步步思考并得出结论。"

    # 输出markdown提示词模板
    md_prompt = "任何回答都请以markdown格式进行输出。"

    # 如果是添加提示词
    if action == 'add':
        if enable_COT:
            messages.messages[-1]["content"] += cot_prompt
            messages.history_messages[-1]["content"] += cot_prompt

        if enable_md_output:
            messages.messages[-1]["content"] += md_prompt
            messages.history_messages[-1]["content"] += md_prompt

    # 如果是将指定提示词删除
    elif action == 'remove':
        if enable_md_output:
            messages.messages[-1]["content"] = messages.messages[-1]["content"].replace(md_prompt, "")
            messages.history_messages[-1]["content"] = messages.history_messages[-1]["content"].replace(md_prompt, "")

        if enable_COT:
            messages.messages[-1]["content"] = messages.messages[-1]["content"].replace(cot_prompt, "")
            messages.history_messages[-1]["content"] = messages.history_messages[-1]["content"].replace(cot_prompt, "")

    return messages

if __name__ == '__main__':
    print("this file is the planning module")