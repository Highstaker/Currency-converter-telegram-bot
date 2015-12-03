#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-
#TODO
#-custom bookmarks

VERSION_NUMBER = (0,7,3)

import random
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
from multiprocessing import Process, Queue, Lock
import xml.etree.ElementTree as ET

from webpage_reader import getHTML_specifyEncoding

#if a connection is lost and getUpdates takes too long, an error is raised
socket.setdefaulttimeout(30)

logging.basicConfig(format = u'[%(asctime)s] %(filename)s[LINE:%(lineno)d]# %(levelname)-8s  %(message)s', 
	level = logging.WARNING)


############
##PARAMETERS
############

TEMP_PLOT_IMAGE_FILE_PATH = '/tmp/'

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
SUBSCRIBERS_BACKUP_FILE = 'omni_currency_bot_subscribers_bak.save'

#A subscribers list assigned to a new user.
#["EN",source]
INITIAL_SUBSCRIBERS_LIST = ["EN",'FixerIO']

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

You may request a chart showing rates for a currency pair in a certain range of dates. 
To get a chart for EUR/USD pair for the previous 3 months, type:
_g eur usd 3m_

Available ranges are:
*1m* - one month
*3m* - three months
*6m* - six months
*1y* - one year
*2y* - two years

You may also request a chart with rates for a period before a certain date. For example, if you want rates for 3 months before May 9 2014, type:
_g eur usd 3m 2014-05-09_

You can choose a source of information by pressing a respective button.

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

Также можно отобразить график динамики курса валют. К примеру, чтобы увидеть график динамики курса доллара по отношению к евро за последние три месяца, введите:
_g eur usd 3m_

Доступные периоды:
*1m* - один месяц
*3m* - три месяца
*6m* - шесть месяцев
*1y* - один год
*2y* - два года

Можно также узнать котировки за период до определённой даты. Например, чтобы увидеть курс за 3 месяца до 9 мая 2014 года: введите
_g eur usd 3m 2014-05-09_

Вы можете выбрать источник котировок, нажав на кнопку _Source: (источник)_
'''
}

ABOUT_MESSAGE = {"EN": """*Currency Converter Bot*
_Created by:_ Highstaker a.k.a. OmniSable.
Source: https://github.com/Highstaker/Currency-converter-telegram-bot
Version: """ + ".".join([str(i) for i in VERSION_NUMBER]) + """
[My channel, where I post development notes and update news](https://telegram.me/highstakerdev).

This bot uses the [python-telegram-bot](https://github.com/leandrotoledo/python-telegram-bot) library.

Rates are received from European Central Bank or Central Bank of Russian Federation
"""
,"RU": """*Currency Converter Bot*
_Автор:_ Highstaker a.k.a. OmniSable.
По вопросам и предложениям обращайтесь в Телеграм (@OmniSable).
Исходный код [здесь](https://github.com/Highstaker/Currency-converter-telegram-bot)
Версия: """ + ".".join([str(i) for i in VERSION_NUMBER]) + """
[Мой канал, где я объявляю о новых версиях ботов](https://telegram.me/highstakerdev).

Этот бот написан на основе библиотеки [python-telegram-bot](https://github.com/leandrotoledo/python-telegram-bot).

Данные о курсах валют берутся с портала Европейского Центробанка или Центрального Банка РФ.
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

RATES_ARE_TAKEN_FROM_MESSAGE = {"EN": "Rates are taken from: ", "RU": "Источник: "}

ECB_MESSAGE ={"EN": 'European Central Bank', "RU": 'Европейский Центробанк'}

CBRU_MESSAGE = {"EN": 'Central Bank of Russian Federation', "RU": "Центробанк РФ"}

def split_list(alist,max_size=1):
	"""Yield successive n-sized chunks from l."""
	for i in range(0, len(alist), max_size):
		yield alist[i:i+max_size]

MAIN_MENU_KEY_MARKUP = [
[CURRENCY_LIST_BUTTON]
,[HELP_BUTTON,ABOUT_BUTTON,RATE_ME_BUTTON]
,[EN_LANG_BUTTON,RU_LANG_BUTTON]
,["Source: ECB", "Source: CBRU"]
]

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

	#{chat_id: ["EN",source]}
	subscribers = {}

	#dictionary containing process and queue id for graph-plotting processes
	graph_processes = {}

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

	def assignBotLanguage(self,chat_id,language):
		'''
		Assigns bot language to a subscribers list and saves to disk
		'''
		self.subscribers[chat_id][0] = language
		self.saveSubscribers()

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
			# print("Invalid base")#debug
		elif "date too old" in page.lower():
			result= {'error': self.languageSupport(chat_id,DATE_TOO_OLD_MESSAGE)}
		elif "not found" in page.lower():
			result={'error': self.languageSupport(chat_id,COULD_NOT_FIND_DATA_MESSAGE)}
		elif "invalid date" in page.lower():
			result={'error': self.languageSupport(chat_id,DATE_INCORRECT_MESSAGE)}
		else:
			result = json.loads(page)

		return result

	def CBRU_GetData(self,parse,chat_id=None,graph=False):
		'''
		Gets currency data from Russian Central Bank
		'''

		def date_from_std_to_CBRU(date):
			'''
			Standard format (YYYY-MM-DD) to CBRU query format (DD/MM/YYYY)
			'''
			return "/".join(str(date).split("-")[::-1])

		def date_from_CBRU_to_std(date):
			'''
			CBRU return format (DD.MM.YYYY) to Standard format (YYYY-MM-DD)
			'''
			return "-".join(str(date).replace("/",".").split(".")[::-1])

		if not graph:
			if len(parse)==4:
				date = date_from_std_to_CBRU(parse[3])
			else:
				date = ""

			page = getHTML_specifyEncoding( 'http://www.cbr.ru/scripts/XML_daily.asp' + (('?date_req=' + date) if date else "")
				,encoding='windows-1251'
				,method="replace")
			Nominal = float(parse[0])
			currency_from = parse[1].upper()
			currency_to = parse[2].upper()

			page_root = ET.fromstring(page)
			try:
				Valute_from = page_root.findall(".//*[CharCode=\'"+ currency_from+ "\']") if currency_from != "RUB" else None
				value_from = float(Valute_from[0].findall('.//Value')[0].text.replace(",",".")) if currency_from != "RUB" else 1
				nominal_from = float(Valute_from[0].findall('.//Nominal')[0].text.replace(",",".")) if currency_from != "RUB" else 1

				Valute_to= page_root.findall(".//*[CharCode=\'"+ currency_to+ "\']") if currency_to != "RUB" else None
				value_to = float(Valute_to[0].findall('.//Value')[0].text.replace(",",".")) if currency_to != "RUB" else 1
				nominal_to = float(Valute_to[0].findall('.//Nominal')[0].text.replace(",",".")) if currency_to != "RUB" else 1

				rate = Nominal * (value_from/nominal_from)/(value_to/nominal_to)

				print("date_from_CBRU_to_std( page_root.attrib['Date'] ) ",date_from_CBRU_to_std( page_root.attrib['Date'] ) )#debug
				return {'rate':rate, 'date': date_from_CBRU_to_std( page_root.attrib['Date'] )}
			except IndexError:
				return {'error': "Unknown error"}



	def getData(self,parse,chat_id=None,graph=False):
		'''
		Universal data getter handling several sources
		'''

		result=""

		source=self.subscribers[chat_id][1]

		if source=="FixerIO":
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

		elif source=="CBRU":
			result1 = self.CBRU_GetData(parse)
			if 'error' in result1.keys():
				result = self.languageSupport(chat_id,UNKNOWN_ERROR_MESSAGE)
			else:
				result = result1

		return result

	def FixerIO_getCurrencyList(self):
		'''
		Gets list of currencies available from ECB.
		'''
		page = getHTML_specifyEncoding('https://api.fixer.io/latest')
		result = list(json.loads(page)['rates'].keys() ) + [ json.loads(page)['base'] ]
		result.sort()
		result = [i.upper() for i in result]
		return result

	def CBRU_getCurrencyList(self):
		'''
		Gets list of currencies available from CBRU.
		'''
		page = getHTML_specifyEncoding('http://www.cbr.ru/scripts/XML_daily.asp',
			encoding='windows-1251'
			,method="replace")
		result = [i.text.upper() for i in ET.fromstring(page).findall(".//CharCode")]
		result.sort()
		return result

	def getCurrencyList(self,chat_id):
		'''
		Get list of currencies available from the given source
		'''

		result = ""
		source=self.subscribers[chat_id][1]

		if source=="FixerIO":
			result = self.FixerIO_getCurrencyList()
		elif source=="CBRU":
			result = self.CBRU_getCurrencyList()

		return result

	def setSource(self,chat_id,source):
		'''
		Sets the tates source for the current user
		'''
		if "ECB" in source:
			self.subscribers[chat_id][1]= "FixerIO"
			self.saveSubscribers()
		elif "CBRU" in source:
			self.subscribers[chat_id][1]= "CBRU"
			self.saveSubscribers()
		else:
			pass

	def graph_plotting_process(self,chat_id,q,parse):
		'''
		A process that plots a graph
		'''
		if len(parse) < 2 or len(parse) > 5:
			result = "Invalid format!"
		else:

			def daterange(start_date, end_date, only_days=[0,1,2,3,4,5,6]):
				'''
				Returns dates in given range. May be set up to return only certain days of week (specified in `only_days`, Monday is 0, Sunday is 6).
				'''
				daterange = []
				for n in range(int ((end_date - start_date).days) +1):
					date = start_date + timedelta(n)
					if date.weekday() in only_days:
						daterange += [date]
				return daterange

			def create_plot(x,y,x_ticks=None,Title=""):
				import matplotlib
				# Force matplotlib to not use any Xwindows backend.
				matplotlib.use('Agg')
				import matplotlib.pyplot as plt
				fig, ax = plt.subplots()  # create figure & 1 axis
				ax.plot(x,y,'k',x,y,'bo')
				if x_ticks:
					plt.xticks(x,x_ticks)
				plt.title(Title)
				plt.xlabel('Date')
				plt.ylabel('Rates')
				plt.grid(True)
				fig.autofmt_xdate(bottom=0.2, rotation=70, ha='right')
				savefilename = path.join(TEMP_PLOT_IMAGE_FILE_PATH, hex(random.getrandbits(128) )[2:] + ".png" )
				fig.savefig( savefilename )
				plt.close(fig)
				return savefilename

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
					# print("rm_indexes",rm_indexes)#debug
					rm_indexes.sort(reverse=True)
					for i in rm_indexes:
						respective_seq.pop(i)
					return seq_new, respective_seq

			try:
				if len(parse) > 3:
					end_date = datetime.strptime(parse[3],"%Y-%m-%d").date()
				else:
					end_date = date.today()
			except:
				result = "Invalid date format!"
			else:
				try:
					if parse[2] == "1m":
						start_date = end_date - timedelta(weeks=4)
						date_range = daterange(start_date,end_date,only_days=[0,1,2,3,4])
					elif parse[2] == "3m":
						start_date = end_date - timedelta(weeks=12)
						date_range = daterange(start_date,end_date,only_days=[0,4])
					elif parse[2] == "6m":
						start_date = end_date - timedelta(weeks=24)
						date_range = daterange(start_date,end_date,only_days=[0])
					elif parse[2] in ["1y","12m"]:
						start_date = end_date - timedelta(weeks=49)
						date_range = daterange(start_date,end_date,only_days=[0])
						date_range = date_range[::2]
					elif parse[2] in ["2y","24m"]:
						start_date = end_date - timedelta(weeks=97)
						date_range = daterange(start_date,end_date,only_days=[0])
						date_range = date_range[::4]
					else:
						raise Exception('Wrong daterange parameter')

				except Exception as e:
					if str(e) == 'Wrong daterange parameter':
						result = "wrong daterange parameter!"
					else:
						logging.error("Daterange error: " + str(e))
						result = "Unknown error"
				else:
					#got a parameter right, drawing
					UNIX_dates = []
					rates = []
					text_dates = []

					try:
						for DATE in date_range:
							data = self.getData(['1'] + parse[:2]+ [DATE.strftime("%Y-%m-%d")],chat_id=chat_id)
							text_dates += [ data['date'] ]
							UNIX_dates += [days_since_UNIX_era(datetime.strptime( data['date'], "%Y-%m-%d").date())]
							rates += [data['rate']]

						text_dates = rm_doubles(text_dates)
						UNIX_dates, rates = rm_doubles(UNIX_dates,rates)

						save_filename = create_plot(UNIX_dates,rates,x_ticks=text_dates,Title=parse[0].upper()+"/"+parse[1].upper()+" rates")

						result = "send_pic"


					except Exception as e:
						logging.error("Error! Could not draw graph: " + str(e))
						result = "Error! Could not draw graph!"

		try:
			q.put( (result,save_filename) )
		except UnboundLocalError:
			q.put( (result,) )


	def echo(self):
		bot = self.bot

		updates = self.getUpdates()

		#send messages generated by terminated graph-plotting processes and clean the database
		tempUser = dict(self.graph_processes) #because error occurs if dictionary change size during loop
		for user in tempUser:
			if not self.graph_processes[user][0].is_alive():
				#proc_result is a tuple of ('send_pic',file_path) if the process successfully generated a chart, and a one-element tuple with result message to be shown if it failed.
				proc_result = self.graph_processes[user][1].get()
				print("proc_result",proc_result)
				if proc_result[0] == "send_pic":
					with open(proc_result[1],'rb') as pic:
						self.sendPic(chat_id=user,pic=pic)
						self.sendMessage(chat_id=user,text=self.languageSupport(user,RATES_ARE_TAKEN_FROM_MESSAGE) + self.languageSupport(user,ECB_MESSAGE if self.subscribers[user][1]=="FixerIO" else CBRU_MESSAGE) )
					os.remove(proc_result[1])#I don't need a graph once it is sent. Delete the temporary file
				else:
					self.sendMessage(chat_id=user,text=str(proc_result[0]))
				logging.warning('deleting graph process for user ' + str(user))
				del self.graph_processes[user]
		del tempUser #freeing memory

		#main message processing routine
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
				self.subscribers[chat_id] = INITIAL_SUBSCRIBERS_LIST

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
						self.assignBotLanguage(chat_id,'RU')
						self.sendMessage(chat_id=chat_id
							,text="Сообщения бота будут отображаться на русском языке."
							)
					elif message == EN_LANG_BUTTON:
						self.assignBotLanguage(chat_id,'EN')
						self.sendMessage(chat_id=chat_id
							,text="Bot messages will be shown in English."
							)
					elif "Source:" in message:
						self.setSource(chat_id,message)
						self.sendMessage(chat_id=chat_id
							,text=self.languageSupport(chat_id,{"EN":"Source is set to ","RU":"Иcточник установлен на "}) + message.replace("Source:","")
							)
					elif message == self.languageSupport(chat_id,CURRENCY_LIST_BUTTON):
						result = self.languageSupport(chat_id,{"EN":"*Available currencies:* \n","RU":"*Доступные валюты:* \n"}) + "\n".join( [(i + ( " - " + self.languageSupport(chat_id,CURRENCY_NAMES[i]) if i in CURRENCY_NAMES else "" ) ) for i in self.getCurrencyList(chat_id)] ) + self.languageSupport(chat_id,RATES_ARE_TAKEN_FROM_MESSAGE) + "\n\n" + self.languageSupport(chat_id,RATES_ARE_TAKEN_FROM_MESSAGE) + self.languageSupport(chat_id,ECB_MESSAGE if self.subscribers[chat_id][1]=="FixerIO" else CBRU_MESSAGE)  
						self.sendMessage(chat_id=chat_id
							,text=str(result)
							)
					else:
						#Parse the message into a list, separating with spaces and deleting the empties(they may appear if you type several consecutive spaces)
						parse = [i for i in message.split(" ") if i]

						if parse[0].lower() in ['graph','g']:
							#plot
							parse.pop(0)

							try:
								if self.graph_processes[chat_id][0].is_alive():
									self.sendMessage(chat_id=chat_id
										,text="Your previous chart query is still being processed. Please wait for the processing to finish before sending another one!"
										)

							except KeyError:
								q = Queue()
								p = Process(target=self.graph_plotting_process, args=(chat_id,q,parse,))
								self.graph_processes[chat_id]=(p,q)
								p.start()
							
						else:
							#user asks for one rate

							if not ( len(parse) == 3 or len(parse) == 4) or not is_number(parse[0]):
								result = self.languageSupport(chat_id,INVALID_FORMAT_MESSAGE)
							else:
								result = self.getData(parse,chat_id=chat_id)

								if isinstance(result,str):
									pass
								elif isinstance(result, dict):
									result = parse[0] + " " + parse[1].upper() + " = " + str(result['rate'])  + " " + parse[2].upper() + "\n*" + self.languageSupport(chat_id, RESULT_DATE_MESSAGE) + "*" + str(result['date']) + "\n" + self.languageSupport(chat_id,RATES_ARE_TAKEN_FROM_MESSAGE) + self.languageSupport(chat_id,ECB_MESSAGE if self.subscribers[chat_id][1]=="FixerIO" else CBRU_MESSAGE)  
								else:
									result = self.languageSupport(chat_id,UNKNOWN_ERROR_MESSAGE)

							self.sendMessage(chat_id=chat_id
								,text=str(result)
								)
			except Exception as e:
				logging.error("Message processing failed! Error: " + str(sys.exc_info()[-1].tb_lineno) + ": " + str(e))

			# Updates global offset to get the new updates
			self.LAST_UPDATE_ID = update.update_id + 1


def main():
	bot = TelegramBot(BOT_TOKEN)

	#main loop
	while True:
		bot.echo()

if __name__ == '__main__':
	main()