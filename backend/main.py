# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from flask import Flask, jsonify, request
import flask_cors
from google.appengine.ext import ndb
import google.auth.transport.requests
import google.oauth2.id_token
import requests_toolbelt.adapters.appengine
import calendar
import time

with open('adminHtml.html', 'r') as html:
    adminHtml = html.read()
with open('execHtml.html', 'r') as html:
    execHtml = html.read()
with open('standardHtml.html', 'r') as html:
    standardHtml = html.read()
with open('clubBlock.html', 'r') as html:
    clubBlock = html.read()
with open('tallyBlock.html', 'r') as html:
    tallyBlock = html.read()
with open('timerCode.html', 'r') as html:
    timerCode = html.read()
clubListDiv = 'id="clubList">\n'

# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()
HTTP_REQUEST = google.auth.transport.requests.Request()

app = Flask(__name__)
flask_cors.CORS(app)

class Account(ndb.Model):
    email = ndb.StringProperty()
    clubData = ndb.StringProperty(repeated=True)
    isExec = ndb.StringProperty(repeated=True)
    created = ndb.DateTimeProperty(auto_now_add=True)


# [START gae_python_query_database]
def query_database(user_id): #before live production, rewrite this to be in terms of email and not uid for ease of access
    ancestor_key = ndb.Key(Account, user_id)
    query = Account.query(ancestor=ancestor_key).order(-Account.created)
    accountData = query.fetch()

    acDataParsed = []
    if len(accountData) > 0:
        accountData = accountData[0]
        acDataParsed.append({
            'email': accountData.email,
            'clubData': accountData.clubData,
            'isExec': accountData.isExec,
            'created': accountData.created
        })

    return acDataParsed
# [END gae_python_query_database]

def renderAdminHtml(data):
    sdata = query_database('backend-server')[0]
    clubs = sdata['clubData']
    
    divLocation = adminHtml.find(clubListDiv)+len(clubListDiv)
    htmls = adminHtml[:divLocation]
    htmle = adminHtml[divLocation:]
    for club in clubs:
        htmls += '<h4>'+club+": "
        query = query_database(club)[0]['clubData']
        if len(query) == 0:
            htmls += 'There are no execs in this club!\n'
        else:
            for Exec in query[:-1]:
                htmls += Exec+", "
            htmls += query[-1]+"\n"
    htmls += '</h4>'
    return htmls+htmle

def formatClubBlock(club):
    html = clubBlock.replace('&CLUB&', club.replace(' ', '_')).replace('&CLUBN&', club)
    cdata = query_database(club)[0]
    clubData = cdata['clubData']
    timerterm = club+".tallywindowtimer."
    for i in range(0, len(clubData)):
        if clubData[i].startswith(timerterm):
            tallywtime = clubData[i].split(timerterm)[1]
            if calendar.timegm(time.gmtime()) < tallywtime:
                html = html.split("<!--tally window status-->\n")
                html.insert(1, timerCode.replace('&CLUB&', club.replace(' ', '_')).replace('&TIME&', str(float(tallywtime)*1000)))
                html = ''.join(html)
            else:
                html = html.replace('<!--tally window status-->', '<h4>Window Closed</h4>')
    return html

def renderExecHtml(data):
    
    divLocation = execHtml.find(clubListDiv)+len(clubListDiv)
    htmls = execHtml[:divLocation]
    htmle = execHtml[divLocation:]
    
    for club in data['isExec']:
        htmls += formatClubBlock(club)
    return htmls+htmle

def renderStandardHtml(data):
    html = standardHtml.split(clubListDiv)
    cdata = data['clubData']
    for each in cdata:
        if '.tally.' in each:
            club, tallyCount = each.split('.tally.')
            html.insert(1, '<h4>'+club+': '+tallyCount+'</h4>\n')
    return ''.join(html)


def checkForPromotion(data, uid):
    if data['email'] == 'c.bicheru0@gmail.com':
        newData = Account(
            parent=ndb.Key(Account, uid),
            email=data['email'],
            clubData=data['clubData'],
            isExec=['admin'])
        newData.put()
    sdata = query_database('backend-server')
    if len(sdata) > 0:
        sdata = sdata[0]['clubData']
        email = data['email']
        for club in sdata:
            cdata = query_database(club)
            if len(cdata) == 0 and club in data['isExec']:
                data['isExec'].remove(club)
            else:
                cdata = cdata[0]
                if email in cdata['clubData']:
                    if club not in data['isExec']:
                        data['isExec'].append(club)
                if email not in cdata['clubData']:
                    if club in data['isExec']:
                        data['isExec'].remove(club)
        for club in data['isExec']:
            if club not in sdata and club != 'admin':
                data['isExec'].remove(club)
        newData = Account(
        parent=ndb.Key(Account, uid),
        email=data['email'],
        clubData=data['clubData'],
	isExec=data['isExec'])
        newData.put()
    else:
        logging.exception('mega yikes')

def formatTallyBlock(club, etime):
    thtml = tallyBlock.replace('&CLUB&', club.replace(' ', '_')).replace('&CLUBN&', club)
    thtml = thtml.split("<!--tally window status-->\n")
    thtml.insert(1, timerCode.replace('&CLUB&', club.replace(' ', '_')).replace('&TIME&', str(float(etime)*1000)))
    thtml = ''.join(thtml)
    return thtml

def renderTallyContainer(data, uid):
    sdata = query_database('backend-server')
    if len(sdata) > 0:
        html = ""
        sdata = sdata[0]['clubData']
        for club in sdata:
            timerterm = club+".tallywindowtimer."
            alreadyTallyedTerm = club+".tallyed.["
            cdata = query_database(club)[0]['clubData']

            alreadyTallyed = 0
            for each in cdata:
                if each.startswith(alreadyTallyedTerm):
                    UIDs = each.split(alreadyTallyedTerm)[1].split(']')[0].split(', ')
                    if uid in UIDs:
                        alreadyTallyed = 1
                    break
            if alreadyTallyed == 0:
                for each in cdata:
                    if each.startswith(timerterm):
                        etime = float(each.split(timerterm)[1])
                        if calendar.timegm(time.gmtime()) < etime:
                            html += formatTallyBlock(club, etime)
                        break
        return html
                    
    else:
        logging.exception('mega yikes')

def renderElevatedTallyContainer(data):
    return '<h4>No tallying for admins or execs!</h4>'

def checkForTallyReset(data):
    cdata = data['isExec']

    for club in cdata:
        oldClubData = query_database(club)[0]
        oldCData = oldClubData['clubData']
        timerterm = club+".tallywindowtimer."
        alreadyTallyedTerm = club+".tallyed.["

        for i in range(0, len(oldCData)):
            each = oldCData[i]
            if each.startswith(timerterm):
                if calendar.timegm(time.gmtime()) > float(each.split(timerterm)[1]):
                    oldCData[i] = timerterm+'0'
                    
                    for i2 in range(0, len(oldCData)):
                        each2 = oldCData[i2]
                        if each2.startswith(alreadyTallyedTerm):
                            oldCData[i2] = alreadyTallyedTerm+']'
                            break
                    
                    break

        newClub = Account(
            parent=ndb.Key(Account, club),
            clubData=[],
            isExec=[])
        newClub.clubData = oldCData
        newClub.isExec.append('server')
        newClub.put()
        
        

@app.route('/getdata', methods=['GET'])
def list_notes():
    """Returns a list of notes added by the current Firebase user."""

    # Verify Firebase auth.
    # [START gae_python_verify_token]
    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401
    # [END gae_python_verify_token]

    accountData = query_database(claims['sub'])

    return jsonify(accountData)


@app.route('/tally', methods=['POST', 'PUT'])
def recordTally():

    # Verify Firebase auth.
    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401


    Club = request.get_json()['club']

    clubLedger = query_database('backend-server')

    if len(clubLedger) > 1:
        logging.exception('multiple ledgers detected?!?!?')

    clubLedger = clubLedger[0]
    
    
    if Club not in clubLedger['clubData']:
        logging.exception('A tally for club '+Club+' was requested by UID '+claims['sub']+'.')
        return 'Club does not exist', 400

    clubData = query_database(Club)

    if len(clubData) > 1:
        logging.exception('multiple instances of '+Club+' were detected?!?!?')
        
    clubData = clubData[0]

    timerterm = Club+".tallywindowtimer."

    exist = 0

    cdata = clubData['clubData']
    
    for each in cdata:
        if each.startswith(timerterm):
            etime = each.split(timerterm)[1]
            if calendar.timegm(time.gmtime()) < etime:

                exist2 = 0

                alreadyTallyedTerm = Club+".tallyed.["
                
                for i in range(0, len(cdata)):
                    each2 = cdata[i]
                    if each2.startswith(alreadyTallyedTerm):
                        cdata.pop(i)
                        UIDs = each2.split(alreadyTallyedTerm)[1].split(']')[0].split(', ')
                        if claims['sub'] in UIDs:
                            return 'You have already tallyed!', 401
                        else:
                            UIDs.append(claims['sub'])
                            cdata.append(Club+'.tallyed.['+', '.join(UIDs)+']')
                        exist2 = 1
                        break

                if exist2 == 0:
                    cdata.append(alreadyTallyedTerm+claims['sub']+']')

                newClubData = Account(
                    parent=ndb.Key(Account, Club),
                    clubData=cdata,
                    isExec=clubData['isExec'])

                newClubData.put()
                
                oldData = query_database(claims['sub'])[0]
                
                acData = Account(
                    parent=ndb.Key(Account, claims['sub']),
                    clubData=[],
                    isExec=[])

                tallyTerm = Club+'.tally.'
                exist3 = 0
                ocdata = oldData['clubData']
                
                for i in range(0, len(ocdata)):
                    each3 = ocdata[i]
                    if each3.startswith(tallyTerm):
                        tallyCount = int(each3.split(tallyTerm)[1])
                        ocdata[i] = tallyTerm+str(tallyCount+1)
                        exist3 = 1
                        break

                if exist3 == 0:
                    ocdata.append(tallyTerm+'1') 

                acData.email = oldData['email']
                acData.isExec = oldData['isExec']
                acData.clubData = ocdata
                acData.put()
            else:
                return 'Tally Window is not open', 401
            exist = 1
            break

    if exist == 1:
        return 'Attendance Successfully Recorded', 200
    else:
        return 'Tally Window is not open', 401

    

@app.route('/register', methods=['POST', 'PUT'])
def register():
    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401
    data = query_database(claims['sub'])

    receivedEmail = claims.get('email')

    if receivedEmail.split('@')[1] != 'wrdsb.ca' and receivedEmail != 'c.bicheru0@gmail.com':
        return 'Only WRDSB emails are allowed, please sign in with your school email.', 401
    
    if len(data) > 0:
        if data[0]['email'] != receivedEmail:
            acData = Account(
                parent=ndb.Key(Account, claims['sub']),
                clubData=data[0]['clubData'],
                isExec=data[0]['isExec'])
            acData.email = receivedEmail
            acData.put()
            checkForPromotion(query_database(claims['sub'])[0], claims['sub'])
            return 'Database email error mitigated successfully', 200
        else:
            checkForPromotion(data[0], claims['sub'])
        return 'You are already registered!', 200
    
    acData = Account(
        parent=ndb.Key(Account, claims['sub']),
        clubData=[],
	isExec=[])

    acData.email = receivedEmail
    
    acData.put()
    
    checkForPromotion(query_database(claims['sub'])[0], claims['sub'])
    return 'Registration Successful.', 200

@app.route('/delclub', methods=['POST', 'PUT'])
def deleteClub():
    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401

    data = query_database(claims['sub'])
    
    if len(data) > 1:
        logging.exception('multiple instances found on account '+data[0].email)

    if data[0]['isExec'][0] != 'admin':
        return 'Unauthorized', 401

    json = request.get_json()
    Club = json['club']

    oldLedger = query_database('backend-server')

    if len(oldLedger) > 1:
        logging.exception('multiple ledgers were found in the database')

    oldLedger = oldLedger[0]

    if Club not in oldLedger['clubData']:
        return 'Club Not In Ledger', 400

    oldClub = query_database(Club)

    if len(oldClub) != 1:
        logging.exception('issue with club "'+Club+'", multiple entries detected')
        return 'Database Error', 500

    oldClub = oldClub[0]

    newLedger = Account(
            parent=ndb.Key(Account, 'backend-server'),
            clubData=[],
            isExec=[])
    oldLedger['clubData'].remove(Club)
    newLedger.clubData = oldLedger['clubData']
    newLedger.isExec.append('server')
    newLedger.put()
    
    ndb.Key(Account, Club).delete()
    
    return 'Club Deleted Successfully.', 200

@app.route('/addclub', methods=['POST', 'PUT'])
def addClub():
    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401
    
    data = query_database(claims['sub'])
    
    if len(data) > 1:
        logging.exception('multiple instances found on account '+data[0].email)

    json = request.get_json()
    Club, Exec = json['club'], json['exec']
    
    if data[0]['isExec'][0] != 'admin' and Club not in data[0]['isExec']:
        return 'Unauthorized', 401
    
    oldLedger = query_database('backend-server')

    if len(oldLedger) > 0:
        clubLedger = oldLedger[0]
    else:
        clubLedger = Account(
            parent=ndb.Key(Account, 'backend-server'),
            clubData=[],
            isExec=[])
        clubLedger.isExec.append('server')
        clubLedger.put()
        clubLedger = query_database('backend-server')[0]

    if Club in clubLedger['clubData']:
        oldClub = query_database(Club)[0]
        newClub = Account(
            parent=ndb.Key(Account, Club),
            clubData=[],
            isExec=[])
        newClub.clubData = oldClub['clubData'] + [Exec]
        newClub.isExec.append('server')
        newClub.put()
    else:
        clubLedger['clubData'].append(Club)
        newClub = Account(
            parent=ndb.Key(Account, Club),
            clubData=[],
            isExec=[])
        newClub.isExec.append('server')
        newClub.clubData.append(Exec)
        newClub.put()

    newLedger = Account(
            parent=ndb.Key(Account, 'backend-server'),
            clubData=[],
            isExec=[])
    newLedger.clubData = clubLedger['clubData']
    newLedger.isExec.append('server')
    newLedger.put()

    return 'Club Added Successfully', 200

@app.route('/myattendance', methods=['GET'])
def returnMyAttendance():

    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401
    
    data = query_database(claims['sub'])
    if len(data) > 1:
        logging.exception('multiple instances found on account '+data[0].email)
    data = data[0]
    
    isExec = data['isExec']

    if len(isExec) > 0:
        if isExec[0] == 'admin':
            return renderAdminHtml(data)
        else:
            checkForTallyReset(data)
            return renderExecHtml(data)
    else:
        return renderStandardHtml(data)

@app.route('/loadtallywindows', methods=['GET'])
def returnTallyWindows():

    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401
    
    data = query_database(claims['sub'])
    if len(data) > 1:
        logging.exception('multiple instances found on account '+data[0].email)
    data = data[0]
    
    isExec = data['isExec']

    if len(isExec) > 0:
        return renderElevatedTallyContainer(data)
    else:
        return renderTallyContainer(data, claims['sub'])

@app.route('/delexec', methods=['POST', 'PUT'])
def deleteExec():
    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401

    data = query_database(claims['sub'])
    
    if len(data) > 1:
        logging.exception('multiple instances found on account '+data[0].email)

    json = request.get_json()
    Club, Exec = json['club'], json['exec']
    
    if data[0]['isExec'][0] != 'admin' and Club not in data[0]['isExec']:
        return 'Unauthorized', 401

    oldLedger = query_database('backend-server')

    if len(oldLedger) > 1:
        logging.exception('multiple ledgers were found in the database')

    oldLedger = oldLedger[0]
    
    if Club not in oldLedger['clubData']:
        return 'Club Not In Ledger', 400

    oldClub = query_database(Club)

    if len(oldClub) != 1:
        logging.exception('issue with club "'+Club+'", multiple entries detected')
        return 'Database Error', 500

    oldClub = oldClub[0]
    
    if Exec not in oldClub['clubData']:
        return 'Exec Not An Exec', 400
    
    newClub = Account(
            parent=ndb.Key(Account, Club),
            clubData=[],
            isExec=[])
    
    oldClub['clubData'].remove(Exec)
    newClub.clubData = oldClub['clubData']
    newClub.isExec.append('server')
    newClub.put()
    
    return 'Exec Removed Successfully.', 200

@app.route('/tallywindow', methods=['POST', 'PUT'])
def modifyTallyWindow():
    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401

    data = query_database(claims['sub'])
    
    if len(data) > 1:
        logging.exception('multiple instances found on account '+data[0].email)

    json = request.get_json()
    Club, action = json['club'], json['action'].lower()
    
    if data[0]['isExec'][0] != 'admin' and Club not in data[0]['isExec']:
        return 'Unauthorized', 401

    if action not in ['open', 'close']:
        return 'Bad Action Header', 400

    oldLedger = query_database('backend-server')

    if len(oldLedger) > 1:
        logging.exception('multiple ledgers were found in the database')

    oldLedger = oldLedger[0]
    
    if Club not in oldLedger['clubData']:
        return 'Club Not In Ledger', 400

    oldClub = query_database(Club)

    if len(oldClub) != 1:
        logging.exception('issue with club "'+Club+'", multiple entries detected')
        return 'Database Error', 500

    oldClub = oldClub[0]
    timerterm = Club+".tallywindowtimer."
    
    cdata = oldClub['clubData']

    exist = 0
    
    for i in range(0, len(cdata)):
        each = cdata[i]
        if each.startswith(timerterm):
            if action == 'close':
                cdata[i] = timerterm+'0'
                exist2 = 0
                alreadyTallyedTerm = Club+".tallyed.["
                for i in range(0, len(cdata)):
                    each2 = cdata[i]
                    if each2.startswith(alreadyTallyedTerm):
                        cdata.remove(each2)
                        exist2 = 1
                        break
                if exist2 == 0:
                    logging.exception('Nobody tallyed for club '+Club+' until the session was closed?')
            else:
                cdata[i] = timerterm+str(calendar.timegm(time.gmtime())+600)
            exist = 1
            break
    
    if exist == 0:
        if action == 'open':
            cdata.append(timerterm+str(calendar.timegm(time.gmtime())+600))
        else:
            return 'Tally Window Is Already Closed', 400
    
    
    newClub = Account(
            parent=ndb.Key(Account, Club),
            clubData=[],
            isExec=[])
    
    newClub.clubData = cdata
    newClub.isExec.append('server')
    newClub.put()
    
    return 'Exec Removed Successfully.', 200

@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500
