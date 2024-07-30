import pandas as pd
import numpy as np
import inspect
import openai
import json
import time
from gptLearning import *


class AvailableFunctions():
    """
    The external functions class primarily handles support for relevant features when external functions are called. The class attributes include a list of external functions, a list of external function parameter descriptions, and a description of the call methods.
    """

    def __init__(self, functions_list=[], functions=[], function_call="auto"):
        self.functions_list = functions_list
        self.functions = functions
        self.functions_dic = None
        self.function_call = None
        # When the list of external functions is not empty and the external function parameter descriptions are empty, `auto_functions` is called to create the external function descriptions list.
        if functions_list != []:
            self.functions_dic = {func.__name__: func for func in functions_list}
            self.function_call = function_call
            if functions == []:
                self.functions = auto_functions(functions_list)

    # Add an external function method, and at the same time, you can change the external function call rules.
    def add_function(self, new_function, function_description=None, function_call_update=None):
        self.functions_list.append(new_function)
        self.functions_dic[new_function.__name__] = new_function
        if function_description == None:
            new_function_description = auto_functions([new_function])
            self.functions.append(new_function_description)
        else:
            self.functions.append(function_description)
        if function_call_update != None:
            self.function_call = function_call_update

if __name__ == '__main__':
    print("this file contains AvailableFunctions class")

