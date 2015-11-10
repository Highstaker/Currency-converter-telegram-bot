#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#TODO

VERSION_NUMBER = (0,4,0)

import logging
import telegram
from time import time
from os import path, listdir, walk
import socket
import pickle #module for saving dictionaries to file
from bs4 import BeautifulSoup #HTML parser
import re
import json

from webpage_reader import getHTML_specifyEncoding

#if a connection is lost and getUpdates takes too long, an error is raised
socket.setdefaulttimeout(30)

logging.basicConfig(format = u'[%(asctime)s] %(filename)s[LINE:%(lineno)d]# %(levelname)-8s  %(message)s', 
	level = logging.WARNING)


############
##PARAMETERS
############

CURRENCY_NAMES = {
	"RUB": {"EN":"Russian Rouble","RU": "Российский рубль"}
	,"USD": {"EN":"U.S. Dollar","RU": "Доллар США"}
	,"EUR": {"EN":"Euro", "RU": "Евро"}
	,"SEK": {"EN":"Swedish Krona","RU": "Шведская крона"}
	,"AUD": "Australian Dollar"
	,"NOK": "Norwegian Krone"
	,"CZK": {"EN":"Czech Koruna","RU":"Чешская крона"}
	,"DKK": "Danish Krone"
	,"GBP": "British Pound Sterling"
	,"BGN": "Bulgarian Lev"
	,"BRL": "Brazilian Real"
	,"PLN": "Polish Zloty"
	,"NZD": "New Zealand Dollar"
	,"JPY": "Japanese Yen"
	,"CHF": "Swiss Franc"
	,"CAD": "Canadian Dollar"
	,"ZAR":	"South African rand"
}

#A filename of a file containing a token.
TOKEN_FILENAME = 'token'

#A path where subscribers list is saved.
SUBSCRIBERS_BACKUP_FILE = '/tmp/multitran_bot_subscribers_bak'

#########
####BUTTONS
##########

ABOUT_BUTTON = {"EN":"ℹ️ About", "RU": "ℹ️ О программе"}
START_MESSAGE = "Welcome! Type /help to get help."
HELP_BUTTON = {"EN":"⁉️" + "Help", "RU": "⁉️ Помощь"}
CURRENCY_LIST_BUTTON = {"EN":"List of available currencies", "RU": "Список доступных валют"}
RATE_ME_BUTTON = {"EN" : "⭐️ Like me? Rate!", "RU": "⭐️ Нравится бот? Оцени!"}
EN_LANG_BUTTON = "🇬🇧 EN"
RU_LANG_BUTTON = "🇷🇺 RU"

##############
####MESSAGES
############

HELP_MESSAGE = {"EN": '''
This bot converts currencies.
Input format: \[amount] \[source currency] \[destination currency]

For example, to convert 99 U.S. Dollars 50 cents to Euros, type:
99.50 USD EUR

To see a list of available currencies and their codes, press the \"''' + CURRENCY_LIST_BUTTON["EN"] + '''\" button.
'''
,"RU":'''
Этот бот конвертирует валюты.
Формат ввода: \[количество единиц валюты] \[обозначение валюты, *из которой* надо перевести] \[обозначение валюты, *в которую* надо перевести]

Например, чтобы узнать, сколько евро в 99 долларах 50 центах, введите:
99.50 USD EUR

Чтобы увидеть список валют, доступных для конвертации, и их обозначений, нажмите кнопку \"''' + CURRENCY_LIST_BUTTON["RU"] + '''\".
'''
}

ABOUT_MESSAGE = {"EN": """*Currency Converter Bot*
_Created by:_ Highstaker a.k.a. OmniSable.
Source: https://github.com/Highstaker/Currency-converter-telegram-bot
Version: """ + ".".join([str(i) for i in VERSION_NUMBER]) + """
[My channel, where I post development notes and update news](https://telegram.me/highstakerdev).

This bot uses the [python-telegram-bot](https://github.com/leandrotoledo/python-telegram-bot) library.

Rates are received from ECB
"""
,"RU": """*Currency Converter Bot*
_Автор:_ Highstaker a.k.a. OmniSable.
По вопросам и предложениям обращайтесь в Телеграм (@OmniSable).
Исходный код [здесь](https://github.com/Highstaker/Currency-converter-telegram-bot)
Версия: """ + ".".join([str(i) for i in VERSION_NUMBER]) + """
[Мой канал, где я объявляю о новых версиях ботов](https://telegram.me/highstakerdev).

Этот бот написан на основе библиотеки [python-telegram-bot](https://github.com/leandrotoledo/python-telegram-bot).

Данные о курсах валют берутся с портала Европейского Центробанка.
"""
}

RATE_ME_MESSAGE = {"EN": """
You seem to like this bot. You can rate it [here](about:blank)!

Your ⭐️⭐️⭐️⭐️⭐️ would be really appreciated!
"""
,"RU": """
Нравится бот? Оцените его [здесь](about:blank)!

Буду очень рад хорошим отзывам! 8)
⭐️⭐️⭐️⭐️⭐️ 
"""
}

INVALID_FORMAT_MESSAGE = {"EN":"Invalid format! Use format \"\[amount] \[source currency] \[destination currency]\""
,"RU": "Неверный формат! Используйте формат \"\[количество единиц валюты] \[обозначение валюты, *из которой* надо перевести] \[обозначение валюты, *в которую* надо перевести]\""
}
UNKNOWN_CURRENCY_MESSAGE = {"EN": "Unknown currency: "
,"RU": "Неизвестная валюта: "
}

def split_list(alist,max_size=1):
	"""Yield successive n-sized chunks from l."""
	for i in range(0, len(alist), max_size):
		yield alist[i:i+max_size]

MAIN_MENU_KEY_MARKUP = [[CURRENCY_LIST_BUTTON],[HELP_BUTTON,ABOUT_BUTTON,RATE_ME_BUTTON],[EN_LANG_BUTTON,RU_LANG_BUTTON]]

################
###GLOBALS######
################

with open(path.join(path.dirname(path.realpath(__file__)), TOKEN_FILENAME),'r') as f:
	BOT_TOKEN = f.read().replace("\n","")

#############
##METHODS###
############

def is_number(s):
	'''
	If a string is a number, returns True
	'''
	try:
		float(s)
		return True
	except ValueError:
		return False

###############
###CLASSES#####
###############

class TelegramBot():
	"""The bot class"""

	LAST_UPDATE_ID = None

	#{chat_id: ["EN",]}
	subscribers = {}

	def __init__(self, token):
		super(TelegramBot, self).__init__()
		self.bot = telegram.Bot(token)
		#get list of all image files
		self.loadSubscribers()

	def languageSupport(self,chat_id,message):
		'''
		Returns a message depending on a language chosen by user
		'''
		if isinstance(message,str):
			result = message
		elif isinstance(message,dict):
			try:
				result = message[self.subscribers[chat_id][0]]
			except:
				result = message["EN"]
		elif isinstance(message,list):
			#could be a key markup
			result = list(message)
			for n,i in enumerate(message):
				result[n] = self.languageSupport(chat_id,i)
		else:
			result = " "
			
		# print(result)
		return result


	def loadSubscribers(self):
		'''
		Loads subscribers from a file
		'''
		try:
			with open(SUBSCRIBERS_BACKUP_FILE,'rb') as f:
				self.subscribers = pickle.load(f)
				print("self.subscribers",self.subscribers)
		except FileNotFoundError:
			logging.warning("Subscribers backup file not found. Starting with empty list!")

	def saveSubscribers(self):
		'''
		Saves a subscribers list to file
		'''
		with open(SUBSCRIBERS_BACKUP_FILE,'wb') as f:
			pickle.dump(self.subscribers, f, pickle.HIGHEST_PROTOCOL)
	
	def sendMessage(self,chat_id,text,key_markup=MAIN_MENU_KEY_MARKUP,preview=True):
		logging.warning("Replying to " + str(chat_id) + ": " + text)
		key_markup = self.languageSupport(chat_id,key_markup)
		while True:
			try:
				if text:
					self.bot.sendChatAction(chat_id,telegram.ChatAction.TYPING)
					self.bot.sendMessage(chat_id=chat_id,
						text=text,
						parse_mode='Markdown',
						disable_web_page_preview=(not preview),
						reply_markup=telegram.ReplyKeyboardMarkup(key_markup)
						)
			except Exception as e:
				if "Message is too long" in str(e):
					self.sendMessage(chat_id=chat_id
						,text="Error: Message is too long!"
						)
					break
				if ("urlopen error" in str(e)) or ("timed out" in str(e)):
					logging.error("Could not send message. Retrying! Error: " + str(e))
					sleep(3)
					continue
				else:
					logging.error("Could not send message. Error: " + str(e))
			break

	def sendPic(self,chat_id,pic):
		while True:
			try:
				logging.debug("Picture: " + str(pic))
				self.bot.sendChatAction(chat_id,telegram.ChatAction.UPLOAD_PHOTO)
				#set file read cursor to the beginning. This ensures that if a file needs to be re-read (may happen due to exception), it is read from the beginning.
				pic.seek(0)
				self.bot.sendPhoto(chat_id=chat_id,photo=pic)
			except Exception as e:
				logging.error("Could not send picture. Retrying! Error: " + str(e))
				continue
			break

	def getUpdates(self):
		'''
		Gets updates. Retries if it fails.
		'''
		#if getting updates fails - retry
		while True:
			try:
				updates = self.bot.getUpdates(offset=self.LAST_UPDATE_ID, timeout=3)
			except Exception as e:
				logging.error("Could not read updates. Retrying! Error: " + str(e))
				continue
			break
		return updates

	def FixerIO_GetData(self,parse):
		'''
		Gets currency data from fixer.io (Which in turn gets data from ECB)
		'''
		page = getHTML_specifyEncoding('https://api.fixer.io/latest?base=' + parse[1].upper() + '&symbols=' + parse[2].upper() 
			,method='replace')
		result = float( list(json.loads(page)['rates'].values())[0] ) * float(parse[0])
		result = parse[0] + " " + parse[1].upper() + " = " + str(result) + " " + parse[2].upper()
		return result


	def FixerIO_getCurrencyList(self):
		page = getHTML_specifyEncoding('https://api.fixer.io/latest')
		result = list(json.loads(page)['rates'].keys() ) + [ json.loads(page)['base'] ]
		result.sort()
		result = [i.upper() for i in result]
		return result

	def echo(self):
		bot = self.bot

		updates = self.getUpdates()

		for update in updates:
			chat_id = update.message.chat_id
			Message = update.message
			from_user = Message.from_user
			message = Message.text
			logging.warning("Received message: " + str(chat_id) + " " + from_user.username + " " + message)

			#register the user if not present in the subscribers list
			try:
				self.subscribers[chat_id]
			except KeyError:
				self.subscribers[chat_id] = ["EN"]

			try:
				if message:
					if message == "/start":
						self.sendMessage(chat_id=chat_id
							,text=self.languageSupport(chat_id,START_MESSAGE)
							)
					elif message == "/help" or message == self.languageSupport(chat_id,HELP_BUTTON):
						self.sendMessage(chat_id=chat_id
							,text=self.languageSupport(chat_id,HELP_MESSAGE)
							)
					elif message == "/about" or message == self.languageSupport(chat_id,ABOUT_BUTTON):
						self.sendMessage(chat_id=chat_id
							,text=self.languageSupport(chat_id,ABOUT_MESSAGE)
							)
					elif message == "/rate" or message == self.languageSupport(chat_id,RATE_ME_BUTTON):
						self.sendMessage(chat_id=chat_id
							,text=self.languageSupport(chat_id,RATE_ME_MESSAGE)
							)
					elif message == RU_LANG_BUTTON:
						self.subscribers[chat_id][0] = "RU"
						self.saveSubscribers()
						self.sendMessage(chat_id=chat_id
							,text="Сообщения бота будут отображаться на русском языке."
							)
					elif message == EN_LANG_BUTTON:
						self.subscribers[chat_id][0] = "EN"
						self.saveSubscribers()
						self.sendMessage(chat_id=chat_id
							,text="Bot messages will be shown in English."
							)
					elif message == self.languageSupport(chat_id,CURRENCY_LIST_BUTTON):
						result = self.languageSupport(chat_id,{"EN":"*Available currencies:* \n","RU":"*Доступные валюты:* \n"}) + "\n".join( [(i + ( " - " + self.languageSupport(chat_id,CURRENCY_NAMES[i]) if i in CURRENCY_NAMES else "" ) ) for i in self.FixerIO_getCurrencyList()] )
						self.sendMessage(chat_id=chat_id
							,text=str(result)
							)
					else:
						parse = message.split(" ")
						currency_list = self.FixerIO_getCurrencyList()

						if ( len(parse) != 3 ) or not is_number(parse[0]):
							result = self.languageSupport(chat_id,INVALID_FORMAT_MESSAGE)
						elif parse[1].upper() not in currency_list:
							result = self.languageSupport(chat_id,UNKNOWN_CURRENCY_MESSAGE) + parse[1].upper()
						elif parse[2].upper() not in currency_list:
							result = self.languageSupport(chat_id,UNKNOWN_CURRENCY_MESSAGE) + parse[2].upper()
						else:
							result = self.FixerIO_GetData(parse)
						self.sendMessage(chat_id=chat_id
							,text=str(result)
							)
			except Exception as e:
				logging.error("Message processing failed! Error: " + str(e))

			# Updates global offset to get the new updates
			self.LAST_UPDATE_ID = update.update_id + 1


def main():
	bot = TelegramBot(BOT_TOKEN)

	#main loop
	while True:
		bot.echo()

if __name__ == '__main__':
	main()