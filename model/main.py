import pandas as pd
import numpy as np
import time
import datetime
from fractions import Fraction
import webbrowser
import scipy.io
import requests
import json
import os

#import config file
import model.config as config

#import functions from utils
from model.utils import request_game_stats
from model.utils import convert_time
from model.utils import parse_game_stats
from model.utils import request_game_odds
from model.utils import parse_odds
from model.utils import calculate_score_differential
from model.utils import get_probabilities
from model.utils import calculate_kelly
from model.utils import calculate_EV
from model.utils import oddsB_to_ML
from model.utils import get_median_EV


def get_EV(bet1, bank_roll, daily_file, prob_win_dict):
        
######################GAME STATS FOR EACH GAME################################
    game_info_dict = request_game_stats(config.STATS_API_KEY)
    
    
    #make empty dataframe to append the stats data to for each game
    game_df = pd.DataFrame(columns = ['GameID', 'Home_Team', 'Away_Team','Home_Points', 'Away_Points',
                                      'current_quarter', 'Time_elapsed'])        
    
    '''
    parse_game_stats function extracts GameID, teams, points, current quarter,
    and amount of time left for each game that is currently live
    '''
    #parse game stats and append to dataframe
    for key in range(len(game_info_dict['data'])):
        try:
            # game_df.append(parse_game_stats(game_info_dict, key))
            game_df = game_df.append(parse_game_stats(game_info_dict, key))
        except:
            continue

######################GAME ODDS FOR EACH GAME#################################
    go_dict = request_game_odds(config.ODDS_API_KEY)

    #make empty dataframe to append odds data to for each game
    odds_df = pd.DataFrame(columns = ['GameID', 'Home_fractional', 'Away_fractional'])

    '''
    parse_odds iterates over each game in the game odds dict, if the game is
    live and there is a moneyline listed, the home and away moneylines are
    extracted and converted into fractionals. 
    '''
    for key in range(len(go_dict['data'])):
        try:
            odds_df = odds_df.append(parse_odds(key, go_dict))
        except:
            continue
    
    odds_df = odds_df.drop_duplicates()
    odds_df = odds_df[(odds_df['Home_fractional'] > 0) & (odds_df['Away_fractional'] > 0)]
    
######################MERGE GAME AND ODDS DATAFRAMES##########################
    live_df = game_df.merge(odds_df, on=['GameID'])
    live_df = live_df.set_index('GameID')


######################CREATE MEDIAN DF TO BE USED LATER, OUTSIDE NEXT LOOP#####

    median_df = pd.DataFrame(columns=['lower tier team', 'higher tier team','lower tier points', 'higher tier points',
                                      'lower tier fractional', 'higher tier fractional','timeB', 'low_score', 'high_score',
                          'EV_low_tier', 'EV_higher_tier', 'oddsB lower tier ML', 'oddsB higher tier ML', 'lvh_prob', 'hvl_prob',
                          'lvh_kelly', 'hvl_kelly'])

######################FILTER DAILY FILE#######################################

    for game in live_df.index:
        dfile = pd.read_csv(daily_file)
        daily_file_filtered = dfile[dfile['time_sec'] > live_df['Time_elapsed'].loc[game]]
        #filter out teams that don't relate to current looped index
        df_filt_oneT = daily_file_filtered.loc[(daily_file_filtered['lower tier team'] == live_df['Home_Team'].loc[game]) | (daily_file_filtered['higher tier team'] == live_df['Home_Team'].loc[game]),:]
        if len(df_filt_oneT) < 1:
            continue
        #merge the filtered daily file and the live_df
        if live_df['Home_Team'].loc[game] == df_filt_oneT['lower tier team'].iloc[0]:
            final_df = live_df.merge(df_filt_oneT,
                                 left_on=['Home_Team'],
                                 right_on = ['lower tier team'])
        else:
            final_df = live_df.merge(df_filt_oneT,
                                 left_on=['Home_Team'],
                                 right_on = ['higher tier team'])


#######################EXTRACT WIN PROBABILITIES##############################

        score_diff = calculate_score_differential(final_df)
        tier_matchup = str(final_df['lower tier'][0]) + ',' + str(final_df['higher tier'][0])
        
        #Empty dataframe for EV calculations
        ev_out_df = pd.DataFrame(columns=['index', 'EV_low_tier', 'EV_higher_tier',
                                          'future_time_block', 'oddsB lower tier ML',
                                          'oddsB higher tier ML', 'lvh_prob',
                                          'hvl_prob', 'lvh_kelly', 'hvl_kelly'])
        
        
        for ind in final_df.index:
            oddsB_low = final_df['oddsB lower tier'].iloc[ind]                
            oddsB_high = final_df['oddsB higher tier'].iloc[ind]
            
            lvh_prob_win, hvl_prob_win, future_time = get_probabilities(final_df, ind, prob_win_dict, score_diff, tier_matchup, oddsB_low, oddsB_high)
            
#######################CALCULATE EV AND KELLY FOR LOWER TIER TEAM##############              
            if final_df['Home_Team'].iloc[ind] == final_df['lower tier team'].iloc[ind]:
                EV_low = calculate_EV(final_df, 'Home_fractional', ind, bet1, bank_roll, lvh_prob_win, oddsB_high)
            else:
                EV_low = calculate_EV(final_df, 'Away_fractional', ind, bet1, bank_roll, lvh_prob_win, oddsB_high)
            
            try:    
                lvh_kelly = calculate_kelly(lvh_prob_win, bank_roll)
            except:
                lvh_kelly = 0
            
            if EV_low < 0:
                lvh_kelly=0

#######################CALCULATE EV AND KELLY FOR HIGHER TIER TEAM##############          
            if final_df['Home_Team'].iloc[ind] == final_df['higher tier team'].iloc[ind]:
                EV_high = calculate_EV(final_df, 'Home_fractional', ind, bet1, bank_roll, hvl_prob_win, oddsB_low)
            else:
                EV_high = calculate_EV(final_df, 'Away_fractional', ind, bet1, bank_roll, hvl_prob_win, oddsB_low)
            
            try:
                hvl_kelly = calculate_kelly(hvl_prob_win, bank_roll)
            except:
                hvl_kelly = 0
            
            if EV_high < 0:
                hvl_kelly = 0
                
                
#######################CONVERT ODDSB TO MONEYLINE#############################

            oddsB_low = oddsB_to_ML(oddsB_low)
            oddsB_high = oddsB_to_ML(oddsB_high)

#######################APPEND EV DATA TO DATAFRAME#############################
            
            ev_data = [{'index': ind, 'EV_low_tier': EV_low,
                        'EV_higher_tier': EV_high, 'future_time_block': future_time,
                        'lvh_prob': lvh_prob_win, 'oddsB lower tier ML':oddsB_low,
                        'oddsB higher tier ML':oddsB_high, 'hvl_prob':hvl_prob_win,
                        'lvh_kelly':lvh_kelly, 'hvl_kelly':hvl_kelly}]
            ev_out_df = ev_out_df.append(ev_data, ignore_index=True, sort=False)


        EV_final_full = final_df.merge(ev_out_df, left_index=True, right_on='index')


        #rename columns for easier understanding
        if EV_final_full['Home_Team'].iloc[0] == EV_final_full['lower tier team'].iloc[0]:
            EV_final_full = EV_final_full.rename(columns={'Home_Points':'lower tier points', 'Away_Points': 'higher tier points',
                                          'Home_fractional':'lower tier fractional', 'Away_fractional':'higher tier fractional'})
        else:
            EV_final_full = EV_final_full.rename(columns={'Home_Points':'higher tier points', 'Away_Points': 'lower tier points',
                                          'Home_fractional':'higher tier fractional', 'Away_fractional':'lower tier fractional'})
            
            
#####################FINAL DATAFRAME ##########################################
        EV_df_over20 = EV_final_full[(EV_final_full['EV_low_tier'].between(20,100)) | (EV_final_full['EV_higher_tier'].between(20,100))]
        relevant_feats = ['lower tier points', 'higher tier points', 'lower tier fractional', 'higher tier fractional',
                          'lower tier team', 'higher tier team', 'timeB', 'low_score', 'high_score',
                          'EV_low_tier', 'EV_higher_tier', 'oddsB lower tier ML', 'oddsB higher tier ML', 'lvh_prob', 'hvl_prob',
                          'lvh_kelly', 'hvl_kelly']
        EV_df_over20 = EV_df_over20[relevant_feats]
        
####################ISOLATE MEDIAN EV FOR EACH TIER###########################
        try:
            median_df = median_df.append(get_median_EV(EV_df_over20, median_df, 'EV_low_tier'))
            median_df = median_df.append(get_median_EV(EV_df_over20, median_df, 'EV_higher_tier'))
        except:
            no_bet = [{'lower tier points':'N/A', 'higher tier points':'N/A', 'lower tier fractional':'N/A', 'higher tier fractional':'N/A',
                          'lower tier team':'N/A', 'higher tier team':'N/A', 'timeB':'N/A', 'low_score':'N/A', 'high_score':'N/A',
                          'EV_low_tier':'N/A', 'EV_higher_tier':'N/A', 'oddsB lower tier ML':'N/A', 'oddsB higher tier ML':'N/A', 'lvh_prob':'N/A',
                          'hvl_prob':'N/A', 'lvh_kelly':'N/A', 'hvl_kelly':'N/A'}]
            median_df = median_df.append(no_bet, ignore_index=True, sort=False)       
    return median_df
            
# while True:
#     EV = get_EV(100, 1000, daily_file, prob_win_dict)            
#     print(EV)
#     print('iteration has ended')
#     time.sleep(65)








