#!/usr/bin/env python
# coding: utf-8
''' apexlog
Script to summarise APEX html observing logs.
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import with_statement
import argparse
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
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
    elif not cat.endswith('.cat'):
        cat = cat + '.cat'

    print('Reading science sources from:', cat)
    with open(cat) as f:
        s = f.readlines()
    for line in s:
        if ((line[0] != '!') & (line[0] != '\n') & (line[0] != ' ')):
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
    elif not cat.endswith('.lin'):
        cat = cat + '.lin'

    print('Reading science lines from:', cat)
    with open(cat) as f:
        s = f.readlines()
    for line in s:
        if ((line[0] != '!') & (line[0] != '\n') & (line[0] != ' ')):
            sci_lines.append(line.split()[0])
            sci_freqs.append(float(line.split()[1]))
    sci_lines = dict(zip(sci_lines, sci_freqs))
    return sci_lines


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
    df.drop(df[(df.Source == 'PARK') | (df.Source == 'ZENITH')].index,
            inplace=True)
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
    df['Line'] = df['Mol. line'].apply(get_line_name)
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
        List or dictionary of science lines
    df : pandas.DataFrame
        The obslog data

    Returns
    -------
    dfs : pandas.DataFrame
        Summary of scan duration [min] for sources/lines
    '''

    print('\nSummarising scan duration by science sources/lines:')
    on_types = ['ONOFF', 'OTF']
    dfs = pd.DataFrame(df[df.source.isin(sci_sources)
                          & df.line.isin(sci_lines)
                          & df.scan_type.isin(on_types)
                          ]
                       )
    dfs = dfs.groupby(['source', 'line'])[['scan_duration']].sum()
    dfs['Duration [min]'] = (dfs['scan_duration'] /
                             np.timedelta64(1, 'm')).round(1)
    return dfs[['Duration [min]']]


def parse_inputs():
    '''Parse optional catalogs and obslogs dir'''
    parser = argparse.ArgumentParser(
        description='Summarises APEX obslogs, defaults to APEX account')
    parser.add_argument('-c', '--catalogs', type=str,
                        help='Location/basename of source and line catalogs')
    parser.add_argument('-o', '--obslogs', type=str,
                        help='Location of html obslogs')
    args = parser.parse_args()
    return args.catalogs, args.obslogs


def plot_dfs(dfs):
    dfs[['Duration [min]']].iloc[::-1].plot.barh(zorder=2, legend=False)
    plt.grid(zorder=0)
    plt.title('Sum of "ON" science source/line scan duration')
    plt.xlabel('Duration [min]')
    plt.savefig('dfs.png', bbox_inches='tight')
    print('\nCreated plot: ./apexlog.png')
    return plt.gcf()


def plot_apexlog(sci_sources, sci_lines, df, dfs, eso_id):
    a = 2
    on_types = ['ONOFF', 'OTF']
    science = pd.DataFrame(df[df.source.isin(sci_sources)
                              & df.line.isin(sci_lines)
                              & df.scan_type.isin(on_types)
                              ]
                           )
    pwv = science.groupby(['source', 'line']).mm_pwv.describe()
    pwv = pwv[['mean', 'std']].round(2)

    fig = plt.figure(1, figsize=(a * 6.4, a * 4.8))
    gs = gridspec.GridSpec(2, 4, height_ratios=[3, 1],
                           width_ratios=[0.25, 0.25, 0.25, 0.25])

    gs.update(left=0.1, right=0.95, bottom=0.08,
              top=0.90, wspace=0., hspace=0.2)

    now = pd.datetime.utcnow()
    header = eso_id + ' by ' + now.strftime('%Y-%m-%d')
    fig.text(0.5, 0.93, header,
             ha='center', va='bottom', fontsize=12, weight='bold')
    ax1 = plt.subplot(gs[0, :])
    ax2 = plt.subplot(gs[1, :-1])
    ax3 = plt.subplot(gs[1, -1], sharey=ax2)
    dfs[['Duration [min]']].iloc[::-1].plot.barh(zorder=2, legend=False,
                                                 ax=ax1)
    df.loc[df.mm_pwv <= 0, 'mm_pwv'] = np.nan
    df.set_index('utc', inplace=True)
    df.mm_pwv.plot(style='o', mfc='none', mew=1, ax=ax2)
    df.reset_index(inplace=True)
    df.mm_pwv.plot.hist(bins=np.arange(0, df.mm_pwv.max(), 0.01),
                        cumulative=True, density=True,
                        orientation='horizontal')

    ax1.set_title('Sum of "ON" source scan duration by science source/line')
    ax1.set_xlabel('Duration [min]')
    ax1.set_ylabel('')
    ax2.set_ylabel('PWV [mm]')
    ax2.set_xlabel('')
    for ax in [ax1, ax2, ax3]:
        ax.grid()
    return fig


def main():
    plt.close('all')
    catalogs, obslogs = parse_inputs()
    if (catalogs is None) & (obslogs is None):
        eso_id = getuser()
        print('\033[1;32mDefaulting to APEX account:',
              '~/' + getuser() + '.[cat/lin] and ~/obslogs/\033[0m')
    else:
        eso_id = catalogs.split('/')[-1]
    sci_sources = read_sourcecat(catalogs)
    sci_lines = read_linecat(catalogs)
    df = read_obslogs(obslogs)
    dfs = summarise_sciobs(sci_sources, sci_lines, df)
    print(dfs)
    # plot_dfs(dfs)
    fig = plot_apexlog(sci_sources, sci_lines, df, dfs, eso_id.upper())
    fig.savefig('apexlog.png', bbox_inches='tight', dpi=120)
    df.to_csv('apexlog.csv')
    return sci_sources, sci_lines, df, dfs, fig


if __name__ == '__main__':
    sci_sources, sci_lines, df, dfs, fig = main()
