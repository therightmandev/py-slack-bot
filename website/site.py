from flask import Flask
from google import sheet_scrape

app = Flask(__name__)


# TODO: make the sheet send a POST req., with the changed param(s)
@app.route("/updatedb")
def hello():
    sheet_scrape.update_db()
    return 'successful'


def main():
    app.run(host='0.0.0.0', port=80)
