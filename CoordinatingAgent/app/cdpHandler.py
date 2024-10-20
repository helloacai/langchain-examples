from dotenv import load_dotenv
from cdp import *
import os
import json


load_dotenv()

Cdp.configure(os.environ['CDP_API_KEY'], os.environ['CDP_SECRET_KEY'])

Cdp.use_server_signer = True

def initializeWallet():
    wallet = Wallet.create(network_id="polygon-mainnet")
    agent_id_file = open('./agent_id.json', 'w')
    agent_id_file.write(json.dumps({wallet_id: wallet.id}))

def getWallet():
    agent_id_file = open(os.path.dirname(__file__)+'/agent_id.json', 'r')
    persistedWallet = json.loads(agent_id_file.readline())
    agent_id = persistedWallet["wallet_id"]
    wallet = Wallet.fetch(agent_id)
    return wallet
