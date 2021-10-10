# -*- coding: utf-8 -*-
from flask import Flask, request, render_template
import re
from logging.config import dictConfig
import threading
import concurrent.futures
from settings import Settings
from subprocess import PIPE, run

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

app = Flask(__name__)

pslock = threading.Lock()
threadcount = Settings['threads']

@app.route("/", methods=['GET', 'POST'])
def default():
  if request.method == 'GET':
    return render_template('default.html', title=Settings['title'], post=False, processes=getRunningPS())
  else:
    if request.form['secretkey'] and request.form['subject']:
      if request.form["secretkey"] == Settings["secretkey"] and \
      len(request.form["subject"]) >= Settings["min_symbols"]:
        processing = getRunningPS()
        if not processing and not pslock.locked():
          app.logger.info('Form input %s %s', request.form['secretkey'], request.form['subject'])
          webthread = threading.Thread(target=spawncmd, args=(request.form["subject"],))
          webthread.start()
          return render_template('default.html', title=Settings['title'], post=True)
        else:
          return render_template('default.html', title=Settings['title'], post=True, processes=processing)
      else:
        return render_template('error.html', autherror=True)
    else:
      return render_template('error.html', paramerror=True)


def getRunningPS():
    command = ("ps -aux | grep '[Z]MailboxUtil'")
    activepids = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    convpids = '<br/>'.join([str(item) for item in activepids.stdout.splitlines()])
    return convpids


def getAllUsers():
  command = 'zmprov -l gaa'
  result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
  if result.stderr:
    app.logger.info("env error?: %s", result.stderr)
  return result.stdout.splitlines() # returns list of emails


def searchUserMessages(maillist, subject):
  for mail in maillist:
    app.logger.info("Searching: %s (%s)", mail, subject)
    command = ('zmmailbox -z -m ' + mail + ' s -l 999 -t message "subject:'+ subject +'"')
    searchresult = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    matchlist = []
    for line in searchresult.stdout.splitlines():
      match = re.search(r'(?!^\d\W\W)\d+(?=\W+mess)', line)
      if match:
        matchlist.append(match.group())
    #return matchlist # returns matched message id from searched mailbox
    if len(matchlist):
      app.logger.info("Search done for %s, got: %s", mail, matchlist)
      rmMessage(mail, matchlist)
    else:
      pass


def rmMessage(mail, msgnumbers):
  app.logger.info("Now removing messages for %s", mail)
  for msg in msgnumbers:
    command = ('zmmailbox -z -m ' + mail + ' dm ' + msg)
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
  app.logger.info("Removal done for %s %s", mail, result.stdout)
  return True


def spawncmd(subject):
  pslock.acquire()
  allmails = getAllUsers()
  allmails2 = [allmails[(i*len(allmails))//threadcount:((i+1)*len(allmails))//threadcount] for i in range(threadcount)]
  with concurrent.futures.ThreadPoolExecutor(max_workers=threadcount) as executor2:
    for maillist in allmails2:
      executor2.submit(searchUserMessages, maillist, subject)
  pslock.release()