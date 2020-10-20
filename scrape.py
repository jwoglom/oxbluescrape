import requests
import argparse
import arrow
import os
import datetime
import hashlib

class OxblueApi:
    BASE_URL = 'https://api.oxblue.com/v1/'
    CAMERA_IMAGES_URL = 'cameras/%s/images?date=%s&useMostRecentTime=false'
    X_APP_ID = 'fc18eb502cb52d060bd93897e21d9491'

    sessionID = None
    def __init__(self, link):
        s = self.openlink_sessions(link)
        self.sessionID = s['sessionID']
    
    def headers(self):
        h = {'X-APP-ID': self.X_APP_ID}
        if self.sessionID:
            h['Authorization'] = 'Bearer %s' % self.sessionID
        return h

    def get(self, path, data={}):
        r = requests.get(self.BASE_URL + path, data, headers=self.headers())
        return r.json()
    
    def post(self, path, data={}):
        r = requests.post(self.BASE_URL + path, data, headers=self.headers())
        return r.json()

    def openlink_sessions(self, link):
        return self.post('openlink-sessions', {'openLink': link})
    
    def openlink_cameras(self):
        return self.get('openlink-cameras')

    def configs(self):
        return self.get('configs')
    
    def camera_images(self, camId, date):
        return self.get(self.CAMERA_IMAGES_URL % (camId, date))

def download(path, start, allTimes):
    print('download:', path)

    a = OxblueApi(path)

    cameras = a.openlink_cameras()
    for c in cameras['cameras']:

        download_cam(a, c, start, allTimes)

def prepare_folder(camId):
    if not os.path.exists('output'):
        os.mkdir('output')
    
    folder = os.path.join('output', camId)
    if not os.path.exists(folder):
        os.mkdir(folder)

def save_to_folder(camId, fmtDate, url, lastmd5=None):
    print('Downloading', url)
    r = requests.get(url)
    if r.status_code != 200:
        print('Error', fmtDate, 'HTTP', r.status_code)
        return None

    md5 = hashlib.md5(r.content).hexdigest()
    if lastmd5 and md5 == lastmd5:
        print('Skipping', fmtDate)
        return None

    with open(os.path.join('output', camId, fmtDate + '.jpg'), 'wb') as out:
        out.write(r.content)
    print('Saved', fmtDate)
    return md5


def download_cam(a, c, start, allTimes):
    camId = c['id']

    prepare_folder(camId)
    
    lastUpload = arrow.get(c['lastUpload'], 'M/D/YYYY H:mm A')
    firstUpload = arrow.get(c['firstUpload'])

    if start:
        date = arrow.get(start)
    else:
        date = firstUpload

    md5 = None
    while date <= lastUpload:
        imgs = a.camera_images(camId, date.strftime('%Y%m%d'))
        times = imgs['times']
        defTime = imgs['time']
        savePath = imgs['paths']['savePath']
        fmtDate = date.strftime('%Y%m%d')
        if allTimes:
            for t in times:
                url = savePath.replace('/%s/' % defTime, '/%s/' % t)
                newmd5 = save_to_folder(camId, '%s-%s' % (fmtDate, t), url, md5)
                if newmd5:
                    md5 = newmd5
        else:
            newmd5 = save_to_folder(camId, fmtDate, savePath, md5)
            if newmd5:
                md5 = newmd5
        
        date += datetime.timedelta(days=1)

def main():
    parser = argparse.ArgumentParser(description='Scrape timelapse images from app.oxblue.com')
    parser.add_argument('url', type=str, help='The URL in the form https://app.oxblue.com/open/xxxx/yyyy')
    parser.add_argument('-s', '--start', type=str, default=None, help='The date to start')
    parser.add_argument('-a', '--all-times', action='store_const', const=True, default=False, help='Download all times in a day')

    args = parser.parse_args()

    magic = 'app.oxblue.com/open/'
    if magic not in args.url:
        raise Exception('Invalid URL format. Must contain %s' % magic)

    path = args.url.split(magic)[1]
    download(path, args.start, args.all_times)


if __name__ == '__main__':
    main()