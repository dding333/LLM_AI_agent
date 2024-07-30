def add_task_decomposition_prompt(messages):
    """
    When enhanced mode is enabled, this function is called during the first attempt to answer any question, creating a new message containing task decomposition Few-shot examples.
    :param messages: Required parameter, a ChatMessages type object used to store conversation messages.
    :return: task_decomp_few_shot, a message containing task decomposition Few-shot prompt examples.
    """

    # Task decomposition Few-shot
    # First prompt example
    user_question1 = 'What is Google Cloud Email?'
    user_message1_content = "The existing user question is: “%s”. How many steps are needed to answer this question?\
    If no decomposition is required, please directly answer the original question." % user_question1
    assistant_message1_content = 'Google Cloud Email refers to the Gmail service within Google Workspace (formerly G Suite).\
    It is a secure, intelligent, and user-friendly email service with 15GB of free storage, allowing you to receive and store emails directly.\
    Gmail automatically filters spam and virus emails and can be accessed from any location via computer or mobile devices.\
    You can use search and labeling features to organize emails and make email handling more efficient.'

    # Second prompt example
    user_question2 = 'Please introduce OpenAI.'
    user_message2_content = "The existing user question is: “%s”. How many steps are needed to answer this question?\
    If no decomposition is required, please directly answer the original question." % user_question2
    assistant_message2_content = 'OpenAI is a company that develops and applies friendly artificial intelligence.\
    Its goal is to ensure that artificial general intelligence (AGI) benefits everyone and to maximize benefits as AGI is deployed.\
    OpenAI aims to balance commercial interests with human welfare and is essentially a humanitarian company.\
    OpenAI has developed advanced models like GPT-3, which perform exceptionally well in natural language processing and other fields.'

    # Third prompt example
    user_question3 = 'I want to check if there are missing values in the user_payments table in the database.'
    user_message3_content = "The existing user question is: “%s”. How many steps are needed to answer this question?\
    If no decomposition is required, please directly answer the original question." % user_question3
    assistant_message3_content = 'To check if there are missing values in the user_payments dataset, we will perform the following steps:\
    \n\nStep 1: Use the `extract_data` function to load the user_payments table into the current Python environment.\
    \n\nStep 2: Use the `python_inter` function to execute Python code to check for missing values in the dataset.'

    # Fourth prompt example
    user_question4 = 'I want to find a suitable method for imputing missing values in the user_payments dataset.'
    user_message4_content = "The existing user question is: “%s”. How many steps are needed to answer this question?\
    If no decomposition is required, please directly answer the original question." % user_question4
    assistant_message4_content = 'To find a suitable method for imputing missing values, we need to perform the following three steps:\
    \n\nStep 1: Analyze the missing values in the user_payments dataset. By checking the missing rates for each field and observing the distribution of missing values, understand the extent and pattern of missing data.\
    \n\nStep 2: Determine the imputation strategy. Based on the observations and the nature of specific fields, determine an appropriate imputation strategy, such as using mode, median, mean, or building a model for imputation.\
    \n\nStep 3: Perform the imputation. Execute the imputation according to the chosen strategy and verify the imputation results.'

    # Add Few-shot examples while preserving the original question
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

    new_question = "The existing user question is: “%s”. How many steps are needed to answer this question?\
    If no decomposition is required, please directly answer the original question." % user_question
    question_message = messages.history_messages[-1].copy()
    question_message["content"] = new_question
    task_decomp_few_shot.messages_append(question_message)

    return task_decomp_few_shot


def modify_prompt(messages, action='add', enable_md_output=True, enable_COT=True):
    """
    When developer mode is enabled, users can choose whether to add or remove COT prompts or other prompts, and create a new message with modifications.
    :param messages: Required parameter, a ChatMessages type object used to store conversation messages.
    :param action: 'add' or 'remove', determines whether to add or remove prompts.
    :param enable_md_output: Whether to enable markdown format output.
    :param enable_COT: Whether to enable COT prompts.
    :return: messages, a message with prompt modifications.
    """

    # Chain of Thought (COT) prompt template
    cot_prompt = "Please think step by step and draw a conclusion."

    # Markdown output prompt template
    md_prompt = "Please format all responses in markdown."

    # If adding prompts
    if action == 'add':
        if enable_COT:
            messages.messages[-1]["content"] += cot_prompt
            messages.history_messages[-1]["content"] += cot_prompt

        if enable_md_output:
            messages.messages[-1]["content"] += md_prompt
            messages.history_messages[-1]["content"] += md_prompt

    # If removing specified prompts
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
