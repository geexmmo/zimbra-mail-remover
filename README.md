# zimbra-mail-remover
### now rewriten to use flask and compatable with wsgi servers
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
Fox example: My companiy IT team are now just creating a new ticket - and if it gets confirmed - ITSM software automatically requests this web service for email deletion and periodically check status page if job is done.
<br>
**Web service does not implement any security checks except secret key so if you are planning to use it - at least hide it behind Nginx or something where you can secure requests to this service.**

 
	
## Technologies
- python3   
- python venv to get pip   
- *gunicorn* from pip
- *flask* from pip
	
## Setup
* Copy it to some location on host with Zimbra installation.
Run as user **zimbra** or make sure standard Zimra environment variables are available (PATH), script using some of zimbra cli commands and will do nothing if it can not find them.

### Requirements installation:

- Run `python3 -m venv /opt/zimbra-mail-remover` to initialize virtual environment on path where you cloned this project.
- `source bin/active` to activate python virtual environemnt.
- `pip install -r requirements.txt` to install required pip packages.


### settings.py:

contains:      
- `secretkey` that will be used for authorization on web form   
- `min_symbols` that limits 'subject' field on web form to certain amount of symbols so you wouldn't accidenly delete all mails passing something like single letter (ex: 'a').   
- `threads` amount of concurrent threads to run while searching mailboxes.
```
Settings = {'secretkey':'sbXG7C9RiBgHs',
            'min_symbols': 4,
            'threads': 4
            }
```
modify them according your setup, for example if you are running mail server with 12 cpu cores you can specify a liitle more threads than in this example.   

---   

Example systemd service unit, can be used to start service after restarts or crashes.   
<br>
Dont forget to pass `zimra` user environment variables to service by creating env file and specifying it in `EnvironmentFile=`    
Env file can be creating by switching to user and running printenv:    
```
su zimbra
printenv > /opt/zimbra-mail-remover/env
```
`/etc/systemd/system/zimbra-mail-remover.service`   
```
[Unit]
Description=zimbra-mail-remover service
After=network.target

[Service]
User=zimbra
EnvironmentFile=/opt/zimbra-mail-remover/env
WorkingDirectory=/opt/zimbra-mail-remover
ExecStart=/opt/zimbra-mail-remover/bin/gunicorn app:app -b 0.0.0.0:8000
Restart=on-abort

[Install]
WantedBy=multi-user.target
```

run `systemctl daemon-reload` and `systemctl start zimbra-mail-remover`   
to persist service across reboots, run `systemctl enable zimbra-mail-remover`

You can watch service logs with: `journalctl -u zimbra-remover -f`   
