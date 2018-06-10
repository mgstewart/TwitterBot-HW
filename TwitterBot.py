#import dependencies
import numpy as np
import pandas as pd
import tweepy
import time
import json
import datetime as dt
import csv
from time import sleep
from pprint import pprint
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib import patches as mpatches
import seaborn as sns
from config import consumer_key, consumer_secret, access_token, access_token_secret
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
# Force matplotlib to use a non-TK backend for Heroku support
analyzer = SentimentIntensityAnalyzer()
# Twitter API Keys
consumer_key = consumer_key
consumer_secret = consumer_secret
access_token = access_token
access_token_secret = access_token_secret

# Twitter Credentials
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth, parser=tweepy.parsers.JSONParser())

# Define main and peripheral functions
def TwitterBot():
    target_sn,requester,requesting_id = identify_check_request()
    (compound_list,
    tweet_num_list,
    target_sn,requester,
    requesting_id) = search_for_tweets(target_sn,requester,requesting_id)
    analyze_and_plot(compound_list,tweet_num_list,target_sn,requester,requesting_id)
    
def identify_check_request():
    print('Looking for a tweet that mentions me on my page...')
    #Declare local variables
    target_sn = ''
    requester = ''
    requesting_id = ''
    list_of_targets = []
    # Look at the most recent tweet on the bot's timeline and extract text content and author's sn
    try:
        request_tweet = api.user_timeline('@AwayMikes',count=1,result_type='recent')
    except tweepy.TweepError:
        print('Something went wrong scanning my own timeline. Going to sleep.')
        gotosleep()
    pprint(request_tweet)
    request_text = request_tweet[0]['text']
    requesting_id = request_tweet[0]['id_str']
    requester = '@'+request_tweet[0]['user']['screen_name']
    # Revised this to use the user_mentions key in the tweet JSON to extract the first mention
    # that is NOT the bot's handle
    mentioned_sns = request_tweet[0]['entities']['user_mentions']
    for sn in mentioned_sns:
        if sn['screen_name'] != 'AwayMikes':
            #Concatenate the sn into a Twitter handle
            target_sn = '@'+sn['screen_name']
            break
        else:
            target_sn = '@AwayMikes'
            print('TargetError: The most recent tweet does not contain a valid Twitter User')
    # Open the list_of_targets datafile and read rows into memory
    with open ('list_of_targets.csv',newline='') as csvfile:
        target_reader = csv.reader(csvfile,delimiter=',')
        for row in target_reader:
            list_of_targets.append(row[0])
    # Check to see if the target has already been analyzed
    # if there is a Tweepy error, the bot will attempt to sleep it off
    # if it has been analyzed, the saved analysis file will be reposted
    if target_sn not in list_of_targets:
        try:
            search_for_tweets(target_sn,requester,requesting_id)
        except tweepy.TweepError:
            api.update_status("Something went wrong, I'm going to take a #nap")
            gotosleep()
    if target_sn in list_of_targets:
        try:
            api.update_with_media(f"{target_sn}.png",
                                  f"I'm sorry {requester}, {target_sn} has already been analyzed. Here is the plot: ",
                                  requesting_id)
            gotosleep()
        except tweepy.TweepError:
            print("Could not find the file, kill me!")
            gotosleep()
    if target_sn == '@AwayMikes':
        print("I found a reference to myself. Gonna go to sleep.")
        gotosleep()
    return target_sn,requester,requesting_id
    
def search_for_tweets(target_sn,requester,requesting_id):
    print(f"Target acquired ({target_sn}), now searching for {target_sn}'s tweets!")
    tweets_ago = 0
    # Variable for holding the oldest tweet
    oldest_tweet = None

    # Variables for holding sentiments
    compound_list = []
    tweet_num_list = []

    # Loop through 25 times
    for x in range(25):

        # Pull a page of tweets from the target_sn's timeline
        public_tweets = api.user_timeline(target_sn, page=x, result_type="recent")

        # Loop through all tweets
        for tweet in public_tweets:

            # Run Vader Analysis on each tweet
            results = analyzer.polarity_scores(tweet["text"])
            compound = results["compound"]

            # Add each value to the appropriate list
            compound_list.append(compound)
            
            #Increment the num_tweets to count the tweets from most recent
            tweet_num_list.append(tweets_ago)
            tweets_ago -= 1
                
    # Return the lists and target_sn for next method
    return compound_list,tweet_num_list,target_sn,requester,requesting_id

def analyze_and_plot(compound_list,tweet_num_list,target_sn,requester,requesting_id):
    print('Beginning to plot...')
    # Begin by constructing dataframe from tweet polarity lists
    tweetdf = pd.DataFrame(compound_list,columns=['Compound Score'])
    # Rename index to tweets ago value
    tweetdf.set_axis(tweet_num_list,axis=0,inplace=True)
    # Define Seaborn style and generate plot
    sns.set_style('darkgrid')
    tweetplot = sns.tsplot(data=tweetdf['Compound Score'],time=tweetdf.index.values,condition=['Compound Score'])
    # Label x and y axes
    tweetplot.set_ylabel('Tweet Polarity')
    tweetplot.set_xlabel('Tweets Ago')
    tweetplot.set_title(f"VADERSentimentAnalysis of {target_sn}'s Tweets")
    # Set ylimit higher than possible value to accomodate legend
    tweetplot.set_ylim(bottom=-1,top=1.25)
    # Create a patch for the legend to reflect the target_sn
    user = mpatches.Patch(label=target_sn)
    tweetplot.legend(handles=[user],loc=1)
    # Save the file to post later
    plt.savefig((f'{target_sn}'),dpi=300)
    # Save the target to the list_of_targets.csv
    with open ('list_of_targets.csv','a',newline='') as csvfile:
        target_writer = csv.writer(csvfile,delimiter=',')
        target_writer.writerow([target_sn])
    # Tweet out the generated plot
    try:
        api.update_with_media(f"{target_sn}.png",
                          f"Here you go {requester}, {target_sn}'s sentiment analysis: ",
                          requesting_id)
    except tweepy.TweepError:
        print("Something went wrong, going to sleep.")
        try:
            api.update_status("Something went wrong, I'm going to take a #nap.")
            gotosleep()
        except tweepy.TweepError:
            gotosleep()
    # Go to sleep
    gotosleep()


def gotosleep():
    print("I am now going to sleep!")
    sleep(300)
    TwitterBot()

if __name__ == '__main__':
    TwitterBot()