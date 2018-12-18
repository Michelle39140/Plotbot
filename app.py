# Dependencies
import tweepy
import matplotlib
matplotlib.use('plt')
import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
import time
analyzer = SentimentIntensityAnalyzer()

# Set up Tweepy API Authentication
from wusiapikeys import twitter_plotbot
consumer_key= twitter_plotbot["consumer_key"]
consumer_secret= twitter_plotbot["consumer_secret"]
access_token= twitter_plotbot["access_token"]
access_token_secret= twitter_plotbot["access_token_secret"]

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth, parser=tweepy.parsers.JSONParser() )

# function to search tweets mentioned me and meet the format required
## returns a dictionary include the account name to analysis and the user name(s) who requested it
def get_accountnames(last_id=None):
    
    tweets_mentioned_me = api.mentions_timeline(since_id=last_id) #return all tweets metioned me since last search
    
    if len(tweets_mentioned_me) !=0: # check if there is new results from this search

        last_id = tweets_mentioned_me[0]["id"] #get and store the id of the newest tweet from this search

        AN = {} # initialize accountname to store {account name to analysis:[the user(s) who requested it]}

        # get the @accountname to analysis into a list
        for tweet in tweets_mentioned_me:
            print(tweet["text"])
            word_list = tweet["text"].split()     # split tweet into words
            
            try:
                account_to_analysis = word_list[2].lower()  # get the account to analysis - should be @accountname
                from_user = tweet["user"]["screen_name"]   # get the user who tweeted to me

                # check if the tweets includes "analyze" as the second word, and @ in the account_to_analysis
                # if yes, can add this account to accountname list
                if "analyze" in word_list[1].lower() and "@" in account_to_analysis: 

                    #check if this account is already existing in acountname list
                    if account_to_analysis in AN.keys():
                        #if account is recorded already, check if it's from the same user in record
                        if from_user not in AN[account_to_analysis]:
                            #if not, attach the new user to the account - so when tweet out, can @ all users requested for this account
                            AN[account_to_analysis].append(from_user)
                    else:
                        #if account is not in record, add it to the account list, along with the user who requested it, storing in dictionary
                        AN.update({account_to_analysis:[from_user]})
            except:
                print(f"{tweet['text']} doesn't meet requirement")
    else:   # when there is no new search result, return an empty dictionary and the original last_id
        last_id=last_id
        AN={}
    
    return AN,last_id

# function to do sentimental analysis for a given twitter user
def senti_analysis(user_id=None):
    Tweety_Polarity = []
    Tweets_Ago = 0
    for i in range(10):
        try:
            account_tweets = api.user_timeline(id=user_id,count=50,page=i+1)
            for tweet in account_tweets:
                result = analyzer.polarity_scores(tweet["text"])
                Tweety_Polarity.append({"Tweets Ago":Tweets_Ago, "Tweety Polarity":result["compound"]})
                Tweets_Ago-=1
        except:
            continue

        time.sleep(1) # pause for 1 sec

    Tweety_Polarity_df = pd.DataFrame(Tweety_Polarity)
    return Tweety_Polarity_df

# function to create chart from the sentimental analysis result dataframe 
def generate_plot(Tweety_Polarity_df=None):
    #import seaborn
    #seaborn.pointplot(data=Tweety_Polarity_df,x="Tweets Ago",y="Tweety Polarity",color="b")

    ax =Tweety_Polarity_df.plot(kind="line",x="Tweets Ago",
                                y="Tweety Polarity",figsize=(10,6),color=(0.2,0.5,0.8),
                                legend=False,marker="o",alpha=0.75,linewidth=1.0)

    #set xlim
    start, stop = ax.get_xlim()
    plt.xlim(start-2,stop+2)

    #formating
    plt.style.use("seaborn")   #set chart style
    ax.set_ylabel("Tweety Polarity",fontsize=15)  #add ylabel
    plt.xlabel("Tweets Ago",fontsize=15)  #change xlabel fontsize
    plt.xticks(fontsize=10)  #change xticks fontsize
    plt.yticks(fontsize=10)  #change yticks fontsizeS

    current_time = time.strftime("%d %B %Y, %H:%M",time.localtime()) #get current time in string
    plt.title(f"Sentiment Analysis of Tweets from {account} ({current_time})",fontsize=16) #create title
    
    return ax

    # # create the correct xticks---------------------------------------
    # ##considering there might not always be 500 tweets
    # locs, labels = plt.xticks()           # Get locations and labels

    # xlocs=[0]
    # xlabels=[-locs[-1]-1]

    # for i in np.arange((locs[-1]+1) // 100-1,0,-1):
    #     xlocs.append(locs[-1]-i*100)
    #     xlabels.append(i*-100)

    # xlocs.append(locs[-1])
    # xlabels.append(0)

    # plt.xticks(xlocs,xlabels)   # Set locations and labels
    # #-----------------------------------------------------------------


# read tweeted list and last id from local file
log_file = pd.read_csv("log.csv")

## tweeted list stores the user id of accounts analyzed before - to avoid duplicates
tweeted_list= log_file["tweeted_list"].tolist()

## last id stores the last tweet searched last time - will be used as the start point of new search
last_id = log_file.loc[0,"last_id"] 


# the Main loop:
while True:
    print("starting a new search----------------------------------------------------------------------------------")
    
    # 1. get new accountnames requested since last search, and the users who requested for them - in a dictionary
    accountname,last_id = get_accountnames(last_id)

    # 2. compare the accountname list with tweeted list, get the shorted list for search
    ## check every account name in the dictionary, if it's tweeted out previously, delete it from the accountname dictionary 
    accountname={account:from_user for account,from_user in accountname.items() if account not in tweeted_list}
    print(f"new requests:{accountname}")

    # 3. for each account, search for tweet, do sentimental analysis, create a chart, and tweet it out
    if len(accountname) != 0:
        # for each accountname:
        for account,from_user in accountname.items():
            try:
                # try get the user id from the account name - if error, it means can't access this account
                user_id = api.get_user(screen_name=account)["id"]

                # do sentimental analysis for this user by calling senti_analysis function, get a dataframe contains the results
                Tweety_Polarity_df_returned = senti_analysis(user_id)

                # create a chart from the sentimental analysis result dataframe, get a pointer to the chart
                chart = generate_plot(Tweety_Polarity_df_returned)
                print(f"chart created for {account}")

                # save picture for uploading
                savepath="twitter.png"
                fig = chart.get_figure()
                fig.savefig(savepath)

                # twitter out analysis result
                ## get the users to mention in tweet
                users=""
                for user in from_user:
                    users=users+"@"+user+" "
                api.update_with_media(filename=savepath,status=f"Analysis result for {account}. Thank you {users}!")
                print(f"tweet sent out for {account}")
                
                # after tweet the chart out, add this account to tweeted list, to avoid future duplicates           
                tweeted_list.append(account)
                ## set a 1000 item limit for the tweeted_list: only avoid duplicate in the most recent 1000 tweets
                ## if an account was tweeted out 1000 tweet before, it's worth analyze it again
                ## another purpose is to avoid abusing memory to store large list
                if len(tweeted_list)>1000:
                    tweeted_list.pop(0)

                #delete picture after uploading
                import os
                os.remove(savepath)
                #print("File Removed!")

            except:
                print("the account %s is not accessable" %account)
    
    print("end of this search ------------------------------------------------------------------------------------")
    
    # store the tweeted list and last id to files 
    log_df = pd.DataFrame({"tweeted_list":tweeted_list})
    log_df.loc[0,"last_id"] = last_id
    log_df.to_csv("log.csv",index=False)
    
    #print("log.csv updated")
    
    time.sleep(300) # run every 5 minutes