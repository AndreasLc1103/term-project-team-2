import json
import requests
import boto3
import json
import tweepy
from dotenv import dotenv_values
import constants

USER_CONFIG = dotenv_values("/Users/rvi/Documents/rcPersonal/Year5/Cloud/term-project-team-2/lambdas/.env")
TW_CLIENT = tweepy.Client(USER_CONFIG['BEARER_TOKEN'])
MAX_ITERATION = 10
MAX_TWEET_COUNT = 20
API_BASE_URL = "https://api.twitter.com/1.1"
BASE_URL = "https://twitter.com/i/api/2"
DEFAULT_HEADERS = {
    "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
    "x-guest-token": ""
}
DEFAULT_QUERY_PARAMS = {
    "skip_status": "1",
    "include_quote_count": "true",
    "include_reply_count": "1",
    "simple_quoted_tweet": "true",
    "query_source": "typed_query",
    "spelling_corrections": "1"
}


def set_twitter_token(session):
    response = session.post(f"{API_BASE_URL}/guest/activate.json")
    if response.ok:
        json = response.json()
        session.headers.update({"x-guest-token": json["guest_token"]})
    return response.ok


def retrieve_location(tweet_geo, user_id):
    # maximize chance of collecting geo data by checking user object if unavailable on tweet
    if tweet_geo is None or tweet_geo == "":
        user = TW_CLIENT.get_user(id=user_id)
        return user[0]['location']
    else:
        return tweet_geo


def parse_tweets(json):
    tweets = json["globalObjects"]["tweets"]
    return [
        {"created_at": tweets[key]["created_at"], "id": tweets[key]["id"], "text": tweets[key]["text"], "lang": tweets[key]["lang"], "geo": retrieve_location(tweets[key]["geo"],tweets[key]["user_id"]), "user": tweets[key]["user_id"]} for key in tweets.keys()
    ]
    
def get_next_token(data, cursor):
    if not cursor:
        return data["timeline"]["instructions"][0]["addEntries"]["entries"][-1]["content"]["operation"]["cursor"]["value"]
    return data["timeline"]["instructions"][-1]["replaceEntry"]["entry"]["content"]["operation"]["cursor"]["value"]


def get_tweets(session, count, q):
    # shallow copy for the default params
    headers = DEFAULT_QUERY_PARAMS.copy()
    result = []
    iteration_count = 0
    cursor = None
    while count > 0:
        c = MAX_TWEET_COUNT
        headers.update({"q": q, "count": c, "cursor": cursor})
        response = session.get(
            f"{BASE_URL}/search/adaptive.json", params=headers)
        # guest token probably expired or something of that sorts, attempt to do request again
        # should probably handle this differently
        if response.status_code == 403:
            set_twitter_token(session)
            iteration_count += 1
            if iteration_count == MAX_ITERATION:
                break
        elif response.ok:
            data = response.json()
            result.append(parse_tweets(data))
            cursor = get_next_token(data, cursor)
            count -= MAX_TWEET_COUNT
        else:
            count -= MAX_TWEET_COUNT
    return result


# POST /tweets
#   body / data = {count: int, query: str}

def lambda_handler(event, context):
    [count, query] = event.get(
        "count", MAX_TWEET_COUNT), event.get("query", None)
    if query is None or len(query) <= 0:
        return {"statusCode": 400, "body": "Provide a query with a length greater than zero."}
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    if (not set_twitter_token(session)):
        return {"statusCode": 403}
    data = get_tweets(session, count, query)
    return {"statusCode": 200, "body": json.dumps({"request_count": len(data), "data": data})}

def collection_lambda_handler(event, context):
    [count, query] = event.get(
        "count", MAX_TWEET_COUNT), event.get("query", None)
    if query is None or len(query) <= 0:
        return {"statusCode": 400, "body": "Provide a query with a length greater than zero."}
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    if (not set_twitter_token(session)):
        return {"statusCode": 403}
    data = get_tweets(session, count, query)
    return {"statusCode": 200, "body": json.dumps({"request_count": len(data), "data": data})}