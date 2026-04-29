import json
import requests
from datetime import datetime

from app.ml import config
from app.ml.oss_utils import oss_uploader


class DataCollector:
    def __init__(self, session_id, session_type='video'):
        self.session_id = session_id
        self.session_type = session_type
        self.collected_tracks = set()
        self.oss_image_urls = []
        self.categories = {}
        self.total_annotations = 0
        self.username = ''
        self.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')