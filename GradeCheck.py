#!/usr/bin/python3
#Send an email when IQS sigma grades are updated
#Tested on: 
	#Distributor ID:	Ubuntu
	#Description:	Ubuntu 16.04.1 LTS
	#Release:	16.04
	#Codename:	xenial
	#Python 3.5.2

#Modules for email sending
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
#Modules for browsing
from selenium import webdriver
import signal
#Module for more secure password management
import getpass
#Module for time
from time import sleep
from time import ctime

#Functions
def send_email(fromaddr,passwd,toaddr,subject,body):
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, passwd)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()
    print('Email has been sent successfully')

def get_raw_grades(UserId,UserPasswd):
    #browser setup
    browser = webdriver.PhantomJS(executable_path='/opt/PhantomJs/bin/phantomjs')
    browser.set_window_size(1120, 550)
    #Go to IQS sigma page
    browser.get('https://sgaw.iqs.url.edu/cosmos/Controlador/?@ebf2f349580da806=@1bedd0984ff1624c&@57b88e10f1a90c1a=@a039d9c04653ef8c&@d2e9d205e120747b=@057dbf7322b5fb19&@7768acd4afb2a0dcaab9840b9661a38391fdaa47be8ebfbb=@f6313b39283a9692&@34ee43953e5fe695cf56daffdffb97681d601ab7f2118a8c=@2dd27a357656a68d&@f240380e964aa0b0=@4c3980ce660dc557')
    #Login with user data
    browser.find_element_by_id('Usuario').clear()
    browser.find_element_by_id('Usuario').send_keys(UserId)
    browser.find_element_by_id('password').clear()
    browser.find_element_by_id('password').send_keys(UserPasswd)
    #Find login button and enter
    browser.find_element_by_name('entrar').click()
    #We should be in by now, unless user data is wrong.
    #Go to 'Estudis oficials
    browser.find_element_by_link_text('Estudis oficials').click()
    #Go to 'Consulta expedient'
    browser.find_element_by_link_text('Consulta Expedient').click()
    #Enter iframe
    browser.switch_to_frame(browser.find_element_by_id('iFrameAplZonaAplicacion'))
    #Get web page encoded as utf-8
    grades = browser.page_source
    #make a screenshot(Uncomment to get a browser screenshot)
    #browser.save_screenshot('screenie.png')
    browser.service.process.send_signal(signal.SIGTERM) # kill the specific phantomjs child proc
    browser.quit()
    return grades

def refine_data(raw_grades,school_year): #school_year = '2016/17'
    i=0
    grades=['School_Year','Subject Name','Credit Value','Month','Grade','NºGrade']
    #Split by new line
    raw_grades=raw_grades.split('\n')
    #Now search for the school year, then distances in lines between fields are constant
    while i < len(raw_grades)-2:
        if school_year in raw_grades[i]:
           #Append school year
           grades.append(raw_grades[i])
           #Append subject name
           i=i+8
           grades.append(raw_grades[i])
           #Append credit value
           i=i+4
           grades.append(raw_grades[i])
           #Append month
           i=i+8
           grades.append(raw_grades[i])
           #Append grade
           i=i+3
           grades.append(raw_grades[i])
           #Append NºGrade
           i=i+110
           grades.append(raw_grades[i])
        i=i+1
    refined_grades=[]
    for x in grades:
        refined_grades.append(x.strip(' ').strip('<td>').strip('</td>'))
    return refined_grades

def format_data(refined_data): #Formats the refined grades into 6 column table like string
    row=0
    formated_data=''
    while len(refined_data)-row > 4:
        formated_data+='{:20s} {:40s} {:20s} {:10s} {:20s} {:10s}'.format(refined_data[row+0],refined_data[row+1],refined_data[row+2],refined_data[row+3],refined_data[row+4],refined_data[row+5]) + '\n'
        row=row+6
    return formated_data

def check_new(current,IQS_User,IQS_passwd,year): #Checks if new grades have been added then returns [True,NewCurrent,[NewGrade]]
    refined_data=refine_data(get_raw_grades(IQS_User,IQS_passwd),year)
    New=format_data(refined_data)
    IS_NEW=False
    NewCurrent=New
    NewGrade=[]
    if New != current:
        IS_NEW=True
        current=current.split('\n')
        New=New.split('\n')
        for line in range(len(current)):
            if current[line] != New[line]:
                NewGrade.append(' '.join(New[line].split())[10:])
    return (IS_NEW,NewCurrent,NewGrade)







####################################################################
####################################################################
#########################__MAIN__###################################
####################################################################
####################################################################

#Global Variables
Current=''

#Setup-------------------------------------------------------------
#IQS credentials
print('Seting up IQS Sigma grade checker:')
print('Please enter your IQS data now')
year=input('Year: [eg. 2016/17]\n')
IQS_User=input('IQS User:\n')
IQS_passwd=getpass.getpass('IQS Password:\n')
#Email data
print('Please enter your mail details now [From mail only works with Gmail]')
#Gmail must be used
fromaddr=input('From:\n')
passwd=getpass.getpass('From Password:\n')
#Reciever Mail
toaddr=input('To:\n')
print('Starting IQS Sigma grade checker...')
#Update to current grade state
try:
	current=format_data(refine_data(get_raw_grades(IQS_User,IQS_passwd),year))
	print('Sending setup email')
	send_email(fromaddr,passwd,toaddr,'GChk:Setup complete',current)
except:
	print('Grade Checker can not access sigma!\nAre your details correct? Can this machine reach the internet?')
	quit()
#Main Loop--------------------------------------------------------
while True:
	try:
		trigger=check_new(Current,IQS_User,IQS_passwd,year)  #checking for grades
		print('Last update: '+ctime()) #Give a sign to the user that the program is alive
		if trigger[0]==True:
		    print('THERE IS A NEW GRADE ONLINE!')
		    Current=trigger[1]
		    send_email(fromaddr,passwd,toaddr,'GChk:New Grades Soon!',Current) #Emergency Mail
		    for i in range(len(trigger[2])):
		        send_email(fromaddr,passwd,toaddr,'GChk:'+trigger[2][i],Current)
	except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
		print('Done')
		quit()
	except:
		print('Something has gone wrong, Grade Checker can not access sigma.\n[Retrying in 2.5 min]\n')
		send_email(fromaddr,passwd,toaddr,'GChk:Can not access sigma','Something has gone wrong, Grade Checker can not access sigma.\n[Retrying in 2.5 min]\n') #Emergency Mail
	sleep(150) #wait 2.5 minutes





