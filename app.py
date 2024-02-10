from flask import Flask

import requests
import json


from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


app = Flask(__name__)

def read_api_key(file_name):
    with open(file_name, 'r') as file:
        api_key = file.read().strip()
    return api_key


def get_channel_videos(channel_id, api_key):

    api_key=api_key
    youtube=build(
        'youtube',
        'v3',
        developerKey=api_key
    )

    #Make a request to youtube api
    request = youtube.channels().list(
        part='contentDetails',
        forUsername=channel_id
    #you can change the channel name here
    )


    #get a response for api
    response=request.execute()
    print(response)

    # Retrieve the uploads playlist ID for the given channel
    playlist_id=response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    # Retrieve all videos from uploads playlist
    videos = []
    next_page_token = None

    while True:
        playlist_items_response=youtube.playlistItems().list(
                    #part='contentDetails',
                    part='snippet',
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
        ).execute()

        videos += playlist_items_response['items']

        next_page_token = playlist_items_response.get('nextPageToken')

        if not next_page_token:
            break

    # Extract video URLs
    video_urls = []

    for video in videos:
        #video_id = video['contentDetails']['videoId']
        video_id = video['snippet']['resourceId']['videoId']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        video_title=video['snippet']['title']
        #video_urls.append(video_url)
        video_urls.append({'URL':video_url,'Title':video_title})

    #return video_urls

    return video_urls


@app.route('/')
def main():
    # Get YouTube API key
    api_key_file = "youtube_api_key"
    api_key = read_api_key(api_key_file)

    videos = get_channel_videos('@LVPward', api_key)
    for video in videos:
        print(video)
        
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True)