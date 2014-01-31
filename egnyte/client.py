import json
import urllib
import datetime
import requests
from requests.auth import AuthBase

from . import const

class RequestsAuth(AuthBase):
    """
    Sending oAuth access_token in auth header
    """
    def __init__(self, access_token):
        self.access_token = access_token

    def _oauth_str(self):
        """Returns oAuth string."""
        return 'Bearer %s' % self.access_token

    def __call__(self, r):
        r.headers['Authorization'] = self._oauth_str()
        return r

class EgnyteOAuth(object):
    ACCESS_TOKEN_URI = "/puboauth/token"
    GRANT_TYPE = "password"

    def __init__(self, domain, username, password, api_key):
        self.domain = domain
        self.username = username
        self.password = password
        self.api_key = api_key

    def get_url(self, uri, **kw):
        kw['server'] = const.SERVER
        kw['domain'] = self.domain
        return const.BASE_URL % kw + uri % kw

    def get_access_token(self):
        url = self.get_url(self.ACCESS_TOKEN_URI)
        data = dict(
            client_id = self.api_key,
            username = self.username,
            password = self.password,
            grant_type = self.GRANT_TYPE,
            )
        return requests.post(url, data=data)
    
class EgnyteClient(object):
    USER_INFO_URI = r"/pubapi/v1/userinfo"
    FOLDER_URI = r"/pubapi/v1/fs%(folderpath)s"
    FILE_URI = r"/pubapi/v1/fs-content/%(filepath)s"
    LINK_URI = r"/pubapi/v1/links"
    LINK_URI2 = r"/pubapi/v1/links/%(id)s"

    ACTION_ADD_FOLDER = 'add_folder'
    ACTION_MOVE = 'move'
    ACTION_COPY = 'copy'
    ACTION_LIST = 'list_content'
    ITER_CHUNK_SIZE = 10 * 1024 # bytes

    def __init__(self, domain, access_token):
        self.domain = domain
        self.auth = RequestsAuth(access_token)

    def get_url(self, uri, **kw):
        kw['server'] = const.SERVER
        kw['domain'] = self.domain
        return const.BASE_URL % kw + uri % kw

    def encode_path(self, path):
        return str(urllib.quote(path.encode('utf-8'), '/'))

    def userinfo(self):
        headers = {'content-type': 'application/json'}
        url = self.get_url(self.USER_INFO_URI)
        r = requests.get(url, auth=self.auth, headers=headers)
        return r
    
    def create_folder(self, folderpath):
        url = self.get_url(self.FOLDER_URI, folderpath=self.encode_path(folderpath))
        folderpath = self.encode_path(folderpath)
        data = {'action': self.ACTION_ADD_FOLDER}
        headers = {'content-type': 'application/json'}
        r = requests.post(url, auth=self.auth, data=json.dumps(data), headers=headers)
        ## make sure that success code here is 201
        return r

    def get_file(self, filepath, fptr):
        url = self.get_url(self.FILE_URI, filepath=self.encode_path(filepath))
        r = requests.get(url, auth=self.auth, stream=True)
        if r.status_code == requests.codes.ok:
            for data in r.iter_content(self.ITER_CHUNK_SIZE):
                fptr.write(data)
        return r

    def put_file(self, filepath, fptr):
        url = self.get_url(self.FILE_URI, filepath=self.encode_path(filepath))
        r = requests.post(url, auth=self.auth, data=fptr, stream=True)
        return r

    def delete(self, folderpath):
        url = self.get_url(self.FOLDER_URI, folderpath=self.encode_path(folderpath))
        r = requests.delete(url, auth=self.auth)
        return r

    def move(self, folderpath, destination):
        url = self.get_url(self.FOLDER_URI, folderpath=self.encode_path(folderpath))
        data = {'action': self.ACTION_MOVE, 'destination': destination}
        headers = {'content-type': 'application/json'}
        r = requests.post(url, auth=self.auth, data=json.dumps(data), headers=headers)
        return r

    def copy(self, folderpath, destination):
        url = self.get_url(self.FOLDER_URI, folderpath=self.encode_path(folderpath))
        data = {'action': self.ACTION_COPY, 'destination': destination}
        headers = {'content-type': 'application/json'}
        r = requests.post(url, auth=self.auth, data=json.dumps(data), headers=headers)
        return r

    def list_content(self, folderpath):
        url = self.get_url(self.FOLDER_URI, folderpath=self.encode_path(folderpath))
        data = {'action': self.ACTION_LIST}
        headers = {'content-type': 'application/json'}
        r = requests.get(url, auth=self.auth, data=json.dumps(data), headers=headers)
        return r

    def create_link(self, path, kind, accessibility,
                    recipients=None, send_email=False, message=None,
                    copy_me=False, notify=False, link_to_current=False,
                    expiry=None, add_filename=False,
                    ):
        assert kind in const.LINK_KIND_LIST
        assert accessibility in const.LINK_ACCESSIBILITY_LIST
        if recipients is None:
            recipients = []
        url = self.get_url(self.LINK_URI)
        data = {
            "path": path,
            "type": kind,
            "accessibility": accessibility,
            "sendEmail": send_email,
            "copyMe": copy_me,
            "notify": notify,
            "addFilename": add_filename,
            }
        if kind == const.LINK_KIND_FILE:
            data["linkToCurrent"] = link_to_current
        if recipients:
            data['recipients'] = recipients
        if expiry is not None:
            if type(expiry) == int:
                data["expiryClicks"] = expiry
            elif type(expiry) == datetime.date:
                data["expiryDate"] = expiry.strftime("%Y-%m-%d")
        if message is not None:
            data['message'] = message
        headers = {'content-type': 'application/json'}
        r = requests.post(url, auth=self.auth, data=json.dumps(data), headers=headers)
        return r

    def delete_link(self, id):
        url = self.get_url(self.LINK_URI2, id=id)
        r = requests.delete(url, auth=self.auth)
        return r
        
    def link_details(self, id):
        url = self.get_url(self.LINK_URI2, id=id)
        r = requests.get(url, auth=self.auth)
        return r

    ## def links(self):
    ##     ##TODO
    ##     pass
    