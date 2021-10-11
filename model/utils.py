# -*- coding: utf-8 -*-
"""
Created on Sat Sep 18 18:04:50 2021

@author: joshu
"""

import pandas as pd
import numpy as np
import time
import datetime
from fractions import Fraction
import requests




#pull live game stats
def request_game_stats(game_stats_feed_key):
    game_info = requests.get(game_stats_feed_key)
    game_info_dict = game_info.json()
    
    return game_info_dict


def convert_time(Time):
    try:
        Time_conv = time.strptime(Time, "%M:%S")
        Time_remaining = datetime.timedelta(minutes=Time_conv.tm_min,seconds=Time_conv.tm_sec).total_seconds()
    except:
        Time_remaining = int(float(Time))
    
    return Time_remaining


def parse_game_stats(game_info_dict, key):
    if game_info_dict['data'][key]['status'] == 'Live':
        GameID = game_info_dict['data'][key]['gameUID']
        Home_team = game_info_dict['data'][key]['homeTeam']
        Away_team = game_info_dict['data'][key]['awayTeam']
        Home_points = game_info_dict['data'][key]['scoreHomeTotal']
        Away_points = game_info_dict['data'][key]['scoreAwayTotal']
        current_quarter = game_info_dict['data'][key]['period']
        Time = game_info_dict['data'][key]['clock']

        
        
        Time_remaining = convert_time(Time)
        quarter_time_elapsed = 720 - Time_remaining
        
        if current_quarter == '1':
            time_elapsed = 720-Time_remaining
        elif current_quarter == '2':
            time_elapsed = quarter_time_elapsed + 720
        elif current_quarter == '3':
            time_elapsed = quarter_time_elapsed + 1440
        else:
            time_elapsed = quarter_time_elapsed + 2160
            
        
        temp_df = pd.DataFrame({'GameID':[GameID], 
                                  'Home_Team':[Home_team], 
                                  'Away_Team':[Away_team],
                                  'Home_Points':[Home_points], 
                                  'Away_Points':[Away_points],
                                  'current_quarter':[current_quarter], 
                                  'Time_elapsed':[time_elapsed]})
        
        return temp_df
        
        
def request_game_odds(game_odds_feed_key):
    game_info = requests.get(game_odds_feed_key)
    go_dict = game_info.json()
    
    return go_dict
                

def parse_odds(key_2, go_dict):
    if go_dict['data'][key_2]['isLive'] and go_dict['data'][key_2]['betPrice'] and go_dict['data'][key_2]['betType'] == 'Moneyline':
        for key_3 in range(len(go_dict['data'])):
            if go_dict['data'][key_2]['gameUID'] == go_dict['data'][key_3]['gameUID'] and key_2 != key_3:
                if go_dict['data'][key_2]['betName'] == go_dict['data'][key_2]['homeTeam']:
                    Home_ML = go_dict['data'][key_2]['betPrice']
                    if int(Home_ML) > 0:
                        Home_fractional = int(Home_ML) / 100
                    else:
                        Home_fractional = (-100)/ int(Home_ML)
                    
                    Away_ML = go_dict['data'][key_3]['betPrice']
                    if int(Away_ML) > 0:
                        Away_fractional = int(Away_ML) / 100
                    else:
                        Away_fractional = (-100) / int(Away_ML)

    else:
        Home_fractional = 0
        Away_fractional = 0
            
    GameID = go_dict['data'][key_2]['gameUID']

    temp_df = pd.DataFrame({'GameID':[GameID],
                            'Home_fractional':[Home_fractional],
                            'Away_fractional':[Away_fractional]})

    return temp_df
    
    
def calculate_score_differential(df):
    if df['lower tier team'][0] == df['Home_Team'][0]:
        score_diff = (int(df['Home_Points'][0]) - int(df['Away_Points'][0]))
    else:
        score_diff = (int(df['Away_Points'][0])-int(df['Home_Points'][0]))       
    
    return score_diff



def get_probabilities(final_df, ind, lvh_count_dict, score_diff, tier_matchup, oddsB_low, oddsB_high):
    time_block = int(abs(final_df['Time_elapsed'].iloc[ind]-1)/180) + 1
    future_time = int(abs(final_df['time_sec'].iloc[ind]-1)/180) + 1              

    time_score = str(time_block) + ',' + str(score_diff)
    future_score = final_df['low_score'].iloc[ind]
    if lvh_count_dict[tier_matchup][time_score][str(future_time)][str(future_score)][0] > 49:
        lvh_prob_win_dist = lvh_count_dict[tier_matchup][time_score][str(future_time)].copy()
        lvh_prob_win_dist.loc[:,'-60':'59'] = lvh_prob_win_dist.div(lvh_prob_win_dist.sum(axis=1)[0], axis=0)
        if score_diff < future_score:
            lvh_prob_win = lvh_prob_win_dist.loc[:,str(future_score):].sum(axis=1)[0]
        else:
            lvh_prob_win = lvh_prob_win_dist.loc[:,:str(future_score)].sum(axis=1)[0]
    else:
        lvh_prob_win = 0
    
    if lvh_prob_win == 0:
        hvl_prob_win = 0
    else:
        hvl_prob_win = lvh_prob_win
        
    return lvh_prob_win, hvl_prob_win, future_time
    

def calculate_kelly(prob_win, bank_roll):
    kelly = (0.02/(((1+0.02)/prob_win)-1))*bank_roll
    
    return kelly

def calculate_EV(df, fractional_column, index, bet1, bank_roll, prob_win, oddsB):
    oddsA_low = float(Fraction(df[fractional_column].iloc[index]))
    bet2 = bet1*((oddsA_low+1)/(oddsB+1))
    EV = ((((bet1*oddsA_low)-bet2)*.5)+(((bet2*oddsB)-bet1)*.5))*prob_win-(bet1*(1-prob_win))
    
    return EV

def oddsB_to_ML(oddsB):
    if oddsB > 1:
        oddsB_ML = oddsB*100
    else:
        oddsB_ML = (-100)/oddsB
        
    return oddsB_ML
    
    
    
def get_median_EV(df, median_df, tier):
    try:
        EV_low_idx = df.loc[df[tier] == np.median(df[tier])].index[0]
        if df[tier].loc[EV_low_idx] > 0:
            median_df = median_df.append(df.loc[EV_low_idx],ignore_index=True, sort=False)
    except:
        EV_low_sort = df.iloc[(df[tier]-np.median(df[tier])).abs().argsort()[:2]]
        EV_low_median = EV_low_sort.iloc[0]
        if EV_low_median[tier] > 0:
            median_df = median_df.append(EV_low_median,ignore_index=True, sort=False)
    return median_df
    
    
    
    
    
    
    
    
    
    
    
    
                
        
                
            