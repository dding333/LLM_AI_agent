from planning import *
import openai
import time
import json
from IPython.display import display, Code, Markdown
from openai.error import APIConnectionError
from gptLearning import *


def function_to_call(available_functions, function_call_message):
    """
    Based on a function call message `function_call_message`, return a message with the function's execution result `function_response_messages`.
    :param available_functions: Required parameter, an AvailableFunctions object that describes the basic information of the current external functions.
    :param function_call_message: Required parameter, a message representing an external function call.
    :return: `function_response_messages`, a message consisting of the external function's execution result.
    """

    # Get the name of the function to be called from the function call message
    function_name = function_call_message["function_call"]["name"]

    # Get the corresponding external function object based on the function name
    function_to_call = available_functions.functions_dic[function_name]

    # Extract the function parameters from the function call message
    # This includes the SQL or Python code written by the large model
    function_args = json.loads(function_call_message["function_call"]["arguments"])

    # Pass the parameters to the external function and run it
    try:
        # Add the global variables from the current operation space to the external function
        function_args['g'] = globals()

        # Run the external function
        function_response = function_to_call(**function_args)

    # If the external function encounters an error, extract the error message
    except Exception as e:
        function_response = "The function encountered an error as follows:" + str(e)
        # print(function_response)

    # Create the function_response_messages
    # This message includes information about the successful execution or error of the external function

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
    Responsible for calling the Chat model and obtaining the model's response function, and it allows for a temporary pause of 1 minute if a Rate limit issue occurs when calling the GPT model.\
    Additionally, for unclear questions, it will prompt the user to modify the input prompt to obtain better model results.
    :param model: Required parameter indicating the name of the large model to be called.
    :param messages: Required parameter, a ChatMessages type object used to store conversation messages.
    :param available_functions: Optional parameter, an AvailableFunctions type object representing the basic information of external functions during the conversation.\
    Defaults to None, indicating no external functions.
    :param is_developer_mode: Indicates whether developer mode is enabled, default is False.\
    When developer mode is enabled, prompt templates are automatically added, and user feedback is solicited before executing code and after returning results, with modifications made based on user feedback.
    :param is_enhanced_mode: Optional parameter indicating whether enhanced mode is enabled, default is False.\
    When enhanced mode is enabled, a complex task decomposition process is automatically initiated, and deep debugging is automatically performed during code debugging.
    :return: Returns the response message from the model.
    """

    # If developer mode is enabled, modify the prompt, adding prompts on the first run
    if is_developer_mode:
        messages = modify_prompt(messages, action='add')

    # If enhanced mode is enabled, add complex task decomposition prompts
    if is_enhanced_mode:
        messages = add_task_decomposition_prompt(messages)

    # To account for potential communication errors, loop to call the Chat model
    while True:
        try:
            # If no external functions exist
            if available_functions is None:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages.messages)

            # If external functions exist, obtain functions and function_call parameters from the AvailableFunctions object
            else:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages.messages,
                    functions=available_functions.functions,
                    function_call=available_functions.function_call
                )
            break  # Exit the loop if response is successfully obtained

        except APIConnectionError as e:
            # APIConnectionError usually indicates unclear user requirements causing failure to return results
            # If enhanced mode is enabled, prompt the user to rephrase their query
            if is_enhanced_mode:
                # Create a temporary message list
                msg_temp = messages.copy()
                # Get the user's question
                question = msg_temp.messages[-1]["content"]
                # Prompt the user to modify their query
                new_prompt = "The user's question is: %s. This question is somewhat complex, and the user's intent is unclear.\
                Please write a prompt to guide the user to rephrase their question." % question
                # Modify msg_temp and rephrase the query
                try:
                    msg_temp.messages[-1]["content"] = new_prompt
                    # Modify the user's question and ask again
                    response = openai.ChatCompletion.create(
                        model=model,
                        messages=msg_temp.messages)

                    # Print the GPT prompt modification suggestion
                    display(Markdown(response["choices"][0]["message"]["content"]))
                    # Guide the user to rephrase the question or exit
                    user_input = input("Please re-enter your question, enter 'exit' to exit the current conversation")
                    if user_input == "exit":
                        print("The current model cannot return results, exiting")
                        return None
                    else:
                        # Modify the original question
                        messages.history_messages[-1]["content"] = user_input

                        # Re-ask the question
                        response_message = get_gpt_response(model=model,
                                                            messages=messages,
                                                            available_functions=available_functions,
                                                            is_developer_mode=is_developer_mode,
                                                            is_enhanced_mode=is_enhanced_mode)

                        return response_message
                # If a connection error occurs while prompting the user to modify the query, pause for 1 minute and continue the while loop
                except APIConnectionError as e:
                    print(f"Encountered a connection issue: {str(e)}")
                    print("Due to rate limit, pausing for 1 minute and will continue running after 1 minute...")
                    time.sleep(60)  # Wait for 1 minute
                    print("Waited 60 seconds, starting a new round of questions and answers...")

            # If enhanced mode is not enabled
            else:
                # Print the core error information
                print(f"Encountered a connection issue: {str(e)}")
                # If developer mode is enabled
                if is_developer_mode:
                    # Choose to wait, change model, or exit with an error
                    user_input = input("Please choose to wait 1 minute (1), change model (2), or exit with an error (3)")
                    if user_input == '1':
                        print("Okay, will wait 1 minute before continuing...")
                        time.sleep(60)  # Wait for 1 minute
                        print("Waited 60 seconds, starting a new round of questions and answers...")
                    elif user_input == '2':
                        model = input("Okay, please enter the new model name")
                    else:
                        # if modify:
                        #     messages = modify_prompt(messages, action='remove', enable_md_output=md_output,
                        #                              enable_COT=COT)
                        raise e  # If the user chooses to exit, restore prompts and raise the exception
                # If not in developer mode
                else:
                    print("Due to rate limit, pausing for 1 minute and will continue running after 1 minute...")
                    time.sleep(60)  # Wait for 1 minute
                    print("Waited 60 seconds, starting a new round of questions and answers...")

    # Restore the original message object
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
    Responsible for executing a complete conversation session. Note that a conversation may involve multiple calls to the large model, 
    and this function serves as the main function to complete one conversation session.\
    The last message in the input messages must be a message that can initiate a conversation.\
    This function calls get_gpt_response to obtain the model's output results and then processes the output based on whether it is text or code results,\
    by flexibly calling different functions for post-processing.\
    :param model: Required parameter indicating the name of the large model to be called.
    :param messages: Required parameter, a ChatMessages type object used to store conversation messages.
    :param available_functions: Optional parameter, an AvailableFunctions type object representing the basic information of external functions during the conversation.\
    Defaults to None, indicating no external functions.
    :param is_developer_mode: Indicates whether developer mode is enabled, default is False.\
    When developer mode is enabled, prompt templates are automatically added, and user feedback is solicited before executing code and after returning results, with modifications made based on user feedback.
    :param is_enhanced_mode: Optional parameter indicating whether enhanced mode is enabled, default is False.\
    When enhanced mode is enabled, a complex task decomposition process is automatically initiated, and deep debugging is automatically performed during code debugging.
    :param delete_some_messages: Optional parameter indicating whether to delete several intermediate messages when concatenating messages, default is False.
    :param is_task_decomposition: Optional parameter indicating whether the current task is task decomposition review, default is False.
    :return: Messages concatenating the final results of this Q&A session.
    """

    # Only when modifying the complex task decomposition result will is_task_decomposition=True occur
    # When is_task_decomposition=True, response_message will not be recreated
    if not is_task_decomposition:
        # First obtain the result of a single large model call
        # At this point, response_message is the message returned by the large model call
        response_message = get_gpt_response(model=model,
                                            messages=messages,
                                            available_functions=available_functions,
                                            is_developer_mode=is_developer_mode,
                                            is_enhanced_mode=is_enhanced_mode)

    # Complex condition check, if is_task_decomposition = True,
    # or if enhanced mode is enabled and the task involves function response
    # (Note that when is_task_decomposition = True, there is no response_message object)
    if is_task_decomposition or (is_enhanced_mode and response_message.get("function_call")):
        # Set is_task_decomposition to True, indicating that the current task is task decomposition
        is_task_decomposition = True
        # In task decomposition, the task decomposition prompt is named text_response_messages
        task_decomp_few_shot = add_task_decomposition_prompt(messages)
        # print("Performing task decomposition, please wait...")
        # Also update response_message; now response_message is the response after task decomposition
        response_message = get_gpt_response(model=model,
                                            messages=task_decomp_few_shot,
                                            available_functions=available_functions,
                                            is_developer_mode=is_developer_mode,
                                            is_enhanced_mode=is_enhanced_mode)
        # If the task decomposition prompt is ineffective, response_message might create another function call message
        if response_message.get("function_call"):
            print("The current task does not require decomposition and can be executed directly.")

    # If the current call is generated by modifying conversation requirements, delete several messages from the original messages
    # Note that deleting intermediate messages must be done after creating the new response_message
    if delete_some_messages:
        for i in range(delete_some_messages):
            messages.messages_pop(manual=True, index=-1)

    # Note that at this point, there will definitely be a response_message
    # Next, based on the type of response_message, execute different processes
    # If it is a text response task (including both standard text responses and complex task decomposition reviews, the same code can be used for both)
    if not response_message.get("function_call"):
        # Save the message as text_answer_message
        text_answer_message = response_message
        # Review the text content using is_text_response_valid
        messages = is_text_response_valid(model=model,
                                          messages=messages,
                                          text_answer_message=text_answer_message,
                                          available_functions=available_functions,
                                          is_developer_mode=is_developer_mode,
                                          is_enhanced_mode=is_enhanced_mode,
                                          delete_some_messages=delete_some_messages,
                                          is_task_decomposition=is_task_decomposition)

    # If it is a function response task
    elif response_message.get("function_call"):
        # Create a function_call_message to call the external function
        # In the current Agent, function_call_message is a JSON object containing SQL code or Python code
        function_call_message = response_message
        # Pass function_call_message to the code review and execution function is_code_response_valid
        # and finally obtain the Q&A result after the external function execution
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
    Responsible for executing an external function call completely. The last message in the input `messages` must be a message containing a function call.\
    The function's final task is to pass the code from the function call message to the external function and complete the code execution, supporting both interactive and automated code execution modes.\
    After obtaining a function message containing the result of the external function execution, it will be further processed by the check_get_final_function_response function,\
    which will convert the function message into an assistant message and complete the conversation.
    :param model: Required parameter indicating the name of the large model to be called.
    :param messages: Required parameter, a ChatMessages type object used to store conversation messages.
    :param function_call_message: Required parameter representing a message containing a function call created by the upper-level function.
    :param available_functions: Optional parameter, an AvailableFunctions type object representing the basic information of external functions during the conversation.\
    Defaults to None, indicating no external functions.
    :param is_developer_mode: Indicates whether developer mode is enabled, default is False.\
    When developer mode is enabled, prompt templates are automatically added, and user feedback is solicited before executing code and after returning results, with modifications made based on user feedback.
    :param is_enhanced_mode: Optional parameter indicating whether enhanced mode is enabled, default is False.\
    When enhanced mode is enabled, a complex task decomposition process is automatically initiated, and deep debugging is automatically performed during code debugging.
    :param delete_some_messages: Optional parameter indicating whether to delete several intermediate messages when concatenating messages, default is False.
    :return: Message containing the latest result from the large model's response.
    """

    # Prepare for printing and modifying code (adding image creation code for the family part)
    # Create a JSON string message object
    code_json_str = function_call_message["function_call"]["arguments"]
    # Convert JSON to a dictionary
    try:
        code_dict = json.loads(code_json_str)
    except Exception as e:
        print("JSON parsing error, recreating code...")
        # Recursively call the upper-level function get_chat_response and return the final message result
        # Note that if the upper-level function creates another function_call_message
        # it will call is_code_response_valid again without needing to be executed again in the current function
        messages = get_chat_response(model=model,
                                     messages=messages,
                                     available_functions=available_functions,
                                     is_developer_mode=is_developer_mode,
                                     is_enhanced_mode=is_enhanced_mode,
                                     delete_some_messages=delete_some_messages)

        return messages

    # If JSON is successfully converted to a dictionary, continue executing the following code
    # Create a helper function convert_to_markdown to assist in printing code results
    def convert_to_markdown(code, language):
        return f"```{language}\n{code}\n```"

    # Extract code part parameters
    # If it's SQL, print code in SQL format in Markdown
    if code_dict.get('sql_query'):
        code = code_dict['sql_query']
        markdown_code = convert_to_markdown(code, 'sql')
        print("The following code will be executed:")

    # If it's Python, print code in Python format in Markdown
    elif code_dict.get('py_code'):
        code = code_dict['py_code']
        markdown_code = convert_to_markdown(code, 'python')
        print("The following code will be executed:")

    else:
        markdown_code = code_dict

    display(Markdown(markdown_code))

    # If in developer mode, prompt the user to review the code before running it
    if is_developer_mode:
        user_input = input("Run code directly (1) or provide feedback and let the model modify the code before running it (2)?")
        if user_input == '1':
            print("Okay, running the code, please wait...")

        else:
            modify_input = input("Okay, please provide modification feedback:")
            # Record the code currently created by the model
            messages.messages_append(function_call_message)
            # Record the modification feedback
            messages.messages_append({"role": "user", "content": modify_input})

            # Call the get_chat_response function and retrieve the result again
            # Note that delete_some_messages=2 is required here to delete intermediate conversation results to save tokens
            messages = get_chat_response(model=model,
                                         messages=messages,
                                         available_functions=available_functions,
                                         is_developer_mode=is_developer_mode,
                                         is_enhanced_mode=is_enhanced_mode,
                                         delete_some_messages=2)

            return messages

    # If not in developer mode, or if user_input == '1' in developer mode
    # Call the function_to_call function to get the final result of the external function execution
    # In the current Agent, the external function result is either SQL or Python execution result, or code execution error result
    function_response_message = function_to_call(available_functions=available_functions,
                                                 function_call_message=function_call_message)

    # Pass function_response_message to check_get_final_function_response for review
    messages = check_get_final_function_response(model=model,
                                                 messages=messages,
                                                 function_call_message=function_call_message,
                                                 function_response_message=function_response_message,
                                                 available_functions=available_functions,
                                                 is_developer_mode=is_developer_mode,
                                                 is_enhanced_mode=is_enhanced_mode,
                                                 delete_some_messages=delete_some_messages)

    return messages


# Determine if the code output meets the requirements. Input is the function response message, output is a message based on the external function's execution result.
def check_get_final_function_response(model,
                                      messages,
                                      function_call_message,
                                      function_response_message,
                                      available_functions=None,
                                      is_developer_mode=False,
                                      is_enhanced_mode=False,
                                      delete_some_messages=False):
    """
    Responsible for reviewing the results of external function execution. If the function_response_message does not contain any error information,\
    it will be appended to the message and passed to the get_chat_response function to obtain the next round of conversation results. If error information is present in the function_response_message,\
    automatic debug mode will be enabled. This function will use a method similar to Autogen, replicating multiple Agents, and performing debugging through their interactions.
    :param model: Required parameter indicating the name of the large model to be called.
    :param messages: Required parameter, a ChatMessages type object used to store conversation messages.
    :param function_call_message: Required parameter representing a message containing a function call created by the upper-level function.
    :param function_response_message: Required parameter representing a message containing the result of the external function's execution created by the upper-level function.
    :param available_functions: Optional parameter, an AvailableFunctions type object representing the basic information of external functions during the conversation.\
    Defaults to None, indicating no external functions.
    :param is_developer_mode: Indicates whether developer mode is enabled, default is False.\
    When developer mode is enabled, prompt templates are automatically added, and user feedback is solicited before executing code and after returning results, with modifications made based on user feedback.
    :param is_enhanced_mode: Optional parameter indicating whether enhanced mode is enabled, default is False.\
    When enhanced mode is enabled, a complex task decomposition process is automatically initiated, and deep debugging is automatically performed during code debugging.
    :param delete_some_messages: Optional parameter indicating whether to delete several intermediate messages when concatenating messages, default is False.
    :return: Message containing the latest result from the large model's response.
    """

    # Get the content of the external function's execution result
    fun_res_content = function_response_message["content"]

    # If function_response contains errors
    if "error" in fun_res_content:
        # Print error information
        print(fun_res_content)

        # Choose efficient debug or deep debug based on whether enhanced mode is enabled
        # The difference between efficient debug and deep debug is only in the prompt content and process
        # Efficient debug includes only one prompt and requires only one large model call to complete automatic debugging
        # Deep debug includes three prompts and requires three large model calls for deep summarization and debugging
        # Create different prompts for efficient and deep debugging
        if not is_enhanced_mode:
            # Execute efficient debug
            display(Markdown("**Executing efficient debug, instantiating Efficient Debug Agent...**"))
            debug_prompt_list = ['Your code has errors. Please modify the code according to the error information and re-execute.']

        else:
            # Execute deep debug
            display(Markdown(
                "**Executing deep debug. This debugging process will automatically perform multiple rounds of conversation. Please be patient. Instantiating Deep Debug Agent...**"))
            display(Markdown("**Instantiating deep debug Agent...**"))
            debug_prompt_list = ["The previous code execution resulted in an error. Where do you think the code was written incorrectly?",
                                 "Okay. Based on your analysis, theoretically, how should this error be resolved?",
                                 "Very well. Next, please write and run the corresponding code according to your logic."]

        # Copy the messages, equivalent to creating a new Agent for debugging
        # Note that at this point the last message in messages is a user message, not any function call-related message
        msg_debug = messages.copy()
        # Append the function_call_message
        # The current function_call_message contains the erroneous code
        msg_debug.messages_append(function_call_message)
        # Append the function_response_message
        # The current function_response_message contains the error message of the code execution
        msg_debug.messages_append(function_response_message)

        # Sequentially input the debug prompts to guide the large model to complete the debugging
        for debug_prompt in debug_prompt_list:
            msg_debug.messages_append({"role": "user", "content": debug_prompt})
            display(Markdown("**From Debug Agent:**"))
            display(Markdown(debug_prompt))

            # Call get_chat_response again. Under the current debug prompt, get_chat_response will return modification suggestions or modified code
            # Print the prompt information
            display(Markdown("**From MateGen:**"))
            msg_debug = get_chat_response(model=model,
                                          messages=msg_debug,
                                          available_functions=available_functions,
                                          is_developer_mode=is_developer_mode,
                                          is_enhanced_mode=False,
                                          delete_some_messages=delete_some_messages)

        messages = msg_debug.copy()

    # If function message does not contain error information
    # Pass the function message to the model
    else:
        print("External function execution complete. Parsing the results...")
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
    Responsible for reviewing the creation of text content. The running mode can be either fast mode or manual review mode. In fast mode, the model quickly creates text and saves it to the msg object.\
    In manual review mode, human confirmation is required before the function saves the text content created by the large model. During this process, the model can also be instructed to modify the text based on user input.
    :param model: Required parameter, indicating the name of the large model being called.
    :param messages: Required parameter, a ChatMessages type object used to store conversation messages.
    :param text_answer_message: Required parameter, representing a message containing text content created by the upper-level function.
    :param available_functions: Optional parameter, an AvailableFunctions type object representing the basic information of external functions during the conversation.\
    Defaults to None, indicating no external functions.
    :param is_developer_mode: Indicates whether developer mode is enabled, default is False.\
    When developer mode is enabled, prompt templates are automatically added, and user feedback is solicited before executing code and after returning results, with modifications made based on user feedback.
    :param is_enhanced_mode: Optional parameter indicating whether enhanced mode is enabled, default is False.\
    When enhanced mode is enabled, a complex task decomposition process is automatically initiated, and deep debugging is automatically performed during code debugging.
    :param delete_some_messages: Optional parameter indicating whether to delete several intermediate messages when concatenating messages, default is False.
    :param is_task_decomposition: Optional parameter indicating whether the current task is a review of task decomposition results, default is False.
    :return: Message containing the latest result from the large model's response.
    """

    # Retrieve and print the model's answer from text_answer_message
    answer_content = text_answer_message["content"]

    print("Model's Answer:\n")
    display(Markdown(answer_content))

    # Create a variable user_input to record user feedback, default is None
    user_input = None

    # If in developer mode or reviewing task decomposition results
    # If in developer mode but not task decomposition
    if not is_task_decomposition and is_developer_mode:
        user_input = input("Would you like to record the answer (1),\
        provide modification feedback (2),\
        ask a new question (3),\
        or exit the conversation (4)?")
        if user_input == '1':
            # If recording the answer, append it to the msg object
            messages.messages_append(text_answer_message)
            print("The conversation result has been saved.")

    # If task decomposition
    elif is_task_decomposition:
        user_input = input("Would you like to execute the task according to this process (1),\
        provide modification feedback on the current process (2),\
        ask a new question (3),\
        or exit the conversation (4)?")
        if user_input == '1':
            # In task decomposition, if choosing to execute the process
            messages.messages_append(text_answer_message)
            print("Okay, proceeding to execute the process step by step.")
            messages.messages_append({"role": "user", "content": "Very well, please execute the process step by step."})
            is_task_decomposition = False
            is_enhanced_mode = False
            messages = get_chat_response(model=model,
                                         messages=messages,
                                         available_functions=available_functions,
                                         is_developer_mode=is_developer_mode,
                                         is_enhanced_mode=is_enhanced_mode,
                                         delete_some_messages=delete_some_messages,
                                         is_task_decomposition=is_task_decomposition)

    if user_input is not None:
        if user_input == '1':
            pass
        elif user_input == '2':
            new_user_content = input("Okay, enter your modification feedback for the model's result:")
            print("Okay, making modifications.")
            # Temporarily record the previous answer content in messages
            messages.messages_append(text_answer_message)
            # Record user modification feedback
            messages.messages_append({"role": "user", "content": new_user_content})

            # Call the main function again for a response. To save tokens, the user modification feedback and the first version of the model's answer can be deleted
            # Therefore, delete_some_messages=2 is set here
            # Additionally, is_task_decomposition=is_task_decomposition is set here
            # When modifying complex task decomposition results, is_task_decomposition=True will be automatically included
            messages = get_chat_response(model=model,
                                         messages=messages,
                                         available_functions=available_functions,
                                         is_developer_mode=is_developer_mode,
                                         is_enhanced_mode=is_enhanced_mode,
                                         delete_some_messages=2,
                                         is_task_decomposition=is_task_decomposition)

        elif user_input == '3':
            new_user_content = input("Okay, please ask a new question:")
            # Modify the question
            messages.messages[-1]["content"] = new_user_content
            # Call the main function again for a response
            messages = get_chat_response(model=model,
                                         messages=messages,
                                         available_functions=available_functions,
                                         is_developer_mode=is_developer_mode,
                                         is_enhanced_mode=is_enhanced_mode,
                                         delete_some_messages=delete_some_messages,
                                         is_task_decomposition=is_task_decomposition)

        else:
            print("Okay, exiting the current conversation.")

    # If not in developer mode
    else:
        # Record the returned message
        messages.messages_append(text_answer_message)

    return messages


if __name__ == '__main__':
    print("this file contains functions to get responses from llm")
