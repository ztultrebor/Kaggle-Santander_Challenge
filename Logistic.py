from GridSearch import GridSearch
import numpy as np
import pandas as pd
import scipy
from sklearn.linear_model import LogisticRegression

#===================================prep data==================================

np.random.seed(42)

target_col = 'TARGET'
id_col = 'ID'

X_train = pd.read_csv('./EngineeredData/Xtrain.csv')
y_train = pd.read_csv('./EngineeredData/ytrain.csv')[target_col]
X_test = pd.read_csv('./EngineeredData/Xtest.csv')
id_test = pd.read_csv('./EngineeredData/idtest.csv')[id_col]

#=============================ADA Boster========================================

params = {
            'C'                     :       scipy.stats.expon(0, 1),
            'intercept_scaling'     :       scipy.stats.expon(0, 1)
            }

clf = LogisticRegression()

GridSearch(
                        classifier      =       clf,
                        paramdict       =       params,
                        iters           =       243,
                        X               =       X_train,
                        y               =       y_train
)
