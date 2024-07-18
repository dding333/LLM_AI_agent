import pandas as pd
import numpy as np
import inspect
import openai
import json
import time
from gptLearning import *


class AvailableFunctions():
    """
    外部函数类，主要负责承接外部函数调用时相关功能支持。类属性包括外部函数列表、外部函数参数说明列表、以及调用方式说明三项。
    """

    def __init__(self, functions_list=[], functions=[], function_call="auto"):
        self.functions_list = functions_list
        self.functions = functions
        self.functions_dic = None
        self.function_call = None
        # 当外部函数列表不为空、且外部函数参数解释为空时，调用auto_functions创建外部函数解释列表
        if functions_list != []:
            self.functions_dic = {func.__name__: func for func in functions_list}
            self.function_call = function_call
            if functions == []:
                self.functions = auto_functions(functions_list)

    # 增加外部函数方法，并且同时可以更换外部函数调用规则
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

