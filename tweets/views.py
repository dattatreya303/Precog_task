from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.staticfiles.templatetags.staticfiles import static
from scipy.misc import imread
from datetime import datetime
import tweepy, numpy, os, csv, json
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS

def main(request):
	# homepage
	return render(request, 'tweets/login.html')

def info(request):	
	if request.method == 'GET' and 'screen_name' in request.GET:
		scn = request.GET['screen_name']
		if scn == "":
			return render(request, 'tweets/login.html', {'message':'Enter a valid Twitter handle'})
		else:
			# print("start", datetime.now())
			STAT_PATH = os.path.join(settings.BASE_DIR, 'tweets/static/tweets/')

			handle = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
			handle.set_access_token(settings.ACCESS_TOKEN, settings.ACCESS_TOKEN_SECRET)
			api = tweepy.API(handle)
			try:
				user = api.get_user(screen_name=scn)
			except tweepy.TweepError:
				return render(request, 'tweets/login.html', {'message':'Enter a valid Twitter handle'})


			"""
			Tweets vs Weekday graph 
			"""
			try:
				timeline = api.user_timeline(screen_name=scn, count=3200, include_rts=True)
				mid = timeline[-1].id - 1
				while True:
					tl = api.user_timeline(screen_name=scn, count=3200, include_rts=True, max_id=mid)
					if not len(tl):
						break
					timeline += tl
					mid = tl[-1].id - 1
			except tweepy.TweepError or TypeError:
				return render(request, 'tweets/login.html', {'message':'Enter a valid Twitter handle'})

			y = [0]*7
			for tw in timeline:
				d = tw.created_at.strftime("%w")
				y[int(d)] += 1

			x = [0,1,2,3,4,5,6]
			xpoints = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
			plt.xticks(x, xpoints)
			plt.plot(x, y, 'b-')
			plt.xlabel('Days of week')
			plt.ylabel('No. of tweets')
			
			path_graph = STAT_PATH + 'graph.png'
			if os.path.isfile(path_graph):
				os.remove(path_graph)

			plt.savefig(path_graph, dpi=300, bbox_inches='tight')
			plt.clf()

			"""
			Tag-cloud
			"""
			# more stopwords
			file = open(STAT_PATH + 'stopwords.txt', 'r')
			more_stops = file.readlines()
			for i in range(len(more_stops)):
				more_stops[i] = more_stops[i].rstrip('\n')
			global STOPWORDS
			STOPWORDS = STOPWORDS.union(more_stops)

			words = []
			matrix = []
			for tw in timeline:
				matrix.append(tw.text.split())
				words = words + tw.text.split()
			
			long_tweet_stripd = ""
			for w in words:
				if w != 'RT' and not(w.startswith('http')) and not(w.startswith('@')) and not(w.startswith('#')) and not(w.lower() in STOPWORDS):
					long_tweet_stripd = " ".join([long_tweet_stripd, w.lower()])
					
			un_words = long_tweet_stripd.split()

			mask = imread(STAT_PATH + 'twitter_mask.png')

			wcloud = WordCloud(max_words=50, background_color='white', stopwords=STOPWORDS, mask=mask).generate(long_tweet_stripd)
			
			# print(long_tweet_stripd)

			path_wordcloud = STAT_PATH + 'wordcloud.png'
			if os.path.isfile(path_wordcloud):
				os.remove(path_wordcloud)

			plt.imshow(wcloud)
			plt.gca().invert_yaxis()
			plt.axis('off')
			plt.savefig(path_wordcloud, dpi=600, bbox_inches='tight')
			plt.clf()
			plt.close()

			"""
			Word co-occurences matrix

			"""
			all_words_use = []
			for w in un_words:
				try:
					if all(((ord(char)>=65 and ord(char)<=90) or (ord(char)>=97 and ord(char)<=122)) for char in w) and (not(w.lower() in STOPWORDS)):
						all_words_use.append(w.lower())
				except Exception as e:
					pass

			un_words_use = list(set(all_words_use))

			un_words_use_count = [0 for i in range(len(un_words_use))]
			for w in all_words_use:
				if w in un_words_use:
					un_words_use_count[un_words_use.index(w)] += 1

			most_words_use = []
			for i in range(30):
				if len(un_words_use_count) == 0:
					break;
				most_words_use.append(un_words_use[un_words_use_count.index(max(un_words_use_count))])
				un_words_use_count.remove(un_words_use_count[un_words_use_count.index(max(un_words_use_count))])

			most_words_use = list(set(most_words_use))

			count = [[0 for i in range(len(most_words_use))] for j in range(len(most_words_use))]

			for i in range(len(matrix)):
				for j in range(len(matrix[i])):
					if matrix[i][j].lower() in most_words_use:
						for k in range(j+1, len(matrix[i])):
							if matrix[i][k].lower() in most_words_use:
								count[most_words_use.index(matrix[i][j].lower())][most_words_use.index(matrix[i][k].lower())] += 1;
								count[most_words_use.index(matrix[i][k].lower())][most_words_use.index(matrix[i][j].lower())] += 1;
			
			nodeFile = open(STAT_PATH + 'nodeFile.csv', 'w', newline='')
			nodeW = csv.writer(nodeFile, quotechar='|', quoting=csv.QUOTE_MINIMAL)
			nodeW.writerow(['id'])
			for w in most_words_use:
				nodeW.writerow([w])

			edgeFile = open(STAT_PATH + 'edgeFile.csv', 'w', newline='')
			edgeW = csv.writer(edgeFile, quotechar='|', quoting=csv.QUOTE_MINIMAL)
			edgeW.writerow(['source']+['target']+['weight'])
			for i in range(len(count)):
				for j in range(i, len(count)):
					edgeW.writerow([most_words_use[i]]+[most_words_use[j]]+[count[i][j]])
					edgeW.writerow([most_words_use[j]]+[most_words_use[i]]+[count[i][j]])
			
			nodeFile.close()
			edgeFile.close()

			print("3 tasks completed", datetime.now())

			"""
			Network graph
			"""
			obj = {}
			obj['nodes'] = []
			obj['links'] = []
			obj['nodes'].append({'name':scn, 'group':1})

			follower_ids = api.followers_ids(screen_name=scn, count=100)
			follower_users = []
			if len(follower_ids) > 0:
				follower_users = api.lookup_users(user_ids=follower_ids)

			i=1; # node no., user is node0 
			for u in follower_users:
				obj['nodes'].append({'name':u.screen_name, 'group':2}) # group2 for followers
				obj['links'].append({'source':i, 'target':0, 'weight':1})
				i += 1

			following_ids = api.friends_ids(screen_name=scn, count=100)
			following_users = []
			if len(following_ids) > 0:
				following_users = api.lookup_users(user_ids=following_ids)

			for u in following_users:
				obj['nodes'].append({'name':u.screen_name, 'group':3}) # group3 for friends/following
				obj['links'].append({'source':0, 'target':i, 'weight':1})
				i += 1

			# Exceeds rate-limit, max 15 requests per 15-min interval
			# and 100 api requests per hour
			# Will have to decrease follower and friend count
			# all_users = follower_users + following_users
			# for i in range(len(all_users)):
			# 	frs = api.followers_ids(screen_name=all_users[i].screen_name)
			# 	fwn = api.friends_ids(screen_name=all_users[i].screen_name)
			# 	for j in range(i+1, len(all_users)):
			# 		if all_users[j].id in frs:
			# 			obj['links'].append({'source':j+1, 'target':i+1, 'weight':1})
			# 		if all_users[j].id in fwn:
			# 			obj['links'].append({'source':i+1, 'target':j+1, 'weight':1})



			with open(STAT_PATH + 'network.json', 'w') as jsonFile:
				json.dump(obj, jsonFile, indent=4)

			return render(request, 'tweets/info.html', {'user':user, 'day_list':y})
	else:
		return render(request, 'tweets/login.html', {'message':'Enter a valid Twitter handle'})
