#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#TODO

VERSION_NUMBER = (0,3,3)

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
	"RUB": "Russian Rouble"
	,"USD": "U.S. Dollar"
	,"EUR": "Euro"
	,"SEK": "Swedish Krona"
	,"AUD": "Australian Dollar"
	,"NOK": "Norwegian Krone"
	,"CZK": "Czech Koruna"
	,"DKK": "Danish Krone"
	,"GBP": "British Pound Sterling"
	,"BGN": "Bulgarian Lev"
	,"BRL": "Brazilian Real"
	,"PLN": "Polish Zloty"
	,"NZD": "New Zealand Dollar"
	,"JPY": "Japanese Yen"
	,"CHF": "Swiss Franc"
	,"CAD": "Canadian Dollar"
}

#A filename of a file containing a token.
TOKEN_FILENAME = 'token'

#A path where subscribers list is saved.
SUBSCRIBERS_BACKUP_FILE = '/tmp/multitran_bot_subscribers_bak'


ABOUT_BUTTON = "ℹ️ About"
START_MESSAGE = "Welcome! Type /help to get help."
HELP_BUTTON = "⁉️" + "Help"
CURRENCY_LIST_BUTTON = "List of available currencies"

HELP_MESSAGE = '''
This bot converts currencies.
Input format: [amount] [source currency] [destination currency]

For example, to convert 99 U.S. Dollars 50 cents to Euros, type:
99.50 USD EUR

To see a list of available currencies and their codes, press the \"''' + CURRENCY_LIST_BUTTON + '''\" button.
'''

ABOUT_MESSAGE = """*Currency Converter Bot*
_Created by:_ Highstaker a.k.a. OmniSable.
Source: https://github.com/Highstaker/Currency-converter-telegram-bot
Version: """ + ".".join([str(i) for i in VERSION_NUMBER]) + """

This bot uses the python-telegram-bot library.
https://github.com/leandrotoledo/python-telegram-bot

Rates are received from ECB
"""



def split_list(alist,max_size=1):
	"""Yield successive n-sized chunks from l."""
	for i in range(0, len(alist), max_size):
		yield alist[i:i+max_size]

MAIN_MENU_KEY_MARKUP = [[CURRENCY_LIST_BUTTON],[HELP_BUTTON,ABOUT_BUTTON]]

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

	#{chat_id: [LANGUAGE_INDEX], ...}
	subscribers = {}

	def __init__(self, token):
		super(TelegramBot, self).__init__()
		self.bot = telegram.Bot(token)
		#get list of all image files
		self.loadSubscribers()

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

	def sendMessage(self,chat_id,text,key_markup=MAIN_MENU_KEY_MARKUP):
		logging.warning("Replying to " + str(chat_id) + ": " + text)
		while True:
			try:
				if text:
					self.bot.sendChatAction(chat_id,telegram.ChatAction.TYPING)
					self.bot.sendMessage(chat_id=chat_id,
						text=text,
						parse_mode='Markdown',
						reply_markup=telegram.ReplyKeyboardMarkup(key_markup)
						)
			except Exception as e:
				if "Message is too long" in str(e):
					self.sendMessage(chat_id=chat_id
						,text="Error: Message is too long!"
						)
					break
				else:
					logging.error("Could not send message. Retrying! Error: " + str(e))
					continue
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
				self.subscribers[chat_id] = 1

			try:
				if message:
					if message == "/start":
						self.sendMessage(chat_id=chat_id
							,text=START_MESSAGE
							)
					elif message == "/help" or message == HELP_BUTTON:
						self.sendMessage(chat_id=chat_id
							,text=HELP_MESSAGE
							)
					elif message == "/about" or message == ABOUT_BUTTON:
						self.sendMessage(chat_id=chat_id
							,text=ABOUT_MESSAGE
							)
					elif message == CURRENCY_LIST_BUTTON:
						result = "*Available currencies:* \n" + "\n".join( [(i + ( " - " + CURRENCY_NAMES[i] if i in CURRENCY_NAMES else "" ) ) for i in self.FixerIO_getCurrencyList()] )
						self.sendMessage(chat_id=chat_id
							,text=str(result)
							)
					else:
						parse = message.split(" ")
						currency_list = self.FixerIO_getCurrencyList()

						if ( len(parse) != 3 ) or not is_number(parse[0]):
							result = "Invalid format! Use format \"[number] [From this currency] [To this currency]\""
						elif parse[1].upper() not in currency_list:
							result = "Unknown currency: " + parse[1].upper()
						elif parse[2].upper() not in currency_list:
							result = "Unknown currency: " + parse[2].upper()
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