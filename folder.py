from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseUpload
import os
import json
import shutil


def create_or_get_folder(folder_name, upload_to_google_drive=False):
    """
    create or get the id of the folder
    """
    if upload_to_google_drive:
        # if stored in the drive, get the id of the folder
        creds = Credentials.from_authorized_user_file('token.json')
        drive_service = build('drive', 'v3', credentials=creds)

        # check if the name of folder already exist
        query = f"mineType='application/vnd.google-apps.folder' and name= '{folder_name}' and trashed=false"
        result = drive_service.files().list(q=query).execute()
        items = result.get('files', [])

        # if the folder is empty, creat it
        if not items:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = drive_service.files().create(body=folder_metadata).excute()
            folder_id = folder['id']
        else:
            foler_id = items[0]['id']

    else:
        # if save it locally, get the path, and name it with folder_id
        folder_path = os.path.join('./', folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        folder_id = folder_path

    return folder_id


def create_or_get_doc(folder_id, doc_name,upload_to_google_drive=False):
    """
    create or get the id of the folder
    """
    if upload_to_google_drive:
        # if stored in the drive, get the id of the folder
        creds = Credentials.from_authorized_user_file('token.json')
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)

        # check if the name of doc already exists in the folder
        query = f"name='{doc_name}' and '{folder_id}' in parents"
        results = drive_service.files().list(q=query).execute()
        items = results.get('files', [])

        # if the folder is empty, creat it
        if not items:
            doc_metadata = {
                'name': doc_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [folder_id]
            }
            doc = drive_service.files().create(body=doc_metadata).excute()
            document_id = doc['id']
        else:
            document_id = items[0]['id']

    else:
        # if save it locally, get the path of the folder, and name it with document_id
        file_path = os.path.join(folder_id, f'{doc_name}.md')
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write('') # create a new markdown file

        document_id = file_path

    return document_id

def get_file_content(file_id,upload_to_google_drive=False):
    """
    get the content of a doc, needs to find out if the doc is on the drive first
    """
    # read the doc from drive
    if upload_to_google_drive:
        creds = Credentials.from_authorized_user_file('token.json')
        service = build('drive', 'v3', credentials=creds)
        os.environ['SSL_VERSION'] = 'TLSv1.2'
        request = service.files().export_media(fileId=file_id,mimeType='text/plain')
        content = request.execute()
        decoded_content = content.decode('utf-8')

    # read the doc from local
    else:
        with open(file_id,'r',encoding='utf-8') as file:
            decoded_content = file.read()
    return decoded_content

def append_content_in_doc(doc_id,dict_list,upload_to_google_drive=False):
    """
    get the content of a doc, needs to find out if the doc is on the drive first
    """
    # transfer the list of dicts to json
    json_string = json.dumps(dict_list,indent=4,ensure_ascii=False)

    # read the doc from drive
    if upload_to_google_drive:
        creds = Credentials.from_authorized_user_file('token.json')
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)

        # get the length of current doc
        document = docs_service.documents().get(documentId=doc_id).execute()
        end_of_doc = document['body']['content'][-1]['endIndex'] -1

        # append q and a into the doc
        requests = [{
            'insertText':{
                'location':{'index':end_of_doc},
                'text': json_string + '\n\n'
            }
        }]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'request':requests}).execute()

    # read the doc from local
    else:
        with open(doc_id,'a',encoding='utf-8') as file:
            file.write(json_string)

def clear_content_in_doc(doc_id,upload_to_google_drive=False):
    """
    clear the content in the doc, needs to find out if the doc is on the drive first
    """
    if upload_to_google_drive:
        creds = Credentials.from_authorized_user_file('token.json')
        docs_service = build('docs', 'v1', credentials=creds)

        # get the length of current doc
        document = docs_service.documents().get(documentId=doc_id).execute()
        end_of_doc = document['body']['content'][-1]['endIndex'] - 1

        # append q and a into the doc
        requests = [{
            'deleteContentRange': {
                'range': {
                    'startIndex': 1, # this is where the content starts
                    'endIndex': end_of_doc # this is where the content ends
                }
            }
        }]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'request': requests}).execute()
    else:
        with open(doc_id,'w') as file:
            pass # clear the content in local

def list_files_in_doc(folder_id,upload_to_google_drive=False):
    """
    list all the files in a folder, needs to find out if the folder is on the drive first
    """
    # list all the files in the folder on drive
    if upload_to_google_drive:
        creds = Credentials.from_authorized_user_file('token.json')
        drive_service = build('drive', 'v3', credentials=creds)

        # list all the files
        query = f"'{folder_id}' in parents"
        results = drive_service.files().list(q=query).execute()
        files = results.get('files', [])

        # get the list of file names
        file_names = [file['name'] for file in files]

    # read files in the folder from local
    else:
        file_names = [f for f in os.listdir(folder_id) if os.path.isfile(os.path.join(folder_id, f))]
    return file_names


def rename_doc_in_drive(folder_id, doc_id, new_name, upload_to_google_drive=False):
    """
    rename the doc, needs to find out if the doc is on the drive first
    """
    # if the doc is on drive
    if upload_to_google_drive:
        creds = Credentials.from_authorized_user_file('token.json')
        drive_service = build('drive', 'v3', credentials=creds)

        # creat the request
        update_request_body = {
            'name': new_name
        }

        # send the request
        update_response = drive_service.files().update(
            fileId=doc_id,
            body=update_request_body,
            fields='id,name'
        ).execute()

        # get the updated info of the doc
        update_name = update_response['name']

    # if the doc is in loca
    else:
        # decompose the path
        directory, old_file_name = os.path.split(doc_id)
        extension = os.path.splitext(old_file_name)[1]

        # make the new path
        new_file_name = new_name + extension
        new_file_path = os.path.join(directory, new_file_name)

        # rename the doc
        os.rename(doc_id, new_file_path)

        update_name = new_name

    return update_name


def delete_all_files_in_folder(folder_id, upload_to_google_drive=False):
    """
    delete all the files in a folder, needs to find out if the folder is on the drive first
    """
    # if it is on the drive
    if upload_to_google_drive:
        creds = Credentials.from_authorized_user_file('token.json')
        drive_service = build('drive', 'v3', credentials=creds)

        # list all the files in the folder
        query = f"'{folder_id}' in parents"
        results = drive_service.files().list(q=query).execute()
        files = results.get('files', [])

        # traverse and delete every file accordingly
        for file in files:
            file_id = file['id']
            drive_service.files().delete(fileId=file_id).execute()
            # print(f"Deleted file: {file['name']} (ID: {file_id})")

    # if it is in local
    else:
        for filename in os.listdir(folder_id):
            file_path = os.path.join(folder_id, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

if __name__ == '__main__':
    print("this file contains functions to manipulate folders")
