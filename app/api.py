# -*- coding: utf-8 -*-
"""
Created on Sun Sep 19 11:13:22 2021

@author: joshu
"""

from flask import Flask, request, \
    render_template, redirect, url_for, jsonify, session

import os
import sys

path = os.path.abspath(os.path.join('.'))
if path not in sys.path:
    sys.path.append(path)


import model.main as main
import pandas as pd
import json
import model.make_daily_file as mdf
from model.utils import color_positive_green

app = Flask(__name__)
app.config['SECRET_KEY'] = 'something only you know'
# app.secret_key = 'secret key'

prob_win_dict = pd.read_pickle('probability_distributions_condensed_V2.pkl')


@app.route('/', methods=['POST', 'GET'])
def get_inputs():
    if request.method == 'POST':

        if not os.path.isdir('app/static'):
            os.mkdir('app/static')
        
        #Get Bet1 and bank_roll inputs and dump
        #into json for later use
        form_data = request.form
        
        with open('app/static/inputs.json', 'w') as f:
            json.dump(form_data, f)
            
        df = pd.DataFrame(columns=['Current Time','lower tier team', 'higher tier team','lower tier points', 'higher tier points',
                          'lower tier fractional', 'higher tier fractional','time_sec', 'future_score', 'EV_low_tier',
                          'EV_higher_tier', 'oddsB lower tier ML', 'oddsB higher tier ML', 'probability', 'kelly'])
        
        df.to_csv('app/static/nightly_EVs.csv', index=None)

        return redirect(url_for('choose_teams'))
    return render_template('index.html')

@app.route('/make_daily_file', methods=['POST'])
def daily_file_route():
    if request.method == 'POST':
        daily_file = mdf.make_full_daily_file()
        daily_file.to_csv('app/static/daily_file.csv', index=None)
        
        teams_df = daily_file[['lower tier team', 'higher tier team']].drop_duplicates()
        teams_list = [teams_df['lower tier team'].loc[row] + ' vs. ' + teams_df['higher tier team'].loc[row] for row in teams_df.index]

        with open('app/static/teams_list.txt', 'w') as f:
            for item in teams_list:
                f.write("%s\n" % item)

        return jsonify({'response':'Daily File Created'})
    
@app.route('/choose_teams', methods=['GET', 'POST'])
def choose_teams():
    if request.method == 'POST':
        team_list = request.form.getlist('game')
        print(team_list)
        session['teams'] = team_list
        
        return redirect(url_for('run_model'))
        
    with open('app/static/teams_list.txt', 'r') as f:
        teams_list = f.read().splitlines()
    return render_template('teams.html', teams_list=teams_list)


@app.route('/run_model', methods=['GET', 'POST'])
def run_model():
    if request.method == 'POST':
        
        with open('app/static/inputs.json') as f:
            data = json.load(f)
            
        bet1 = int(data['bet1'])
        bank_roll = int(data['bank_roll'])
        
        night_EVs = pd.read_csv('app/static/nightly_EVs.csv')
        
        team_list = session.get('teams')
        print('run_model teams: ', team_list)
        output = main.get_EV(bet1, bank_roll, prob_win_dict, team_list)
        
        print('output')
        print(output.head())
        
        night_EVs = night_EVs.append(output, ignore_index=True, sort=False)
        night_EVs.to_csv('app/static/nightly_EVs.csv', index=None)
        
        output = output.style.applymap(color_positive_green, subset=pd.IndexSlice[:, ['EV_low_tier', 'EV_higher_tier']]).hide_index().render()
        
        
        night_EVs = night_EVs.style.applymap(color_positive_green, subset=pd.IndexSlice[:, ['EV_low_tier', 'EV_higher_tier']]).hide_index().render()

        return render_template('output.html', output=output, night_EVs = night_EVs)
    
    
    return render_template('output.html')
       
        

@app.route('/remove/')
def remove_files():
    try:
        os.remove('app/static/daily_file.csv')
        os.remove('app/static/inputs.json')
        os.remove('app/static/nightly_EVs.csv')
        os.remove('app/static/teams_list.txt')
        return redirect(url_for('get_inputs'))
    except Exception as e:
        return str(e)


if __name__ == '__main__':
    app.run(debug=False)