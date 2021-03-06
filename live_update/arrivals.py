from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
from bs4 import BeautifulSoup
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
import sqlalchemy
from sqlalchemy import create_engine
import os
import requests
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

#This script hits the NYC transit live update feed and populate the d
db_name = os.getenv('DBNAME')
db_pw = os.getenv('PW')
db_host = os.getenv('HOST')
db_user =os.getenv('USER')
try:

    key = os.getenv("MTAKEY")

    urls = ['http://datamine.mta.info/mta_esi.php?key=' + key + '&feed_id=1',
            'http://datamine.mta.info/mta_esi.php?key='+ key + '&feed_id=26',
            'http://datamine.mta.info/mta_esi.php?key='+ key + '&feed_id=16',
            'http://datamine.mta.info/mta_esi.php?key='+ key + '&feed_id=21',
            'http://datamine.mta.info/mta_esi.php?key='+ key + '&feed_id=2',
            'http://datamine.mta.info/mta_esi.php?key='+ key + '&feed_id=11',
            'http://datamine.mta.info/mta_esi.php?key='+ key + '&feed_id=31',
            'http://datamine.mta.info/mta_esi.php?key='+ key + '&feed_id=26',
            'http://datamine.mta.info/mta_esi.php?key='+ key + '&feed_id=36',
            'http://datamine.mta.info/mta_esi.php?key='+ key + '&feed_id=51',
        ]

    feed_list = []
   
    def parser(url):
    
        feed = gtfs_realtime_pb2.FeedMessage()
        response = requests.get(url)
        feed.ParseFromString(response.content)
        count = len(feed.entity)
        for val in feed.entity:
            for idx in range(count):
                try:
                    values = {
                        "route": val.trip_update.trip.route_id,
                        "arrival": val.trip_update.stop_time_update[idx].arrival.time,
                        "stop_id": val.trip_update.stop_time_update[idx].stop_id  
                    }
                    feed_list.append(values)
                except Exception as e:
    #                logging.debug(e)
                    pass
        return feed_list

    for link in urls:
        stream = parser(link)

    df = pd.DataFrame(stream)
    df['arrival'] = pd.to_datetime(df['arrival'], unit='s')
    # df.to_csv('arrival_times.csv')

    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    engine = create_engine('postgresql://{}:{}@{}/{}').format(db_user,db_pw,db_host,db_name)

    df.to_sql("arrivals", 
            engine, 
            if_exists="replace",  
            index=False, 
            )
    print('New arrival data pushed')
except Exception as e:
    logging.error(e)
    logging.debug(engine)
    os.system('python live_update.py')
