from __future__ import (absolute_import, division, with_statement,
                        print_function, unicode_literals)
import pandas as pd


def read_sourcecat(cat=None):
    """Parse APEX source catalogue (.cat)

    Parameters
    ----------
    cat : string (optional)
        name of source catalogue, defaults to ~/'user'.cat

    Returns
    -------
    sci_sources : list
        Names of science sources
    """

    sci_sources = []

    if cat is None:
        from os.path import expanduser
        from getpass import getuser
        cat = expanduser("~/") + getuser() + ".cat"

    # print("Reading science sources from:", cat)
    with open(cat) as f:
        s = f.readlines()

    for line in s:
        if ((line[0] != "!") & (line[0] != "\n")):
            sci_sources.append(line.split()[0])
    return sci_sources


def read_linecat(cat=None):
    """Parse APEX line cat .lin

    Parameters
    ----------
    cat : string (optional)
        name of line catalogue, defaults to ~/'user'.lin

    Returns
    -------
    sci_lines : dict
        Dictionary of science lines / frequencies
    """
    sci_lines = []
    sci_freqs = []

    if cat is None:
        from os.path import expanduser
        from getpass import getuser
        cat = expanduser("~/") + getuser() + ".lin"

    # print("Reading science lines from:", cat)
    with open(cat) as f:
        s = f.readlines()

    for line in s:
        if ((line[0] != "!") & (line[0] != "\n")):
            sci_lines.append(line.split()[0])
            sci_freqs.append(float(line.split()[1]))
    sci_lines = dict(zip(sci_lines, sci_freqs))
    return sci_lines


def read_one(filename):
    """Read a html obslog to pandas DataFrame

    Parameters
    ----------
    filename : string
        obslog html file

    Returns
    -------
    df : pandas.DataFrame
        The obslog data
    """

    import pandas as pd
    df = pd.read_html(filename, header=0)[0]
    df.set_index("Scan")
    df['UTC'] = pd.to_datetime(df.UTC, format='%Y-%m-%dU%H:%M:%S')
    df["Scan duration"] = pd.to_timedelta(df["Scan duration"], unit="s")
    return df


def get_line(string):
    """Get first white spaced deliminated part of string"""
    return string.split()[0]


def read_obslogs(dir=None):
    """Read APEX html obslogs

    Parameters
    ----------
    dir : string (optional)
        Directory with html log files, defaults to ~/obslogs/

    Returns
    -------
    df : pandas.DataFrame
        The obslog data
    """

    import pandas as pd
    from os.path import expanduser
    from glob import glob

    if dir is None:
        dir = expanduser("~/obslogs/")

    logs = glob(dir + "*.html")

    # print("Reading obslogs:", logs)
    df = read_one(logs[0])
    for log in logs[1:]:
        df = pd.concat([df, read_one(log)], axis=0)
    df.sort_index(inplace=True)
    df["Line"] = df["Mol. line"].apply(get_line)
    return df


def summarise_sciobs(sci_sources, sci_lines, df):
    """Summarise science observations in DataFrame

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
    """

    from numpy import timedelta64

    # print("Summarizing scan duration by:", sci_sources, sci_lines)
    dfs = df[(df.Source.isin(sci_sources)) & (df.Line.isin(sci_lines))]
    dfs = dfs.groupby(["Source", "Line"])[["Scan duration"]].sum()
    dfs.sort_values("Scan duration", ascending=False, inplace=True)
    dfs["Duration [min]"] = (dfs["Scan duration"] /
                             timedelta64(1, 'm')).round(1)
    return dfs[["Duration [min]"]]


def main():
    sci_sources = read_sourcecat()
    sci_lines = read_linecat()
    df = read_obslogs()
    dfs = summarise_sciobs(sci_sources, sci_lines, df)
    return sci_sources, sci_lines, df, dfs


if __name__ == "__main__":
    sci_sources, sci_lines, df, dfs = main()
    print(dfs)
    df.set_index("UTC", inplace=True)
    df.sort_index(inplace=True)
    # date = str(pd.datetime.utcnow().date())
    # today = pd.DataFrame(df[df.Source.isin(sci_sources) &
    #                         df.Line.isin(sci_lines)][date])
    # print("\n", date, today["Scan duration"].sum())
    # print('Observed: ' + date)
    # print(today.Source.value_counts())
    sci_types = ['CAL', 'ONOFF', 'OTF', 'RASTER']
    sci = pd.DataFrame(df[df.Source.isin(sci_sources) &
                          df.Line.isin(sci_lines) &
                          df['Scan type'].isin(sci_types)])
    print(sci.groupby(sci.index.date).Source.unique())

    # May need to get rid of any cancelled scans
    sci.to_csv('Betelgeuse_scans.dat', index=False,
               columns=['Scan'], header=False)

    sci['date'] = sci.index.date.astype('str')
    for date in sci.date.unique():
        # print(date)
        sci[date].to_csv('Betelgeuse_' + str(date) + '_scans.dat',
                         index=False, columns=['Scan'], header=False)
