#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

def load_data(train_file, test_file):
    '''
    Takes as input:
        train_file: the training csv data filename
        train_file: the test csv data filename
    What it does:
        makes use of the pandas read_csv method to convert the csv data to
        pandas dataframes
    Returns:
        training data DataFrame
        test data DataFrame
        '''
    return pd.read_csv(train_file), pd.read_csv(test_file)

def zap_empties(train, test):
    '''
    Takes as input:
        train: the training factor data in the form a pandas DataFrame
        test: the test factor data in the form a pandas DataFrame
    What it does:
        finds all columns in the training factor data where the standard
        deviation is zero. This implies those columns are constant in the
        training factor data and therefore cannot be used for learning. The
        columns are removed from both the training and test factor data
    Returns:
        training data DataFrame
        test data DataFrame
        '''
    sd = train.std()
    empties = sd[sd==0.0].index
    return train.drop(empties,1), test.drop(empties,1)

def zap_dependencies(train, test, verbose):
    '''
    Takes as input:
        train: the training factor data in the form a pandas DataFrame
        test: the test factor data in the form a pandas DataFrame
        verbose: if TRUE then prints out dependent column names
    What it does:
        Converts the training factor data to a numpy matrix then performs a QR
        decomposition on it. Dependent columns are identified as all those that
        do not have pivots (i.e., are within a certain tolerence of zero where
        the pivot should be). These columns are then removed from the training
        and test factor data
    Returns:
        training data DataFrame
        test data DataFrame
    '''
    dependencies = []
    feature_cols = train.columns
    Q, R = np.linalg.qr(np.matrix(train))
    indep_locs = np.where(abs(R.diagonal())>1e-7)[1]
    for i, col in enumerate(feature_cols):
        if i not in indep_locs:
            dependencies.append(col)
            if verbose:
                print col
    return train.drop(dependencies,1), test.drop(dependencies,1)

def num_to_card(train, test, frac0=0.5):
    '''
    Takes as input:
        train: the training factor data in the form a pandas DataFrame
        test: the test factor data in the form a pandas DataFrame
        frac0: the fraction of values that are 0 in a feature colums
    What it does:
        Determines the fraction of values in a data column that are equal to
        zero. If this fraction is higher than that given by frac0, then all
        positive values are set to 1 and all negative values to -1
    Why are we doing this?
        It seems that many of the columns are mostly zero. This seems to imply
        that the fact that a value is other than zero is more important than
        the quantitative value itself.
    Returns:
        training data DataFrame
        test data DataFrame
    '''
    feature_cols = train.columns
    points = train.shape[0]
    for col in feature_cols:
        if (train[col]==0).sum() > 0.5*points:
            train.loc[train[col]>0, col] = 1
            train.loc[train[col]<0, col] = -1
            test.loc[test[col]>0, col] = 1
            test.loc[test[col]<0, col] = -1
    return train, test

def acquire_data(train_file, test_file, target_col, id_col, verbose=False):
    '''
    Takes as input:
        train: the training data in the form a pandas DataFrame
        test: the test data in the form a pandas DataFrame
        target_col: the name of the target (output) column
        id_col: the name of the ID column
        verbose: fed to zyp_dependencies function
    What it does:
        Calls upon helper functions to read in and manipulate data. Splits
        the train and test data into X and y groupings
    Returns:
        training data features
        training data labels
        test data features
        test data IDs
    '''
    df_train, df_test = load_data(train_file, test_file)
    feature_cols = df_train.columns.difference([target_col, id_col])
    y_train = df_train[target_col]
    id_test = df_test[id_col]
    X_train, X_test = df_train[feature_cols], df_test[feature_cols]
    X_train, X_test = zap_empties(X_train, X_test)
    X_train, X_test = zap_dependencies(X_train, X_test, verbose)
    X_train, X_test = num_to_card(X_train, X_test)
    X_train, X_test = zap_dependencies(X_train, X_test, verbose)
    return X_train, y_train, X_test, id_test


target_col = 'TARGET'
id_col = 'ID'

X_train, y_train, X_test, id_test = acquire_data('train.csv', 'test.csv',
                                    target_col, id_col, verbose=True)

X_train.to_csv('./EngineeredData/Xtrain.csv', index=False)
pd.DataFrame({target_col:y_train}).to_csv('./EngineeredData/ytrain.csv',
                index=False)
X_test.to_csv('./EngineeredData/Xtest.csv', index=False)
pd.DataFrame({id_col:id_test}).to_csv('./EngineeredData/idtest.csv',
                index=False)
