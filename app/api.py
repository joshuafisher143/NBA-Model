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

import model.main as main
import pandas as pd
import json
import model.make_daily_file as mdf
from model.utils import color_positive_green


app = Flask(__name__)
app.config['SECRET_KEY'] = 'something only you know'

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
                          'lower tier fractional', 'higher tier fractional','time_sec', 'low_score', 'EV_low_tier',
                          'EV_higher_tier', 'oddsB lower tier ML', 'oddsB higher tier ML', 'probability', 'kelly'])
        
        df.to_csv('app/static/nightly_EVs.csv', index=None)
        daily_file = mdf.make_full_daily_file()
        daily_file.to_csv('app/static/daily_file.csv', index=None)

        return redirect(url_for('run_model'))
    return render_template('index.html')


@app.route('/run_model', methods=['GET', 'POST'])
def run_model():
    if request.method == 'POST':
        
        with open('app/static/inputs.json') as f:
            data = json.load(f)
            
        bet1 = int(data['bet1'])
        bank_roll = int(data['bank_roll'])
        
        night_EVs = pd.read_csv('app/static/nightly_EVs.csv')

        output = main.get_EV(bet1, bank_roll, prob_win_dict)
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
        return redirect(url_for('get_inputs'))
    except Exception as e:
        return str(e)


if __name__ == '__main__':
    app.run(debug=False)