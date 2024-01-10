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

def list_threads(service, query):
    threadList = []
    pageToken = ""
    cont = True

    print("=> [i] Getting threads... ")

    while cont:
        results = service.users().threads().list(userId='me', q=query, maxResults=500, pageToken=pageToken).execute()
        threads = results.get('threads', [])

        for thread in threads:
            threadList.append(thread['id'])

        try:
            pageToken = results['nextPageToken']
        except KeyError:
            pageToken = ""
            cont = False
    if len(threadList) != 0: threadList = dedup_thread_list(threadList)
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
        print('===============================')
        query = input("[?] Which Gmail query operator do you want to use? ")

        # labelId = get_label_id(service, labelName)
        # if labelId == None:
        #     print("=> [x] Label [{}] is not existing.".format(labelName))
        #     return

        # threadTotal = get_label_thread_total(service, labelId)

        # maxResult = input("[?] There are {} threads in label [{}]. How many thread do you wanna to delete at one time: ".format(threadTotal, labelName))

        threadList = list_threads(service, query)
        if len(threadList) == 0:
            print("=> [x] No thread found.")
            return

        numOfExe = int(input("[?] There are {} threads for the query [{}]. How many thread do you want to delete? ".format(len(threadList), query.strip())))
        msgErrList, amountOfMsg, totalTime = delete_threads(service, threadList[:numOfExe])
        if len(msgErrList) != 0:
            print("=> [x] There is/are {} being unable to delete.".format(len(msgErrList)))
            return

        print("=> [i] Just deleted {}/{} threads in {} seconds.".format(amountOfMsg-len(msgErrList), amountOfMsg, totalTime))

if __name__ == '__main__':
    main()