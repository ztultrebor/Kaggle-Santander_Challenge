#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from dataloader import import_data
import numpy as np
import pandas as pd
import scipy
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.cross_validation import StratifiedKFold
from sklearn.metrics import roc_auc_score

#==============================================================================

def set_params(classifier, paramdict):
    '''
    Takes as input:
        classifier: an estimator object (scikit-learn compatible)
        paramdict: a dictionary keyed by hyperparameter names with random
        distribution objects as values
    What it does:
        Sets hyperparemeters of an estimator object. Checks to see if the
        value is a RNG and behaves accordingly
    Returns:
        - an estimator with hyperparemeters updated
    '''
    for param in paramdict:
        if (type(paramdict[param]) is
                    scipy.stats._distn_infrastructure.rv_frozen):
            v = paramdict[param].rvs()
            if param in ('max_depth', 'min_samples_leaf', 'n_estimators'):
                setattr(classifier, param, int(v))
            else:
                setattr(classifier, param, v)
        else:
            setattr(classifier, param, paramdict[param])
    return classifier

#==============================================================================

def shuffle_labels(y_train, folded):
    '''
    Takes as input:
        y_train: a pandas series object contining the training labels/target
        folded: a scikit-learn KFold object
    What it does:
        Reorders the training labels in cross-validated order
    Returns:
        - a pandas series object contining the reordered training labels/target
    '''
    y_train_shuffled = pd.Series()
    for fit, val in folded:
        y_train_shuffled = pd.concat([y_train_shuffled, y_train[val]],
                            ignore_index=True)
    return y_train_shuffled

#==============================================================================

def generalized_CV(method, classifier, paramdict, iters, folds,
                    X_train, y_train, X_test=None):
    '''
    Takes as input:
        method: tells the function how to act: should it perform Grid Search,
        or should it stack or bag?
        classifier: an estimator object (scikit-learn compatible)
        paramdict: a dictionary keyed by hyperparameter names with random
        distribution objects as values
        iters: number of estimators to iterate over
        folds: a scikit-learn KFold cross validation object
        X_train: a pandas DataFrame containing the training data
        y_train: a pandas series containing the target/labels
    What it does:
        Iterates through a sequence of estimators with randomly selected
        hyperparameters. If method=='GridSearch', then it finds the best
        hyperparemeters given the training data. If method=='Stack' or 'Bag'
        then it generates cross validation estimates for the training data and
        fully-trained predictions for the test data using estimators for each
        combination of hyperparameters
    Returns if method=='GridSearch':
        - the best estimator object
        - dictionary of hyperparemeters for the best estimator
        - the ROC-AuC score for the best estimator
    Returns if method is 'Stack' or 'Bag':
        - a pandas DataFrame containing cross-validation estimates of the
        training labels; each column cotains the estimates for a particular
        estimator
        - a pandas DataFrame containing fully-trained predictions for the test
        data; each column cotains the estimates for a particular estimator
        column cotains the estimates for a particular estimator
        - a list of weights for each estimator proportional to that estimator's
        ROC-AuC score
        - a pandas series contining the properly ordered training labels/target
        - a list of the hyperparameters for each individual estimator
    '''
    best_score = 0
    weights = []
    paramlist = []
    y_train_shuffled = shuffle_labels(y_train, folds)
    estimates = pd.DataFrame()
    predictions = pd.DataFrame()
    for _ in xrange(iters):
        esty = set_params(classifier, paramdict)
        training_probs = pd.Series()
        for fit, val in folds:
            # fit this model using this fitting subset
            esty.fit(X_train.iloc[fit], y_train.iloc[fit])
            # predict probs for this validation subset
            val_probs = pd.Series(esty.predict_proba(X_train.iloc[val])[:,1])
            training_probs = pd.concat([training_probs, val_probs],
                                        ignore_index=True)
        score = roc_auc_score(y_train_shuffled, training_probs)
        if method == 'GridSearch':
            if score > best_score:
                best_score = score
                best_params = esty.get_params()
                print score
                print best_params
        elif method in ('Stack', 'Bag'):
            estimates = pd.concat([estimates, training_probs], axis=1,
                                        ignore_index=True)
            # fit this model using full training data
            classifier.fit(X_train, y_train)
            # predict probs for test data
            test_probs = pd.Series(classifier.predict_proba(X_test)[:,1])
            predictions = pd.concat([predictions, test_probs], axis=1,
                                        ignore_index=True)
            params = classifier.get_params()
            paramlist.append(params)
            weights.append((score-0.5)/(0.844-0.5))
            print score
            print params
    if method == 'GridSearch':
        best_estimator = set_params(classifier, best_params)
        # fit training data using best estimator
        best_estimator.fit(X_train, y_train)
        return best_estimator, best_params, best_score
    elif method in ('Stack', 'Bag'):
        return estimates, predictions, weights, y_train_shuffled, params

#==============================================================================

def engineered_data_prep(folder, ftrain, ftest, fy, fid, target_col, id_col):
    '''
    Takes as input:
        folder: the name of the folder where the csv data is located
        ftrain: the file name of the training data
        ftest: the file name of the test data
        fy: the file name of the training data labels
        fid: the file name of the test data IDs
        target_col: the name of the column in the fy file DataFrame
        id_col: the name of the column in the fid file DataFrame
    What it does:
        Reads data from csv files. Separates out training labels and test IDs.
    Returns:
        - a pandas DataFrame containing the training input data
        - a pandas DataFrame containing the test input data
        - a pandas DataFrame containing the training labels
        - a pandas DataFrame containing the test IDs
    '''
    return (pd.read_csv('./'+ folder + '/' + ftrain),
            pd.read_csv('./'+ folder + '/' + ftest),
            pd.read_csv('./'+ folder + '/' + fy)[target_col],
            pd.read_csv('./'+ folder + '/' + fid)[id_col])

#==============================================================================

def write(estimates, y_train, predictions, id_test, folder, ftrain, ftest, fy,
                fid, target_col, id_col):
    '''
    Takes as input:
        estimates: a pandas DataFrame containing the L1 training estimate data
        y_train: a pandas DataFrame containing the training labels
        predictions: a pandas DataFrame containing the L1 test prediction data
        id_test: a pandas DataFrame containing the test IDs
        folder: the name of the folder where the csv data is located
        ftrain: the file name of the training data
        ftest: the file name of the test data
        fy: the file name of the training data labels
        fid: the file name of the test data IDs
        target_col: the name of the column in the fy file DataFrame
        id_col: the name of the column in the fid file DataFrame
    What it does:
        Writes data to csv files, stored in a folder of choice with filenames
        of choice
    Returns:
        - da nada
    '''
    estimates.to_csv('./' + folder + '/' + ftrain, index=False)
    pd.DataFrame({target_col:y_train}).to_csv('./' + folder + '/' + fy,
                index=False)
    predictions.to_csv('./' + folder + '/' + ftest, index=False)
    pd.DataFrame({id_col:id_test}).to_csv('./' + folder + '/' + fid,
                index=False)

#==============================================================================

def prep_submission(best_estimator, estimates, master_cols, y_train,
                    predictions, id_test, fsubmission, target_col, id_col,
                    top_score):
    print 'The Level1 training data ROC-AuC score is %s' % top_score
    best_estimator.fit(estimates[master_cols], y_train)
    stacked_prediction = best_estimator.predict_proba(
                            predictions[master_cols])[:,1]
    submission = pd.DataFrame({id_col:id_test, target_col:stacked_prediction})
    submission.to_csv(fsubmission, index=False)

#==============================================================================

def L0_classification(Clf, params, X, y, test, folded, niters):
    '''
    Takes as input:
        Clf: a scikit-learn-compatible classifier object
        params: a dictionary of hyperparameters for the classifier
        X: a pandas DataFrame containing the training data
        y: a pandas DataFrame containing the training labels
        test: a pandas DataFrame containing the test data
        folded: a scikit-learn KFold cross validation object
        niters: number of iterations/classifiers
    What it does:
        Acts as a wrapper for the generalized_CV function acting as a 'Stacker'.
        This function basically prepares the randomized hyperparameter
        dictionary
    Returns:
        - the resuts from generalized_CV 'Stack'
    '''
    depth = params['max_depth']
    mcw = params['min_child_weight']
    g = params['gamma']
    sub = params['subsample']
    csbt = params['colsample_bytree']
    a = params['reg_alpha']
    nest = params['n_estimators']
    learning = params['learning_rate']
    base = params['base_score']
    spw = params['scale_pos_weight']
    randoprams = {
        'max_depth'         :       scipy.stats.norm(depth, depth/3.),
        'min_child_weight'  :       scipy.stats.exp(0, mcw),
        'gamma'             :       scipy.stats.exp(0, g),
        'subsample'         :       scipy.stats.beta(sub/(1-sub), 1),
        'colsample_bytree'  :       scipy.stats.beta(csbt/(1-csbt), 1),
        'reg_alpha'         :       scipy.stats.esp(0, a),
        'n_estimators'      :       scipy.stats.exp(0, nest),
        'learning_rate'     :       scipy.stats.exp(0, learning),
        'base_score'        :       scipy.stats.beta(base/(1-base), 1),
        'scale_pos_weight'  :       scipy.stats.exp(0, spw)
                }
    return generalized_CV(
                method                  =       'Stack',
                classifier              =       Clf,
                paramdict               =       randoprams,
                iters                   =       niters,
                folds                   =       folded,
                X_train                 =       X,
                y_train                 =       y,
                X_test                  =       test
                )

#==============================================================================

def L1_aggregation(Clf, params, estimates, y_train, predictions, folded,
                    niters):
    '''
    Takes as input:
        Clf: a scikit-learn-compatible classifier object
        params: a dictionary of hyperparameters for the classifier
        estimates: a pandas DataFrame containing the L1 training estimate data
        y_train: a pandas DataFrame containing the training labels
        predictions: a pandas DataFrame containing the L1 test prediction data
        folded: a scikit-learn KFold cross validation object
        niters: number of iterations/classifiers
    What it does:
        Sorts the L0 estimates in decreasing ROC-AuC order. Aggregates the
        estimates, one-by-one, using logistic regression. Identifies the best
        choice of estimators, and the best choice of logit hyperparameters
    Returns:
        - the resuts from generalized_CV 'Stack'
    '''
    estim_cols = estimates.columns
    ROCs = [roc_auc_score(y_train, estimates[col]) for col in estim_cols]
    l1Clf = LogisticRegression(max_iter=10000, tol=0.000001,
                                class_weight='balanced')
    sorting_hat = zip(estim_cols, ROCs)
    sorting_hat.sort(key=lambda x: -x[1])
    ordered_cols = [s[0] for s in sorting_hat]
    master_cols = []
    top_score = 0
    for i, result in enumerate(ordered_cols):
        _, _, score = generalized_CV(
                        method        =       'GridSearch',
                        classifier    =       Clf,
                        paramdict     =       params,
                        iters         =       niters,
                        folds         =       folded,
                        X_train       =       estimates[master_cols + [result]],
                        y_train       =       y_train
                )
        if score > top_score:
            top_score = score
            best_params = params
            master_cols.append(result)
        print 'WIP: from %s estimates we choose %s' % (i+1, len(master_cols))
    best_estimator = set_params(l1Clf, best_params)
    print 'We decided upon %s XGB results' % len(master_cols)
    return best_estimator, master_cols, top_score


#================Level 1 Estimator: Logistic Regression========================
target_col = 'TARGET'
id_col = 'ID'
X_train, X_test , y_train, id_test = engineered_data_prep('EngineeredData',
                        'Xtrain.csv', 'Xtest.csv', 'ytrain.csv', 'idtest.csv',
                        target_col, id_col)
np.random.seed(3)
kfcv = StratifiedKFold(y_train, n_folds=4, shuffle=True)
l0Clf = XGBClassifier()
l1Clf = LogisticRegression(max_iter=10000, tol=0.000001,
                            class_weight='balanced')
record_score = 0
golden_params = {
            'n_estimators'      :       109,
            'learning_rate'     :       0.040989631409769696,
            'max_depth'         :       5,
            'subsample'         :       0.46667628427710284,
            'colsample_bytree'  :       0.7874691933152562,
            'gamma'             :       0.0960752812134071,
            'reg_alpha'         :       0,
            'scale_pos_weight'  :       5.39673009847897,
            'min_child_weight'  :       12.14694715535773,
            'base_score'        :       0.9698413679536542
            }
L1_params = {
            'C'                 :       scipy.stats.expon(0, 0.0000005),
            'intercept_scaling' :       scipy.stats.expon(0, 0.01)
            }
estimates, predictions, _, shuffled_y, _ = generalized_CV('Stack', l0Clf,
                                            golden_params, 1, kfcv, X_train,
                                            y_train, X_test)
kfcv1 = StratifiedKFold(shuffled_y, n_folds=5, shuffle=True)
while True:
    new_estimates, new_predictions, _, _, _ = L0_classification(l0Clf,
                                                golden_params, X_train, y_train,
                                                X_test, kfcv, 10)
    estimates = pd.concat([estimates, new_estimates], axis=1, ignore_index=True)
    predictions = pd.concat([predictions, new_predictions], axis=1,
                            ignore_index=True)
    write(estimates, y_train, predictions, id_test, 'Level1Data', 'Xtrain.csv',
                'Xtest.csv', 'ytrain.csv', 'idtest.csv', target_col, id_col)
    best_estimator, master_cols, score = L1_aggregation(l1Clf, L1_params,
                                                estimates, shuffled_y,
                                                predictions,
                                                kfcv1, 25)
    if score > record_score:
        prep_submission(best_estimator, estimates, master_cols, shuffled_y,
                        predictions, id_test, 'submission.csv', target_col,
                        id_col, score)
        record_score = score
