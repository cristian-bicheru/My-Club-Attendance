# Built on top of the 'FireNotes' Firebase example. Coded by Cristian Bicheru 2018

import logging
from flask import Flask, jsonify, request
import flask_cors
from google.appengine.ext import ndb
import google.auth.transport.requests
import google.oauth2.id_token
import requests_toolbelt.adapters.appengine
import calendar
import time


# Import all of the template html files.
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
# End import.


# Define the end of the 'clubList' div. This is used to split the html files
# in certain functions.
clubListDiv = 'id="clubList">\n'


# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()
HTTP_REQUEST = google.auth.transport.requests.Request()

app = Flask(__name__)
flask_cors.CORS(app)


# Define the 'Account' class which is used for all user accounts and backend
# data.
class Account(ndb.Model):
    email = ndb.StringProperty()
    clubData = ndb.StringProperty(repeated=True)
    isExec = ndb.StringProperty(repeated=True)
    created = ndb.DateTimeProperty(auto_now_add=True)


# [START gae_python_query_database]
def query_database(user_id):
    ancestor_key = ndb.Key(Account, user_id)
    query = Account.query(ancestor=ancestor_key).order(-Account.created)
    accountData = query.fetch()

    acDataParsed = []
    if len(accountData) > 0:
        accountData = accountData[0]
        acDataParsed.append({
            'key'       : accountData.key,
            'email'     : accountData.email,
            'clubData'  : accountData.clubData,
            'isExec'    : accountData.isExec,
            'created'   : accountData.created
        })

    return acDataParsed
# [END gae_python_query_database]


# Define the function which renders the panel shown to admins in the
# attendance page on the UI.
def renderAdminHtml(data):
    # Query database for the server data (sometimes referred to as the club ledger,
    # since it contains a list of all the clubs)
    sdata = query_database('backend-server')[0]

    # The clubData element contains all the clubs as mentioned in the previous comment.
    clubs = sdata['clubData']

    # Split the template html by the clubListDiv.
    divLocation = adminHtml.find(clubListDiv)+len(clubListDiv)
    htmls = adminHtml[:divLocation]
    htmle = adminHtml[divLocation:]

    for club in clubs:
        # Open an h4 heading and add the club name.
        htmls += '<h4>' + club + ": "

        # Query for the club and get the list of execs.
        query = query_database(club)[0]['clubData']

        # If the list of execs is empty, relay this info to the admin and close the heading.
        if len(query) == 0:
            htmls += 'There are no execs in this club!</h4>\n'

        # Otherwise, add each exec to the html and close the heading.
        else:
            for Exec in query[:-1]:
                htmls += Exec+", "
            htmls += query[-1]+"</h4>\n"

    # Recombine the html parts and return the result.
    return htmls+htmle


# Define the function which formats a club block for the exec panel.
def formatClubBlock(club):
    # Replace the club block template's placeholders with the values for the club.
    # &CLUB& tags should be replaced with the club name after spaces (and special
    # characters, but this has yet to be implemented) have been removed. &CLUBN&
    # Tags should be replaced with whatever the club's name is.
    html = clubBlock.replace('&CLUB&', club.replace(' ', '_')).replace('&CLUBN&', club)

    # Query the club and set the clubData equal to the clubdata found in the query.
    cdata = query_database(club)[0]
    clubData = cdata['clubData']

    # This is the term where the tally window timer is stored.
    timerterm = club+".tallywindowtimer."

    for i in range(0, len(clubData)):
        # If the term begins with the defined timerterm:
        if clubData[i].startswith(timerterm):
            # Split the term to get the actual time.
            tallywtime = clubData[i].split(timerterm)[1]

            # If the current time is not past the tally window time:
            if calendar.timegm(time.gmtime()) < tallywtime:
                # Split the html by the split term and insert the timer code with the proper formatting.
                html = html.split("<!--tally window status-->\n")
                html.insert(1, timerCode.replace('&CLUB&', club.replace(' ', '_')).replace('&TIME&', str(float(tallywtime)*1000)))
                html = ''.join(html)
            else:
                # Otherwise just add that the tally window is currently closed.
                html = html.replace('<!--tally window status-->', '<h4>Window Closed</h4>')
    return html


# Define the function which renders the exec panel.
def renderExecHtml(data):
    # Split the execHtml template by the clubListDiv.
    divLocation = execHtml.find(clubListDiv)+len(clubListDiv)
    htmls = execHtml[:divLocation]
    htmle = execHtml[divLocation:]

    # For each club in the exec is an exec of, format a club block.
    for club in data['isExec']:
        htmls += formatClubBlock(club)
    return htmls+htmle


# Define the function which renders the attendance panel for regular users.
def renderStandardHtml(data):
    # Split the template html by the clubListDiv.
    html = standardHtml.split(clubListDiv)

    # Define cdata to be the user's clubData.
    cdata = data['clubData']

    # Then, for each club in their cdata, add the number of times they've tallyed in a heading.
    for each in cdata:
        if '.tally.' in each:
            club, tallyCount = each.split('.tally.')
            html.insert(1, '<h4>'+club+': '+tallyCount+'</h4>\n')
    return ''.join(html)


# This function is called when signing in and checks for any
# changes to the account (as in if they became an exec or were
# kicked off an exec team).
def checkForPromotion(data, uid):
    # If the email is my email, make the account admin.
    if data['email'] == 'c.bicheru0@gmail.com':
        newData = Account(
            key     =data['key'],
            email   =data['email'],
            clubData=data['clubData'],
            isExec  =['admin'])
        newData.put()

    # Query the server and save it in the sdata variable.
    sdata = query_database('backend-server')

    # If there is a club ledger:
    if len(sdata) > 0:
        # Redefine sdata to be the clubData in the ledger.
        sdata = sdata[0]['clubData']

        # Define the email as a variable.
        email = data['email']

        for club in sdata:
            # Query the database for the club.
            cdata = query_database(club)

            # If the query returned no results but the club is still in the
            # exec's data, remove it.
            if len(cdata) == 0 and club in data['isExec']:
                data['isExec'].remove(club)

            else:
                cdata = cdata[0]

                # Otherwise if the email is in the club's exec list but not the user's list,
                # add the club to the user's exec list.
                if email in cdata['clubData']:
                    if club not in data['isExec']:
                        data['isExec'].append(club)

                # And if the email happens to not be in the club's exec list but in the user's list,
                # remove the club from the user's exec list.
                if email not in cdata['clubData']:
                    if club in data['isExec']:
                        data['isExec'].remove(club)

        # If the club is in the user's exec list but not the club ledger, remove
        # the club from the user's list.
        for club in data['isExec']:
            if club not in sdata and club != 'admin':
                data['isExec'].remove(club)

        # Update the user's account data with the new data.
        newData = Account(
            key     =data['key'],
            email   =data['email'],
            clubData=data['clubData'],
            isExec  =data['isExec'])
            newData.put()

    # Otherwise, if the club ledger does not exist:
    else:
        # Log that something bad has likely happened to the database.
        logging.exception('mega yikes')


# Define the function which formats an indivdual tally block.
def formatTallyBlock(club, etime):
    # Format the template 'tallyBlock' html and insert the countdown timer.
    thtml = tallyBlock.replace('&CLUB&', club.replace(' ', '_')).replace('&CLUBN&', club)
    thtml = thtml.split("<!--tally window status-->\n")
    thtml.insert(1, timerCode.replace('&CLUB&', club.replace(' ', '_')).replace('&TIME&', str(float(etime)*1000)))
    thtml = ''.join(thtml)
    return thtml


# Define the function which renders the entire tally container.
def renderTallyContainer(data, uid):
    # Query the database for the club ledger and store it as sdata.
    sdata = query_database('backend-server')

    # If the query wasn't empty, continue as normal.
    if len(sdata) > 0:
        # Define an empty html variable and the sdata variable as the clubData entry.
        html = ""
        sdata = sdata[0]['clubData']

        # For each club in the ledger:
        for club in sdata:
            # Define the terms used to split the timer and tallyed list.
            timerterm = club+".tallywindowtimer."
            alreadyTallyedTerm = club+".tallyed.["

            # Query the database for the club and store the clubData as cdata.
            cdata = query_database(club)[0]['clubData']

            # Define the alreadyTallyed boolean to be 0.
            alreadyTallyed = 0

            # For each in the clubData:
            for each in cdata:

                # If it is the alreadyTallyed list:
                if each.startswith(alreadyTallyedTerm):

                    # Generate a list of the UIDs from the data.
                    UIDs = each.split(alreadyTallyedTerm)[1].split(']')[0].split(', ')

                    # If the user's UID is in the alreadyTallyed list, set the boolean to True and break.
                    if uid in UIDs:
                        alreadyTallyed = 1
                    break

            # If the user has not already tallyed this session and the tally window has
            # not expired yet:
            if alreadyTallyed == 0:
                for each in cdata:
                    if each.startswith(timerterm):
                        etime = float(each.split(timerterm)[1])
                        if calendar.timegm(time.gmtime()) < etime:

                            # Format and add a tally block to the html.
                            html += formatTallyBlock(club, etime)
                        break
        return html
    # If for some reason, the club ledger is missing:
    else:
        # Log that something bad has probably happened to the database.
        logging.exception('mega yikes')


# Defines the function which renders the tally container for 'elevated' users.
def renderElevatedTallyContainer(data):
    return '<h4>No tallying for admins or execs!</h4>'


# Define the function which checks if the tally window has expired and
# resets the alreadyTallyed list, along with the tally window timer.
def checkForTallyReset(data):
    # For each club the exec is an exec of (the reason we don't check
    # every club is because the alreadyTallyed only needs to be reset
    # when reopening the tally window, and an exec of any given club
    # must render the panel in order to open the window, hence it saves
    # some database queries and accomplishes the same goal), check to
    # see if the club window has expired and reset the data if it has.
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
            key     =oldClubData['key'],
            clubData=[],
            isExec  =[])
        newClub.clubData = oldCData
        newClub.isExec.append('server')
        newClub.put()


# Define the tally function.
@app.route('/tally', methods=['POST', 'PUT'])
def recordTally():

    # Verify Firebase auth.
    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401

    # Get the club the user's is requesting to tally.
    Club = request.get_json()['club']

    # Query the database for the club ledger.
    clubLedger = query_database('backend-server')

    # If there are multiple ledgers, log this.
    if len(clubLedger) > 1:
        logging.exception('multiple ledgers detected?!?!?')

    clubLedger = clubLedger[0]

    # If the requested club is not in the ledger, raise an error and log it.
    if Club not in clubLedger['clubData']:
        logging.exception('A tally for club '+Club+' was requested by UID '+claims['sub']+'.')
        return 'Club does not exist', 400

    # Otherwise query for the club.
    clubData = query_database(Club)

    # If multiple instances of the club were detected, log this.
    if len(clubData) > 1:
        logging.exception('multiple instances of '+Club+' were detected?!?!?')

    clubData = clubData[0]

    # Define the term with which we will split the timer data in order to get
    # the window close time.
    timerterm = Club+".tallywindowtimer."

    # Define the boolean exist to be False by default, and cdata to be the
    # Club's clubData.
    exist = 0
    cdata = clubData['clubData']

    # This for loop checks each item in the cdata in order to find the timer
    # and alreadyTallyed list. If the user has already tallyed or the window
    # is closed at the time of the tally, return a 401 Unauthorized.
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
                    key     =clubData['key'],
                    clubData=cdata,
                    isExec  =clubData['isExec'])

                newClubData.put()

                oldData = query_database(claims['sub'])[0]

                acData = Account(
                    key     =oldData['key'],
                    clubData=[],
                    isExec  =[])

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
                key     =data[0]['key'],
                clubData=data[0]['clubData'],
                isExec  =data[0]['isExec'])
            acData.email = receivedEmail
            acData.put()
            checkForPromotion(query_database(claims['sub'])[0], claims['sub'])
            return 'Database email error mitigated successfully', 200
        else:
            checkForPromotion(data[0], claims['sub'])
        return 'You are already registered!', 200

    acData = Account(
        parent  =ndb.Key(Account, claims['sub']),
        clubData=[],
	isExec  =[])

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
            key     =oldLedger['key'],
            clubData=[],
            isExec  =[])
    oldLedger['clubData'].remove(Club)
    newLedger.clubData = oldLedger['clubData']
    newLedger.isExec.append('server')
    newLedger.put()

    uid = int(str(oldClub['key']).split("'Account', ")[-1][:-1])
    ndb.Key(Account, uid).delete()

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
            parent  =ndb.Key(Account, 'backend-server'),
            clubData=[],
            isExec  =[])
        clubLedger.isExec.append('server')
        clubLedger.put()
        clubLedger = query_database('backend-server')[0]

    if Club in clubLedger['clubData']:
        oldClub = query_database(Club)[0]
        newClub = Account(
            key     =oldClub['key'],
            clubData=[],
            isExec  =[])
        newClub.clubData = oldClub['clubData'] + [Exec]
        newClub.isExec.append('server')
        newClub.put()
    else:
        clubLedger['clubData'].append(Club)
        newClub = Account(
            parent  =ndb.Key(Account, Club),
            clubData=[],
            isExec  =[])
        newClub.isExec.append('server')
        newClub.clubData.append(Exec)
        newClub.put()

    newLedger = Account(
            key     =clubLedger['key'],
            clubData=[],
            isExec  =[])
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
            key     =oldClub['key'],
            clubData=[],
            isExec  =[])

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
            key     =oldClub['key'],
            clubData=[],
            isExec  =[])

    newClub.clubData = cdata
    newClub.isExec.append('server')
    newClub.put()

    return 'Exec Removed Successfully.', 200


@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500
