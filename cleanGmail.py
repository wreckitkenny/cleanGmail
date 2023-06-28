import os.path
import argparse, sys, time
from tqdm import tqdm
from time import sleep

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://mail.google.com/']

def credential(credFile):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credFile, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def get_label_id(service, labelName):
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    print("=> [i] Getting label ID... ")

    if not labels:
        print('No labels found.')
        return

    for label in labels:
        if label['name'] == labelName:
            return label['id']

def get_label_thread_total(service, labelId):
    results = service.users().labels().get(userId='me', id=labelId).execute()
    return results['threadsTotal']

def list_threads(service, labelId, maxResult):
    threadList = []
    pageToken = ""
    rep = 0

    print("=> [i] Getting threads... ")

    if maxResult > 500: reps = maxResult / 500
    if maxResult <= 500: reps = 1

    while rep < reps:
        # if pageToken:
        results = service.users().threads().list(userId='me', labelIds=labelId, maxResults=maxResult, pageToken=pageToken).execute()
        # else:
        #     results = service.users().threads().list(userId='me', labelIds=labelId, maxResults=maxResult).execute()

        threads = results.get('threads', [])

        for thread in threads:
            threadList.append(thread['id'])

        rep += 1
        try:
            pageToken = results['nextPageToken']
        except KeyError:
            pageToken = ""

    return threadList

def dedup_thread_list(threadList):
    newThreadList = []
    _ = [newThreadList.append(t) for t in threadList if t not in newThreadList]
    return newThreadList

def delete_threads(service, threadList):
    threadErrList = []

    print("=> [i] Starting thread deletion... ")

    st = time.time()
    for threadId in tqdm(range(len(threadList)),desc="=> [i] Running..."):
    # for threadId in np.nditer(npthreadList):
        results = service.users().threads().delete(userId='me', id=threadList[threadId]).execute()
        if results != '':
            threadErrList.append(threadList[threadId])
    et = time.time()
    return threadErrList, len(threadList), et - st

def main():
    parser=argparse.ArgumentParser(
    description='''A tool to clean Gmail messages''',
    epilog="""Author: _wiky""")
    parser.add_argument('--creds', help='path/to/credentials.json')
    args=parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return

    if args.creds != "":
        creds = credential(args.creds)
        service = build('gmail', 'v1', credentials=creds)

        print('WARNING: MAKE SURE THAT YOU HAVE RESPONSIBILITY ON YOUR OWN ACTION.\n=> Loading...\n')
        sleep(3)
        print('===== cleanGmail features =====\n+ Delete mails based on Labels\n')
        print('@Developer: _wiky\n---\n')
        print('===============================')
        labelName = input("[?] Which Gmail label do you wanna choose to delete: ")

        labelId = get_label_id(service, labelName)
        if labelId == None:
            print("=> [x] Label [{}] is not existing.".format(labelName))
            return

        threadTotal = get_label_thread_total(service, labelId)

        maxResult = input("[?] There are {} threads in label [{}]. How many thread do you wanna to delete at one time: ".format(threadTotal, labelName))

        threadList = list_threads(service, labelId, int(maxResult))
        if len(threadList) == 0:
            print("=> [x] No thread found in label [{}].".format(labelName))
            return

        msgErrList, amountOfMsg, totalTime = delete_threads(service, threadList)
        if len(msgErrList) != 0:
            print("=> [x] There is/are {} being unable to delete.".format(len(msgErrList)))
            return

        print("=> [i] {} - Just deleted {}/{} threads in {} seconds.".format(labelName, amountOfMsg-len(msgErrList), amountOfMsg, totalTime))

if __name__ == '__main__':
    main()