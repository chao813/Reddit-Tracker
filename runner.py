import os
import sqlite3
import re
import requests
from bs4 import BeautifulSoup

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from twilio.rest import Client



def main():
    connect = sqlite3.connect('db.sqlite3')
    c = connect.cursor()
    c.execute("SELECT * FROM Keywords WHERE active=?",('Yes',))
    for row in c:
        print(row)
        #(1, 'testing1', 'science', 'post', 'yuanchao813', 'chao9@purdue.edu', 'Yes')
        keyword=row[1]
        subreddit=row[2]
        scan_type=row[3]
        user=row[4]
        email=row[5]




        if not re.match('\S+@\S+', email):
            alert = 'sms'
        else:
            alert = 'email'


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

        if scan_type == "post":
            scanposts(keyword, urls, email, alert, user)
        elif scan_type == "comment":
            scancomments(keyword, urls, email, alert, user)





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

if __name__== "__main__":
    main()
                                                                                 


