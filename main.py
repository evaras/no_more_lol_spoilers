from flask import Flask, render_template
from flask_caching import Cache

import requests
import json

import pandas as pd

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

def read_api_key(file_name):
    with open(file_name, 'r') as file:
        api_key = file.read().strip()
    return api_key

def get_videos_from_youtube_api(api_key):
    #print('Getting videos from YouTube API')
    # Credential builder
    youtube=build(
            'youtube',
            'v3',
            developerKey=api_key
        )

    # Get channel ID by channel name
    # Call the search().list() function
    request = youtube.search().list(
        part="snippet",
        q="LVPesLOL",  # Replace with your channel ID
        maxResults=1,  # You can adjust this value
        order="date"  # This will sort the videos by date
    )
    response = request.execute()
    channel_id = response['items'][0]['snippet']['channelId']
    
    # Get upload list
    request = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    )
    response = request.execute()

    # Get the 'Uploads' playlist ID
    uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    # Get the videos in the 'Uploads' playlist (By default they are in descending cronological order)
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_playlist_id,
        maxResults=50  # You can adjust this value
    )
    response = request.execute()
    
    # Get the videos in the 'Uploads' playlist
    next_page_token = None
    response_list = []
    i = 1
    while i>0:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50,  # You can adjust this value
            pageToken = next_page_token
        )

        response = request.execute()
        response_list.append(response)
        next_page_token = response.get('nextPageToken')
        i = i-1
        if next_page_token is None or i==0:
            break
    # Obtain all data needed for the latest videos
    df = pd.DataFrame(columns = ['date', 'match_name', 'map_number', 'league', 'split', 'video_id', 'embed_link'])
    for response in response_list:
        # compute the embed code for each video
        for item in response['items']:
            title = item['snippet']['title']
            date = item['snippet']['publishedAt'][0:10]
            title_split = title.split(' - ')
            try:
                if 'VS' not in title_split[0]:
                    continue
                match_name = title_split[0]
                if 'MAPA' in title_split[1]:
                    map_number = title_split[1]
                else:
                    map_number = 'Mapa 1'

                if 'MAPA' in title_split[1]:
                    league = title_split[3]
                    split = title_split[4]
                else:
                    league = title_split[2]
                    split = title_split[3]

                video_id = item['snippet']['resourceId']['videoId']
                embed_link = f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'

                df = pd.concat([df, pd.DataFrame([[date, match_name, map_number, league, split, video_id, embed_link]],
                                            columns = ['date', 'match_name', 'map_number', 'league', 'split', 'video_id', 'embed_link'])])
            except:
                print(title_split[0])
    
    # Clean strange characters when bad formatted titles
    df['match_name'] = df['match_name'].str.strip()
    # Sort values
    df = df.sort_values(by=['date', 'match_name', 'map_number'], ascending=[False, True, True])
    # Transform to dict format to simplify presentation
    full_match_info_dict = df.to_dict('records')
    match_dict = df.reindex(columns=['date', 'match_name']).drop_duplicates().to_dict('records')
    date_dict = df.reindex(columns=['date']).drop_duplicates().to_dict('records')
    for match_map in full_match_info_dict:
        for match in match_dict:
            if match['date'] == match_map['date'] and match['match_name'] == match_map['match_name']:
                try:
                    match['details'].append(match_map)
                except:
                    match['details'] = [match_map]
    for match in match_dict:
        for date in date_dict:
            if date['date'] == match['date']:
                try:
                    date['matches'].append(match)
                except:
                    date['matches'] = [match]
    #print(date_dict)
    return date_dict


@app.route('/')
@app.route('/<int:page_number>')
def main(page_number=1):
    # Get YouTube API key
    api_key_file = "youtube_api_key"
    api_key = read_api_key(api_key_file)

    if not cache.get('videos_dict'):
        print('Getting videos from YouTube API')
        videos_dict = get_videos_from_youtube_api(api_key)
        cache.set('videos_dict', videos_dict, timeout=60*60)
    else:
        print('Getting videos from cache')
        videos_dict = cache.get('videos_dict')
    real_dict_index = (page_number-1)*2
    has_next = False
    if len(videos_dict) / 2 > page_number:
        has_next = True

    videos_dict = videos_dict[real_dict_index:real_dict_index+2]

    return render_template('index.html', videos_dict=videos_dict, page_number=page_number, has_next=has_next)


if __name__ == '__main__':
    app.run(debug=False)