#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#TODO
#-Add more sources. ECB is not sufficient
#+Graphs/charts over days
#-error handling in graphs
#-don't forget to turn the try back on in echo()
#+remove doubles from a list of graph points
#-limits the number of points on the graph, to prevent too many queries.
#-put graph-getting into a separate process to prevent bot chunking
#-prevent bot from getting messages from a user while it processes graph

VERSION_NUMBER = (0,6,3)

import logging
import telegram
from time import time
import sys
import os
from os import path, listdir, walk
import socket
import pickle #module for saving dictionaries to file
from bs4 import BeautifulSoup #HTML parser
import re
import json
from datetime import date, timedelta, datetime
import matplotlib.pyplot as plt

from webpage_reader import getHTML_specifyEncoding

#if a connection is lost and getUpdates takes too long, an error is raised
socket.setdefaulttimeout(30)

logging.basicConfig(format = u'[%(asctime)s] %(filename)s[LINE:%(lineno)d]# %(levelname)-8s  %(message)s', 
	level = logging.WARNING)


############
##PARAMETERS
############

TEMP_PLOT_IMAGE_FILE_PATH = '/tmp/001.png'

MAXIMUM_DOTS_PER_CHART = 30

CURRENCY_NAMES = {
	"RUB": {"EN":"Russian Rouble","RU": "Российский рубль"}
	,"USD": {"EN":"U.S. Dollar","RU": "Доллар США"}
	,"EUR": {"EN":"Euro", "RU": "Евро"}
	,"SEK": {"EN":"Swedish Krona","RU": "Шведская крона"}
	,"AUD": {"EN":"Australian Dollar","RU":"Австралийский доллар"}
	,"NOK": {"EN":"Norwegian Krone","RU":"Норвежская крона"}
	,"CZK": {"EN":"Czech Koruna","RU":"Чешская крона"}
	,"DKK": {"EN":"Danish Krone","RU":"Датская крона"}
	,"GBP": {"EN":"British Pound Sterling","RU":"Британский фунт стерлингов"}
	,"BGN": {"EN":"Bulgarian Lev","RU":"Болгарский лев"}
	,"BRL": {"EN":"Brazilian Real","RU":"Бразильский реал"}
	,"PLN": {"EN":"Polish Zloty","RU":"Польский злотый"}
	,"NZD": {"EN":"New Zealand Dollar","RU":"Новозеландский доллар"}
	,"JPY": {"EN":"Japanese Yen","RU":"Японская йена"}
	,"CHF": {"EN":"Swiss Franc","RU":"Швейцарский франк"}
	,"CAD": {"EN":"Canadian Dollar","RU":"Канадский доллар"}
	,"ZAR":	{"EN":"South African rand","RU":"Южноафриканский рэнд"}
	,"SGD": {"EN":"Singaporean Dollar","RU":"Сингапурский доллар"}
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

To see the latest rate, use: \[amount] \[source currency] \[destination currency]

For example, to convert 99 U.S. Dollars 50 cents to Euros, type:
_99.50 USD EUR_

If you want to see a rate on a certain day in the past, use: \[amount] \[source currency] \[destination currency] \[YYYY-MM-DD]

For example, to convert 99 U.S. Dollars 50 cents to Euros using a rate of September 6, 2012, type:
_99.50 USD EUR 2012-09-06_

To see a list of available currencies and their codes, press the \"''' + CURRENCY_LIST_BUTTON["EN"] + '''\" button.

Additionally, you may request a chart showing rates for a currency pair in a certain range of dates. For example, to see the graph for USD/EUR pair between September 25 and October 7, 2014, type:
_graph USD EUR 2014-09-25 2014-10-07_
'''
,"RU":'''
Этот бот конвертирует валюты.
Чтобы увидеть последний курс, введите: \[количество единиц валюты] \[обозначение валюты, *из которой* надо перевести] \[обозначение валюты, *в которую* надо перевести]

Например, чтобы узнать, сколько евро в 99 долларах 50 центах, введите:
_99.50 USD EUR_

Чтобы узнать курс в определённый день в прошлом, введите: \[количество единиц валюты] \[обозначение валюты, *из которой* надо перевести] \[обозначение валюты, *в которую* надо перевести] \[ГГГГ-ММ-ДД]

Например, чтобы узнать, сколько евро в 99 долларах 50 центах по состоянию на 6 сентября 2012 года, введите:
_99.50 USD EUR 2012-09-06_

Чтобы увидеть список валют, доступных для конвертации, и их обозначений, нажмите кнопку \"''' + CURRENCY_LIST_BUTTON["RU"] + '''\".

Также можно отобразить график динамики курса валют. К примеру, чтобы увидеть график динамики курса доллара по отношению к евро в период с 25 сентября по 7 октября 2014 года, введите:
_graph USD EUR 2014-09-25 2014-10-07_

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
You seem to like this bot. You can rate it [here](https://storebot.me/bot/omnicurrencyexchangebot)!

Your ⭐️⭐️⭐️⭐️⭐️ would be really appreciated!
"""
,"RU": """
Нравится бот? Оцените его [здесь](https://storebot.me/bot/omnicurrencyexchangebot)!

Буду очень рад хорошим отзывам! 8)
⭐️⭐️⭐️⭐️⭐️ 
"""
}

INVALID_FORMAT_MESSAGE = {"EN":"Invalid format! Use format \"\[amount] \[source currency] \[destination currency]\""
,"RU": "Неверный формат! Используйте формат \"\[количество единиц валюты] \[обозначение валюты, *из которой* надо перевести] \[обозначение валюты, *в которую* надо перевести]\""
}
UNKNOWN_CURRENCY_MESSAGE = {"EN": "Unknown currency or no data available for this currency for the given date: "
,"RU": "Неизвестная валюта, или нет данных для этой валюты для указанной даты: "
}

RESULT_DATE_MESSAGE = {"EN": "This rate is given for this date: ", "RU": "Курс указан по состоянию на: "}

DATE_TOO_OLD_MESSAGE = {"EN": "The given date is too old. There are no results available for it." , "RU": "Дата слишком давняя. Для неё нет результатов"}

COULD_NOT_FIND_DATA_MESSAGE = {"EN": "Could not find any data. Is the date format correct?", "RU": "Не могу найти данные. Верный ли формат даты?"}

DATE_INCORRECT_MESSAGE  = {"EN":"Date is incorrect!", "RU": "Неверная дата!"}

UNKNOWN_ERROR_MESSAGE = {"EN": "Unknown error!", "RU": "Неизвестная ошибка!"}

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
					logging.error("Could not send message. Retrying! Error: " + str(sys.exc_info()[-1].tb_lineno) + ": " + str(e))
					sleep(3)
					continue
				else:
					logging.error("Could not send message. Error: " + str(sys.exc_info()[-1].tb_lineno) + ": " + str(e))
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
				logging.error("Could not send picture. Retrying! Error: " + str(sys.exc_info()[-1].tb_lineno) + ": " + str(e))
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
				logging.error("Could not read updates. Retrying! Error: " + str(sys.exc_info()[-1].tb_lineno) + ": " + str(e))
				continue
			break
		return updates

	def FixerIO_GetData(self,parse,chat_id=None):
		'''
		Gets currency data from fixer.io (Which in turn gets data from ECB)
		'''
		if len(parse)==4:
			date=str(parse[3])
		else:
			date="latest"

		page = getHTML_specifyEncoding('https://api.fixer.io/' + date + '?base=' + parse[1].upper() + '&symbols=' + parse[2].upper() 
			,method='replace')
		if "Invalid base" in page:
			result = {'error':"Invalid base"}
			print("Invalid base")#debug
		elif "date too old" in page.lower():
			result= {'error': self.languageSupport(chat_id,DATE_TOO_OLD_MESSAGE)}
		elif "not found" in page.lower():
			result={'error': self.languageSupport(chat_id,COULD_NOT_FIND_DATA_MESSAGE)}
		elif "invalid date" in page.lower():
			result={'error': self.languageSupport(chat_id,DATE_INCORRECT_MESSAGE)}
		else:
			result = json.loads(page)

		return result


	def FixerIO_getCurrencyList(self):
		page = getHTML_specifyEncoding('https://api.fixer.io/latest')
		result = list(json.loads(page)['rates'].keys() ) + [ json.loads(page)['base'] ]
		result.sort()
		result = [i.upper() for i in result]
		return result

	def getData(self,parse,chat_id=None):
		'''
		Universal data getter handling several sources
		'''

		page = self.FixerIO_GetData(parse)
		if 'error' in page.keys():
			pass
			if "Invalid base" in page['error']:
				result = self.languageSupport(chat_id,UNKNOWN_CURRENCY_MESSAGE) + parse[1].upper()
			else:
				result = page['error']
		else:
			try:
				rate = float(list(page['rates'].values())[0]) * float(parse[0])
				date = page['date']
				result = {'rate' : rate, 'date': date}
			except IndexError:
				result = self.languageSupport(chat_id,UNKNOWN_CURRENCY_MESSAGE) + parse[2].upper()

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

			# try:
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
					#Parse the message into a list, separating with spaces and deleting the empties(they may appear if you type several consecutive spaces)
					parse = [i for i in message.split(" ") if i]

					if parse[0].lower() == 'graph':
						#plot
						parse.pop(0)
						result = "Plotting"

						if len(parse) != 4:
							result = "Invalid format!"
						else:

							def daterange(start_date, end_date):
								'''
								Generator returning dates in given range
								'''
								for n in range(int ((end_date - start_date).days) +1):
									yield start_date + timedelta(n)

							def create_plot(x,y,x_ticks=None,Title=""):
								fig, ax = plt.subplots()  # create figure & 1 axis
								ax.plot(x,y,'k',x,y,'bo')
								if x_ticks:
									plt.xticks(x,x_ticks)
								plt.title(Title)
								plt.xlabel('Date')
								plt.ylabel('Rates')
								plt.grid(True)
								fig.autofmt_xdate(bottom=0.2, rotation=70, ha='right')
								fig.savefig(TEMP_PLOT_IMAGE_FILE_PATH)
								plt.close(fig)

							def days_since_UNIX_era(Date):
								'''
								Returns the amount of days that have passed since the start of UNIX era on a given day
								'''
								return (Date - date(1970,1,1)).days

							def rm_doubles(seq,respective_seq=None):
								'''
								Remove duplicates from list,preserving order.
								If respective_seq is specified, the indicies respective to the ones removed from seq will be removed from respective_seq as well.
								'''
								seen = set()
								seen_add = seen.add
								if not respective_seq:
									return [ x for x in seq if not (x in seen or seen_add(x))]
								else:
									rm_indexes = []
									seq_new = []
									for n,x in enumerate(seq):
										if x in seen:
											rm_indexes.append(n)
										else:
											seq_new.append(x)
											seen_add(x)
									print("rm_indexes",rm_indexes)
									rm_indexes.sort(reverse=True)
									for i in rm_indexes:
										respective_seq.pop(i)
									return seq_new, respective_seq

							try:
								start_date = datetime.strptime(parse[2],"%Y-%m-%d").date()
								end_date = datetime.strptime(parse[3],"%Y-%m-%d").date()
							except:
								result = "Invalid date format!"
							else:
								UNIX_dates = []
								rates = []
								text_dates = []

								date_range = list(daterange(start_date,end_date))

								while len(date_range)>MAXIMUM_DOTS_PER_CHART:
									#remove every second entry until the range is smaller than the maximum
									date_range = date_range[::2]

								try:
									for DATE in date_range:
										pass
										data = self.getData(['1'] + parse[:2]+ [DATE.strftime("%Y-%m-%d")],chat_id=chat_id)
										text_dates += [ data['date'] ]
										UNIX_dates += [days_since_UNIX_era(datetime.strptime( data['date'] , "%Y-%m-%d").date())]
										rates += [data['rate']]

									text_dates = rm_doubles(text_dates)
									UNIX_dates, rates = rm_doubles(UNIX_dates,rates)


									print(text_dates)#debug
									print(UNIX_dates)#debug
									print(rates)#debug

									create_plot(UNIX_dates,rates,x_ticks=text_dates,Title=parse[0].upper()+"/"+parse[1].upper()+" rates")

									with open(TEMP_PLOT_IMAGE_FILE_PATH,'rb') as pic:
										self.sendPic(chat_id=chat_id,pic=pic)

									result = ""
								except Exception as e:
									result = "Error! Could not draw graph: " + str(e)

					else:
						#user asks for one rate

						if not ( len(parse) == 3 or len(parse) == 4) or not is_number(parse[0]):
							result = self.languageSupport(chat_id,INVALID_FORMAT_MESSAGE)
						else:
							result = self.getData(parse,chat_id=chat_id)

							if isinstance(result,str):
								pass
							elif isinstance(result, dict):
								result = parse[0] + " " + parse[1].upper() + " = " + str(result['rate'])  + " " + parse[2].upper() + "\n*" + self.languageSupport(chat_id, RESULT_DATE_MESSAGE) + "*" + str(result['date']) 
							else:
								result = self.languageSupport(chat_id,UNKNOWN_ERROR_MESSAGE)

					self.sendMessage(chat_id=chat_id
						,text=str(result)
						)
			# except Exception as e:
			# 	logging.error("Message processing failed! Error: " + str(sys.exc_info()[-1].tb_lineno) + ": " + str(e))

			# Updates global offset to get the new updates
			self.LAST_UPDATE_ID = update.update_id + 1


def main():
	bot = TelegramBot(BOT_TOKEN)

	#main loop
	while True:
		bot.echo()

if __name__ == '__main__':
	main()