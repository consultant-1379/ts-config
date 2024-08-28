#!/usr/bin/env python
import os
import base64
import getpass
import requests
import time
from subprocess import CalledProcessError, STDOUT, check_output


SPACE_KEY = "PCCSDP"
ANCESTOR_PAGE_TITLE = "Solution Configuration Templates"
PAGE_TITLE = "ts-config Parameter Guide"
USER = getpass.getuser()
PASSWORD_PATH = \
    os.path.join(os.path.abspath(os.path.dirname(__file__)), ".userpwd")
BASE_URL = "https://pdupc-confluence.internal.ericsson.com"
FILE_NAME = "TS-configuration-templates-parameters-guide"
FILE_SUFFIX = ".xlsx"


def run_cmd(cmd):
    try:
        return check_output(cmd, stderr=STDOUT, text=True).rstrip()
    except CalledProcessError as err:
        raise(err)


def request_auto_retry(
        req_type, url, headers, action_msg=None, data=None, files=None, retry_times=3, interval=30):
    req_type = req_type.lower()
    print(f"Try to request the {url}. "
          f"The request method is {req_type}. "
          f"The request data is {data}. "
          f"Max retry time is {retry_times}.")
    for i in range(retry_times):
        if req_type == "post":
            response = requests.post(url, headers=headers, files=files, data=data)
        elif req_type == "get":
            response = requests.get(url, headers=headers, params=data)
        else:
            raise(f"Request type {req_type} is not supported.")
        if response.ok:
            print(f"Request {url} successfully.")
            break
        prefix_msg = f"ERROR!!! Failed to request {url} to " \
                     f"{action_msg}: {response.text.encode('utf-8')}. Tried {i + 1} times,"
        if i + 1 < retry_times:
            print(f"{prefix_msg} continue to retry...")
            time.sleep(interval)
        else:
            raise(f"{prefix_msg} end to retry!")
    return response


class ConfluenceApi(object):
    def __init__(self, username, password, base_url):
        """
        :param username: str, the username to send Confluence API.
        :param password: str, the password of user.
        :param base_url: str, the base url of Confluence.
        """
        self.username = username
        self.password = password
        self.user_info = self._generate_user_info(self.username, self.password)
        self.headers = {
            'Authorization': 'Basic ' + self.user_info.decode(),
            'Content-Type': 'application/json'
        }
        self.base_url = base_url

    def _generate_user_info(self, username, password):
        user_info_str = username + ":" + password
        user_info = base64.b64encode(user_info_str.encode())
        return user_info

    def get_content_id_by_title(self, space_key, page_title):
        url = f"{self.base_url}/rest/api/content/"
        params = {
            'spaceKey': space_key,
            'title': page_title
        }
        action_msg = "get content id by title"
        response = request_auto_retry("get", url, self.headers, action_msg, params)

        return (
            response.json()["results"][0]["id"]
            if response.json()["results"]
            else None
        )

    def update_file(self, content_id, attachment_id):
        url = f"{self.base_url}/rest/api/content/{content_id}/child/attachment/{attachment_id}/data"
        header = {
            'Authorization': 'Basic ' + self.user_info.decode(),
            'X-Atlassian-Token': 'nocheck'
        }
        data = {
                "comment": "File attached via REST API"
            }
        action_msg = "update template parameter guide to confluence guide"
        with open(FILE_NAME + FILE_SUFFIX, 'rb') as f:
            files = {'file': f}
            request_auto_retry("post", url, header, action_msg, files=files, data=data)
        return

    def get_attachment_id(self, content_id):
        url = f"{self.base_url}/rest/api/content/{content_id}/child/attachment"
        header = {
            'Authorization': 'Basic ' + self.user_info.decode(),
            'X-Atlassian-Token': 'nocheck'
        }
        action_msg = "get file attachment id"
        response = request_auto_retry("get", url, header, action_msg)
        return (
            response.json()["results"][0]["id"]
            if response.json()["results"]
            else None
        )


def main():
    if not run_cmd(["git", "show", "HEAD", "jsonschemas"]):
        return
    run_cmd(['cnat', 'docgen', '--src', 'jsonschemas', '-d', f"{FILE_NAME}"])
    with open(PASSWORD_PATH) as f:
        password = base64.b64decode(f.read()).decode()
    confluence_api = ConfluenceApi(USER, password, BASE_URL)
    content_id = confluence_api.get_content_id_by_title(SPACE_KEY, PAGE_TITLE)
    if not content_id:
        raise Exception(f"'{PAGE_TITLE}' page lost!")
    attachment_id = confluence_api.get_attachment_id(content_id)
    if not attachment_id:
        raise Exception("The ancient guide file lost!")
    confluence_api.update_file(content_id, attachment_id)
    print(F"'{FILE_NAME}' is uploaded to Confluence page '{PAGE_TITLE}' successfully.")

if __name__ == '__main__':
    main()
