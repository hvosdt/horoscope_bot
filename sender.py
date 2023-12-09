from pymongo.mongo_client import MongoClient
import config
import requests

client = MongoClient('localhost', 27017)
db = client.horoscope_db
users = db.users

def send_msg(chat_id, text):
    response = requests.post('https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}&disable_web_page_preview=True'.format(
        token = config.TELEGRAM_TOKEN,
        chat_id = chat_id,
        text = text
    ))

def send_to_all(message):
    for user in users.find():
        send_msg(user['user_id'], message)

def send_to_user(user_id, message):
    send_msg(user_id, message)
    
if __name__ == '__main__':
    recipient = input('Кому? 1-всем, 2-конкретному пользователю: ')
    if recipient == '1':
        message = input('Введите сообщение: ')
        send_to_all(message)
    if recipient == '2':
        user_id = input('User ID: ')
        message = input('Введите сообщение: ')
        send_to_user(user_id, message)