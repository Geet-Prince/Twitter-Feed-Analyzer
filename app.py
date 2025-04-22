from flask import Flask, render_template, request
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pymongo
import tweepy
import requests

from config import TWITTER_BEARER_TOKEN, MONGO_URI

app = Flask(__name__)

# MongoDB setup
client = pymongo.MongoClient(MONGO_URI)
db = client["twitterDB"]
tweets_collection = db["tweets"]

# Tweepy client (without session)
twitter_client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)

# Sentiment analyzer
analyzer = SentimentIntensityAnalyzer()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form["username"]
        tweets_collection.delete_many({})  # clear old data

        try:
            user = twitter_client.get_user(username=username)
            user_id = user.data.id

            tweets = twitter_client.get_users_tweets(
                id=user_id,
                max_results=5,
                tweet_fields=["created_at", "text"]
            )

            tweet_data = []

            if tweets.data:
                for tweet in tweets.data:
                    sentiment = analyzer.polarity_scores(tweet.text)
                    data = {
                        "text": tweet.text,
                        "created_at": tweet.created_at.isoformat(),
                        "sentiment": sentiment
                    }
                    tweet_data.append(data)
                    tweets_collection.insert_one(data)
            else:
                return render_template("index.html", tweets=[], username=username, error="No tweets found.")

            return render_template("index.html", tweets=tweet_data, username=username)

        except tweepy.TooManyRequests:
            return render_template("index.html", error="🚫 Rate limit reached! Please wait and try again.")
        except tweepy.BadRequest:
            return render_template("index.html", error="⚠️ Invalid request. Make sure the username exists.")
        except Exception as e:
            print("Error:", e)
            mock_tweets = [
                {
                    "text": "This is a mock tweet!",
                    "created_at": "2023-01-01T12:00:00",
                    "sentiment": analyzer.polarity_scores("This is a mock tweet!")
                }
            ]
            return render_template("index.html", tweets=mock_tweets, username="mock_user", error=f"Mock mode: {e}")

    return render_template("index.html", tweets=[])


if __name__ == "__main__":
    app.run(debug=True)
