import os
import sys
import json
from datetime import datetime
from aqt import mw
import time


try:
    from .state import get_index
except:
    from state import get_index
import utility.misc


def log(text):
    dir = utility.misc.get_addon_base_folder_path()
    try:
        with open(dir + 'log.txt', 'a', encoding="utf-8") as out:
            out.write(text + '\n')
    except:
        pass

def start_watch():
    return time.time() * 1000

def stop_watch(t_start):
    return time.time() * 1000 - t_start

def persist_index_info(search_index):
    if search_index is None:
        return

    config = mw.addonManager.getConfig(__name__)

    c_json = _get_data_file_content() 
    c_json["index"]["timestamp"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c_json["index"]["type"] = search_index.type 
    c_json["index"]["size"] = search_index.get_number_of_notes()
    # not used yet
    c_json["index"]["lastInsertedId"] = -1
    c_json["index"]["fieldsToExclude"] = search_index.creation_info["fields_to_exclude_original"]
    c_json["index"]["decks"] = search_index.creation_info["decks"]
    c_json["index"]["stopwordsSize"] = search_index.creation_info["stopwords_size"]
    # not used yet
    c_json["index"]["shouldRebuild"] = False

    _write_to_data_file(c_json)

def get_index_info():
    c_json = _get_data_file_content() 
    return c_json["index"]

def _get_data_file_content():
    dir = utility.misc.get_user_files_folder_path()
    with open(dir + "data.json", "r") as json_file:
        return json.load(json_file)

def _write_to_data_file(c_json):
    dir = utility.misc.get_user_files_folder_path() + "data.json"
    with open(dir, "w") as json_file:
        json.dump(c_json, json_file)
        
def toggle_should_rebuild():
    c_json = _get_data_file_content() 
    c_json["index"]["shouldRebuild"] = not c_json["index"]["shouldRebuild"]
    _write_to_data_file(c_json)


