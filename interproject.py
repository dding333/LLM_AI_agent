from folder import *


class InterProject():
    """
    Project Category: A project is the fundamental object for each analysis task.
    In other words, every analysis task should be "affiliated" with a specific project.
    Each code interpreter must specify the project it belongs to.
    If there is no specified project, a project will be automatically created when the code interpreter runs.
    It is important to note that a project not only serves to explain and label the current analysis task, but more crucially,
    it provides "long-term memory" for each analysis task.
    This means that each project has a corresponding Google Drive and
    Google Docs to save the multi-round dialogue content during the analysis and modeling process.
    Additionally, local documents can also be used for storage.
    """
    def __init__(self, project_name, part_name, folder_id=None, doc_id=None, doc_content =None, upload_to_google_drive = False):
        self.project_name = project_name
        self.part_name = part_name
        self.upload_to_google_drive = upload_to_google_drive

        if folder_id is None:
            folder_id = create_or_get_folder(folder_name=project_name,upload_to_google_drive=upload_to_google_drive)
        self.folder_id = folder_id
        self.doc_list = list_files_in_doc(folder_id,upload_to_google_drive=upload_to_google_drive)
        if doc_id is None:
            doc_id = create_or_get_doc(folder_id,doc_name=part_name,upload_to_google_drive=upload_to_google_drive)
        self.doc_id = doc_id
        self.doc_content = doc_content
        if doc_content != None:
            append_content_in_doc(folder_id=folder_id,doc_id=doc_id,qa_string=doc_content,upload_to_google_drive=upload_to_google_drive)

    def get_doc_content(self):
        self.doc_content = get_file_content(file_id=self.doc_id,upload_to_google_drive=self.upload_to_google_drive)
        return self.doc_content

    def append_doc_content(self,content):
        append_content_in_doc(folder_id=self.folder_id,doc_id=self.doc_id,dict_list=content,upload_to_google_drive=self.upload_to_google_drive)

    def delete_all_files(self):
        delete_all_files_in_folder(folder_id=self.folder_id,upload_to_google_drive=self.upload_to_google_drive)

    def rename_doc(self,new_name):
        self.part_name = rename_doc_in_drive(folder_id=self.folder_id,doc_id=self.doc_id,new_name=new_name,upload_to_google_drive=self.upload_to_google_drive)


if __name__ == '__main__':
    print("this file contains InterProject class")