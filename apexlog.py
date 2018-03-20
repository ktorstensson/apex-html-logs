#!/usr/bin/env python
# coding: utf-8
''' apexlog.py
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import with_statement
import argparse
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re
from os.path import expanduser
from getpass import getuser
from glob import glob


def read_sourcecat(cat=None):
    '''Parse APEX source catalogue (.cat)

    Parameters
    ----------
    cat : string (optional)
        name of source catalogue, defaults to ~/'user'.cat

    Returns
    -------
    sci_sources : list
        Names of science sources
    '''

    sci_sources = []
    if cat is None:
        cat = expanduser('~/') + getuser() + '.cat'
    elif ~cat.endswith('.cat'):
        cat = cat + '.cat'
    # print("Reading science sources from:", cat)
    with open(cat) as f:
        s = f.readlines()
    for line in s:
        if ((line[0] != '!') & (line[0] != '\n')):
            sci_sources.append(line.split()[0])
    return sci_sources


def read_linecat(cat=None):
    '''Parse APEX line cat .lin

    Parameters
    ----------
    cat : string (optional)
        name of line catalogue, defaults to ~/'user'.lin

    Returns
    -------
    sci_lines : dict
        Dictionary of science lines / frequencies
    '''
    sci_lines = []
    sci_freqs = []
    if cat is None:
        cat = expanduser('~/') + getuser() + '.lin'
    elif ~cat.endswith('.lin'):
        cat = cat + '.lin'
    # print("Reading science lines from:", cat)
    with open(cat) as f:
        s = f.readlines()
    for line in s:
        if ((line[0] != '!') & (line[0] != '\n')):
            sci_lines.append(line.split()[0])
            sci_freqs.append(float(line.split()[1]))
    sci_lines = dict(zip(sci_lines, sci_freqs))
    return sci_lines


def read_one(filename):
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

    df = pd.read_html(filename, header=0)[0]
    # df.set_index("Scan")
    df['UTC'] = pd.to_datetime(df.UTC, format='%Y-%m-%dU%H:%M:%S')
    df['Scan duration'] = pd.to_timedelta(df['Scan duration'], unit='s')
    return df


def get_line(string):
    '''Get first white spaced deliminated part of string'''
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

    # print("Reading obslogs:", logs)
    df = read_one(logs[0])
    for log in logs[1:]:
        df = pd.concat([df, read_one(log)], axis=0)
    df['Line'] = df['Mol. line'].apply(get_line)
    df.rename(columns=(lambda x: re.sub('[().]', '', x)), inplace=True)
    df.rename(columns=(lambda x: re.sub('[ -]', '_', x)), inplace=True)
    df.rename(columns=(lambda x: x.lower()), inplace=True)
    df.set_index('utc', inplace=True)
    df.sort_index(inplace=True)
    df.reset_index(inplace=True)
    return df


def summarise_sciobs(sci_sources, sci_lines, df):
    '''Summarise science observations in DataFrame

    Parameters
    ----------
    sci_sources : list
        List of science sources
    sci_lines : list/dict
        List or dicttionary of science lines
    df : pandas.DataFrame
        The obslog data

    Returns
    -------
    dfs : pandas.DataFrame
        Summary of scan duration [min] for sources/lines
    '''

    # print("Summarizing scan duration by:", sci_sources, sci_lines)
    on_types = ['ONOFF', 'OTF']
    dfs = pd.DataFrame(df[df.source.isin(sci_sources)
                          & df.line.isin(sci_lines)
                          & df.scan_type.isin(on_types)
                          ]
                       )
    dfs = dfs.groupby(['source', 'line'])[['scan_duration']].sum()
    # dfs.sort_values('scan_duration', ascending=False, inplace=True)
    dfs['Duration [min]'] = (dfs['scan_duration'] /
                             np.timedelta64(1, 'm')).round(1)
    return dfs[['Duration [min]']]


def parse_inputs():
    '''Parse optinal catalogs and obslogs dir'''
    parser = argparse.ArgumentParser(
        description='Summarises APEX obslogs, defaults to APEX account')
    parser.add_argument('-c', '--catalogs', type=str,
                        help='Location/basename of source and line catalogs')
    parser.add_argument('-o', '--obslogs', type=str,
                        help='Location of html obslogs')
    args = parser.parse_args()
    return args.catalogs, args.obslogs


def plot_dfs(dfs):
    dfs[['Duration [min]']].plot.barh(zorder=2, legend=False)
    plt.grid(zorder=0)
    plt.title('Sum of "ON" science source/line scan duration')
    plt.xlabel('Duration [min]')
    plt.savefig('apexlog.png', bbox_inches='tight')
    print('Created plot: ./apexlog.png')
    return plt.gcf()


def main():
    catalogs, obslogs = parse_inputs()
    if (catalogs is None) & (obslogs is None):
        print('\033[1;32mDefaulting to APEX account:',
              '~/' + getuser() + '.[cat/lin] and ~/obslogs/\033[0m')
    sci_sources = read_sourcecat(catalogs)
    sci_lines = read_linecat(catalogs)
    df = read_obslogs(obslogs)
    dfs = summarise_sciobs(sci_sources, sci_lines, df)
    # print(dfs.sort_values(by='Duration [min]', ascending=False))
    print(dfs)
    fig = plot_dfs(dfs)
    return sci_sources, sci_lines, df, dfs


if __name__ == '__main__':
    sci_sources, sci_lines, df, dfs = main()

    # # date = str(pd.datetime.utcnow().date())
    # # today = pd.DataFrame(df[(df.Source.isin(sci_sources))
    # #                      & (df.Line.isin(sci_lines))][date])
    # # print("\n", date, today["Scan duration"].sum())
    # # print('Observed: ' + date)
    # # print(today.Source.value_counts())
    # df.set_index('utc', inplace=True)
    # sci = pd.DataFrame(df[(df.source.isin(sci_sources))
    #                       & (df.line.isin(sci_lines))])
    # print(sci.groupby(sci.index.date).source.unique())
