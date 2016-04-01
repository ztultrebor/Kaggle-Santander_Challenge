#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import numpy as np
from sklearn.cross_validation import StratifiedKFold
from sklearn.grid_search import RandomizedSearchCV

def GridSearch(classifier, paramdict, iters, X, y):
    '''
    Takes as input:
        classifier: the sklearn classifier to investigate
        paramdict: a dictionary of parameters to perform the randomized search
        on
        iters: number of iterations of randomized search to perform
        kfcv: a pre-defined StratifiedKFold object
        X: the training data
        y: the target or labels
    What it does:
        acts as a convenent wrapper function for the scikit-learn randomized
        search cross validation method
    Returns:
        the best estimator object
        dictionary of hyperparemeters for the best estimator
        the ROC-AuC score for the best estimator
    '''
    np.random.seed(42)
    kfcv = StratifiedKFold(y, n_folds=5, shuffle=True)
    gs = RandomizedSearchCV(classifier, paramdict, n_iter=iters, cv=kfcv,
                            scoring='roc_auc')
    gs.fit(X, y)
    return gs.best_estimator_, gs.best_params_, gs.best_score_
