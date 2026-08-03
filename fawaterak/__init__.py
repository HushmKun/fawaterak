from dotenv import load_dotenv

from fawaterak._http import *
from fawaterak.auth import *
from fawaterak.auth import TokenManager
from fawaterak.config import *
from fawaterak.exceptions import *

load_dotenv()

conf = Config.resolve()

Manager = TokenManager(
	conf.client_id, conf.client_secret, conf.base_url, requests.Session()
)

token_1 = Manager.access_token

Manager.refresh()

token_2 = Manager.access_token

print(token_1 == token_2)

client = HTTPClient(conf.base_url, Manager, timeout=30)
