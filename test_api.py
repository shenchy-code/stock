import requests
import time

def test_ranking_api():
    # 天天基金排行 API
    url = "http://fund.eastmoney.com/data/rankhandler.aspx"
    # 简化参数
    params = {
        'op': 'ph',
        'dt': 'kf',
        'ft': 'all',
        'rs': '',
        'gs': '0',
        'sc': '1nzf', # 1年涨幅
        'st': 'desc',
        'pi': '1',
        'pn': '10',
        'dx': '1'
    }
    
    headers = {
        'Referer': 'http://fund.eastmoney.com/data/fundranking.html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        resp = requests.get(url, params=params, headers=headers)
        print("Ranking Status:", resp.status_code)
        print("Ranking Content Length:", len(resp.text))
        print("Ranking Content Preview:", resp.text[:200])
    except Exception as e:
        print("Ranking Error:", e)

def test_money_flow_api():
    # 尝试获取行业或ETF资金流向
    # 东方财富行业资金流向
    url = "http://push2.eastmoney.com/api/qt/clist/get"
    params = {
        'pn': '1',
        'pz': '10',
        'po': '1',
        'np': '1',
        'fltt': '2',
        'invt': '2',
        'fid': 'f62', # f62 是主力净流入
        'fs': 'm:90 t:2 f:!50', # 行业板块
        'fields': 'f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13'
    }
    # f12: code, f14: name, f2: price, f3: change%, f62: main_flow (主力净流入)
    
    try:
        resp = requests.get(url, params=params)
        print("\nMoney Flow Status:", resp.status_code)
        data = resp.json()
        print("Money Flow Data:", data['data']['diff'][0] if data.get('data') and data['data'].get('diff') else "No data")
    except Exception as e:
        print("Money Flow Error:", e)

if __name__ == "__main__":
    test_ranking_api()
    test_money_flow_api()
