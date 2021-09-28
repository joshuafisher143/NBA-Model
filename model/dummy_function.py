# -*- coding: utf-8 -*-
"""
Created on Sun Sep 19 17:57:19 2021

@author: joshu
"""

import time
import pandas as pd
import numpy as np

def dummy_function(bet1: int, bank_roll: int):
    result = np.random.rand()
    temp_df = pd.DataFrame({'bet1':[bet1], 'bank_roll':[bank_roll], 'result':[result], 'other_result':[result]})
    
    return temp_df
