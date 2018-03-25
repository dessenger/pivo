import serial
import csv
import datetime 
import paho.mqtt.client as mqtt
import json
import time

import os
import sys
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

recipients = ['mails you want to notify, example@example.xyz]

COMMASPACE = ', '

THINGSBOARD_HOST = 'demo.thingsboard.io'
ACCESS_TOKEN = 'YOUR TOKEN'

sensor_data = {'teplotaAktual': 0, 'teplotaPrirustek': 0}

client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)
client.connect(THINGSBOARD_HOST, 1883, 60)
client.loop_start()

cnt = 0
cntMin = 0
casStart = str(datetime.datetime.now())

tempSec = [0,0]
tempMin = [0,0]
temp = 0

teplotaPrirustek = 0

arduinoData = serial.Serial(port = '/dev/ttyACM0', baudrate = 115200)

def updateTemp():
	global teplotaAktual
	for i in range(20):
		while (arduinoData.inWaiting()==0): 
			time.sleep(0.0001)
		try:
			temp = float(arduinoData.readline().strip())
		except ValueError:
			print('tohle jsem nechytil...')
		try:
			tempSec.append(temp)
		except:
			pass
		if len(tempSec)>20:
			tempSec.pop(0)
		teplotaAktual = round(sum(tempSec)/len(tempSec), 2)
	return teplotaAktual
def tempMinList():
	tempMin.append(teplotaAktual)
	if len(tempMin)>59:
		tempMin.pop(0)
	return tempMin
def CSVlog(cntMin):
	if (cnt%60 == 0):
		print('Zapisuji data do CSV')
		csvPayload = [teplotaAktual, teplotaPrirustek, cntMin]
		with open ('graf.csv', 'a') as csvfile:
			writer = csv.writer(csvfile)
			writer.writerow(csvPayload)
		cntMin = cntMin + 1
		print("Zapsana data do CSV")

def Thingsboard():
	try:
		sensor_data['teplotaAktual'] = teplotaAktual
		sensor_data['teplotaPrirustek'] = teplotaPrirustek
		client.publish('v1/devices/me/telemetry', json.dumps(sensor_data), 1)	
	except:
		print('nepodarilo se odeslat data na Thingsboard')

def udelejZapis():
	file = open('zapis.txt', 'w')
	file.write('Zápis z vaření Nerudného ležáku \n \n')
	file.write('Začátek vaření:\t' + casStart + '\n')
	file.write('Konec vaření:\t' + casKonec + '\n')
	file.write('Celková doba vaření:\t' + celkovaDoba)
	file.close()

def prirustek_teploty_za_min(tempMin):
	prvniCislo = tempMin[0]
	posledniCislo = tempMin[-1]
	teplotaPrirustek = round((posledniCislo - prvniCislo), 2)
	#print(str(prvniCislo) + '\t' + str(posledniCislo) + '\t' + str(teplotaPrirustek))
	return teplotaPrirustek

def mailni():
	#global recipients
	print('Posilam mail...')
	sender = 'Mail that sends the message'
	gmail_password = 'password'
	# Create the enclosing (outer) message
	outer = MIMEMultipart()
	outer['Subject'] = 'Automaticka zprava: Nerudny Lezak'
	outer['To'] = COMMASPACE.join(recipients)
	outer['From'] = sender
	outer.preamble = 'Automaticka zprava z vareni.\n'

	# List of attachments
	attachments = ['graf.csv','zapis.txt']

	# Add the attachments to the message
	for file in attachments:
		try:
			with open(file, 'rb') as fp:
				msg = MIMEBase('application', "octet-stream")
				msg.set_payload(fp.read())
			encoders.encode_base64(msg)
			msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file))
			outer.attach(msg)
		except:
			print("Unable to open one of the attachments. Error: ", sys.exc_info()[0])
			raise

	composed = outer.as_string()

    # Send the email
	try:
		with smtplib.SMTP('smtp.gmail.com', 587) as s:
			s.ehlo()
			s.starttls()
			s.ehlo()
			s.login(sender, gmail_password)
			s.sendmail(sender, recipients, composed)
			s.close()
		print("Email poslan!")
	except:
		print("Unable to send the email. Error: ", sys.exc_info()[0])
		raise

print('Spoustim program')
print('Posilam pouze na maily:')
print(recipients)
while True: 
	try:
		updateTemp()
		tempMinList()
		teplotaPrirustek = prirustek_teploty_za_min(tempMin)
		Thingsboard()
		CSVlog(cntMin)
		#print(tempMin)
		celkovaDoba = str(datetime.timedelta(seconds = cnt))
		print('Aktualni T:\t'+ str(teplotaAktual)+ '\t Prirustek za min:\t'+ str(teplotaPrirustek)+ '\t Cas vareni: \t'+ celkovaDoba)

		cnt = cnt + 1
	except KeyboardInterrupt:
		print('\nSTOP')
		client.loop_stop()
		client.disconnect()
		print('Odpojeno od serveru')
		casKonec = str(datetime.datetime.now())
		udelejZapis()
		mailni()
		print('Konec vareni, vypinam program! \n\n Zdar a silu najdes v PIVU \n NERUDNY LEZAK \n est. 2017 \n Program napsal dessenger \n Funkce mail napsal rdempsey \t https://gist.github.com/rdempsey/22afd43f8d777b78ef22')
		break
