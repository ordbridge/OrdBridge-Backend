import json
import os
import subprocess
import uuid
import requests
from flask import Blueprint, jsonify, request, current_app
from pymongo import MongoClient
from cachetools import TTLCache
from datetime import datetime
from dotenv import load_dotenv
from src.utils.helper_utils import create_uuid_with_time
from src.models.user_model import UserDetails

load_dotenv()

HOST_URL = os.environ.get("DATABASE_URL")
DB_NAME = os.environ.get("DB_NAME")
COLLECTION_NAME_ALL_TOKENS = os.environ.get("COLLECTION_NAME_ALL_TOKENS")
COLLECTION_NAME_CONTROLLED_TOKENS = os.environ.get("COLLECTION_NAME_CONTROLLED_TOKENS")
COLLECTION_NAME_USER = os.environ.get("COLLECTION_NAME_USER")
COLLECTION_NAME_INSCRIPTIONS = os.environ.get("COLLECTION_NAME_INSCRIPTIONS")
COLLECTION_NAME_TRANSFERRED = os.environ.get("COLLECTION_NAME_TRANSFERRED")
COLLECTION_NAME_LOGS = os.environ.get("COLLECTION_NAME_LOGS")
COLLECTION_INIT_PAYMENT_LOGS = os.environ.get("COLLECTION_INIT_PAYMENT_LOGS")
COLLECTION_PENDING_ENTRIES_LOGS = os.environ.get("COLLECTION_PENDING_ENTRIES_LOGS")
OK_LINK_API_KEY = os.environ.get("OK_LINK_API_KEY")
OK_LINK_TOKEN_CONTRACT_ADDRESS = os.environ.get("OK_LINK_TOKEN_CONTRACT_ADDRESS")
OK_LINK_CHAIN_ID = os.environ.get("OK_LINK_CHAIN_ID")
OK_LINK_ADDRESS = os.environ.get("OK_LINK_ADDRESS")
BRIDGE_ADDRESS = os.environ.get("BRIDGE_ADDRESS")
RANDOM_KEY_GEN_ID = os.environ.get("RANDOM_KEY_GEN_ID")

bapi = Blueprint('bapi', __name__)
cache = TTLCache(maxsize=5, ttl=300)

# Connect to MongoDB
client = MongoClient(HOST_URL)

# Access the database and collection
db = client[DB_NAME]
collection_all_tokens = db[COLLECTION_NAME_ALL_TOKENS]
collection_inscriptions = db[COLLECTION_NAME_INSCRIPTIONS]
collection_transferred = db[COLLECTION_NAME_TRANSFERRED]
collection_user = db[COLLECTION_NAME_USER]
collection_controlled_tickers = db[COLLECTION_NAME_CONTROLLED_TOKENS]
collection_logs = db[COLLECTION_NAME_LOGS]
collection_init_payment_logs = db[COLLECTION_INIT_PAYMENT_LOGS]
collection_pending_entries_logs = db[COLLECTION_PENDING_ENTRIES_LOGS]

homepage_data = {
    "total_deposits": 0,
    "daily_volume": 0,
    "percent_change_volume": 0
}

"""
    update the map if new chain is add in the system
"""
CHAIN_WISE_FLAG_MAP = {
    "ethchain": "BRC_TO_ETH",
    "avaxchain": "BRC_TO_AVAX",
    "basechain": "BRC_TO_BASE",
    "arbichain": "BRC_TO_ARBI"
}


@bapi.route('/bridge/home', methods=['GET'])
def get_home():
    return jsonify(homepage_data)


def push_log(types):
    data = {}
    current_time = datetime.now()
    data["created_at"] = current_time
    data["type"] = types
    collection_logs.insert_one(data)


# @bapi.route('/bridge/get_logs', methods=['GET'])
def get_logs():
    records = collection_logs.find()
    data = [{"created_at": record["created_at"], "type": record["type"]} for record in records]
    return jsonify(data)


@bapi.route('/bridge/tickers_controlled', methods=['GET'])
def get_controlled_tickers():
    record = collection_controlled_tickers.find_one()
    if record:
        tickers = record["tickers"]
        return tickers
    return ["brge"]


@bapi.route('/bridge/user_details', methods=['POST'])
def post_user_details():
    data = request.json

    user_detail = data.get('user_details', {})
    unisat_address = user_detail.get('unisat_address')
    metamask_address = user_detail.get('metamask_address')

    _user_data = {}
    # Process user details here
    if unisat_address is not None:
        _user_data["unisat_address"] = unisat_address
    if metamask_address is not None:
        _user_data['metamask_address'] = metamask_address
    _user_data["session_key"] = create_uuid_with_time()

    user_details = UserDetails(**_user_data)
    user_details.save()
    response_data = {"user_details": user_details.to_dict()}
    return jsonify(response_data)


@bapi.route('/bridge/update_user_details', methods=['POST'])
def post_update_user_details():
    data = request.json
    session_key = request.headers.get('session-key')
    current_app.logger.info("[post_update_user_details] request %s session-key %s", data, session_key)
    push_log("USER")

    user_detail = data.get('user_details', {})
    unisat_address = user_detail.get('unisat_address')
    metamask_address = user_detail.get('metamask_address')

    if unisat_address is None and metamask_address is None:
        raise Exception("BAD REQUEST")

    if session_key is not None:
        user_details = UserDetails.objects(session_key=session_key).first()
        if user_details is None:
            raise Exception("Invalid session key")
        if unisat_address is not None:
            user_details.unisat_address = unisat_address
        if metamask_address is not None:
            user_details.metamask_address = metamask_address
        user_details.save()
        response_data = {"user_details": user_details.to_dict()}
        return jsonify(response_data)

    elif unisat_address is not None:
        user_details = UserDetails.objects(unisat_address=unisat_address).first()
        if user_details is not None:
            if metamask_address is not None:
                user_details.metamask_address = metamask_address
            user_details.save()
            response_data = {"user_details": user_details.to_dict()}
            return jsonify(response_data)
        else:
            _user_data = {"unisat_address": unisat_address}
            if metamask_address is not None:
                _user_data['metamask_address'] = metamask_address
            _user_data["session_key"] = create_uuid_with_time()
            user_details = UserDetails(**_user_data)
            user_details.save()
            response_data = {"user_details": user_details.to_dict()}
            return jsonify(response_data)

    else:
        user_details = UserDetails.objects(metamask_address=metamask_address).first()
        if user_details is not None:
            if unisat_address is not None:
                user_details.unisat_address = unisat_address
            user_details.save()
            response_data = {"user_details": user_details.to_dict()}
            return jsonify(response_data)
        else:
            _user_data = {"metamask_address": unisat_address}
            if unisat_address is not None:
                _user_data['unisat_address'] = metamask_address
            _user_data["session_key"] = create_uuid_with_time()
            user_details = UserDetails(**_user_data)
            user_details.save()
            response_data = {"user_details": user_details.to_dict()}
            return jsonify(response_data)


@bapi.route('/bridge/init_payment', methods=['POST'])
def init_payment():
    our_address = BRIDGE_ADDRESS
    push_log("INITIATE")
    # session_key = request.headers.get('session_key')
    data = request.json
    current_app.logger.info("[init_payment] with request %s", data)

    tickername = data.get('tickername')
    tickerval = data.get('tickerval')
    unisat_address = data.get('unisat_address')
    metamask_address = data.get('metamask_address')
    chain = data.get('chain')

    if not all([tickername, tickerval, unisat_address, metamask_address]):
        return jsonify({'error': 'Missing required fields'})

    collection_init_payment_logs.insert_one({
        "tickername": tickername,
        "tickerval": tickerval,
        "unisat_address": unisat_address,
        "metamask_address": metamask_address, "created_at": datetime.now()})

    response_data = {
        "data": {
            "inscribe": {
                "p": "brc-20",
                "op": "transfer",
                "tick": str(tickername),
                "amt": str(tickerval),
                "ethchain": str(metamask_address)
            },
            "address": our_address
        }
    }

    if chain:
        if chain.lower() == "avax" and response_data["data"]["inscribe"]["ethchain"]:
            response_data["data"]["inscribe"]["avaxchain"] = response_data["data"]["inscribe"].pop("ethchain")
        elif chain.lower() == "base" and response_data["data"]["inscribe"]["ethchain"]:
            response_data["data"]["inscribe"]["basechain"] = response_data["data"]["inscribe"].pop("ethchain")
        elif chain.lower() == "arbi" and response_data["data"]["inscribe"]["ethchain"]:
            response_data["data"]["inscribe"]["arbichain"] = response_data["data"]["inscribe"].pop("ethchain")

    current_app.logger.info("[init_payment] with request %s response %s", data, response_data)

    return jsonify(response_data)


def validate_inscribe_json(inscribe_json):
    required_fields = ['p', 'op', 'amt', 'tick']

    missing_fields = [field for field in required_fields if field not in inscribe_json]
    if missing_fields:
        return False

    if not (not ('ethchain' not in inscribe_json) or not ('avaxchain' not in inscribe_json) or not (
            'basechain' not in inscribe_json)) and 'arbichain not in inscribe_json':
        return False

    return True


def generate_custom_uuid():
    c_id = str("a") + uuid.uuid4().hex + str(RANDOM_KEY_GEN_ID) + str("i0")
    return c_id


@bapi.route('/bridge/inscribe', methods=['POST'])
def inscribe():
    push_log("INSCRIBE")
    data = request.json
    current_app.logger.info("[inscribe] with request %s", data)

    inscribe_json = data.get('inscribe_json')
    unisat_address = data.get('unisat_address')
    metamask_address = data.get('metamask_address')

    if not all([inscribe_json, unisat_address, metamask_address]):
        return jsonify({'error': 'Missing required fields'})

    if not validate_inscribe_json(inscribe_json):
        return jsonify({'error': 'invalid inscribe json'})

    ins_id = generate_custom_uuid()
    db_obj = {"inscription_id": ins_id, "transaction_data": data, "transaction_status": "INSCRIBED"}
    collection_inscriptions.update_one({"inscription_id": ins_id}, {"$set": db_obj}, upsert=True)
    response_data = {
        "data": {
            "inscription_id": ins_id,
        }
    }
    current_app.logger.info("[init_payment] with request %s response %s", data, response_data)

    return jsonify(response_data)


def send_mint_entries(send_data):
    api_url = "http://localhost:5001/add_mint_entries"
    headers = {'Content-Type': 'application/json'}

    request_body = json.dumps(send_data)
    print(request_body)
    response = requests.post(api_url, json=request_body, headers=headers)
    response_data = response.text
    return response_data


@bapi.route('/bridge/pending_entries', methods=['POST'])
def pending_entries():
    current_app.logger.info("[pending_entries] with request %s", request.json)
    data = request.json

    unisat_address = data.get('unisat_address')
    metamask_address = data.get('metamask_address')

    if not all([unisat_address, metamask_address]):
        return jsonify({'error': 'Missing required fields'})

    collection_pending_entries_logs.insert_one({"unisat_address": unisat_address,
                                                "metamask_address": metamask_address,
                                                "created_at": datetime.now()})

    data = {}
    unprocessed = collection_inscriptions.find({"transaction_data.unisat_address": unisat_address,
                                                "$or": [{"deleted": {"$ne": "true"}},
                                                        {"deleted": {"$exists": "false"}}]})
    data["unprocessed"] = [{
        "transaction_data": entry["transaction_data"],
        "inscription_id": entry["inscription_id"],
        "transaction_status": entry["transaction_status"],
        "chain": CHAIN_WISE_FLAG_MAP.get(
            get_chain_type_from_inscription_json(entry["transaction_data"]["inscribe_json"]
                                                 if entry["transaction_data"] is not None and "inscribe_json" in entry[
                "transaction_data"] else None))}
        for entry in unprocessed]

    pending_claim = collection_transferred.find(
        {"metamask_address": metamask_address, "transaction_status": "BRIDGING"})
    data["pending_claim"] = [
        {
            "transaction_data": entry["transaction_data"],
            "transfer_inscription_id": entry["transfer_inscription_id"],
            "transaction_status": entry["transaction_status"]
        } for entry in pending_claim]

    data["pending_tickers"] = get_controlled_tickers()

    return jsonify(data)


@bapi.route('/reporting', methods=['GET'])
def get_token_price():

    # Check if the response exists in the cache
    cache_key = f"oklink.com-tokenprice"
    cached_response = cache.get(cache_key)

    if cached_response:
        print(f"[get_token_price] get from cache {str(cached_response)}")
        return jsonify(cached_response)  # Return cached response if available
    else:
        url = f'https://www.oklink.com/api/v5/explorer/tokenprice/market-data?' \
              f'chainId={OK_LINK_CHAIN_ID}&tokenContractAddress={OK_LINK_TOKEN_CONTRACT_ADDRESS}'
        headers = {'Ok-Access-Key': OK_LINK_API_KEY}

        try:
            # Make an internal request to the external API
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                # Add the response to cache
                cache[cache_key] = data
                print(f"[get_token_price] store in cache {data}")
                return jsonify(response.json())

            return jsonify(response.json()), response.status_code
        except requests.RequestException as e:
            return jsonify({'error': str(e)}), 500  # Return an error response if the request fails


@bapi.route('/token/btc/balance', methods=['GET'])
def get_token_balance():

    # Check if the response exists in the cache
    cache_key = f"oklink.com-address-balance-list"
    cached_response = cache.get(cache_key)

    if cached_response:
        print(f"[get_token_balance] get from cache {str(cached_response)}")
        return jsonify(cached_response)  # Return cached response if available
    else:
        url = f"https://www.oklink.com/api/v5/explorer/btc/address-balance-list?address={OK_LINK_ADDRESS}"
        headers = {'Ok-Access-Key': OK_LINK_API_KEY}

        try:
            # Make an internal request to the external API
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                # Add the response to cache
                cache[cache_key] = data
                print(f"[get_token_balance] store in cache {data}")
                return jsonify(response.json())

            return jsonify(response.json()), response.status_code
        except requests.RequestException as e:
            return jsonify({'error': str(e)}), 500  # Return an error response if the request fails


def execute_bitcoin_cli(command):
    result = subprocess.check_output(command.split(), universal_newlines=True)
    return result


def get_chain_type_from_inscription_json(inscribe_json):
    if inscribe_json is None:
        return None
    return next((chain_type for chain_type in CHAIN_WISE_FLAG_MAP.keys()
                 if chain_type in inscribe_json), None)
