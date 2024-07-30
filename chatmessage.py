import tiktoken
import openai
import copy


class ChatMessages():
    """
    The ChatMessages class is used to create message objects that the Chat model can receive and interpret. This object is a more advanced representation of the original messages object received by the Chat model. 
    The ChatMessages class takes a list of dictionaries as one of its attributes and can distinguish between system messages and historical conversation messages. 
    It can also automatically calculate the token count of the current conversation and delete the earliest messages when appending new ones, allowing for smoother input to the large model and meeting the requirements of multi-turn conversations.
    """

    def __init__(self,
                 system_content_list=[],
                 question='Hello',
                 tokens_thr=None,
                 project=None):

        self.system_content_list = system_content_list
        # List of system message documents, equivalent to an external input document list
        system_messages = []
        # Historical conversation messages excluding system messages
        history_messages = []
        # List used to store all messages
        messages_all = []
        # System message string
        system_content = ''
        # Historical message string, which is currently the user input
        history_content = question
        # Combined string of system messages and historical messages
        content_all = ''
        # Number of system messages input into messages, initially 0
        num_of_system_messages = 0
        # Total token count of all information
        all_tokens_count = 0

        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

        # Save external input documents as system messages sequentially
        if system_content_list != []:
            for content in system_content_list:
                system_messages.append({"role": "system", "content": content})
                # Concatenate all document content
                system_content += content
        
            # Calculate the number of tokens in system messages
            system_tokens_count = len(encoding.encode(system_content))
            # Append system messages to all messages
            messages_all += system_messages
            # Count the number of system messages
            num_of_system_messages = len(system_content_list)
        
            # If there is a maximum token limit
            if tokens_thr is not None:
                # If the system messages exceed the limit
                if system_tokens_count >= tokens_thr:
                    print("The number of tokens in system_messages exceeds the limit. The current system messages will not be input into the model. If necessary, please adjust the number of external documents.")
                    # Delete system messages
                    system_messages = []
                    messages_all = []
                    # Reset the number of system messages
                    num_of_system_messages = 0
                    # Reset the system messages token count
                    system_tokens_count = 0


        all_tokens_count += system_tokens_count

        # Create the initial user message
        history_messages = [{"role": "user", "content": question}]
        # Create the list of all messages
        messages_all += history_messages
        
        # Calculate the number of tokens in the user's question
        user_tokens_count = len(encoding.encode(question))
        
        # Calculate the total number of tokens
        all_tokens_count += user_tokens_count
        
        # If there is a maximum token limit
        if tokens_thr is not None:
            # If the total exceeds the maximum token limit
            if all_tokens_count >= tokens_thr:
                print("The number of tokens in the current user question exceeds the limit. This message cannot be input into the model. Please re-enter the user question or adjust the number of external documents.")
                # Clear both system and user messages
                history_messages = []
                system_messages = []
                messages_all = []
                num_of_system_messages = 0
                all_tokens_count = 0


        # All messages information
        self.messages = messages_all
        # System messages information
        self.system_messages = system_messages
        # User messages information
        self.history_messages = history_messages
        # Total token count of all content in messages
        self.tokens_count = all_tokens_count
        # Number of system messages
        self.num_of_system_messages = num_of_system_messages
        # Maximum token count threshold
        self.tokens_thr = tokens_thr
        # Encoding method for token count calculation
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        # Project associated with the messages
        self.project = project

    # Remove some conversation information
    def messages_pop(self, manual=False, index=None):
        def reduce_tokens(index):
            drop_message = self.history_messages.pop(index)
            self.tokens_count -= len(self.encoding.encode(str(drop_message)))
    
        if self.tokens_thr is not None:
            while self.tokens_count >= self.tokens_thr:
                reduce_tokens(-1)
    
        if manual:
            if index is None:
                reduce_tokens(-1)
            elif 0 <= index < len(self.history_messages) or index == -1:
                reduce_tokens(index)
            else:
                raise ValueError("Invalid index value: {}".format(index))
        
        # Update messages
        self.messages = self.system_messages + self.history_messages

    # Add some conversation information
    def messages_append(self, new_messages):
        
        # If new_messages is a single dictionary or JSON-like dictionary
        if isinstance(new_messages, dict) or isinstance(new_messages, openai.openai_object.OpenAIObject):
            self.messages.append(new_messages)
            self.tokens_count += len(self.encoding.encode(str(new_messages)))
    
        # If new_messages is also a ChatMessages object
        elif isinstance(new_messages, ChatMessages):
            self.messages += new_messages.messages
            self.tokens_count += new_messages.tokens_count
    
        # Update the history_messages
        self.history_messages = self.messages[self.num_of_system_messages:]
    
        # Perform pop if needed, which may delete some historical messages
        self.messages_pop()

    # Copy information
    def copy(self):
        # Create a new ChatMessages object, copying all important attributes
        system_content_str_list = [message['content'] for message in self.system_messages]
        new_obj = ChatMessages(
            system_content_list=copy.deepcopy(system_content_str_list),  # Use deep copy to duplicate system messages
            question=self.history_messages[0]['content'] if self.history_messages else '',
            tokens_thr=self.tokens_thr
        )
        # Copy any other necessary attributes
        new_obj.history_messages = copy.deepcopy(self.history_messages)  # Use deep copy to duplicate historical messages
        new_obj.messages = copy.deepcopy(self.messages)  # Use deep copy to duplicate all messages
        new_obj.tokens_count = self.tokens_count
        new_obj.num_of_system_messages = self.num_of_system_messages
        return new_obj

    # Add system messages
    def add_system_messages(self, new_system_content):
        system_content_list = self.system_content_list
        system_messages = []
        
        # If input is a string, convert it to a list
        if type(new_system_content) == str:
            new_system_content = [new_system_content]
    
        # Extend the existing system content list with new content
        system_content_list.extend(new_system_content)
        
        # Concatenate new system content to create a single string
        new_system_content_str = ''
        for content in new_system_content:
            new_system_content_str += content
        
        # Calculate the number of tokens in the new system content
        new_token_count = len(self.encoding.encode(str(new_system_content_str)))
        self.tokens_count += new_token_count
        
        # Update system content list
        self.system_content_list = system_content_list
        
        # Convert the system content list to system messages
        for message in system_content_list:
            system_messages.append({"role": "system", "content": message})
        
        # Update system messages and other attributes
        self.system_messages = system_messages
        self.num_of_system_messages = len(system_content_list)
        self.messages = system_messages + self.history_messages
    
        # Execute pop to remove old messages if necessary
        self.messages_pop()

    # Delete system messages
    def delete_system_messages(self):
        system_content_list = self.system_content_list
        
        if system_content_list != []:
            # Concatenate all system content into a single string
            system_content_str = ''
            for content in system_content_list:
                system_content_str += content
            
            # Calculate the number of tokens in the system content to be deleted
            delete_token_count = len(self.encoding.encode(str(system_content_str)))
            
            # Update the total token count by subtracting the deleted tokens
            self.tokens_count -= delete_token_count
            
            # Reset system message related attributes
            self.num_of_system_messages = 0
            self.system_content_list = []
            self.system_messages = []
            
            # Update the messages to only include history messages
            self.messages = self.history_messages

    # Clear function messages from conversation messages
    def delete_function_messages(self):
        # Used to remove external function messages
        history_messages = self.history_messages
        
        # Iterate through the list from the end to the beginning
        for index in range(len(history_messages) - 1, -1, -1):
            message = history_messages[index]
            
            # Check if the message is a function call or a function role
            if message.get("function_call") or message.get("role") == "function":
                # Remove the message from the messages
                self.messages_pop(manual=True, index=index)

if __name__ == '__main__':
    print("this file contains ChatMessages class")
