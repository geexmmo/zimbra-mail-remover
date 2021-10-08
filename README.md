# zimbra-mail-remover
## Table of contents
* [General info](#general-info)
* [Technologies](#technologies)
* [Setup](#setup)

## General info
This script removes emails from mailboxes of your Zimbra installation searching them by subject, this allows accidentally sent emails to be deleted.
It is designed to be launched on host where Zimbra is installed.
<br>
Script implements basic multithreading so search and delete job time is multiplied based on number of threads allowed.
<br>
Threading evenly distributes all the mailboxes to each thread (ex: 5300 mailboxes / 6 threads = 883 mailboxes per thread ) 
Resource usage of those threads heavily depends on number of mailboxes on your server and also their age (old ones are usually mail-heavy)
It usually takes 90-120% of core time for each thread (java thing) so take care of sanely distributing workload by adjusting number of allowed threads!
<br>
Basic web service is implemented, representing command interface and status display page that shows information about script execution state, this interface provides the ability to integrate mail deletion with ITSM solution like Jira or ServiceDesk. 
<br>
Fox example: My companiy IT team are now just creating a new ticket - and if it gets confirmed - ITSM automatically requests this web service for email deletion and periodically check status page if job is done.
<br>
**Web service is not launched by default and does not implement any security checks so if you are planning to use it - at least hide it behind Nginx or something where you can secure requests to this service.**
<br>
Script can be run both locally or as a web service, below are -h explanation of flags that changes it's behavior:

```
usage: zimbra-mail-remover.py [-h] [-w] [-l LISTEN] [-p PORT] [-s SUBJECT]
                              [-t THREADS]

Run a simple HTTP server

optional arguments:
  -h, --help            show this help message and exit
  -w, --web             Add this flag if you want to run web server
  -l LISTEN, --listen LISTEN
                        Specify the IP address on which the server listens
                        (localhost for localhost)
  -p PORT, --port PORT  Specify the port on which the server listens
  -s SUBJECT, --subject SUBJECT
                        If not running web service - specify subject here
                        manually
  -t THREADS, --threads THREADS
                        Specify the number of threads to run
```

 
	
## Technologies
Use python3 haha
	
## Setup
Copy it to some location on host with Zimbra installation.
Run as user **zimbra** or make sure standard Zimra environment variables are available (PATH), script using some of zimbra cli commands and will do nothing if it can not find them.

---
settings.py
contains:      
`secretkey` that will be used for authorization on web form   
`min_symbols` that limits 'subject' field on web form to certain amount of symbols so you wouldn't accidenly delete all mails passing something like single letter (ex 'a').
```
Settings = {'secretkey':'sbXG7C9RiBgHs',
            'min_symbols': 4
            }
```
---
Example of local execution with 6 threads:
```
python3 zimbra-mail-remover.py -t 6 -s "hello привет test"
21:00:18: not running webserver
21:00:18: running localy
```
Example of starting web service on port `8888` (also can be restricted to listening only on localhost by passing `-l localhost`)
```
python3 zimbra-mail-remover.py -w -p 8888
21:05:24: Starting http 0.0.0.0 8888...
```
And then make POST request like such: `curl -X POST zimbra.example.com:8000 -d "subject=hello привет test"`<br>
You will get; "`Accepted post!`" in resonse if query is correct and there is no script threads running at this time<br>
"`Wrong post parameters!`" if you've posted parameters different than `subject` <br>
"`Threads are already active, command ignored.`" if script has already started some workload.<br>
<br>
If you want to check run status - do a get request:   
`curl zimbra.example.com:8000`

---
Example systemd service unit, sets 4 threads and web-server, can be used to start service after restarts or crashes.   
`/etc/systemd/system/zimbra-remover.service`   
```
[Unit]
Description=zimbra-remover service
After=syslog.target network.target

[Service]
Type=simple
User=zimbra
WorkingDirectory=/opt/zimbra-mail-remover
ExecStart=/bin/bash -l -c 'python3 /opt/zimbra-mail-remover/zimbra-mail-remover.py -w -t 4'
Restart=always

[Install]
WantedBy=multi-user.target
```

You can watch service logs: `journalctl -u zimbra-remover -f`   
