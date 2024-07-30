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
    # Decode the JSON string
    data = json.loads(json_str)

    # Extract and return the value of 'sql_query'
    return data.get('sql_query', None)


def check_code_run(messages,
                   functions_list=None,
                   model="gpt-4-0613",
                   function_call="auto",
                   auto_run=True):
    """
    A Chat model that can automatically execute external function calls, designed for the code interpreter construction process.
    The auto_run parameter determines whether to automatically execute the code.
    
    :param messages: Required parameter, a dictionary type object representing the messages input to the Chat model.
    :param functions_list: Optional parameter, default is None. Can be set to a list object containing all external functions.
    :param model: Chat model, optional parameter. Default model is gpt-4.
    :param function_call: Determines whether to call external functions automatically. This parameter only takes effect if external functions exist.
    :param auto_run: Determines whether to automatically proceed with the Second Response when calling external functions. This parameter only applies if external functions are present.
    :return: The output result from the Chat model.
    """

    # If there are no external functions, perform a regular conversation task
    if functions_list is None:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
        )
        response_message = response["choices"][0]["message"]
        final_response = response_message["content"]

    # If there are external functions, select and call them as needed
    else:
        print("Calling external function to answer the question")
        # Create functions object
        functions = auto_functions(functions_list)
        # Create external functions dictionary
        available_functions = {func.__name__: func for func in functions_list}

        # First response
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            functions=functions,
            function_call=function_call)
        response_message = response["choices"][0]["message"]

        # Check if the response includes a function_call to determine if an external function needs to be called
        if response_message.get("function_call"):
            # External function needs to be called
            # Get function name
            function_name = response_message["function_call"]["name"]
            # Get function object
            function_to_call = available_functions[function_name]
            # Get function arguments
            function_args = json.loads(response_message["function_call"]["arguments"])
            if not auto_run:
                sql_query = extract_sql(response_message["function_call"]["arguments"])

                res = input(f'About to execute the following code: {sql_query}. Confirm and continue execution (1), or exit this run (2): ')
                if res == '2':
                    print("Execution terminated")
                    return None
                else:
                    print("Executing code, please wait...")

            # Input function arguments into the function and get the function's result
            function_response = function_to_call(**function_args)

            # Append first response message to messages
            messages.append(response_message)
            # Append function output result to messages
            messages.append(
                {
                    "role": "function",
                    "name": function_name,
                    "content": function_response,
                }
            )
            # Call the model for the second time
            second_response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
            )
            # Get the final result
            final_response = second_response["choices"][0]["message"]["content"]
        else:
            final_response = response_message["content"]

    del messages

    return final_response

def auto_functions(functions_list):
    """
    Function for generating the `functions` parameter for the Chat model.
    
    :param functions_list: A list containing one or more function objects.
    :return: `functions` object that meets the requirements of the Chat model's `functions` parameter.
    """
    def functions_generate(functions_list):
        # Create an empty list to hold the description dictionaries for each function
        functions = []
        
        def chen_ming_algorithm(data):
            """
            Chen Ming algorithm function, defines a special data set computation process.
            :param data: Required parameter, the data table for computation, represented as a string.
            :return: The result of Chen Ming algorithm computation, returned as a JSON-formatted DataFrame object.
            """
            df_new = pd.read_json(data)
            res = np.sum(df_new, axis=1) - 1
            return res.to_json(orient='records')
        
        chen_ming_function_description = inspect.getdoc(chen_ming_algorithm)
        chen_ming_function_name = chen_ming_algorithm.__name__
        
        chen_ming_function = {
            "name": "chen_ming_algorithm",
            "description": "Function for executing Chen Ming algorithm, defines a special data set computation process.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "string",
                        "description": "Data set for executing Chen Ming algorithm"
                    },
                },
                "required": ["data"],
            },
        }

        # Loop through each external function
        for function in functions_list:
            # Read the function object's description
            function_description = inspect.getdoc(function)
            # Read the function's name as a string
            function_name = function.__name__

            user_message1 = (
                f'Here is a function description: {chen_ming_function_description}. '
                f'Based on this function description, please create a function object to describe the basic information of this function. '
                f'This function object is a JSON-formatted dictionary with the following 5 requirements: '
                f'1. The dictionary has three key-value pairs; '
                f'2. The first key-value pair has the key "name" with the value being the function\'s name: {chen_ming_function_name}, which is also a string; '
                f'3. The second key-value pair has the key "description" with the value being the function\'s description, which is also a string; '
                f'4. The third key-value pair has the key "parameters" with the value being a JSON Schema object describing the function\'s parameter input specification; '
                f'5. The output must be a JSON-formatted dictionary, and no additional pre- or post-explanatory statements are needed.'
            )
            
            assistant_message1 = json.dumps(chen_ming_function)
            
            user_prompt = (
                f'Now there is another function with the name: {function_name}; function description: {function_description}; '
                f'Please create a similar function object for the current function in the same format.'
            )

            response = openai.ChatCompletion.create(
                model="gpt-4-0613",
                messages=[
                    {"role": "user", "name":"example_user", "content": user_message1},
                    {"role": "assistant", "name":"example_assistant", "content": assistant_message1},
                    {"role": "user", "name":"example_user", "content": user_prompt}
                ]
            )
            functions.append(json.loads(response.choices[0].message['content']))
        return functions
    
    max_attempts = 3
    attempts = 0

    while attempts < max_attempts:
        try:
            functions = functions_generate(functions_list)
            break  # Exit loop if code executes successfully
        except Exception as e:
            attempts += 1  # Increment attempt count
            print("Error occurred:", e)
            print("Due to model rate limit error, pausing for 1 minute. Retry after 1 minute.")
            if attempts == max_attempts:
                print("Maximum attempts reached. Program terminating.")
                raise  # Re-raise the last exception
            else:
                print("Retrying...")
    return functions




def run_conversation(messages, functions_list=None, model="gpt-4-0613", function_call="auto"):
    """
    Chat model that can automatically execute external function calls.
    
    :param messages: Required parameter, a dictionary type object for the `messages` parameter in the Chat model.
    :param functions_list: Optional parameter, default is None, can be set to a list object containing all external functions.
    :param model: Chat model, optional parameter, default model is gpt-4.
    :param function_call: Determines whether to automatically call external functions.
    :return: The output result from the Chat model.
    """
    
    # If there are no external functions, perform a standard conversation task
    if functions_list is None:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
        )
        response_message = response["choices"][0]["message"]
        final_response = response_message["content"]
        
    # If there are external functions, select and use them flexibly to respond
    else:
        # Create functions object
        functions = auto_functions(functions_list)
        # Create dictionary of available functions
        available_functions = {func.__name__: func for func in functions_list}

        # First response
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            functions=functions,
            function_call=function_call
        )
        response_message = response["choices"][0]["message"]

        # Check if the response includes `function_call`, indicating if an external function needs to be called
        if response_message.get("function_call"):
            # Need to call an external function
            # Get function name
            function_name = response_message["function_call"]["name"]
            # Get function object
            function_to_call = available_functions[function_name]
            # Get function arguments
            function_args = json.loads(response_message["function_call"]["arguments"])
            # Pass function arguments to the function to get the function result
            function_response = function_to_call(**function_args)

            # Append the first response message to `messages`
            messages.append(response_message)  
            # Append the function output result to `messages`
            messages.append(
                {
                    "role": "function",
                    "name": function_name,
                    "content": function_response,
                }
            )  
            # Second call to the model
            second_response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
            )  
            # Get the final result
            final_response = second_response["choices"][0]["message"]["content"]
        else:
            final_response = response_message["content"]
            
    del messages
    
    return final_response



def chat_with_model(functions_list=None, 
                    prompt="Hello there", 
                    model="gpt-4-0613", 
                    system_message=[{"role": "system", "content": "You are a helpful assistant."}]):
    
    messages = system_message
    messages.append({"role": "user", "content": prompt})
    
    while True:           
        answer = run_conversation(messages=messages, 
                                    functions_list=functions_list, 
                                    model=model)
        
        print(f"Model Response: {answer}")

        # Ask the user if they have any more questions
        user_input = input("Do you have any other questions? (Type 'exit' to end the conversation): ")
        if user_input.lower() == "exit":
            del messages
            break

        # Record the user's response
        messages.append({"role": "user", "content": user_input})

        
def extract_function_code(s, detail=0, tested=False, g=globals()):
    """
    Extracts a function from a given string and executes its contents. Optionally, it can print function information and choose where to save the code.
    """
    def extract_code(s):
        """
        If the input string `s` is a Markdown-formatted string containing Python code, extract the code part.
        Otherwise, return the original string.

        Parameters:
        s: The input string.

        Returns:
        Extracted code part or the original string.
        """
        # Check if the string is in Markdown format
        if '```python' in s or 'Python' in s or 'PYTHON' in s:
            # Find the start and end positions of the code block
            code_start = s.find('def')
            code_end = s.find('```\n', code_start)
            # Extract the code part
            code = s[code_start:code_end]
        else:
            # If the string is not Markdown format, return the original string
            code = s

        return code
    
    # Extract the code string
    code = extract_code(s)
    
    # Extract the function name
    match = re.search(r'def (\w+)', code)
    function_name = match.group(1)
    
    # Create a directory with the function name inside the 'untested functions' folder
    directory = f'./functions/untested functions/{function_name}'
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # Save the function to a local file
    if not tested:
        with open(f'./functions/untested functions/{function_name}/{function_name}_module.py', 'w', encoding='utf-8') as f:
            f.write(code)
    else:
        # Move the function folder to the 'tested functions' folder
        remove_to_tested(function_name)
        with open(f'./functions/tested functions/{function_name}/{function_name}_module.py', 'w', encoding='utf-8') as f:
            f.write(code)
    
    # Execute the function
    try:
        exec(code, g)
    except Exception as e:
        print("An error occurred while executing the code:")
        print(e)
    
    # Print the function name
    if detail == 0:
        print(f"The function name is: {function_name}")
    
    if detail == 1:
        if not tested:
            with open(f'./functions/untested functions/{function_name}/{function_name}_module.py', 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            with open(f'./functions/tested functions/{function_name}/{function_name}_module.py', 'r', encoding='utf-8') as f:   
                content = f.read()
                
        print(content)
        
    return function_name

        
def remove_to_tested(function_name):
    """
    Move the function's folder from the 'untested' folder to the 'tested' folder.\
    Completing the move indicates that the function has passed the tests and can be used. At this point, the function's source code should be written to `gptLearning.py` for easy future reference.
    """

    # Write the function code to the gptLearning.py file
    with open(f'./functions/untested functions/{function_name}/{function_name}_module.py', encoding='utf-8') as f:
        function_code = f.read()

    with open('gptLearning.py', 'a', encoding='utf-8') as f:
        f.write("\n" + function_code)

    # Source directory path
    src_dir = f'./functions/untested functions/{function_name}'

    # Destination directory path
    dst_dir = f'./functions/tested functions/{function_name}'

    # Move the folder
    shutil.move(src_dir, dst_dir)


def show_functions(tested=False, if_print=False):
    """
    Print all functions in the 'tested' or 'untested' folder.
    """
    current_directory = os.getcwd()
    if not tested:
        directory = current_directory + '\\functions\\untested functions'
    else:
        directory = current_directory + '\\functions\\tested functions'

    files_and_directories = os.listdir(directory)
    # Filter results to keep only .py files and non-__pycache__ directories
    files_and_directories = [name for name in files_and_directories if (os.path.splitext(name)[1] == '.py' or os.path.isdir(os.path.join(directory, name))) and name != "__pycache__"]
    
    if if_print:
        for name in files_and_directories:
            print(name)
    
    return files_and_directories


def code_generate(req, few_shot='all', model='gpt-4-0613', g=globals(), detail=0):
    """
    Automatically creates a function that can be called externally using Function Calling. 
    It translates user requirements into code that can be directly called by the Chat model.
    :param req: Required parameter, a string representing the user's input requirement.
    :param few_shot: Optional parameter, default is 'all'. Describes the selection scheme for Few-shot prompt examples. 
                     When 'all' is provided, it means all tested functions in the current external function library are used as Few-shot. 
                     If a list of function names is provided, those functions are used as Few-shot examples.
    :param model: Optional parameter, specifies the Chat model to use, default is 'gpt-4-0613'.
    :param g: Optional parameter, specifies the scope for the extract_function_code function, default is globals(), i.e., effective in the current operational space.
    :param detail: Optional parameter, default is 0. It can also be 1, indicating whether to print details of the newly created external function in the extract_function_code function.
    :return: The name of the newly created function. Note that the function will also be defined in the current operational space and can be called directly afterwards.
    """
    
    # Extract the function names for the Few-shot examples
    if few_shot == 'all':
        few_shot_functions_name = show_functions(tested=True)
    elif isinstance(few_shot, list):
        few_shot_functions_name = few_shot
    
    # Read system prompts for each stage
    with open('./functions/tested functions/system_messages.json', 'r') as f:
        system_messages = json.load(f)
        
    # Message objects for different stages
    few_shot_messages_CM = []
    few_shot_messages_CD = []
    few_shot_messages = []
    
    # Save the initial system message
    few_shot_messages_CD += system_messages["system_message_CD"]
    few_shot_messages_CM += system_messages["system_message_CM"]
    few_shot_messages += system_messages["system_message"]

    # Create messages for different stages
    for function_name in few_shot_functions_name:
        with open(f'./functions/tested functions/{function_name}/{function_name}_prompt.json', 'r') as f:
            msg = json.load(f)
        few_shot_messages_CD += msg["stage1_CD"]
        few_shot_messages_CM += msg["stage1_CM"]
        few_shot_messages += msg['stage2']
        
    # Read user requirement as the first stage CD user content
    new_req_CD_input = req
    few_shot_messages_CD.append({"role": "user", "content": new_req_CD_input})
    
    print('First stage CD prompt creation completed, proceeding with CD prompt...')
    
    # First stage CD Chat model call
    response = openai.ChatCompletion.create(
                  model=model,
                  messages=few_shot_messages_CD
                )
    new_req_pi = response.choices[0].message['content']
    
    print('First stage CD prompt completed')
    
    # First stage CM Messages creation
    new_req_CM_input = new_req_CD_input + new_req_pi
    few_shot_messages_CM.append({"role": "user", "content": new_req_CM_input})
    
    print('First stage CM prompt creation completed, proceeding with first stage CM prompt...')
    # First stage CM Chat model call
    response = openai.ChatCompletion.create(
                      model=model,
                      messages=few_shot_messages_CM
                    )
    new_req_description = response.choices[0].message['content']
    
    print('First stage CM prompt completed')
    
    # Second stage Messages creation
    few_shot_messages.append({"role": "user", "content": new_req_description})
    
    print('Second stage prompt creation completed, proceeding with second stage prompt...')
    
    # Second stage Chat model call
    response = openai.ChatCompletion.create(
                  model=model,
                  messages=few_shot_messages
                )
    new_req_function = response.choices[0].message['content']
    
    print('Second stage prompt completed, preparing to run the function and create prompt examples')
    
    # Extract the function and run it, create a function name object, and save everything in the untested folder
    function_name = extract_function_code(s=new_req_function, detail=detail, g=g)
    
    print(f'New function saved in ./functions/untested functions/{function_name}/{function_name}_module.py')
    
    # Create the prompt example for this function
    new_req_messages_CD = [
                          {"role": "user", "content": new_req_CD_input},
                          {"role": "assistant", "content": new_req_pi}
                         ]
    new_req_messages_CM = [
                          {"role": "user", "content": new_req_CM_input},
                          {"role": "assistant", "content": new_req_description}
                         ]
    
    with open(f'./functions/untested functions/{function_name}/{function_name}_module.py', encoding='utf-8') as f:
        new_req_function_code = f.read()
    
    new_req_messages = [
                       {"role": "user", "content": new_req_description},
                       {"role": "assistant", "content": new_req_function_code}
                      ] 
    
    new_req_prompt = {
                     "stage1_CD": new_req_messages_CD,
                     "stage1_CM": new_req_messages_CM,
                     "stage2": new_req_messages
                    }   
    
    with open(f'./functions/untested functions/{function_name}/{function_name}_prompt.json', 'w') as f:
        json.dump(new_req_prompt, f)
        
    print(f'New function prompt example saved in ./functions/untested functions/{function_name}/{function_name}_prompt.json')
    print('done')
    return function_name


def prompt_modified(function_name, system_content='inference_chain_modification.md', model="gpt-4-0613", g=globals()):
    """
    External function review function for the Intelligent Email project, used to review whether the external function creation prompts are correct and whether the final created code is accurate.
    :param function_name: Required parameter, a string representing the name of the function to be reviewed.
    :param system_content: Optional parameter, default is 'inference_chain_modification.md', representing the name of the document to review the external function's attached document, which should be in Markdown format.
    :param model: Optional parameter, specifies the Chat model to use, default is 'gpt-4-0613'.
    :param g: Optional parameter, specifies the scope for the extract_function_code function, default is globals(), i.e., effective in the current operational space.
    :return: The name of the newly created function after review.
    """
    print(f"Executing review function, review target: {function_name}")
    
    with open(system_content, 'r', encoding='utf-8') as f:
        md_content = f.read()
        
    # Read all prompt content for the original function
    with open(f'./functions/untested functions/{function_name}/{function_name}_prompt.json', 'r') as f:
        msg = json.load(f)
    
    # Save it as a string
    msg_str = json.dumps(msg)
    
    # Perform review
    response = openai.ChatCompletion.create(
                    model=model,
                    messages=[
                    {"role": "system", "content": md_content},
                    {"role": "user", "content": f'The following is an incorrect inference chain for the Intelligent Email project. Please modify it according to the requirements: {msg_str}'}
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
    
    # Extract function source code
    code = json.loads(modified_json)['stage2'][1]['content']
    
    # Extract function name
    match = re.search(r'def (\w+)', code)
    function_name = match.group(1)
    
    print(f"Review completed. The new function name is: {function_name}.\nRunning the function definition process and saving function source code and prompt.")
    
    exec(code, g)
    
    # Create a folder with the function's name in the untested folder
    directory = f'./functions/untested functions/{function_name}'
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    # Write the function code
    with open(f'./functions/untested functions/{function_name}/{function_name}_module.py', 'w', encoding='utf-8') as f:
        f.write(code)
        
    # Write the prompt
    with open(f'./functions/untested functions/{function_name}/{function_name}_prompt.json', 'w') as f:
        json.dump(json.loads(modified_json), f)
    
    print(f'New function prompt example saved in ./functions/untested functions/{function_name}/{function_name}_prompt.json')
    print(f"{function_name} function has been defined in the current operational space and can be tested for effectiveness.")
    
    return function_name


def function_test(function_name, req, few_shot, model="gpt-4-0613", g=globals()):

    def test_messages(user_content):
        messages = [
            {"role": "system", "content": "Endumi Tian's email address is: 2323365771@qq.com"},
            {"role": "system", "content": "My email address is: ksken166@gmail.com"},
            {"role": "user", "content": user_content}
        ]
        return messages

    messages = test_messages(req)
    
    new_function = globals()[function_name]
    functions_list = [new_function]
    
    print(f"Testing the functionality of the {function_name} function based on the given user requirement 'req'. Please ensure the function is already defined in the current operational space...")
    
    # This block may raise an error during run_conversation
    # If no error occurs, then run:
    try:
        final_response = run_conversation(messages=messages, functions_list=functions_list, model=model)
        print(f"Current function output: '{final_response}'")
        
        feedback = input("Does the function meet the requirements (yes/no)? ")
        if feedback.lower() == 'yes':
            print("Function has passed the test. Writing the function to the tested folder.")
            remove_to_tested(function_name)
            print('done')
        else:
            next_step = input("The function did not pass the test. Do you want to: 1. Test again, or 2. Enter debug mode?")
            if next_step == '1':
                print("Preparing for retest...")
                function_test(function_name, req, few_shot)
            else:
                solution = input("Choose a debug solution:\n1. Retry the function creation process and test results;\n2. Execute the review function;\n3. Re-enter user requirements;\n4. Exit the program and try manually")
                if solution == '1':
                    # Retry function creation process
                    print("Okay, attempting to recreate the function. Please wait...")
                    few_shot_str = input("For the retest, would you like to: 1. Use the previous Few-shot method, or 2. Use all function examples for Few-shot?")
                    if few_shot_str == '1':
                        function_name = code_generate(req=req, few_shot=few_shot, model=model, g=g)
                    else:
                        function_name = code_generate(req=req, few_shot='all', model=model, g=g)
                    function_test(function_name=function_name, req=req, few_shot=few_shot, g=g)
                elif solution == '2':
                    # Execute the review function
                    print("Okay, executing the review function. Please wait...")
                    function_name = prompt_modified(function_name=function_name, model="gpt-3.5-turbo-16k-0613", g=g)
                    # Proceed to test with the new function
                    print("New function has been created. Proceeding to test...")
                    function_test(function_name=function_name, req=req, few_shot=few_shot, g=g)
                elif solution == '3':
                    new_req = input("Okay, please re-enter the user requirements. Note that the description method will greatly affect the final function creation result.")
                    few_shot_str = input("How would you like to proceed with code generation? 1. Use the previous Few-shot method; \n2. Use all external functions for Few-shot")
                    if few_shot_str == '1':
                        function_name = code_generate(req=new_req, few_shot=few_shot, model=model, g=g)
                    else:
                        function_name = code_generate(req=new_req, few_shot='all', model=model, g=g)
                    function_test(function_name=function_name, req=new_req, few_shot=few_shot, g=g)
                elif solution == '4':
                    print("Okay, good luck with debugging~")
        
    # If run_conversation raises an error, then run:
    except Exception as e:
        next_step = input("run_conversation failed. Would you like to: 1. Retry run_conversation, or 2. Enter debug mode?")
        if next_step == '1':
            function_test(function_name, req, few_shot)
        else:
            solution = input("Choose a debug solution:\n1. Retry the function creation process and test results;\n2. Execute the review function;\n3. Re-enter user requirements;\n4. Exit the program and try manually")
            if solution == '1':
                # Retry function creation process
                print("Okay, attempting to recreate the function. Please wait...")
                few_shot_str = input("For the retest, would you like to: 1. Use the previous Few-shot method, or 2. Use all function examples for Few-shot?")
                if few_shot_str == '1':
                    function_name = code_generate(req=req, few_shot=few_shot, model=model, g=g)
                else:
                    function_name = code_generate(req=req, few_shot='all', model=model, g=g)
                function_test(function_name=function_name, req=req, few_shot=few_shot, g=g)
            elif solution == '2':
                # Execute the review function
                print("Okay, executing the review function. Please wait...")
                max_attempts = 3
                attempts = 0

                while attempts < max_attempts:
                    try:
                        function_name = prompt_modified(function_name=function_name, model="gpt-3.5-turbo-16k-0613", g=g)
                        break  # Break loop if code executes successfully
                    except Exception as e:
                        attempts += 1  # Increase attempt count
                        print("An error occurred:", e)
                        if attempts == max_attempts:
                            print("Maximum attempt count reached. Program terminated.")
                            raise  # Re-raise the last exception
                        else:
                            print("Retrying the review process...")
                # Proceed to test with the new function
                print("New function has been created. Proceeding to test...")
                function_test(function_name=function_name, req=req, few_shot=few_shot, g=g)
            elif solution == '3':
                new_req = input("Okay, please re-enter the user requirements. Note that the description method will greatly affect the final function creation result.")
                few_shot_str = input("How would you like to proceed with code generation? 1. Use the previous Few-shot method; \n2. Use all external functions for Few-shot")
                if few_shot_str == '1':
                    function_name = code_generate(req=new_req, few_shot=few_shot, model=model, g=g)
                else:
                    function_name = code_generate(req=new_req, few_shot='all', model=model, g=g)
                function_test(function_name=function_name, req=new_req, few_shot=few_shot, g=g)
            elif solution == '4':
                print("Okay, good luck with debugging~")

                
def Gmail_auto_func(req, few_shot='all', model='gpt-4-0613', g=globals(), detail=0):
    function_name = code_generate(req, few_shot=few_shot, model=model, g=g, detail=detail)
    function_test(function_name=function_name, req=req, few_shot=few_shot, model=model, g=g)

################################
# External functions section

def get_email_counts(userId='me'):
    """
    Query the total number of emails in a Gmail account.
    :param userId: Required parameter, a string representing the email ID to query. 
    Note: Use 'me' for querying your own email.
    :return: The total number of emails, returned as a JSON object.
    """
    # Load credentials from local file
    creds = Credentials.from_authorized_user_file('token.json')

    # Create Gmail API client
    service = build('gmail', 'v1', credentials=creds)

    # List all emails for the user
    results = service.users().messages().list(userId=userId).execute()
    messages = results.get('messages', [])

    # Get the number of emails
    email_counts = len(messages)

    return json.dumps({"email_counts": email_counts})

def get_latest_email(userId):
    """
    Query the information of the latest email in a Gmail account.
    :param userId: Required parameter, a string representing the email ID to query. 
    Note: Use 'me' for querying your own email.
    :return: An object containing all information of the latest email, created and saved as JSON by the Gmail API.
    """
    # Load credentials from local file
    creds = Credentials.from_authorized_user_file('token.json')
    
    # Create Gmail API client
    service = build('gmail', 'v1', credentials=creds)
    
    # List the latest email for the user
    results = service.users().messages().list(userId=userId, maxResults=1).execute()
    messages = results.get('messages', [])

    # Retrieve email details
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        
    return json.dumps(msg)

def retrieve_emails(n, user_id='me'):
    """
    Retrieve a specified number of recent emails.

    Parameters:
    n: The number of emails to retrieve. This should be an integer.
    user_id: The ID of the user whose emails are to be retrieved. Default is 'me', indicating the currently authorized user.

    Returns:
    A list where each element is a dictionary representing an email. Each dictionary contains the following keys:
    'From': The sender's email address.
    'Date': The date when the email was sent.
    'Subject': The subject of the email.
    'Snippet': The email's snippet (first 100 characters).
    """
    # Load credentials from local file
    creds = Credentials.from_authorized_user_file('token.json')

    # Create Gmail API client
    service = build('gmail', 'v1', credentials=creds)

    # Get email list
    results = service.users().messages().list(userId=user_id).execute()
    messages = results.get('messages', [])[:n]

    emails = []
    for message in messages:
        msg = service.users().messages().get(userId=user_id, id=message['id']).execute()

        # Decode email content
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

    # Return the list of emails
    return json.dumps(emails, indent=2)

def send_email(to, subject, message_text):
    """
    Create and send an email using the Gmail API.
    :param to: Required parameter, a string representing the target email address to send the email to.
    :param subject: Required parameter, a string representing the email subject.
    :param message_text: Required parameter, a string representing the entire body of the email.
    :return: Returns a dictionary with the result of the send operation, including the email ID and send status if successful.
    """
    
    creds_file = 'token_send.json'
    
    def create_message(to, subject, message_text):
        """Create a MIME email"""
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = 'me'
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_string().encode('utf-8')).decode('utf-8')
        return {
            'raw': raw_message
        }

    def send_message(service, user_id, message):
        """Send email"""
        try:
            sent_message = service.users().messages().send(userId=user_id, body=message).execute()
            print(f'Message Id: {sent_message["id"]}')
            return sent_message
        except Exception as e:
            print(f'An error occurred: {e}')
            return None

    # Load credentials from local file
    creds = Credentials.from_authorized_user_file(creds_file)

    # Create Gmail API client
    service = build('gmail', 'v1', credentials=creds)

    message = create_message(to, subject, message_text)
    res = send_message(service, 'me', message)

    return json.dumps(res)

def get_oldest_email(userId='me'):
    """
    Query the oldest email in a Gmail account based on the given userId, including the sender and main content of the email.
    :param userId: Optional parameter, default is 'me', indicating the oldest email of the user calling this function in Gmail.
    :return: A JSON object containing the sender and content of the oldest email.
    """
    # Load credentials from local file
    creds = Credentials.from_authorized_user_file('token.json')

    # Create Gmail API service client
    service = build('gmail', 'v1', credentials=creds)

    # List user's emails
    results = service.users().messages().list(userId=userId).execute()
    messages = results.get('messages', [])
    
    # Check if emails exist and get the oldest one
    if not messages:
        return json.dumps({"error":"No emails found."})
    else:
        message = messages[-1]
        # Get email details
        msg = service.users().messages().get(userId=userId, id=message['id']).execute()
        
    # Parse email content
    headers = msg['payload']['headers']
    snippet = msg['snippet']
    for d in headers:
        if d['name'] == 'From':
            sender = d['value']

    return json.dumps({"Sender": sender, "Content": snippet})

def get_emails_by_sender(sender, userId='me'):
    """
    Query the list of emails in a Gmail account based on the sender.

    Parameters:
    sender: The sender of the emails.
    userId: The ID of the user whose emails are to be queried. Default is 'me'.

    Returns:
    A list of emails received from the specified sender. Each email is represented as a dictionary containing the email ID and subject.
    """
    # Load credentials from local file
    creds = Credentials.from_authorized_user_file('token.json')

    # Create Gmail API service client
    service = build('gmail', 'v1', credentials=creds)

    # Get list of emails from the specified sender
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
    Query and count the list of emails in Gmail based on the sender.

    Parameters:
    sender: The sender of the email.
    userId: The ID of the user whose emails are to be counted, default is 'me'.

    Returns:
    A JSON object containing the total count of emails.
    """
    # Load credentials from local file
    creds = Credentials.from_authorized_user_file('token.json')

    # Create Gmail API service client
    service = build('gmail', 'v1', credentials=creds)

    # Get the list of emails from the specified sender
    try:
        request = service.users().messages().list(userId=userId, q=f"from:{sender}")
        response = request.execute()
    except Exception as error:
        print(f"An error occurred: {error}")
        return None

    # Count the total number of emails
    email_count = len(response['messages'])

    # Return the total number of emails
    return json.dumps({'count': email_count})

def count_emails_before_date(date, userId='me'):
    """
    Query the number of emails received before the specified date.

    Parameters:
    date: The specified date in the format 'yyyy/mm/dd'. The number of emails received before this date will be counted.
    userId: The ID of the user whose emails are to be counted, default is 'me'.

    Returns:
    The number of emails received before the specified date, returned as a JSON object.
    """
    # Load credentials from local file
    creds = Credentials.from_authorized_user_file('token.json')

    # Create Gmail API service client
    service = build('gmail', 'v1', credentials=creds)

    # List the user's emails
    results = service.users().messages().list(userId=userId).execute()
    messages = results.get('messages', [])

    # Counter
    count = 0

    # Iterate through each email
    for message in messages:
        msg = service.users().messages().get(userId=userId, id=message['id']).execute()

        # Get the email's received date
        headers = msg['payload']['headers']
        for header in headers:
            if header['name'] == 'Date':
                msg_date = parser.parse(header['value']).strftime('%Y/%m/%d')
                if msg_date < date:
                    count += 1

    # Return the number of emails
    return json.dumps({"count": count})

def get_unread_email_count(userId='me'):
    """
    Get the number of unread emails in Gmail.

    Parameters:
    userId: The ID of the Gmail account user, a string, default is 'me', representing the currently authorized user.

    Returns:
    The number of unread emails, returned as a JSON object.
    """
    # Load credentials from local file
    creds = Credentials.from_authorized_user_file('token.json')

    # Create Gmail API service client
    service = build('gmail', 'v1', credentials=creds)

    # Find unread emails
    results = service.users().messages().list(userId=userId, q='is:unread').execute()
    messages = results.get('messages', [])

    # Get the number of unread emails
    unread_count = len(messages)

    return json.dumps({"unread_email_count": unread_count})

def count_emails_with_query(query, userId='me'):
    """
    Query the number of emails containing the specified content.

    Parameters:
    query: The content to search for in emails.
    userId: The ID of the user whose emails are to be searched, default is 'me'.

    Returns:
    The number of emails containing the query content, returned as a JSON object.
    """
    # Load credentials from local file
    creds = Credentials.from_authorized_user_file('token.json')

    # Create Gmail API service client
    service = build('gmail', 'v1', credentials=creds)

    # Get the list of emails containing the specified content
    try:
        request = service.users().messages().list(userId=userId, q=query)
        response = request.execute()
    except Exception as error:
        print(f"An error occurred: {error}")
        return None

    # Count the total number of emails
    email_count = len(response['messages'])

    # Return the total number of emails
    return json.dumps({'count': email_count})

def count_emails_from_sender_in_period(sender, date_range, userId='me'):
    """
    Query the number of emails sent by a specific sender within a specified date range.

    Parameters:
    sender: The sender of the email.
    date_range: The date range for the emails received, in the format 'yyyy-mm-dd to yyyy-mm-dd'.
    userId: The ID of the user whose emails are to be searched, default is 'me'.

    Returns:
    The number of emails sent by the specified sender within the date range, returned as a JSON object.
    """

    # Load credentials from local file
    creds = Credentials.from_authorized_user_file('token.json')

    # Create Gmail API service client
    service = build('gmail', 'v1', credentials=creds)

    try:
        # Query emails sent by the specified sender within the date range
        request = service.users().messages().list(userId=userId, q=f"from:{sender} after:{date_range.split(' to ')[0]} before:{date_range.split(' to ')[1]}")
        response = request.execute()
    except Exception as e:
        print(f'An error occurred: {e}')
        return None

    # Count the total number of emails
    email_count = len(response['messages'])

    # Return the number of emails
    return json.dumps({'count': email_count})


if __name__ == '__main__':
    print("this file contains assist functions")
