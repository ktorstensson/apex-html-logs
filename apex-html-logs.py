#!/usr/bin/env python
# coding: utf-8
''' apex-html-logs.py
Script to summarise APEX html observing logs.
ktorsten@eso.org
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import with_statement
import argparse
import numpy as np
import pandas as pd
import re
from os.path import expanduser
from getpass import getuser
from glob import glob


def read_one_log(filename):
    '''Read a html obslog to pandas DataFrame

    Parameters
    ----------
    filename : string
        obslog html file

    Returns
    -------
    df : pandas.DataFrame
        The obslog data
    '''

    print('Reading obslog:', filename)
    df = pd.read_html(filename, header=0)[0]
    df['UTC'] = pd.to_datetime(df.UTC, format='%Y-%m-%dU%H:%M:%S')
    cancelled = df[df['Scan duration'] == -999]
    df.loc[cancelled.index, 'Scan duration'] = 0
    df['Scan duration'] = pd.to_timedelta(df['Scan duration'], unit='s')
    df['mm PWV'] = df[['mm PWV']].astype(str)
    df.drop(df[df.Source.isin(['PARK', 'ZENITH', 'RECYCLE', 'RECYCLING']) |
               (df['mm PWV'] == 'Shutter closed')].index, inplace=True)
    df['mm PWV'] = df[['mm PWV']].apply(pd.to_numeric)
    return df


def get_line_name(string):
    '''Get first white spaced delimited part of string'''
    return string.split()[0]


def read_obslogs(dir=None):
    '''Read APEX html obslogs

    Parameters
    ----------
    dir : string (optional)
        Directory with html log files, defaults to ~/obslogs/

    Returns
    -------
    df : pandas.DataFrame
        The obslog data
    '''

    if dir is None:
        dir = expanduser('~/obslogs/')
    logs = glob(dir + '*.html')

    print('')
    df = read_one_log(logs[0])
    for log in logs[1:]:
        df = pd.concat([df, read_one_log(log)], axis=0)
    df['Line'] = df['Mol. line'].apply(lambda x: x.split()[0])
    df.rename(columns=(lambda x: re.sub('[().]', '', x)), inplace=True)
    df.rename(columns=(lambda x: re.sub('[ -]', '_', x)), inplace=True)
    df.rename(columns=(lambda x: x.lower()), inplace=True)
    df.set_index('utc', inplace=True)
    df.sort_index(inplace=True)
    df.reset_index(inplace=True)
    return df


def parse_inputs():
    '''Parse optional catalogs and obslogs dir'''
    parser = argparse.ArgumentParser(description='Summarises APEX html obslogs')
    parser.add_argument('-s', '--source', type=str,
                        help='Source name')
    args = parser.parse_args()
    return args.source


def main():
    source = parse_inputs()
    df = read_obslogs(dir=None)
    if source is None:
        dfs = df.groupby(['scan_status', 'source', 'line'])[['scan_duration']].sum()
    else:
        dfs = df[df.source == source].groupby(['scan_status', 'line'])[['scan_duration']].sum()
    
    print(dfs)
    return df, dfs


if __name__ == '__main__':
    df, dfs = main()

