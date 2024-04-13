import json,os
# import logging
# import logging.config
from datetime import date

import requests

from endpoints.endpointconfig import config



def authenticate(email, password):
    try:
        payload = {"strategy": "local", "email": email, "password": password}
        headers = {"Content-type": "application/json"}
        url = f"{config['BASEURL']}{config['AUTHENTICATION']}"
        response = requests.post(url, json=payload, headers=headers)
        return response
    except requests.exceptions.Timeout:
        # file_logger.error(f"connection timeout")
        raise SystemExit("connection timeout")
    except requests.exceptions.RequestException as err:
        # file_logger.error(f"{err}")
        raise SystemExit("unable to connect to server")


def get_project_list(token):
    try:
        headers = {"Authorization": f"{token}"}
        url = f"{config['BASEURL']}{config['PROJECTS']}/get-my-projects"
        response = requests.get(url, headers=headers)
        return response
    except requests.exceptions.Timeout:
        # file_logger.error(f"connection timeout")
        raise SystemExit("connection timeout")
    except requests.exceptions.RequestException as err:
        # file_logger.error(f"{err}")
        raise SystemExit("unable to connect to server")


def get_task_list(token, project_id, user_id):
    try:
        headers = {"Authorization": f"{token}"}
        url = f"{config['BASEURL']}{config['TASKS']}?fk_project={project_id}&fk_user={user_id}&is_completed=false&$limit=-1"
        response = requests.get(url, headers=headers)
        return response
    except requests.exceptions.Timeout:
        # file_logger.error("connection timeout")
        raise SystemExit("connection timeout")
    except requests.exceptions.RequestException as err:
        # file_logger.error(f"{err}")
        raise SystemExit("unable to connect to server")
    
def get_task_completed_list(token, project_id, user_id):
    try:
        headers = {"Authorization": f"{token}"}
        url = f"{config['BASEURL']}{config['TASKS']}?fk_project={project_id}&fk_user={user_id}&is_completed=true&$limit=-1"
        response = requests.get(url, headers=headers)
        return response
    except requests.exceptions.Timeout:
        # file_logger.error("connection timeout")
        raise SystemExit("connection timeout")
    except requests.exceptions.RequestException as err:
        # file_logger.error(f"{err}")
        raise SystemExit("unable to connect to server")    


def create_task(token, project_id, text, user_id):
    try:
        headers = {"Content-type": "application/json", "Authorization": f"{token}"}
        payload = {"title": text, "fk_project": project_id, "fk_user": user_id}
        url = f"{config['BASEURL']}{config['TASKS']}"
        response = requests.post(url, json=payload, headers=headers)
        return response
    except requests.exceptions.Timeout:
        # file_logger.error("connection timeout")
        raise SystemExit("connection timeout")
    except requests.exceptions.RequestException as err:
        # file_logger.error(f"{err}")
        raise SystemExit("unable to connect to server")

def edit_task(token, project_id, text, user_id,task_id):
    try:
        headers = {"Content-type": "application/json", "Authorization": f"{token}"}
        payload = {"title": text, "fk_project": project_id, "fk_user": user_id}
        url = f"{config['BASEURL']}{config['TASKS']}/{task_id}"
        response = requests.patch(url, json=payload, headers=headers)
        return response
    except requests.exceptions.Timeout:
        # file_logger.error("connection timeout")
        raise SystemExit("connection timeout")
    except requests.exceptions.RequestException as err:
        # file_logger.error(f"{err}")
        raise SystemExit("unable to connect to server")

def mark_task_complete(token, task_id):
    try:
        headers = {"Content-type": "application/json", "Authorization": f"{token}"}
        payload = {"is_completed": 1}
        url = f"{config['BASEURL']}{config['TASKS']}/{task_id}"
        response = requests.patch(url, data=json.dumps(payload), headers=headers)
        return response
    except requests.exceptions.Timeout:
        # file_logger.error("connection timeout")
        raise SystemExit("connection timeout")
    except requests.exceptions.RequestException as err:
        # file_logger.error(f"{err}")
        raise SystemExit("unable to connect to server")

def create_activity_log(token, payload, image_list):
    final_image_list = []
    if len(image_list) !=0:
        for image_path in image_list:
            _tuple = ("screenshots", open(f"{image_path}", "rb"))
            final_image_list.append(_tuple)
    else:
        final_image_list = [("screenshots", None)]

    try:
        headers = {"User-Agent": "Mozilla/5.0", "Authorization": f"{token}"}
        url = f"{config['BASEURL']}{config['ACTIVITYLOG']}"
        response = requests.post(
            url, data=(payload), headers=headers, files=final_image_list
        )
        return response
    
    except requests.exceptions.Timeout:
        # file_logger.error("connection timeout")
        raise SystemExit("connection timeout")
    except requests.exceptions.RequestException as err:
        # file_logger.error(f"{err}")
        raise SystemExit("unable to connect to server")
    except Exception as _error:
        raise SystemExit("Data fail to send")

def get_daily_stats(token):
    try:
        headers = {"Authorization": f"{token}"}
        url = f"{config['BASEURL']}{config['PROJECTS']}/get-my-projects?dashboard=true"
        response = requests.get(url, headers=headers)
        return response
    except requests.exceptions.Timeout:
        # file_logger.error("connection timeout")
        raise SystemExit("connection timeout")
    except requests.exceptions.RequestException as err:
        # file_logger.error(f"{err}")
        raise SystemExit("unable to connect to server")