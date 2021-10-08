import re
import logging
import argparse
import threading
import concurrent.futures
from typing import Set
from settings import Settings
from subprocess import PIPE, run
from urllib.parse import parse_qs
from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
# multithreaded http server
  pass

class S(BaseHTTPRequestHandler):
  def _set_headers(self):
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.end_headers()

  def _html(self, message):
    content = f"""
<!DOCTYPE html>
  <html>
    <head>
      <meta charset="UTF-8">
    </head>
    <body>
      <h5>{message}</h5>
    </body>
  </html>"""
    return content.encode("utf8")

  def do_GET(self):
    self._set_headers()
    command = ("ps -aux | grep '[Z]MailboxUtil'")
    activepids = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    convpids = [str(item) for item in activepids.stdout.splitlines()]
    htmlpids = "<h3>Commands are only received on POST request to this page. Simple form will be shown above only if there is no active proccesses.</h3>"
    if convpids:
      htmlpids += "<br>Running processes:<br><hr>".join(convpids)
    else:
      htmlpids += """<br><form action="/" method="post">
        <label for="secretkey">key:</label>
        <input type="text" id="secretkey" name="secretkey"><br><br>
        <label for="subject">subject:</label>
        <input type="text" id="subject" name="subject"><br><br>
        <input type="submit" value="Go">
        </form>"""
    self.wfile.write(self._html(htmlpids))
    # self.wfile.write(self._html("Hello, try sending post request to this location"))

  def do_POST(self):
    self._set_headers()
    content_len = int(self.headers.get('content-length', 0))
    post_body = self.rfile.read(content_len)
    post_vars = parse_qs(post_body.decode('utf-8'))
    logging.info("Parsed parameters:") 
    for i in post_vars:
      logging.info(post_vars)
      logging.info(post_vars[i][0].encode('utf-8'))
    if "secretkey" in post_vars and post_vars["secretkey"][0] == Settings["secretkey"]:  
      if "subject" in post_vars and len(post_vars["subject"][0]) >= Settings["min_symbols"]:
        # check if global lock was acquired aready
        if pslock.locked():
          command = ("ps -aux | grep '[Z]MailboxUtil'")
          activepids = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
          convpids = [str(item) for item in activepids.stdout.splitlines()]
          htmlpids = "<h2>Threads are already active, command ignored.</h2><br><br>"
          htmlpids += "<hr>".join(convpids)
          self.wfile.write(self._html(htmlpids))
          logging.info("Run denied, threadlock not released")
        else:
          self.wfile.write(self._html("Accepted post!"))
          webthread = threading.Thread(target=spawncmd, args=(post_vars["subject"][0],))
          webthread.start()
      else:
        self.wfile.write(self._html("Wrong post parameters!"))
    else:
      self.wfile.write(self._html("Run denied"))


def webserverrun(server_class=ThreadingSimpleServer, handler_class=S, addr="localhost", port=8000):
  logging.basicConfig(level=logging.INFO)
  logging.info('Starting http %s %s...\n', addr, port)
  server_address = (addr, port)
  http = server_class(server_address, handler_class)
  http.serve_forever()

def getAllUsers():
  command = 'zmprov -l gaa'
  result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
  logging.info("env error?: %s", result.stderr)
  return result.stdout.splitlines() # returns list of emails

def searchUserMessages(maillist, subject):
  for mail in maillist:
    logging.info("Searching: %s (%s)", mail, subject)
    command = ('zmmailbox -z -m ' + mail + ' s -l 999 -t message "subject:'+ subject +'"')
    searchresult = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    matchlist = []
    for line in searchresult.stdout.splitlines():
      match = re.search(r'(?!^\d\W\W)\d+(?=\W+mess)', line)
      if match:
        matchlist.append(match.group())
    #return matchlist # returns matched message id from searched mailbox
    if len(matchlist):
      logging.info("Search done for %s, got: %s", mail, matchlist)
      rmMessage(mail, matchlist)
    else:
      pass

def rmMessage(mail, msgnumbers):
  logging.info("Now removing messages for %s", mail)
  for msg in msgnumbers:
    command = ('zmmailbox -z -m ' + mail + ' dm ' + msg)
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
  logging.info("Removal done for %s", mail)
  return True # there is nothing to return even if run results in error


def spawncmd(subject):
  if args.web:
    # first valid POST request triggers this lock
    # following ones gets rejected with message until this unlocks
    pslock.acquire()
  allmails = getAllUsers()
  allmails2 = [allmails[(i*len(allmails))//threadcount:((i+1)*len(allmails))//threadcount] for i in range(threadcount)]
  with concurrent.futures.ThreadPoolExecutor(max_workers=threadcount) as executor2:
    for maillist in allmails2:
      executor2.submit(searchUserMessages, maillist, subject)
  if args.web:
    # unlock new threads when all done
    pslock.release()


if __name__ == "__main__":
  format = "%(asctime)s: %(message)s"
  logging.basicConfig(format=format, level=logging.DEBUG, datefmt="%H:%M:%S")
  parser = argparse.ArgumentParser(description="Run a simple HTTP server")
  parser.add_argument(
    "-w",
    "--web",
    action='store_true',
    default=False,
    help="Add this flag if you want to run web server (defaults: False)",
  )
  parser.add_argument(
    "-l",
    "--listen",
    default="0.0.0.0",
    help="Specify the IP address on which the server listens (defaults: *) (localhost for localhost)",
  )
  parser.add_argument(
    "-p",
    "--port",
    type=int,
    default=8000,
    help="Specify the port on which the server listens (defaults: 8000)",
  )
  parser.add_argument(
    "-s",
    "--subject",
    help="If not running web service - specify subject here manually",
  )
  parser.add_argument(
    "-t",
    "--threads",
    type=int,
    default=2,
    help="Specify the number of threads to run (defaults: 2)",
  )
  args = parser.parse_args()
  # CONTOLS HOW MUCH PROCESSES TO SPAWN
  threadcount = args.threads
  # threading evenly distrbutes all of the mailboxes to each thead (ex: 5300 boxes / 6 threads = 883 boxes per thread ) 
  # resourse usage of those threads heavily depends on number of mailboxes on your server and their age (old ones are mail-heavy)
  # it's usually takes 90-120% of core time for each thread (java thing) so take care to sanely distribute workload  
  
  if args.web:
    pslock = threading.Lock()
    webserverrun(addr=args.listen, port=args.port)
  else:
    logging.info('not running webserver')
    if args.subject:
      logging.info('running localy')
      spawncmd(args.subject)