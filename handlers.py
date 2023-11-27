from aiogram import Bot, Dispatcher, types
from typing import Optional
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from aiogram.filters.command import Command

import requests
import config
import logging
from time import sleep
from celery import Celery
from celery.schedules import crontab
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from pymongo.mongo_client import MongoClient
import os

from horoscope import Horoscope

client = MongoClient('localhost', 27017)

db = client.horoscope_db
users = db.users
compatibility = db.compatibility

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

logging.basicConfig(level=logging.DEBUG, filename='horoscope_bot.log')

client = Celery('haroscope', broker=config.CELERY_BROKER_URL)
client.conf.result_backend = config.CELERY_RESULT_BACKEND
client.conf.timezone = 'Europe/Moscow'

my_id = '182149382'

client.conf.beat_schedule = {
    'send_daily_horoscope': {
        'task': 'handlers.send_daily_horoscope',
        'schedule': crontab(hour=8, minute=10)
    },
    'send_weekly_horoscope': {
        'task': 'handlers.send_weekly_horoscope',
        'schedule': crontab(day_of_week='sunday', hour=20, minute=0)
    },
}

bot = Bot(token=config.TELEGRAM_TOKEN)

dp = Dispatcher()

def send_msg(chat_id, text):
    response = requests.post('https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}&disable_web_page_preview=True'.format(
        token = config.TELEGRAM_TOKEN,
        chat_id = chat_id,
        text = text
    ))

@dp.message(Command('start'))
async def start(message: types.message):
    user = {
        'user_id': message.from_user.id,
        'first_name': message.from_user.first_name,
        'sign': ''
    }
    users.delete_one({'user_id': message.from_user.id})
    users.insert_one(user) 
      
    #send_msg(my_id, 'Нажали старт')
    await message.answer('Привет {name}!\nВыбери свой знак зодиака!\n '.format(
        name=message.from_user.first_name,
        id = message.from_user.id
    ), reply_markup=get_keyboard_sign())
    

class SignCallbackFactory(CallbackData, prefix="sign"):
    #action: str
    value: Optional[str] = None

class PeriodCallbackFactory(CallbackData, prefix="period"):
    #action: str
    value: Optional[str] = None

class CompatibilityCallbackFactory(CallbackData, prefix="compatibility"):
    #action: str
    value: Optional[str] = None
    payload: Optional[str] = None
    
ZODIAC_SIGNS = {
    "aries": '♈ Овен',
    "taurus": '♉ Телец',
    "gemini": '♊ Близнецы',
    "cancer": '♋ Рак',
    "leo": '♌ Лев',
    "virgo": '♍ Дева',
    "libra": '♎ Весы',
    "scorpio": '♏ Скорпион',
    "sagittarius": '♐ Стрелец',
    "capricorn": '♑ Козерог',
    "aquarius": '♒ Водолей',
    "pisces": '♓ Рыбы'
} 

def get_keyboard_sign():    
    builder = InlineKeyboardBuilder()
    for key, value in ZODIAC_SIGNS.items():    
        builder.button(
            text=value, callback_data=SignCallbackFactory(value=key)
        )
    
    builder.adjust(3)
    return builder.as_markup()

def get_keyboard_period():    
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text='На сегодня', callback_data=PeriodCallbackFactory(value='today')
    )
    
    builder.button(
        text='На завтра', callback_data=PeriodCallbackFactory(value='tomorrow')
    )
    
    builder.button(
        text='На неделю', callback_data=PeriodCallbackFactory(value='week')
    )
    
    builder.adjust(3)
    return builder.as_markup()

def get_keyboard_compatibility(payload=None):    
    builder = InlineKeyboardBuilder()
    for key, value in ZODIAC_SIGNS.items():    
        builder.button(
            text=value, callback_data=CompatibilityCallbackFactory(value=key, payload=payload)
        )
    
    builder.adjust(3)
    return builder.as_markup()


@dp.callback_query(SignCallbackFactory.filter())
async def callbacks_num_change_fab(
        callback: types.CallbackQuery, 
        callback_data: SignCallbackFactory
):
    data = {}
    sign = callback_data.value
    data['chat_id'] = callback.from_user.id
    user = users.find({'user_id': callback.from_user.id})[0]
    #user['sign'] = sign.lower()
    users.update_one({'user_id': callback.from_user.id}, {'$set': {'sign': sign}})
    await bot.send_message(text='Выбери период', chat_id=callback.from_user.id, reply_markup=get_keyboard_period())
    #send_msg(callback.from_user.id, horoscope.get_tooday())
        
    await callback.answer()
    
@dp.callback_query(PeriodCallbackFactory.filter())
async def callbacks_num_change_fab(
        callback: types.CallbackQuery, 
        callback_data: PeriodCallbackFactory
):
    data = {}
    period = callback_data.value
    data['chat_id'] = callback.from_user.id
    user = users.find({'user_id': callback.from_user.id})[0]
    horoscope = Horoscope(user['sign'])
    
    send_msg(callback.from_user.id, horoscope.get(period))
        
    await callback.answer()
        
@dp.callback_query(CompatibilityCallbackFactory.filter())
async def callbacks_num_change_fab(
        callback: types.CallbackQuery, 
        callback_data: CompatibilityCallbackFactory
):
    data = {}
    user = users.find({'user_id': callback.from_user.id})[0]
    if callback_data.payload == None:
        female = callback_data.value
        data['chat_id'] = callback.from_user.id

        await bot.send_message(text='Мужчина', chat_id=callback.from_user.id, reply_markup=get_keyboard_compatibility(payload=female))
    else:
        male = callback_data.value
        female = callback_data.payload
        horo = compatibility.find({'title': f'{female}-{male}'})[0]
        percent = horo['percent']
        description = f'<b>Ваша совместимость:</b> {percent}\n'
        for k, v in horo['description'].items():
            description = description + '\n' + f'<b>{k}</b>' +'\n' + v[0] + '\n'
        await bot.send_message(text=description, chat_id=callback.from_user.id, parse_mode='html')
    await callback.answer()
        
@dp.message(Command('horoscope'))
async def horoscope(message: types.message):
    await message.answer('Выбери период', reply_markup=get_keyboard_period())
    
@dp.message(Command('compatibility'))
async def comand_compatibility(message: types.message):
    await message.answer('Женщина', reply_markup=get_keyboard_compatibility())
    
@client.task()
def send_daily_horoscope():
    for i in users.find():
        horoscope = Horoscope(i['sign'])
        send_msg(i['user_id'], 'Ваш гороскоп на сегодня')
        send_msg(i['user_id'], horoscope.get('today'))

@client.task()
def send_weekly_horoscope():
    for i in users.find():
        horoscope = Horoscope(i['sign'])
        send_msg(i['user_id'], 'Ваш гороскоп на следующую неделю')
        send_msg(i['user_id'], horoscope.get('week'))
        
if __name__ == '__main__':
    pass