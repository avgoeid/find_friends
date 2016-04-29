"""
This module contain functionality for find a unique friend in vk.com
and add their to your friends

Finding user in your friends, check their(is valid)
Check the user album, if albums name contain keywords, find people who comment that album
Check the people(is valid) and unique and add their to your friends
DELAY it is delay after each operations with api, restricted vk.com
"""

import time
import sys
import random

import vk

# modul that contain user data
import users



SECONDS_IN_MONTH = 60*60*24*30
DELAY = 15

def read_keyword(file):
    """
    Read keywords from file

    Return a tuple
    """
    with open(file, 'r', encoding='utf-8') as f:
        words = f.readlines()
    return  tuple([i.strip() for i in words])

def get_api(app_id, user_login, user_password):
    """
    Use app_id, user_login, user_password for create vk.API object

    Return that oblect
    """
    session = vk.AuthSession(app_id=app_id, user_login=user_login, user_password=user_password, scope="photos, friends, offline")
    return vk.API(session)
    
def is_valid(api, current_user_id):
    """
    Check is a user activity last month, users country(Ukraine or not specify) and active

    Return True or False
    """
    user = api.users.get(user_ids=current_user_id, fields="country, last_seen")[0]
    time.sleep(DELAY)
    return not "deactivated" in user and time.time() - user["last_seen"]["time"] < SECONDS_IN_MONTH and (user["country"] == 2 or user["country"] == 0)
    
def get_album_with_desired_words(api, current_user_id, words):
    """
    The words use for find a users albums, that have the same words in it's names

    Return a list
    """
    albums_name = api.photos.getAlbums(owner_id=current_user_id)
    found_albums = []
    for album in albums_name:
        for word in words:
            if word in album["title"].lower():
                found_albums.append(album["aid"])
    return found_albums
    
def get_comments_in_albums(api, current_user_id, found_albums):
    """
    Collect comments in a found albums
    
    Return a list
    """
    found_comments = []
    for album in found_albums:
        found_comments.append(api.photos.getAllComments(owner_id=current_user_id, album_id=album))
        time.sleep(DELAY)
    return found_comments

def already_send_invitation(api):
    """
    Find a friends who already take a invitation

    Return a list
    """
    time.sleep(DELAY)
    return api.friends.getRequests(out=1, count=1000)
    
def get_who_send_comments(found_comments):
    """
    Parse a comments and find who send the comments 

    Return a list
    """
    who_send_comment = []
    for comments in found_comments:
        for comment in comments:
            who_send_comment.append(comment["from_id"])
    return who_send_comment
    
def get_unique_future_friends(api, my_id, who_send_comment):
    """
    Select unique friends who don't take a invitation or who is not a friend

    Return a set
    """
    my_friends = api.friends.get(user_id=my_id)
    time.sleep(DELAY)
    return set(who_send_comment) - set(my_friends) - set(already_send_invitation(api))

def send_invitation(api, future_friends, amound_user):
    """
    Send invitation a future friends
    """
    count_sended_invitation = 0
    for number in range(amound_user):
        try:
            api.friends.add(user_id=future_friends.pop())
            count_sended_invitation += 1
        except Exception as e:
            print("Before was error sended {} invitation.".format(count_sended_invitation))
            raise e
        time.sleep(DELAY)
    return count_sended_invitation
        
def init_user(user_data):
    """
    Initialize user

    Return tuple(api, user id)
    """
    my_id = user_data["my_id"]
    app_id = user_data["app_id"]
    user_login = user_data["user_login"]
    user_password = user_data["user_password"]
    api = get_api(app_id, user_login, user_password)
    return api, my_id

def bfs(api, id):
    """
    Randomize bfs friends
    """
    friends = api.friends.get(user_id=id)
    random.shuffle(friends)
    visited, queue = set(), friends
    time.sleep(DELAY)
    while queue:
        vertex = queue.pop(0)
        if vertex not in visited:
            visited.add(vertex)
            if is_valid(api, vertex):
                friends = list(set(api.friends.get(user_id=vertex)) - visited)
                random.shuffle(friends)
                queue.extend(friends)
                yield vertex
                time.sleep(DELAY)
        
def main_loop(api, my_id, amound_user, key_path, avto=False, bfs_function=None):
    future_friends = set()
    valid_future_friends = set()
    checked = set()
    words = read_keyword(key_path)
    is_end = False
    while True:
        if is_end: break
        if avto:
            current_user_id = bfs_function
            for i in current_user_id:
                current_user_id = i
                break
            print(current_user_id)
        else:
            current_user_id = int(input("Enter the client id - "))
        try:
            if is_valid(api, current_user_id):
                albums = get_album_with_desired_words(api, current_user_id, words)
                if not albums: 
                    print("No the unknown albums.")
                    continue
                sender_comments = get_who_send_comments(get_comments_in_albums(api, current_user_id, albums))
                if not sender_comments: 
                    print("No comments in the unknown albums.")
                    continue
                future_friends |= get_unique_future_friends(api, my_id, sender_comments)
                for i in future_friends:
                    if i not in checked:
                        checked.add(i)
                        if is_valid(api, i):
                            valid_future_friends.add(i)
                print("Found a {} unique valid users.".format(len(valid_future_friends)))
                if len(valid_future_friends) < amound_user: continue
                amound_user = int(input("\aEnter an amound user - "))
                while True:
                    ans = input("Do send a {} invitation(y/n)? ".format(amound_user)).lower()
                    if ans == "y":
                        count_sended_invitation = send_invitation(api, valid_future_friends, amound_user)
                        print("\aSended a {} invitation.".format(count_sended_invitation))
                        is_end = True
                        break
                    elif ans == "n":
                        break
            else:
                print("Id is not valid.")
        except Exception as e:
            print("\a", e)
            input()
            sys.exit()
                
def auto_mode(key_path, users_path):
    for user_name, user_data in users.read_data(users_path).items():  
        api_myid = init_user(user_data)
        amound_user = int(input("Enter an amound user for {} - ".format(user_name)))
        bfs_function = bfs(api_myid[0], api_myid[1])
        
        main_loop(api_myid[0], api_myid[1], amound_user, key_path, avto=True, bfs_function=bfs_function)
                
def manual_mode(user, key_path, users_path):
    user_data = users.read_data(users_path)[user]
    api_myid = init_user(user_data)
    amound_user = int(input("Enter amound user - "))
    
    main_loop(api_myid[0], api_myid[1], amound_user, key_path)
        
if __name__ == "__main__":
    # path where saved key words and user info
    words_path = r"data\key_word.data"
    users_path = r"data\users.data"
    while True:
        ans = input("Check mode(a/m) - ").lower()
        if ans == "a":
            auto_mode(words_path, users_path)
            break
        elif ans == "m":
            user_name = input("Input user name(4 characters) - ")
            manual_mode(user_name, words_path, users_path)
            break
    input("Good lack!!!")
