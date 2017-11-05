# from personal_dashboard.mint import Mint
from flask import Flask, render_template, request, redirect, url_for, abort, session, jsonify
import time, threading, random, webbrowser
from personal_dashboard.bus_directions import NextBus
from personal_dashboard.quotes import Quote
from flask import send_from_directory
from personal_dashboard.rescuetime import RescueTime
from personal_dashboard.withings import Withings
from personal_dashboard.todoist import Todoist
from personal_dashboard.spotify import Spotify
from personal_dashboard.darksky import DarkSky
from personal_dashboard.moves import Moves
from personal_dashboard.chess import Chess
from personal_dashboard.toggl import Toggl
import requests
import psycopg2
import os
from flask_sqlalchemy import SQLAlchemy
import time
import datetime as dt


STEPS_GOAL = 5000
FOCUS_GOAL = 2.4
UNPRODUCTIVITY_GOAL = 1
first_time_loading = True

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['DEBUG'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

from models import *

@app.route('/')
def hello_world():
    global first_time_loading
    first_time_loading = True
    return render_template('index.html')


@app.route("/datesCompletedGoals", methods=['GET'])
def dates_completed_goals():
    now = dt.datetime.now()
    rescue_time = RescueTime()
    toggl = Toggl().get_daily_pomodoros()
    moves = Moves()
    total_pomodoros = sum(toggl.values())
    #Check that we are almost done the day, we use two minutes in case the url
    #doesn't get pinged during the 59th minute for whatever reason
    if now.hour == 23 and now.minute == 59:
        if moves.get_current_days_steps() >= STEPS_GOAL and \
        total_pomodoros >= FOCUS_GOAL and \
        rescue_time.get_current_days_data()["unproductive_hours"] < 1:
            now = time.time()
            todayDict = {str(now) : 100}
            try:
                goalCompletion = GoalCompletion(date=todayDict)
                db.session.add(goalCompletion)
                db.session.commit()
            except Exception as e:
                print(e)
                print("Unable to add items to database")
    try:
        session = db.session()
        rows = session.execute("SELECT * FROM dates_completed_goals")
        datesDict={}
        for row in rows:
            datesDict={**datesDict, **row[0]}
        session.close()
        return jsonify(datesDict)
    except psycopg2.DatabaseError as e:
        print('Error %s') % e
        sys.exit(1)


@app.route("/data", methods=['GET'])
def data():
    global first_time_loading
    if (first_time_loading):
        first_time_loading = False
        session = db.session()
        dictionary = session.execute("SELECT * FROM personal_data WHERE id=(select max(id) from personal_data)")
        for diction in dictionary:
            personal_info_dict = diction[1]
        session.close()
        return jsonify(personal_info_dict)
    else:
        #Sleeping to avoid too many pings to API's
        time.sleep(10)
        rescue_time = RescueTime()
        # next_bus = NextBus().get_next_bus()
        withings = Withings()
        todoist = Todoist()
        spotify = Spotify()
        darksky = DarkSky()
        moves = Moves()
        chess = Chess()
        toggl = Toggl()
        quote = Quote()
        withings_line_data = withings.get_weight_line_data()
        coding_time = requests.get('https://wakatime.com/share/@0c62f2ad-9fa5-43c7-a08f-7b1562918a7d/43cd4128-5361-43db-b51b-d965e3c575a5.json').json()['data']
        coding_type = requests.get('https://wakatime.com/share/@0c62f2ad-9fa5-43c7-a08f-7b1562918a7d/27967d19-0ce0-42a6-9f4a-c3c2440cf575.json').json()['data']
        rescuetime_bar_data = rescue_time.get_daily_week_view()
        info = { 'rescue_time_daily_productivity': rescue_time.get_current_days_data()["productive_hours"],
                'rescue_time_daily_unproductivity' : rescue_time.get_current_days_data()["unproductive_hours"],
                'rescue_time_daily_top_three' :  rescue_time.get_current_days_data()["top_three_sources"],
                'rescue_time_past_seven_productivity' : rescue_time.get_past_seven_days_data()["productive_hours"],
                'rescue_time_past_seven_unproductivity' : rescue_time.get_past_seven_days_data()["unproductive_hours"],
                'rescue_time_past_seven_top_five' : rescue_time.get_past_seven_days_data()["top_five_sources"],
                # 'next_bus' : next_bus,
                'weight' : withings.weight,
                'total_tasks' : todoist.get_total_tasks(),
                'past_seven_completed_tasks' : todoist.get_past_seven_completed_tasks(),
                'daily_completed_tasks' : todoist.get_daily_completed_tasks(),
                'top_tracks' : spotify.get_monthly_top_tracks(),
                'top_artists' : spotify.get_monthly_top_artists(),
                'temp' : darksky.temp,
                'weather_today' : darksky.weather_today,
                'current_steps' : moves.get_current_days_steps(),
                'average_past_seven_steps' : moves.get_average_past_seven_steps(),
                'chess_games' : chess.get_games(),
                'chess_rating' : chess.get_rating(),
                'chess_int_rating' : chess.get_int_rating(),
                'daily_pomodoros' : str(toggl.get_daily_pomodoros()),
                'quote_content' : quote.content,
                'quote_author' : quote.author,
                'moves_places' : moves.get_past_seven_days_places(),
                'steps_bar_data' : moves.get_daily_week_view(),
                #This is the integer version which gets stored in the database and used for doughnut chart
                'daily_doughnut_pomodoro' : toggl.get_daily_pomodoros(),
                'past_seven_days_pomodoros' : toggl.get_past_seven_days_pomodoros(),
                'coding_time' : coding_time,
                'coding_type' : coding_type,
                'rescuetime_bar_data' : rescuetime_bar_data[0],
                'rescuetime_bar_data_dates' : rescuetime_bar_data[1],
                'toggl_bar_data' : toggl.get_daily_week_view(),
                'weight_line_data' : withings_line_data[0],
                'weight_line_dates' : withings_line_data[1]
                }
        now = dt.datetime.now()
        if now.minute == 0:
            try:
                personal_data = PersonalData(personal_data_dictionary=info)
                db.session.add(personal_data)
                db.session.commit()
                db.session.close()
            except Exception as e:
                print(e)
                print("Unable to add items to database")
        return jsonify(info)


@app.route("/updated")
def updated():
    """
    Wait until something has changed, and report it. Python has *meh* support
    for threading, as witnessed by the umpteen solutions to this problem (e.g.
    Twisted, gevent, Stackless Python, etc). Here we use a simple check-sleep
    loop to wait for an update. app.config is handy place to stow global app
    data.
    """
    time.sleep(10)
    return "changed!"


def occasional_update(minsecs=40, maxsecs=50, first_time=False):
    """
    Simulate the server having occasional updates for the client. The first
    time it's run (presumably synchronously with the main program), it just
    kicks off an asynchronous Timer. Subsequent invocations (via Timer)
    actually signal an update is ready.
    """
    app.config['updated'] = not first_time
    delay = random.randint(minsecs, maxsecs)
    threading.Timer(delay, occasional_update).start()


if __name__ == "__main__":
    # start occasional update simulation
    occasional_update(first_time=True)
    app.run(threaded=True)
    # start server and web page pointing to it
    # url = "http://127.0.0.1:{}".format(port)
    # wb = webbrowser.get(None)  # instead of None, can be "firefox" etc
    # threading.Timer(1.25, lambda: wb.open(url) ).start()
    app.run(debug=True)
