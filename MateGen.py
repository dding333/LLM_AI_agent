from chatmessage import ChatMessages
from IPython.display import display, Code, Markdown
from response import *


class MateGen():
    def __init__(self,
                 api_key,
                 model='gpt-3.5-turbo-0613',
                 system_content_list=[],
                 project=None,
                 messages=None,
                 available_functions=None,
                 is_enhanced_mode=False,
                 is_developer_mode=False):
        """
        'api_key': Required parameter, representing the string key necessary to call the OpenAI model. There is no default value; users must set this before using MateGen.
        'model': Optional parameter, representing the type of Chat model currently selected. The default is gpt-3.5-turbo-0613. For information on which models are available for the current OpenAI account, refer to the official limit link: OpenAI Account Limits.
        'system_content_list': Optional parameter, representing the input system messages or external documents. The default is an empty list, indicating no external documents are input.
        'project': Optional parameter, representing the project name to which the current conversation belongs. This requires an InterProject class object to indicate the local storage method of the current conversation. The default is None, meaning no local storage.
        'messages': Optional parameter, representing the Messages inherited by the current conversation. This needs to be a ChatMessages object or a list composed of dictionaries. The default is None, meaning no Messages are inherited.
        'available_functions': Optional parameter, representing external tools for the current conversation. This needs to be an AvailableFunction object. The default is None, indicating no external functions are available for the current conversation.
        'is_enhanced_mode': Optional parameter, indicating whether the current conversation is in enhanced mode. Enhanced mode will automatically enable complex task decomposition processes and deep debugging functions, which will require more computation time and cost but will improve overall Agent performance. 
        'is_developer_mode': Optional parameter, indicating whether the current conversation is in developer mode. In developer mode, the model will first confirm with the user whether the text or code is correct before choosing to save or execute it. 
         This can greatly enhance model usability for developers, but it is not recommended for beginners. The default is False.
        """

        self.api_key = api_key
        self.model = model
        self.project = project
        self.system_content_list = system_content_list
        tokens_thr = None

        # calculate tokens_thr
        if '1106' in model:
            tokens_thr = 110000
        elif '16k' in model:
            tokens_thr = 12000
        elif '4-0613' in model:
            tokens_thr = 7000
        else:
            tokens_thr = 3000

        self.tokens_thr = tokens_thr

        # create self.messages
        self.messages = ChatMessages(system_content_list=system_content_list,
                                     tokens_thr=tokens_thr)

        # if the initial messages is not none, add it to the self.messages
        if messages != None:
            self.messages.messages_append(messages)

        self.available_functions = available_functions
        self.is_enhanced_mode = is_enhanced_mode
        self.is_developer_mode = is_developer_mode

    def chat(self, question=None):
        """
        The MateGen class's main method supports both single-round and multi-round conversation modes. When the user does not input a question, multi-round conversation mode is enabled; otherwise, single-round conversation mode is activated. 
        Regardless of whether single-round or multi-round conversation mode is enabled, the conversation results will be saved in self.messages, making it convenient for future use.
        """
        head_str = "▌ Model set to %s" % self.model
        display(Markdown(head_str))

        if question != None:
            self.messages.messages_append({"role": "user", "content": question})
            self.messages = get_chat_response(model=self.model,
                                              messages=self.messages,
                                              available_functions=self.available_functions,
                                              is_developer_mode=self.is_developer_mode,
                                              is_enhanced_mode=self.is_enhanced_mode)

        else:
            while True:
                self.messages = get_chat_response(model=self.model,
                                                  messages=self.messages,
                                                  available_functions=self.available_functions,
                                                  is_developer_mode=self.is_developer_mode,
                                                  is_enhanced_mode=self.is_enhanced_mode)

                user_input = input(" Do you have any other questions? (Enter 'exit' to end the conversation) ")
                if user_input == "exit":
                    break
                else:
                    self.messages.messages_append({"role": "user", "content": user_input})

    def reset(self):
        """
        reset the messages
        """
        self.messages = ChatMessages(system_content_list=self.system_content_list)

    def upload_messages(self):
        """
        upload the current messages to project file 
        """
        if self.project == None:
            print("You need to first input the project parameter (which needs to be an InterProject object) before uploading messages.")
            return None
        else:
            self.project.append_doc_content(content=self.messages.history_messages)

if __name__ == '__main__':
    print("this file contains the MateGen class")
