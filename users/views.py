from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, UserInputForm
from django.contrib.auth.decorators import login_required
import os

import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from twilio.rest import Client

#from .models import Input



# Create your views here.
def register(request):
	if request.method == 'POST':
		form = UserRegisterForm(request.POST)
		if form.is_valid():
			form.save()
			username = form.cleaned_data.get('username')
			messages.success(request, 'Acount created for {}! You are now able to log in'.format(username))
			return redirect('login')
	else:
		form = UserRegisterForm()
	return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
	if request.method == 'POST':
		u_form = UserUpdateForm(request.POST, instance=request.user)
		p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
		if u_form.is_valid() and p_form.is_valid():
			u_form.save()
			p_form.save()
			messages.success(request, f'Your Account have been updated!')
			return redirect('profile')
	else:
		u_form = UserUpdateForm(instance=request.user)
		p_form = ProfileUpdateForm(instance=request.user.profile)

	i_form = UserInputForm(request.POST or None)
	if i_form.is_valid():
		instance = i_form.save(commit=False)
		instance.user = request.user		
		output = main(instance.keyword, instance.subreddit, instance.scan_type, instance.enter_email_or_phone_number, instance.user.username, instance.disable)
		instance.save()

	keywordtable = accessinfo(request.user.username)


	#if(request.POST.get('update_button')):
	#	keywordtable = accessinfo(request.user.username)
		
	context = {
		'u_form' : u_form,
		'p_form' : p_form,
		'i_form' : i_form,
		'keywordtable' : keywordtable,
	}



	return render(request, 'users/profile.html', context)



def accessinfo(user):
	connect = sqlite3.connect('db.sqlite3')
	c = connect.cursor()
	create_keywordTable()

	c.execute("SELECT * FROM Keywords WHERE user=?",(user,))
	
	rows = c.fetchall()
	keywordtable =[]
	if rows:
		for row in rows:
			keywordtable.append((row[1],row[2], row[3],row[5]))
		

	return keywordtable

def main(keyword, subreddit, scan_type, email, user, disable):
	print(keyword)
	print(subreddit)
	print(scan_type)
	print(email)
	print(user)
	print(disable)

	if not re.match('\S+@\S+', email):
		alert = 'sms'
	else: 
		alert = 'email'


	create_keywordTable()
	create_postsTable()
	create_commentTable()


	url = ("https://www.reddit.com/r/{}").format(subreddit)
	url_s = ("http://www.reddit.com/r/{}").format(subreddit)

	headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}


	result = requests.get(url, headers=headers)

	soup = BeautifulSoup(result.text, 'html.parser')

	urls = []

	for link in soup.find_all('a'):
	    href = str(link.get('href'))
	    if url+"/comments" in href or url_s+"/comments " in href:
	        urls.append(href)  

	if disable == False:
		active = 'Yes'
	if disable == True:
		active = 'No'

	update_keyword(keyword, subreddit, user, active, scan_type)
	insert_keyword(keyword, subreddit, user, active, scan_type)
	if scan_type == "post" and disable == False:
	    scanposts(keyword, urls, email, alert, user)
	elif scan_type == "comment" and disable == False:
	    scancomments(keyword, urls, email, alert, user)


def update_keyword(keyword, subreddit, user, active, scan):
	connect = sqlite3.connect('db.sqlite3')
	c = connect.cursor()
	c.execute("UPDATE Keywords SET active=? WHERE keyword=? and subreddit=? and user=? and scan=?", (active, keyword, subreddit,user, scan))
	connect.commit()



def insert_keyword(keyword, subreddit, user, active, scan):
	connect = sqlite3.connect('db.sqlite3')
	c = connect.cursor()

	c.execute("SELECT * FROM Keywords WHERE keyword=? and subreddit=? and user=? and active=? and scan=?", (keyword, subreddit, user, active, scan))
	entry = c.fetchone()

	if entry is None:
		c.execute("INSERT INTO Keywords(keyword, subreddit, user, active, scan) VALUES(?, ?, ?, ?, ?)", (keyword, subreddit, user, active, scan))
	
	connect.commit()
	



def create_keywordTable():
	connect = sqlite3.connect('db.sqlite3')
	c = connect.cursor()
	c.execute('CREATE TABLE IF NOT EXISTS Keywords(id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, keyword TEXT NOT NULL, subreddit TEXT NOT NULL, scan TEXT NOT NULL, user TEXT NOT NULL, active TEXT NOT NULL DEFAULT "Yes")')


def create_commentTable():
	connect = sqlite3.connect('db.sqlite3')
	c = connect.cursor()
	c.execute('CREATE TABLE IF NOT EXISTS Comment(id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, keyword TEXT NOT NULL, post_url TEXT NOT NULL, comment_id TEXT NOT NULL, user TEXT NOT NULL)')

def create_postsTable():
	connect = sqlite3.connect('db.sqlite3')
	c = connect.cursor()
	c.execute('CREATE TABLE IF NOT EXISTS Posts(id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, keyword TEXT NOT NULL, post_url TEXT NOT NULL, user TEXT NOT NULL)')

def scanposts(keyword, urls, email, alert, user):
	headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}
	connect = sqlite3.connect('db.sqlite3')
	c = connect.cursor()

	for url in urls:
	    result = requests.get(url, headers=headers)

	    soup = BeautifulSoup(result.text, 'html.parser')
	    
	    print(url)
	    for i in soup.find_all('div', attrs={"data-test-id":"post-content"}):
	        if str(keyword).lower() in str(i).lower():
	            c.execute("SELECT post_url FROM Posts WHERE post_url=? and user=? and keyword=?", (url,user,keyword,))
	            result = c.fetchall()
	            print(result)
	            if result:
	                print('post exists already dont alert')
	            else: 
	                print('post doesnt exist')
	                c.execute("INSERT INTO Posts(post_url, keyword, user) VALUES(?, ?, ?)", (url, keyword, user))

	                if alert.lower() == "email":
	                    fromaddr = "reddittrack@gmail.com"
	                    toaddr = "{}".format(email)
	                    msg = MIMEMultipart()
	                    msg['From'] = fromaddr
	                    msg['To'] = toaddr
	                    msg['Subject'] = "NEW Post with Keyword: {}".format(keyword)
	                     
	                    body = "Found Post with keyword! Link: {}".format(url)
	                    msg.attach(MIMEText(body, 'plain'))
	                     
	                    server = smtplib.SMTP('smtp.gmail.com', 587)
	                    server.ehlo()
	                    server.starttls()
	                    server.ehlo()
	                    server.login("reddittrack@gmail.com", "reddittrack1!")
	                    text = msg.as_string()
	                    server.sendmail(fromaddr, toaddr, text)
	                    server.quit()

	                if alert.lower() == "sms":
	                    accountSid = os.environ.get('TWILIO_SID')
	                    authToken = os.environ.get('TWILIO_AUTH')
	                    twilioClient = Client(accountSid, authToken)
	                    myTwilioNumber = "+17652957391"
	                    destCellPhone = "{}".format(email)
	                    myMessage = twilioClient.messages.create(body = "Found Post with keyword: {}. Link: {}".format(keyword, url), from_=myTwilioNumber, to=destCellPhone)



	            connect.commit()


def scancomments(keyword, urls, email, alert, user):
	headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}
	connect = sqlite3.connect('db.sqlite3')
	c = connect.cursor()

	for url in urls:
	    result = requests.get(url, headers=headers)

	    soup = BeautifulSoup(result.text, 'html.parser')
	    
	    print(url)
	    for i in soup.find_all('div', attrs={"class":"Comment"}):
	        i = str(i.find_all('p')).lower()
	        if str(keyword).lower() in i:
	            index = i.find(keyword)
	            new = i[index-15:index+15]
	            print('found in comments') 
	            c.execute("SELECT comment_id FROM Comment WHERE comment_id=? and user=? and keyword=?", (new,user,keyword,))
	            result = c.fetchall()
	            print(result)
	            if result:
	                print('comment exists already dont alert')
	            else: 
	                print('comment doesnt exist')
	                c.execute("INSERT INTO Comment(post_url, comment_id, keyword, user) VALUES(?, ?, ?, ?)", (url, new, keyword, user))

	                if alert.lower() == "email":
	                    fromaddr = "reddittrack@gmail.com"
	                    toaddr = "{}".format(email)
	                    msg = MIMEMultipart()
	                    msg['From'] = fromaddr
	                    msg['To'] = toaddr
	                    msg['Subject'] = "New Comment with Keyword: {}".format(keyword)
	                     
	                    body = "Found Comment with keyword! Link: {}".format(url)
	                    msg.attach(MIMEText(body, 'plain'))
	                     
	                    server = smtplib.SMTP('smtp.gmail.com', 587)
	                    server.starttls()
	                    server.login(fromaddr, "reddittrack1!")
	                    text = msg.as_string()
	                    server.sendmail(fromaddr, toaddr, text)
	                    server.quit()

	                if alert.lower() == "sms":
	                    accountSid = os.environ.get('TWILIO_SID')
	                    authToken = os.environ.get('TWILIO_AUTH')
	                    twilioClient = Client(accountSid, authToken)
	                    myTwilioNumber = "+17652957391"
	                    destCellPhone = "{}".format(email)
	                    myMessage = twilioClient.messages.create(body = "Found comment with keyword {}, Link: {}".format(keyword, url), from_=myTwilioNumber, to=destCellPhone)

	            connect.commit()
