import scraper
import pandas as pd
from tqdm import tqdm
from sklearn.externals import joblib


def get_past(df_all, timestamp):
    return df_all[df_all.DateTimestamp < timestamp]


def get_player(df_all, player):
    return df_all[df_all.Player == player]


def clean_skater_data(df_skaters):
    df_skaters = df_skaters.drop('URL', 1)
    toi = df_skaters.TOI
    numtoi = []
    for t in toi:
        n = t.split(":")
        time = int(n[0]) * 60 + int(n[1])
        numtoi.append(time)
    df_skaters.TOI = numtoi
    return df_skaters


def get_teammates(pg, df_skaters):
    df = df_skaters[df_skaters.GameName == pg.GameName]
    df = df[df.Home == pg.Home]
    df = df[df.Player != pg.Player]
    return list(df.Player)


def get_opponents(pg, df_skaters):
    df = df_skaters[df_skaters.GameName == pg.GameName]
    df = df[df.Home != pg.Home]
    return list(df.Player)


def get_team_stats():
    return 0
    # Target team season stats
    # # teammates = get_teammates(cur, df_skaters)
    # # tm_goalspergame = 0
    # # tm_shotspergame = 0
    # # for teammate in teammates:
    # #     df_tm_past = get_player(df_past, teammate)
    # #     df_tm_past = df_tm_past.drop(drops, 1)
    # #     sums = df_tm_past.sum(axis=0)
    # #     tm_goalspergame += sums['G']
    # #     tm_shotspergame += sums['S']
    # tm_goalspergame = tm_goalspergame / num
    # tm_shotspergame = tm_shotspergame / num


SKATER_COLS = ['GameNum', 'GameName', 'Player', 'DateTimestamp', 'Num', 'GNum',
               'O_Goals', 'O_Assists', 'O_Blocks', 'O_Shorthanded', 'O_Shots',
               'TS_Goals', 'TS_Assists', 'TS_PlusMinus', 'TS_SoG',
               'TS_Shot%', 'TS_ATOI', 'TS_iCF', 'TS_SATF', 'TS_SATA',
               'TS_ZSO', 'TS_HIT', 'TS_BLK',
               'TM_Goals', 'Opp_GA',
               'Opp_SA', 'Opp_SV%']


def get_skater_feat(cur, df_skaters, df_goalies, df_overall):
    timestamp = cur.DateTimestamp

    # All past playergames
    df_past = get_past(df_skaters, timestamp)

    # Season stats for target player
    df_past_t = get_player(df_past, cur.Player)
    drops = ['DateTimestamp', 'Player', 'Home',
             'Team', 'GameName', 'S%']
    df_past_t = df_past_t.drop(drops, 1)
    num = len(df_past_t)
    df_t_sums = df_past_t.sum(axis=0)

    t_goals = df_t_sums['G'] / num
    t_assists = df_t_sums['A'] / num
    t_plus_minus = df_t_sums['+/-']
    t_shots = df_t_sums['S'] / num
    t_iCF = df_t_sums['iCF'] / num
    t_SATF = df_t_sums['SATF'] / num
    t_SATA = df_t_sums['SATA'] / num
    t_ZSO = df_t_sums['ZSO'] / num
    t_hit = df_t_sums['HIT'] / num
    t_blk = df_t_sums['BLK'] / num
    t_atoi = df_t_sums['TOI'] / num
    if(t_shots > 0):
        t_shoot_percentage = t_goals / t_shots
    else:
        t_shoot_percentage = 0

    df_overall_past = get_past(df_overall, timestamp)
    df1 = df_overall_past[df_overall_past.Home == cur.Team]
    goals_home = df1.sum(axis=0)['G.1']
    df2 = df_overall_past[df_overall_past.Visitor == cur.Team]
    goals_away = df2.sum(axis=0)['G']
    tm_goalspergame = (goals_away + goals_home) / (len(df1) + len(df2))

    df = df_goalies[df_goalies.GameName == cur.GameName]
    opp_goalie = list(df[df.Home != cur.Home].Player)[0]

    df_past_goalie = get_past(df_goalies, timestamp)
    df_opp_goalie = df_past_goalie[df_past_goalie.Player == opp_goalie]
    g_num = len(df_opp_goalie)

    opp_goalies_sums = df_opp_goalie.sum(axis=0)
    opp_ga = opp_goalies_sums['GA'] / g_num
    opp_sa = opp_goalies_sums['SA'] / g_num
    opp_svpercentage = 1 - (opp_ga / opp_sa)

    out_goals = cur['G']
    out_assists = cur['A']
    out_blks = cur['BLK']
    out_short = cur['SH'] + cur['A_SH']
    out_shots = cur['S']

    cur_features = [cur.GameNum, cur.GameName, cur.Player, timestamp, num, g_num,
                    out_goals, out_assists, out_blks, out_short, out_shots,
                    t_goals, t_assists, t_plus_minus, t_shots,
                    t_shoot_percentage, t_atoi, t_iCF,
                    t_SATF, t_SATA, t_ZSO, t_hit, t_blk, tm_goalspergame,
                    opp_ga, opp_sa, opp_svpercentage]

    return cur_features


def get_cleaned_data(raw_s, raw_g, raw_o):
    df_skaters = clean_skater_data(raw_s)
    df_skaters = df_skaters.sort_values('GameNum', ascending=True)
    df_goalies = raw_g.sort_values('GameNum', ascending=True)
    df_overall = raw_o.sort_values('GameNum')
    return df_skaters, df_goalies, df_overall


def get_skater_data(season=2015):
    raw_s = scraper.get_raw_skatergames_df(season)
    raw_g = scraper.get_raw_goaliegames_df(season)
    raw_o = scraper.get_raw_overallgames_df(season)
    df_s, df_g, df_o = get_cleaned_data(raw_s, raw_g, raw_o)

    X = pd.DataFrame(columns=SKATER_COLS)
    for index in tqdm(range(len(df_s) // 2, len(df_s))):
        cur = df_s.iloc[index]
        cur_features = get_skater_feat(cur, df_s, df_g, df_o)
        X.loc[index] = cur_features

    return X


def build_skater_data(fn, season):
    X = get_skater_data(season)
    joblib.dump(X, fn)
