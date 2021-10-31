# -*- coding: utf-8 -*-
"""
Created on Mon Oct 25 15:08:19 2021

@author: joshu
"""

import math
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import os

def get_portal_odds():
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.binary_location = os.environ['GOOGLE_CHROME_BIN']
    # options.binary_location = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'

    # driver = webdriver.Chrome(options=options, executable_path='C:/Users/joshu/Documents/py_projects/NBA-Model/old/chromedriver.exe')
    driver = webdriver.Chrome(options=options, executable_path=os.environ['CHROMEDRIVER_PATH'])
    driver.get('https://www.oddsportal.com/basketball/usa/nba/')   
    
    result=None
    while result is None:
        try:
            time.sleep(1.5)
            driver.find_element(By.XPATH, '//*[@id="user-header-oddsformat-expander"]').click()
            time.sleep(1.5)
            driver.find_element(By.XPATH, '//*[@id="user-header-oddsformat"]/li[3]/a').click()
            time.sleep(1.5)
            driver.find_element(By.XPATH, '//*[@id="user-header-timezone-expander"]').click()
            time.sleep(1.5)
            driver.find_element(By.XPATH, '//*[@id="timezone-content"]/a[40]').click()
            result = True
        except:
            print('Trying again')
            pass
    
    df = pd.DataFrame(columns=['lower tier team', 'higher tier team', 'oddsB lower tier', 'oddsB higher tier'])
    
    for i in range(4, 14):
        try:
            try:
                teams = driver.find_element(By.XPATH, '//*[@id="tournamentTable"]/tbody/tr[{}]/td[2]/a[2]'.format(i)).text.split(' - ')
                team1, team2 = teams[0], teams[1]
                odds1 = driver.find_element(By.XPATH,'//*[@id="tournamentTable"]/tbody/tr[{}]/td[3]/a'.format(i)).text
                odds2 = driver.find_element(By.XPATH,'//*[@id="tournamentTable"]/tbody/tr[{}]/td[4]/a'.format(i)).text
                
                df = df.append({'lower tier team': team1, 'higher tier team':team2, 'oddsB lower tier':odds1, 'oddsB higher tier':odds2}, ignore_index=True)
            except:
                teams = driver.find_element(By.XPATH, '//*[@id="tournamentTable"]/tbody/tr[{}]/td[2]/a[2]'.format(i)).text.split(' - ')
                team1, team2 = teams[0], teams[1]
                odds1 = driver.find_element(By.XPATH,'//*[@id="tournamentTable"]/tbody/tr[{}]/td[4]/a'.format(i)).text
                odds2 = driver.find_element(By.XPATH,'//*[@id="tournamentTable"]/tbody/tr[{}]/td[5]/a'.format(i)).text
                
                df = df.append({'lower tier team': team1, 'higher tier team':team2, 'oddsB lower tier':odds1, 'oddsB higher tier':odds2}, ignore_index=True)
        except:
            continue
    driver.close()
        
    for row in range(len(df)):
        if df['oddsB lower tier'].iloc[row] > df['oddsB higher tier'].iloc[row]:
            
            lower_tier_team = df['lower tier team'].iloc[row]
            higher_tier_team = df['higher tier team'].iloc[row]
            
            oddsB_lower_tier = df['oddsB lower tier'].iloc[row]
            oddsB_higher_tier = df['oddsB higher tier'].iloc[row]
            
            df['lower tier team'].iloc[row] = higher_tier_team
            df['higher tier team'].iloc[row] = lower_tier_team
            df['oddsB lower tier'].iloc[row] = oddsB_higher_tier
            df['oddsB higher tier'].iloc[row] = oddsB_lower_tier
            
           
    return df


def calculate_daily(lower_tier_SO_perc, higher_tier_SO_perc, time_sec, score_diff):

    oddsB_lower_tier=(math.exp(-1.8635+(0.00018843*time_sec)+(0.10366*score_diff)+3.4324*lower_tier_SO_perc))/(1+math.exp(-1.8635+(0.00018843*time_sec)+(0.10366*score_diff)+3.4324*lower_tier_SO_perc))
    oddsB_lower_tier_fractional = (1/oddsB_lower_tier) - 1
    
    
    oddsB_higher_tier = (math.exp(-1.77-(0.00012557*time_sec)+(0.11173*(score_diff*-1))+3.9179*higher_tier_SO_perc))/(1+math.exp(-1.77-(0.00012557*time_sec)+(0.11173*(score_diff*-1))+3.9179*higher_tier_SO_perc))
    oddsB_higher_tier_fractional = (1/oddsB_higher_tier) - 1
    
    return oddsB_lower_tier_fractional, oddsB_higher_tier_fractional


def odds_to_decimal(odds):
    if int(odds) < 0:
        odds_decimal = (-1*int(odds))/(-1*int(odds) + 100)
    else:
        odds_decimal = 100 / (int(odds)+100)
    return odds_decimal

def make_tier(starting_odds):
    odds_decimal = odds_to_decimal(starting_odds)
    
    if odds_decimal < 0.25:
        tier = 1
    elif 0.25 <= odds_decimal < 0.4:
        tier = 2
    elif 0.4 <= odds_decimal < 0.5:
        tier = 3
    elif 0.5 <= odds_decimal < 0.625:
        tier = 4
    elif 0.625 <= odds_decimal < 0.75:
        tier = 5
    else:
        tier = 6
    return tier


def make_one_team_daily_file(team_odds):
    df = pd.read_csv('app/static/score_time_blank.csv')
    
    df['lower tier team'] = team_odds['lower tier team']
    df['higher tier team'] = team_odds['higher tier team']
    
    oddsB_lower_tier = team_odds['oddsB lower tier']
    oddsB_higher_tier = team_odds['oddsB higher tier']
    
    lower_tier = make_tier(oddsB_lower_tier)
    higher_tier = make_tier(oddsB_higher_tier)
    
    df['lower tier'] = lower_tier
    df['higher tier'] = higher_tier
    
    lower_tier_SO_perc = odds_to_decimal(oddsB_lower_tier)
    higher_tier_SO_perc = odds_to_decimal(oddsB_higher_tier)
    
    for row in range(len(df)):
        oddsB_lower_tier_fractional, oddsB_higher_tier_fractional = calculate_daily(lower_tier_SO_perc, higher_tier_SO_perc, df['time_sec'].iloc[row], df['low_score'].iloc[row])
        df['oddsB lower tier'].iloc[row] = oddsB_lower_tier_fractional
        df['oddsB higher tier'].iloc[row] = oddsB_higher_tier_fractional
    
    return df
    
def make_full_daily_file():
    
    team_odds = get_portal_odds()
    
    final_daily_file = pd.DataFrame(columns=['lower tier team', 'higher tier team', 'lower tier', 'higher tier',
           'low_score', 'time_sec', 'oddsB lower tier', 'oddsB higher tier'])
    
    for row in team_odds.index:
        df = make_one_team_daily_file(team_odds.iloc[row])
        final_daily_file = final_daily_file.append(df, ignore_index=True)   
    return final_daily_file
        
    
    
    
    