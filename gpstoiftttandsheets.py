import logging
import threading
import json
import serial   
import os, time
import pynmea2
from subprocess import call
from time import sleep
from datetime import datetime
from pprint import pprint

logging.basicConfig(filename='gps.log', level=logging.DEBUG, filemode='w', format='%(name)s - %(levelname)s - %(message)s')
logging.debug('Script started')

# Enable Serial Communication
logging.debug('Enabling serial')
port = serial.Serial('/dev/ttyAMA1', baudrate=9600, timeout=5) ## Enter serial port here
port.write("AT+CGNSTST=0\r\n".encode())  ## Ensure gps stream is off before we start

#activate internet commands
gprspwr = "AT+CFUN=1\r\n"
gprsconntype = 'AT+SAPBR=3,1,"Contype","GPRS"\r\n'
apnset = 'AT+SAPBR=3,1,"APN","pp.vodafone.co.uk"\r\n' ## Set your APN
apnuser = 'AT+SAPBR=3,1,"USER","wap"\r\n' ## APN User
apnpass = 'AT+SAPBR=3,1,"PWD","wap"\r\n' ## APN Password
startconn = "AT+SAPBR=1,1\r\n"
getip = "AT+SAPBR=2,1\r\n"
attachgprs = "AT+HTTPINIT\r\n"

#powerup gps
gpspowerup = "AT+CGNSPWR=1\r\n"

#startgps
gpsgo = "AT+CGNSTST=1\r\n"
#
#   FIRE UP MODULE -- Turn on gps and start sending readings
logging.debug("Enabling features")
port.write(gprspwr.encode())
res = port.readline().decode('utf-8', errors='replace')
logging.debug(res)
time.sleep(1)
logging.debug("APN Setup")
port.write(gprsconntype.encode())
res = port.read(50).decode('utf-8', errors='replace')
res1 = port.read(50).decode('utf-8', errors='replace')

logging.debug(res)
logging.debug(res1)
time.sleep(1)

port.write(apnset.encode())
res = port.readline().decode('utf-8', errors='replace')
logging.debug(res)
time.sleep(1)

port.write(apnuser.encode())
res = port.readline().decode('utf-8', errors='replace')
logging.debug(res)
time.sleep(1)

port.write(apnpass.encode())
res = port.readline().decode('utf-8', errors='replace')
logging.debug(res)
time.sleep(1)

print("Start Connection")
port.write(startconn.encode())
res = port.readline().decode('utf-8', errors='replace')
logging.debug(res)
time.sleep(1)

logging.debug("Get IP")
port.write(getip.encode())
res = port.readline().decode('utf-8', errors='replace')
logging.debug(res)

port.write(attachgprs.encode())
res = port.readline().decode('utf-8', errors='replace')
logging.debug(res)
logging.debug("GPS Power ON")

port.write(gpspowerup.encode())
res = port.read(100)
logging.debug(res)
time.sleep(1)

logging.debug("GPS Start")
port.write(gpsgo.encode())
res = port.read(25).decode('utf-8', errors='replace')
logging.debug(res)


def getTimeAndDate():
	date = datetime.now()
	timestr = '{}:{}:{:02d}'.format(date.hour, date.minute, date.second)
	datestr = '{}-{:02d}-{:02d}'.format(date.year, date.month, date.day)
	return (timestr, datestr)

def handleGPSmsg(GGAmsg, RMCmsg):
	"""
	GGAmsg is a pynmea2 parsed GGA string (http://www.gpsinformation.org/dale/nmea.htm#GGA)
	To see what fields are available see the pynmea2 docs (https://github.com/Knio/pynmea2)
	To get latitude in degrees for example you can do msg.latitude
	"""
	speed = RMCmsg.spd_over_grnd # speed in knots
	speed *= 0.514444 # speed in meters/sec

	msg = GGAmsg
	altitude = str(msg.altitude)
	timestmp = str(getTimeAndDate()[0] + ', ' + getTimeAndDate()[1])
	
	longitude = str(msg.longitude)
	latitude = str(msg.latitude)

	#longitude = '%02d°%02d′%07.4f″' % (msg.longitude, msg.longitude_minutes, msg.longitude_seconds)
	#latitude = '%02d°%02d′%07.4f″' % (msg.latitude, msg.latitude_minutes, msg.latitude_seconds)
	logging.debug('Stop GPS for loop run...')
	port.write("AT+CGNSTST=0\r\n".encode())
	time.sleep(2)
	port.reset_input_buffer()
	print(timestmp + " Lat: " + latitude + " Long: " + longitude + ' Alt: ' + altitude + ' Meters spd: ' + '{:.3f}'.format(speed) + "m/s")

	logging.debug('Set CID')
	port.write('AT+HTTPPARA=\"CID\",1\r\n'.encode())
	response = port.read(100).decode('utf-8', errors='replace')
	logging.debug(response)

	logging.debug('Set URL')
	port.write(('AT+HTTPPARA=\"URL\",\"maker.ifttt.com/trigger/VanGPSUpdate/with/key/e2YZxbF2MzyhvzwDPtLXew5NMw9fIXlDquXKkRKNnsy?value1=' + str(timestmp) + '&value2=' + str(latitude) + ',' + str(longitude) + '&value3=' + str(speed) + '\"\r\n').encode())
	logging.debug('URL SET:' + (port.read(400).decode('utf-8', errors='replace')))
	response = port.read(100).decode()
	logging.debug(response)
	time.sleep(1)

	logging.debug('Set SSL')
	port.write('AT+HTTPSSL=1\r\n'.encode())
	response = port.readline().decode('utf-8', errors='replace')
	if "OK" in response:
		logging.debug("SSL DONE!")
	else: logging.error('SSL Error!')

	logging.debug('HTTP POST Set')
	port.write('AT+HTTPACTION=1\r\n'.encode())
	response = port.read(54).decode('utf-8', errors='replace')
	logging.debug(response)
	logging.debug('Read Response')
	port.write('AT+HTTPREAD\r\n'.encode())
	response = port.read(87).decode('utf-8', errors='replace')
	logging.debug(response)
#	logging.debug('Length:' + str(len(response)))

	logging.debug('Restart GPS')
	port.write("AT+CGNSTST=1\r\n".encode())
	response = port.readline().decode("utf-8",errors='replace')
	logging.debug(response)
	response = port.read(100).decode("utf-8",errors='replace')
	logging.debug(response)

	while "OK" not in (response):
		logging.error('GPS Stop')
		port.write("AT+CGNSTST=0\r\n".encode())
		response = port.read(300).decode('utf-8', errors='replace')
		logging.debug(response)
		time.sleep(1)
		logging.error('GPS Restart')
		port.write("AT+CGNSTST=1\r\n".encode())
		response = port.read(300).decode('utf-8', errors='replace')
		logging.debug(response)
		time.sleep(1)

	time.sleep(30)

if __name__ == '__main__':

	GGAmsg = None # location info
	RMCmsg = None # speed info
	try:
		while True:
			line = port.readline()
			logging.debug(line)
			line = line.strip()
			try:
				line = line.decode("utf-8")
				msg = pynmea2.parse(line, check=False)
				if isinstance(msg, pynmea2.types.talker.GGA):
					GGAmsg = msg
				elif isinstance(msg, pynmea2.types.talker.RMC):
					RMCmsg = msg
			except pynmea2.nmea.ChecksumError:
				print('ignoring checksum error: ' + str(line))
			except pynmea2.nmea.ParseError:
				print('ignoring parse error: ' + str(line))
			except UnicodeDecodeError:
				print('ignoring unicode error: ' + str(line))

			if GGAmsg and RMCmsg:
				handleGPSmsg(GGAmsg, RMCmsg)
				GGAmsg = None; RMCmsg = None

	finally:
		port.close()
