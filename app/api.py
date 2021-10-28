# -*- coding: utf-8 -*-
"""
Created on Sun Sep 19 11:13:22 2021

@author: joshu
"""

from flask import Flask, request, \
    render_template, redirect, url_for
import os
import sys

path = os.path.abspath(os.path.join('.'))
if path not in sys.path:
    sys.path.append(path)

# import model.config as config
import model.main as main
import pandas as pd
import numpy as np
import json
import model.make_daily_file as mdf


app = Flask(__name__)
app.config['SECRET_KEY'] = 'something only you know'

'''
Load file

prob_win_dict - nested dictionary that contains historical game score-time probabilities

'''
prob_win_dict = pd.read_pickle('small_prob_dist.pkl')


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
                          'lower tier fractional', 'higher tier fractional','timeB', 'low_score', 'EV_low_tier',
                          'EV_higher_tier', 'oddsB lower tier ML', 'oddsB higher tier ML', 'probability', 'kelly'])
        
        df.to_csv('app/static/nightly_EVs.csv', index=None)
        
        return redirect(url_for('run_model'))
    return render_template('index.html')


@app.route('/run_model', methods=['GET', 'POST'])
def run_model():
    if request.method == 'POST':
        with open('app/static/inputs.json') as f:
            data = json.load(f)
            
        bet1 = int(data['bet1'])
        bank_roll = int(data['bank_roll'])
        
        daily_file = 'app/static/daily_file.csv'
        
        night_EVs = pd.read_csv('app/static/nightly_EVs.csv')

        output = main.get_EV(bet1, bank_roll, daily_file, prob_win_dict)
        
        night_EVs = night_EVs.append(output, ignore_index=True, sort=False)
        night_EVs.to_csv('app/static/nightly_EVs.csv', index=None)
        return render_template('output.html', output=output.to_html(index=False), night_EVs = night_EVs.to_html(index=False))
    daily_file = mdf.make_full_daily_file()
    daily_file.to_csv('app/static/daily_file.csv', index=None)
    return render_template('output.html')

@app.route('/remove/')
def remove_files():
    try:
        os.remove('app/static/daily_file.csv')
        os.remove('app/static/inputs.json')
        os.remove('app/static/nightly_EVs.csv')
        return redirect(url_for('get_inputs'))
    except Exception as e:
        return str(e)


if __name__ == '__main__':
    app.run(debug=False)