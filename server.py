import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    VALID_LOCATIONS = [
        "Albuquerque, New Mexico", "Carlsbad, California", "Chula Vista, California",
        "Colorado Springs, Colorado", "Denver, Colorado", "El Cajon, California",
        "El Paso, Texas", "Escondido, California", "Fresno, California", "La Mesa, California",
        "Las Vegas, Nevada", "Los Angeles, California", "Oceanside, California",
        "Phoenix, Arizona", "Sacramento, California", "Salt Lake City, Utah",
        "San Diego, California", "Tucson, Arizona"
    ]
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """

        if environ["REQUEST_METHOD"] == "GET":
            # Create the response body from the reviews and convert to a JSON byte string
            response_body = json.dumps(reviews, indent=2).encode("utf-8")
            
            # Write your code here
            query = parse_qs(environ['QUERY_STRING'])
            location = query.get('location', [None])[0]
            start_date = query.get('start_date',[None])[0]
            end_date = query.get('end_date', [None])[0]

            filtered_reviews = reviews 

            if location :
                if location not in ReviewAnalyzerServer.VALID_LOCATIONS:
                    start_response("400 Bad Request",[
                        ("Content-Type", "application/json"),
                    ])
                    return[json.dumps({"error":"invalid location"}).encode('utf-8')]
                filtered_reviews = [review for review in filtered_reviews if review['Location']== location]
            
            if start_date :
                start_date_dt = datetime.strptime(start_date,'%Y-%m-%d')
                filtered_reviews= [review for review in filtered_reviews if datetime.strptime(review['Timestamp'],'%Y-%m-%d %H:%M:%S') >= start_date_dt]

            if end_date :
                end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
                filtered_reviews= [review for review in filtered_reviews if datetime.strptime(review['Timestamp'],'%Y-%m-%d %H:%M:%S') <= end_date_dt]
            
            for review in filtered_reviews:
                sentiment = self.analyze_sentiment(review['ReviewBody'])
                review['sentiment'] = sentiment

            filtered_reviews.sort(key = lambda x :x['sentiment']['compound'],reverse = True)

            response_body = json.dumps(filtered_reviews, indent = 2).encode("utf-8")
            ''''start_response("200 OK",[("Content-Type","application/json"),
                                     ("Content-Length",str(len(response_body)))])
            return[response_body]'''
    
            # Set the appropriate response headers
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            # Write your code here
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
                request_body = environ['wsgi.input'].read(request_body_size)
                post_data = parse_qs(request_body.decode('utf-8'))
                location = post_data.get ('Location',[None])[0]
                review_body = post_data.get('ReviewBody', [None])[0]

                if not location or not review_body:
                    start_response("400 Bad Request",[
                        ("Content-Type", "application/json"),
                    ])
                    return [json.dumps({"error": "Location and ReviewBody are required"}).encode('utf-8')]
                
                if location not in self.VALID_LOCATIONS:
                    start_response("400 Bad Request", [
                        ("Content-Type","application/json"),
                    ])
                    return [json.dumps({"error":"invalid location"}).encode('utf-8')]
                new_review = {
                    "ReviewId": str(uuid.uuid4()),
                    "Location": location,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ReviewBody": review_body

                }
                reviews.append(new_review)

                response_body=json.dumps(new_review,indent=2).encode("utf-8")
                start_response("201 Created", [
                    ("Content-Type","application/json"),
                    ("Content-Length",str(len(response_body)))])

                return[response_body]

            except Exception as e:
                start_response("500 Internal Server Error",[
                    ("Content-Type", "application/json")
                ])
                return[json.dumps({"error":str(e)}).encode('utf-8')]
            

if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()