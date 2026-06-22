"""
基金&股票监控系统 - 后服务
数据来源：天天基金网（eastmoney.com? 东方财富
"""
import json
import os
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from strategy_service import build_strategy_report, parse_float
from theme_service import build_theme_signals

app = Flask(__name__, static_folder='static')
CORS(app)

# 获取当前文件在目
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据存储文件
DATA_FILE = os.path.join(BASE_DIR, 'funds_data.json')

# 创建线程池用于并发
executor = ThreadPoolExecutor(max_workers=10)

# 全局 HTTP 会话：复用 TCP 连接，减少握手开销（不缓存任何响应数据）
http = requests.Session()
_adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
http.mount('http://', _adapter)
http.mount('https://', _adapter)

def load_data():
    """加载朜保存的基金和股票列表"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 兼旧数捻构，硿有stocks字
            if 'stocks' not in data:
                data['stocks'] = []
            return data
    return {"funds": [], "stocks": [], "last_update": None}

# 保持向后兼的别
def load_funds():
    return load_data()

def save_data(data):
    """保存基金和股票列表到朜"""
    data['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 硿有stocks字
    if 'stocks' not in data:
        data['stocks'] = []
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 保持向后兼的别
def save_funds(data):
    save_data(data)

def safe_float(value):
    """安全轍为浮点数"""
    try:
        if value == '--' or value == '' or value is None:
            return None
        return float(value)
    except:
        return None

def get_trading_advice(fund_data, all_funds):
    """
    分析基金数据，给出买?持有/卖出建
    返回: {'action': 'buy'|'hold'|'sell', 'score': 分数, 'reason': '原因', 'text': '显示文字'}
    """
    score = 50  # 基准50
    reasons = []
    
    # 1. 当日表现分析 (权重30?
    today_change = safe_float(fund_data.get('estimate_change', 0))
    if today_change is not None:
        if today_change > 3:
            score += 15
            reasons.append('今日大涨')
        elif today_change > 1:
            score += 10
            reasons.append('今日上涨')
        elif today_change > 0:
            score += 5
            reasons.append('今日徶')
        elif today_change < -3:
            score -= 15
            reasons.append('今日大跌')
        elif today_change < -1:
            score -= 10
            reasons.append('今日下跌')
        elif today_change < 0:
            score -= 5
            reasons.append('今日德')
    
    # 2. 近期趋势分析 (权重40?
    week = safe_float(fund_data.get('week_growth'))
    if week is not None:
        if week > 3:
            score += 12
            reasons.append('周线强势')
        elif week < -3:
            score -= 12
            reasons.append('周线走弱')
    
    month = safe_float(fund_data.get('month_growth'))
    if month is not None:
        if month > 5:
            score += 15
            reasons.append('月线强势')
        elif month > 2:
            score += 8
            reasons.append('月线上涨')
        elif month < -5:
            score -= 15
            reasons.append('月线走弱')
        elif month < -2:
            score -= 8
            reasons.append('月线下跌')
    
    three_month = safe_float(fund_data.get('three_month_growth'))
    if three_month is not None:
        if three_month > 10:
            score += 13
            reasons.append('季线优')
        elif three_month < -10:
            score -= 13
            reasons.append('季线疲软')
    
    # 3. 长期表现分析 (权重20?
    year = safe_float(fund_data.get('year_growth'))
    if year is not None:
        if year > 20:
            score += 15
            reasons.append('年度收益优')
        elif year > 10:
            score += 10
            reasons.append('年度收益艥')
        elif year > 0:
            score += 5
            reasons.append('年度正收?')
        elif year < -15:
            score -= 15
            reasons.append('年度亏损严重')
        elif year < 0:
            score -= 5
            reasons.append('年度负收?')
    
    # 4. 相排名分析 (权重10?
    if all_funds and len(all_funds) > 1:
        valid_funds = [f for f in all_funds if f.get('success') and safe_float(f.get('estimate_change')) is not None]
        if valid_funds:
            changes = [safe_float(f.get('estimate_change')) for f in valid_funds]
            changes.sort(reverse=True)
            current_change = safe_float(fund_data.get('estimate_change'))
            if current_change is not None:
                rank_position = changes.index(current_change) / len(changes) if current_change in changes else 0.5
                if rank_position <= 0.3:
                    score += 10
                    reasons.append('持仓排名前列')
                elif rank_position >= 0.7:
                    score -= 10
                    reasons.append('持仓排名靠后')
    
    # 硿分数?-100之间
    score = max(0, min(100, score))
    
    # 判断建
    if score >= 70:
        action = 'buy'
        text = '买入'
        icon = '🟢'
    elif score >= 45:
        action = 'hold'
        text = '持有'
        icon = '🟡'
    else:
        action = 'sell'
        text = '卖出'
        icon = '🔴'
    
    # 组合原因说明
    reason_text = '、'.join(reasons[:3]) if reasons else '数据不足'
    
    return {
        'action': action,
        'score': score,
        'text': text,
        'icon': icon,
        'reason': reason_text
    }

def fetch_fund_info(fund_code):
    """
    从天天基金网获取基金实时数据
    接口来源：天天基金网 (fund.eastmoney.com)
    """
    try:
        # 天天基金网实时估值接
        url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js"
        headers = {
            'Referer': 'https://fund.eastmoney.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = http.get(url, headers=headers, timeout=5)
        response.encoding = 'utf-8'

        if response.status_code == 200 and 'jsonpgz' in response.text:
            # 解析 JSONP 格式: jsonpgz({...});
            json_str = response.text.replace('jsonpgz(', '').rstrip(');')
            data = json.loads(json_str)

            # 获取基金详细信息
            detail_info = fetch_fund_detail(fund_code)
            official_nav = fetch_latest_official_nav(fund_code)

            return {
                'code': data.get('fundcode', fund_code),
                'name': data.get('name', '期基金'),
                'nav': official_nav.get('nav') or data.get('dwjz', '--'),           # 单位净值
                'estimate_nav': data.get('gsz', '--'),   # 估算净值
                'estimate_change': data.get('gszzl', '--'),  # 估算涨跌幅
                'nav_date': official_nav.get('nav_date') or data.get('jzrq', '--'),      # 净值日期
                'estimate_time': data.get('gztime', '--'),  # 估算时间
                'success': True,
                # 新详细数据
                'fund_type': detail_info.get('fund_type', '--'),
                'company': detail_info.get('company', '--'),
                'day_growth': official_nav.get('day_growth') or detail_info.get('day_growth', '--'),
                'week_growth': detail_info.get('week_growth', '--'),
                'month_growth': detail_info.get('month_growth', '--'),
                'three_month_growth': detail_info.get('three_month_growth', '--'),
                'six_month_growth': detail_info.get('six_month_growth', '--'),
                'year_growth': detail_info.get('year_growth', '--'),
                'total_growth': detail_info.get('total_growth', '--'),
                'manager': detail_info.get('manager', '--')
            }
        else:
            # 尝试获取基金基本信息
            return fetch_fund_basic_info(fund_code)

    except Exception as e:
        print(f"获取基金 {fund_code} 数据失败: {e}")
        return {'code': fund_code, 'success': False, 'error': str(e)}

def fetch_fund_basic_info(fund_code):
    """获取基金基本信息（用于货币基金等无估值的基金?"""
    try:
        url = f"https://fund.eastmoney.com/{fund_code}.html"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = http.get(url, headers=headers, timeout=5)  # 减少超时??
        if response.status_code == 200:
            return {
                'code': fund_code,
                'name': f'基金{fund_code}',
                'nav': '--',
                'estimate_nav': '--',
                'estimate_change': '--',
                'nav_date': '--',
                'estimate_time': '--',
                'success': True,
                'note': '该基金暂无实时估值数?',
                'fund_type': '--',
                'company': '--',
                'day_growth': '--',
                'week_growth': '--',
                'month_growth': '--',
                'three_month_growth': '--',
                'six_month_growth': '--',
                'year_growth': '--',
                'total_growth': '--',
                'manager': '--'
            }
    except:
        pass

    return {'code': fund_code, 'success': False, 'error': '基金代码不存?'}

def fetch_latest_official_nav(fund_code):
    """Fetch the latest published official NAV from Eastmoney history API."""
    try:
        url = "https://api.fund.eastmoney.com/f10/lsjz"
        params = {
            'fundCode': fund_code,
            'pageIndex': 1,
            'pageSize': 1
        }
        headers = {
            'Referer': 'https://fundf10.eastmoney.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = http.get(url, params=params, headers=headers, timeout=5)
        payload = response.json()
        rows = payload.get('Data', {}).get('LSJZList') or []
        if not rows:
            return {}
        latest = rows[0]
        return {
            'nav': latest.get('DWJZ') or '--',
            'nav_date': latest.get('FSRQ') or '--',
            'day_growth': latest.get('JZZZL') or '--'
        }
    except Exception as e:
        print(f"获取基金 {fund_code} 最新正式净值失败: {e}")
        return {}

def fetch_fund_detail(fund_code):
    """
    获取基金详细信息，包括类型、公司、历史收益率等
    """
    try:
        # 使用天天基金的API接口获取详细数据
        detail_url = f"http://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
        
        headers = {
            'Referer': 'http://fund.eastmoney.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = http.get(detail_url, headers=headers, timeout=5)  # 减少超时时间
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            text = response.text
            
            # 解析基金类型
            fund_type = '--'
            if 'var fS_name = "' in text:
                start = text.find('var fS_name = "') + len('var fS_name = "')
                end = text.find('"', start)
                fund_type = text[start:end] if start < end else '--'
            
            # 解析基金公司与经理（新接口的 Data_currentFundManager 块内含嵌套结构，直接抓字段）
            import re as _re
            company = '--'
            manager = '--'
            mgr_block_idx = text.find('Data_currentFundManager')
            if mgr_block_idx != -1:
                # 只取到下一个 var 声明之前，避免串到其它变量
                next_var = text.find('var ', mgr_block_idx + 25)
                scope = text[mgr_block_idx:next_var] if next_var != -1 else text[mgr_block_idx:mgr_block_idx + 2000]
                names = _re.findall(r'"name":"([^"]+)"', scope)
                if names:
                    manager = '、'.join(dict.fromkeys(names))  # 去重保序
                fc = _re.search(r'"fundcompany":"([^"]+)"', scope)
                if fc:
                    company = fc.group(1)

            # 兼容旧字段
            if company == '--' and 'var fS_company = "' in text:
                start = text.find('var fS_company = "') + len('var fS_company = "')
                end = text.find('"', start)
                if start < end:
                    company = text[start:end]

            # 解析收益率数据
            # 注意：天天基金网变量命名里 y=月(yue), n=年(nian)
            #   syl_1y=近1月, syl_3y=近3月, syl_6y=近6月, syl_1n=近1年, syl_6n=近6年, syl_ln=成立以来
            growths = {
                'day_growth': '--',
                'week_growth': '--',
                'month_growth': '--',
                'three_month_growth': '--',
                'six_month_growth': '--',
                'year_growth': '--',
                'total_growth': '--'
            }

            patterns = [
                ('var syl_1z="', 'week_growth'),        # 近1周（部分基金有）
                ('var syl_1y="', 'month_growth'),       # 近1月
                ('var syl_3y="', 'three_month_growth'), # 近3月
                ('var syl_6y="', 'six_month_growth'),   # 近6月
                ('var syl_1n="', 'year_growth'),        # 近1年
                ('var syl_ln="', 'total_growth')        # 成立以来
            ]
            
            for pattern, key in patterns:
                if pattern in text:
                    start = text.find(pattern) + len(pattern)
                    end = text.find('"', start)
                    if start < end:
                        growths[key] = text[start:end]
            
            return {
                'fund_type': fund_type,
                'company': company,
                'manager': manager,
                **growths
            }
    
    except Exception as e:
        print(f"获取基金 {fund_code} 详细信息失败: {e}")
    
    return {
        'fund_type': '--',
        'company': '--',
        'manager': '--',
        'day_growth': '--',
        'week_growth': '--',
        'month_growth': '--',
        'three_month_growth': '--',
        'six_month_growth': '--',
        'year_growth': '--',
        'total_growth': '--'
    }

def fetch_fund_rankings(sort_by='1nzf', count=50):
    """
    获取基金排
    sort_by: 1nzf(1?, 6yzf(6?, 3yzf(3?, 1yzf(1?, zzf(?
    """
    try:
        url = "http://fund.eastmoney.com/data/rankhandler.aspx"
        params = {
            'op': 'ph',
            'dt': 'kf',
            'ft': 'all',
            'rs': '',
            'gs': '0',
            'sc': sort_by,
            'st': 'desc',
            'pi': '1',
            'pn': str(count),
            'dx': '1'
        }
        
        headers = {
            'Referer': 'http://fund.eastmoney.com/data/fundranking.html',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = http.get(url, params=params, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        # 解析数据: var rankData = {datas:[...]}
        text = response.text
        start_idx = text.find('datas:[')
        if start_idx == -1:
            return []
            
        # 简单的字符串解析
        start_idx += 7
        end_idx = text.find('],allRecords')
        if end_idx == -1:
            return []
            
        data_str = text[start_idx:end_idx]
        # data_str 是 "item1","item2" 的格式
        # 使用 eval 不安全，这里手动处理
        # 去掉首尾引号，按 "," 分割 (注意有的字參包含逗号，但这里数据格式比较固定，先单?
        # 实际格式: "code,name,...","code,name,..."
        
        # 更好的方法：利用 json 解析，先构成合法?json
        # 但这里只昮单的 JS 对象字面量，不是 JSON
        
        # 单理：split('","')
        items = data_str[1:-1].split('","')
        
        funds = []
        for item in items:
            parts = item.split(',')
            if len(parts) < 15:
                continue
                
            # 格式: code, name, abbr, date, nav, accum_nav, day, 1w, 1m, 3m, 6m, 1y, 2y, 3y, this_year, total
            funds.append({
                'code': parts[0],
                'name': parts[1],
                'date': parts[3],
                'nav': parts[4],
                'day_growth': parts[6],
                'week_growth': parts[7],
                'month_growth': parts[8],
                'three_month_growth': parts[9],
                'six_month_growth': parts[10],
                'year_growth': parts[11],
                'this_year_growth': parts[14]
            })
            
        return funds
    except Exception as e:
        print(f"获取排失败: {e}")
        return []

def fetch_stock_info(stock_code, exchange='sh'):
    """
    从新浪财经获取股票实时行情
    stock_code: 股票代码（如 '600000'）
    exchange: 交易所 'sh'=上海, 'sz'=深圳
    """
    try:
        # 新浪财经API
        symbol = f"{exchange}{stock_code}"
        url = f"http://hq.sinajs.cn/list={symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn'
        }

        response = http.get(url, headers=headers, timeout=10)
        response.encoding = 'gbk'  # 新浪返回的是GBK编码

        # 解析返回数据
        # 格式: var hq_str_sh600000="股票名称,今开,昨收,当前???买一,卖一,成交?成交?...";
        text = response.text
        if 'hq_str_' not in text or '=""' in text:
            return {
                'code': stock_code,
                'exchange': exchange,
                'success': False,
                'error': '股票代码不存在或无法获取数据',
                'type': 'stock'
            }

        # 提取引号内的数据
        start = text.find('"') + 1
        end = text.rfind('"')
        data_str = text[start:end]

        if not data_str:
            return {
                'code': stock_code,
                'exchange': exchange,
                'success': False,
                'error': '股票代码不存?',
                'type': 'stock'
            }

        parts = data_str.split(',')
        if len(parts) < 32:
            return {
                'code': stock_code,
                'exchange': exchange,
                'success': False,
                'error': '数据格式错',
                'type': 'stock'
            }

        # 解析字
        # 0:名称, 1:今开, 2:昨收, 3:当前? 4:? 5:? 6:买一, 7:卖一, 8:成交? 9:成交
        name = parts[0]
        open_price = float(parts[1]) if parts[1] else 0
        yesterday_close = float(parts[2]) if parts[2] else 0
        price = float(parts[3]) if parts[3] else 0
        high = float(parts[4]) if parts[4] else 0
        low = float(parts[5]) if parts[5] else 0
        volume = int(float(parts[8])) if parts[8] else 0  # 成交量（股）
        amount = float(parts[9]) / 100000000 if parts[9] else 0  # 成交额（亿元?
        # 计算涨跌
        change_percent = 0
        if yesterday_close > 0:
            change_percent = round((price - yesterday_close) / yesterday_close * 100, 2)

        change_amount = round(price - yesterday_close, 2)

        # 获取时间
        date_str = parts[30] if len(parts) > 30 else ''
        time_str = parts[31] if len(parts) > 31 else ''
        update_time = time_str if time_str else datetime.now().strftime('%H:%M:%S')

        return {
            'code': stock_code,
            'exchange': exchange,
            'full_code': f"{exchange}{stock_code}",
            'name': name,
            'price': price,  # 当前价
            'yesterday_close': yesterday_close,  # 昨收
            'open': open_price,  # 盘价
            'high': high,  # 高价
            'low': low,  # 低价
            'volume': volume,  # 成交量（股）
            'amount': round(amount, 2),  # 成交额（亿元）
            'change_percent': change_percent,  # 涨跌幅（%）
            'change_amount': change_amount,  # 涨跌额
            'update_time': update_time,
            'success': True,
            'type': 'stock'
        }

    except Exception as e:
        print(f"获取股票 {exchange}{stock_code} 数据失败: {e}")
        return {
            'code': stock_code,
            'exchange': exchange,
            'success': False,
            'error': str(e),
            'type': 'stock'
        }

# 周期 -> 东方财富 (主力净流入字段, 累计涨跌幅字段)
# f62/f3=今日, f164/f109=5日, f174/f160=10日
SECTOR_FLOW_PERIODS = {
    'today': ('f62',  'f3'),
    '5d':    ('f164', 'f109'),
    '10d':   ('f174', 'f160'),
}

def fetch_sector_money_flow(direction='in', period='today'):
    """获取行业资金流向
    direction: 'in' 主力净流入>0  'out' 主力净流入<0
    period: 'today' / '5d' / '10d'
    数据源：东方财富 push2 接口；主 host 失败时回退到 push2delay
    """
    flow_field, change_field = SECTOR_FLOW_PERIODS.get(period, SECTOR_FLOW_PERIODS['today'])
    params = {
        'pn': '1',
        'pz': '100',
        'po': '1' if direction == 'in' else '0',  # 流入降序、流出升序（取最负）
        'np': '1',
        'fltt': '2',
        'invt': '2',
        'fid': flow_field,
        'fs': 'm:90 t:2 f:!50',
        'fields': f'f12,f14,{change_field},{flow_field}'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'http://quote.eastmoney.com/center/boardlist.html',
        'Accept': '*/*'
    }

    data = None
    last_err = None
    for host in ('push2.eastmoney.com', 'push2delay.eastmoney.com'):
        try:
            r = http.get(f'http://{host}/api/qt/clist/get',
                             params=params, headers=headers, timeout=10)
            data = r.json()
            if data and data.get('data') and data['data'].get('diff'):
                break
        except Exception as e:
            last_err = e
            continue

    if not data or not data.get('data') or not data['data'].get('diff'):
        if last_err:
            print(f"获取资金流向失败: {last_err}")
        return []

    sectors = []
    for item in data['data']['diff']:
        flow = item.get(flow_field)
        try:
            flow_val = round(float(flow) / 1e8, 2) if flow else 0
        except Exception:
            flow_val = 0

        if direction == 'in' and flow_val > 0:
            sectors.append({
                'name': item.get('f14'), 'flow': flow_val,
                'change': item.get(change_field), 'code': item.get('f12')
            })
        elif direction == 'out' and flow_val < 0:
            sectors.append({
                'name': item.get('f14'), 'flow': abs(flow_val),
                'change': item.get(change_field), 'code': item.get('f12')
            })

    sectors.sort(key=lambda x: x['flow'], reverse=True)
    return sectors[:20]

@app.route('/')
def index():
    """返回主页"""
    return send_from_directory('static', 'index.html')

@app.route('/api/funds', methods=['GET'])
def get_funds():
    """获取有保存的基金及其新数?- 使用并发加?"""
    data = load_funds()
    fund_codes = data.get('funds', [])
    
    if not fund_codes:
        return jsonify({
            'funds': [],
            'last_update': data.get('last_update')
        })
    
    # 使用线程池并发获取所有基金数
    funds_with_data = []
    futures = {executor.submit(fetch_fund_info, code): code for code in fund_codes}
    
    for future in as_completed(futures):
        try:
            fund_info = future.result(timeout=15)  # 单个基金最多等15秒
            funds_with_data.append(fund_info)
        except Exception as e:
            code = futures[future]
            print(f"获取基金 {code} 失败: {e}")
            funds_with_data.append({'code': code, 'success': False, 'error': str(e)})
    
    # 按基金代码排序，保持顺序
    funds_with_data.sort(key=lambda x: fund_codes.index(x['code']) if x['code'] in fund_codes else 999)
    
    # 为每丟金添加交易建
    for fund in funds_with_data:
        if fund.get('success'):
            advice = get_trading_advice(fund, funds_with_data)
            fund['advice'] = advice
    
    return jsonify({
        'funds': funds_with_data,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

# 大盘指数：上证、深成、创业板
# (代码, 交易所, 显示名, 东方财富 secid 用于获取历史成交额)
MARKET_INDICES = [
    ('000001', 'sh', '上证指数', '1.000001'),
    ('399001', 'sz', '深成指数', '0.399001'),
    ('399006', 'sz', '创业板指', '0.399006'),
]


# 昨日成交额缓存：昨日成交额一天内是常量，成功获取一次即缓存，
# 之后即便东财 kline 接口临时限流也能从缓存兜底。
INDEX_PREV_AMOUNT_CACHE = os.path.join(BASE_DIR, 'index_prev_amount_cache.json')


def _load_prev_amount_cache():
    try:
        if os.path.exists(INDEX_PREV_AMOUNT_CACHE):
            with open(INDEX_PREV_AMOUNT_CACHE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_prev_amount_cache(cache):
    try:
        with open(INDEX_PREV_AMOUNT_CACHE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"写入昨日成交额缓存失败: {e}")


def fetch_index_prev_amount(secid):
    """获取指数上一交易日的成交额（亿元）。
    数据源：东方财富日K线接口，取倒数第二根K线（昨日完整成交额）。
    多 host 回退（push2his / push2 / push2delay）+ 本地缓存兜底。
    返回 float（亿元）或 None。
    """
    params = {
        'secid': secid,
        'fields1': 'f1',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57',  # 日期,开,收,高,低,量,额
        'klt': '101',   # 日K
        'fqt': '0',
        'end': '20500101',
        'lmt': '3',     # 取最近3根，倒数第二根为昨日
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'http://quote.eastmoney.com/',
        'Accept': '*/*',
    }
    last_err = None
    for host in ('push2his.eastmoney.com', 'push2.eastmoney.com', 'push2delay.eastmoney.com'):
        try:
            resp = http.get(f'http://{host}/api/qt/stock/kline/get',
                                params=params, headers=headers, timeout=10)
            klines = (resp.json().get('data') or {}).get('klines') or []
            if len(klines) >= 2:
                prev_kline = klines[-2]              # 倒数第二根 = 上一交易日
                prev_day = prev_kline.split(',')[0]  # 该交易日日期
                prev_amount = round(float(prev_kline.split(',')[6]) / 100000000, 2)  # 亿元
                # 写入缓存（按 secid 存日期+金额）
                cache = _load_prev_amount_cache()
                cache[secid] = {'day': prev_day, 'amount': prev_amount}
                _save_prev_amount_cache(cache)
                return prev_amount
        except Exception as e:
            last_err = e
            continue

    # 接口全部失败：回退到本地缓存（昨日成交额一天内不变）
    cache = _load_prev_amount_cache()
    cached = cache.get(secid)
    if cached and cached.get('amount') is not None:
        print(f"指数 {secid} 昨日成交额接口失败，使用缓存值 {cached['amount']} 亿（{cached.get('day')}）")
        return cached['amount']

    if last_err:
        print(f"获取指数 {secid} 昨日成交额失败: {last_err}")
    return None


@app.route('/api/indices', methods=['GET'])
def get_indices():
    """获取大盘指数实时行情（上证、深成、创业板），含成交额及与昨日对比"""
    indices = []
    quote_futures = {
        executor.submit(fetch_stock_info, code, exchange): (name, secid)
        for code, exchange, name, secid in MARKET_INDICES
    }
    prev_futures = {
        executor.submit(fetch_index_prev_amount, secid): name
        for _, _, name, secid in MARKET_INDICES
    }

    # 收集昨日成交额（按显示名）
    prev_amounts = {}
    for future in as_completed(prev_futures):
        name = prev_futures[future]
        try:
            prev_amounts[name] = future.result(timeout=10)
        except Exception:
            prev_amounts[name] = None

    for future in as_completed(quote_futures):
        name, _secid = quote_futures[future]
        try:
            info = future.result(timeout=10)
            info['display_name'] = name
            # 成交额与昨日对比：达成率 = 今日成交额 / 昨日成交额
            prev_amount = prev_amounts.get(name)
            info['prev_amount'] = prev_amount
            today_amount = info.get('amount') or 0
            if prev_amount and prev_amount > 0:
                info['amount_completion_percent'] = round(
                    today_amount / prev_amount * 100, 1)
            else:
                info['amount_completion_percent'] = None
            indices.append(info)
        except Exception as e:
            indices.append({'display_name': name, 'success': False, 'error': str(e)})

    # 按 MARKET_INDICES 顺序排序
    order = [n for _, _, n, _ in MARKET_INDICES]
    indices.sort(key=lambda x: order.index(x['display_name']) if x.get('display_name') in order else 999)
    return jsonify({'indices': indices})

@app.route('/api/funds', methods=['POST'])
def add_fund():
    """添加新基?"""
    fund_code = request.json.get('code', '').strip()

    if not fund_code or not fund_code.isdigit() or len(fund_code) != 6:
        return jsonify({'success': False, 'error': '基金代码必须?位数?'}), 400

    data = load_funds()

    if fund_code in data['funds']:
        return jsonify({'success': False, 'error': '该基金已存在'}), 400

    # 验证基金昐存在
    fund_info = fetch_fund_info(fund_code)
    if not fund_info.get('success'):
        return jsonify({'success': False, 'error': '基金代码不存在或无法获取数据'}), 400

    data['funds'].append(fund_code)
    save_funds(data)

    return jsonify({'success': True, 'fund': fund_info})

@app.route('/api/funds/<fund_code>', methods=['DELETE'])
def delete_fund(fund_code):
    """删除基金"""
    data = load_funds()

    if fund_code in data['funds']:
        data['funds'].remove(fund_code)
        save_funds(data)
        return jsonify({'success': True})

    return jsonify({'success': False, 'error': '基金不存?'}), 404


@app.route('/api/funds/reorder', methods=['POST'])
def reorder_funds():
    """»˳"""
    codes = request.json.get('codes', [])

    if not isinstance(codes, list):
        return jsonify({'success': False, 'error': 'codes must be a list'}), 400

    data = load_data()
    existing_funds = data.get('funds', [])

    if sorted(codes) != sorted(existing_funds):
        return jsonify({'success': False, 'error': 'fund list mismatch'}), 400

    data['funds'] = codes
    save_data(data)

    return jsonify({'success': True, 'funds': data['funds']})
@app.route('/api/rankings', methods=['GET'])
def get_rankings():
    """获取基金排"""
    sort_by = request.args.get('sort', '1nzf')
    funds = fetch_fund_rankings(sort_by)
    return jsonify(funds)

@app.route('/api/money-flow', methods=['GET'])
def get_money_flow():
    """获取资金流向
    参数: direction - 'in'(流入,默) 或 'out'(流出)
          period    - 'today'(默认) / '5d' / '10d'
    """
    direction = request.args.get('direction', 'in')
    period = request.args.get('period', 'today')
    sectors = fetch_sector_money_flow(direction, period)
    return jsonify(sectors)

@app.route('/api/funds/<fund_code>/refresh', methods=['GET'])
def refresh_fund(fund_code):
    """刷新单个基金数据"""
    fund_info = fetch_fund_info(fund_code)
    return jsonify(fund_info)

# ==================== 股票相关API ====================

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    """获取有保存的股票及其新数?"""
    data = load_data()
    stock_list = data.get('stocks', [])

    if not stock_list:
        return jsonify({
            'stocks': [],
            'last_update': data.get('last_update')
        })

    # 使用线程池并发获取所有股票数
    stocks_with_data = []
    futures = {
        executor.submit(fetch_stock_info, s['code'], s['exchange']): s
        for s in stock_list
    }

    for future in as_completed(futures):
        try:
            stock_info = future.result(timeout=15)
            stocks_with_data.append(stock_info)
        except Exception as e:
            s = futures[future]
            print(f"获取股票 {s['exchange']}{s['code']} 失败: {e}")
            stocks_with_data.append({
                'code': s['code'],
                'exchange': s['exchange'],
                'success': False,
                'error': str(e),
                'type': 'stock'
            })

    return jsonify({
        'stocks': stocks_with_data,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/stocks', methods=['POST'])
def add_stock():
    """添加新股?"""
    stock_code = request.json.get('code', '').strip()
    exchange = request.json.get('exchange', 'sh').strip().lower()

    if not stock_code or not stock_code.isdigit() or len(stock_code) != 6:
        return jsonify({'success': False, 'error': '股票代码必须?位数?'}), 400

    if exchange not in ['sh', 'sz']:
        return jsonify({'success': False, 'error': '交易必须?sh(上海) ?sz(深圳)'}), 400

    data = load_data()

    # 查是否已存在
    for s in data.get('stocks', []):
        if s['code'] == stock_code and s['exchange'] == exchange:
            return jsonify({'success': False, 'error': '该股票已存在'}), 400

    # 验证股票昐存在
    stock_info = fetch_stock_info(stock_code, exchange)
    if not stock_info.get('success'):
        return jsonify({'success': False, 'error': '股票代码不存在或无法获取数据'}), 400

    # 添加到列
    if 'stocks' not in data:
        data['stocks'] = []
    data['stocks'].append({'code': stock_code, 'exchange': exchange})
    save_data(data)

    return jsonify({'success': True, 'stock': stock_info})

@app.route('/api/stocks/<exchange>/<stock_code>', methods=['DELETE'])
def delete_stock(exchange, stock_code):
    """删除股票"""
    data = load_data()

    stocks = data.get('stocks', [])
    for i, s in enumerate(stocks):
        if s['code'] == stock_code and s['exchange'] == exchange:
            stocks.pop(i)
            save_data(data)
            return jsonify({'success': True})

    return jsonify({'success': False, 'error': '股票不存?'}), 404

@app.route('/api/smart-add', methods=['POST'])
def smart_add():
    """智能添加 - 臊识别代码类型"""
    code = request.json.get('code', '').strip()

    if not code or not code.isdigit() or len(code) != 6:
        return jsonify({'success': False, 'error': '代码必须?位数?'}), 400

    data = load_data()

    # 查是否已存在
    if code in data.get('funds', []):
        return jsonify({'success': False, 'error': '该基金已存在'})

    for s in data.get('stocks', []):
        if s['code'] == code:
            return jsonify({'success': False, 'error': '该股票已存在'})

    # 并发测基金和股票
    fund_result = None
    stock_sh_result = None
    stock_sz_result = None

    from concurrent.futures import ThreadPoolExecutor, wait
    with ThreadPoolExecutor(max_workers=3) as ex:
        fund_future = ex.submit(fetch_fund_info, code)
        stock_sh_future = ex.submit(fetch_stock_info, code, 'sh')
        stock_sz_future = ex.submit(fetch_stock_info, code, 'sz')

        wait([fund_future, stock_sh_future, stock_sz_future], timeout=15)

        try:
            fund_result = fund_future.result(timeout=1)
        except:
            fund_result = {'success': False}

        try:
            stock_sh_result = stock_sh_future.result(timeout=1)
        except:
            stock_sh_result = {'success': False}

        try:
            stock_sz_result = stock_sz_future.result(timeout=1)
        except:
            stock_sz_result = {'success': False}

    # 判断基金昐有效（排除无数据的情况）
    fund_valid = fund_result.get('success') and fund_result.get('name') and not fund_result.get('name', '').startswith('基金')

    # 判断股票昐有效
    stock_sh_valid = stock_sh_result.get('success') and stock_sh_result.get('price', 0) > 0
    stock_sz_valid = stock_sz_result.get('success') and stock_sz_result.get('price', 0) > 0

    options = []

    if fund_valid:
        options.append({
            'type': 'fund',
            'name': fund_result.get('name'),
            'exchange': None
        })

    if stock_sh_valid:
        options.append({
            'type': 'stock',
            'name': stock_sh_result.get('name'),
            'exchange': 'sh'
        })

    if stock_sz_valid:
        options.append({
            'type': 'stock',
            'name': stock_sz_result.get('name'),
            'exchange': 'sz'
        })

    # 根据匹配结果处理
    if len(options) == 0:
        return jsonify({'success': False, 'error': '代码不存圼请查输?'})

    elif len(options) == 1:
        # 双配到丼直接添加
        opt = options[0]
        if opt['type'] == 'fund':
            data['funds'].append(code)
            save_data(data)
            fund_result['type'] = 'fund'
            return jsonify({'success': True, 'type': 'fund', 'fund': fund_result})
        else:
            if 'stocks' not in data:
                data['stocks'] = []
            data['stocks'].append({'code': code, 'exchange': opt['exchange']})
            save_data(data)
            stock_result = stock_sh_result if opt['exchange'] == 'sh' else stock_sz_result
            return jsonify({'success': True, 'type': 'stock', 'stock': stock_result})

    else:
        # 匹配到丼让用户择
        return jsonify({
            'success': False,
            'need_choose': True,
            'options': options
        })

# ==================== 组合持仓API ====================

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """获取完整持仓（基?股票?"""
    data = load_data()
    fund_codes = data.get('funds', [])
    stock_list = data.get('stocks', [])

    portfolio = []

    # 并发获取有数
    futures = {}

    # 基金任务
    for code in fund_codes:
        futures[executor.submit(fetch_fund_info, code)] = ('fund', code)

    # 股票任务
    for s in stock_list:
        futures[executor.submit(fetch_stock_info, s['code'], s['exchange'])] = ('stock', s)

    for future in as_completed(futures):
        asset_type, asset_info = futures[future]
        try:
            result = future.result(timeout=15)
            if asset_type == 'fund':
                result['type'] = 'fund'
            portfolio.append(result)
        except Exception as e:
            if asset_type == 'fund':
                portfolio.append({
                    'code': asset_info,
                    'success': False,
                    'error': str(e),
                    'type': 'fund'
                })
            else:
                portfolio.append({
                    'code': asset_info['code'],
                    'exchange': asset_info['exchange'],
                    'success': False,
                    'error': str(e),
                    'type': 'stock'
                })

    # 分别对基金和股票排序
    funds = [p for p in portfolio if p.get('type') == 'fund']
    stocks = [p for p in portfolio if p.get('type') == 'stock']

    # 基金按原顺序排序
    funds.sort(key=lambda x: fund_codes.index(x['code']) if x['code'] in fund_codes else 999)

    # 为基金添加交易建
    for fund in funds:
        if fund.get('success'):
            advice = get_trading_advice(fund, funds)
            fund['advice'] = advice

    return jsonify({
        'portfolio': funds + stocks,
        'funds_count': len(funds),
        'stocks_count': len(stocks),
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

# ==================== 基金策略API ====================

def normalize_strategy_positions(raw_positions, allowed_codes, existing_positions=None):
    """Validate and normalize saved strategy position inputs."""
    if not isinstance(raw_positions, dict):
        return None, ['positions must be an object']

    allowed = set(allowed_codes)
    normalized = {}
    existing_positions = existing_positions or {}

    for code, position in existing_positions.items():
        if code in allowed and isinstance(position, dict):
            buy_price = parse_float(position.get('buy_price'))
            amount = parse_float(position.get('amount'))
            if buy_price and buy_price > 0 and amount and amount > 0:
                normalized[code] = {
                    'buy_price': round(buy_price, 6),
                    'amount': round(amount, 2)
                }

    errors = []
    for code, position in raw_positions.items():
        code = str(code).strip()
        if code not in allowed:
            continue

        if not isinstance(position, dict):
            errors.append(f'{code}: position must be an object')
            continue

        buy_price_raw = position.get('buy_price')
        amount_raw = position.get('amount')
        buy_price = parse_float(buy_price_raw)
        amount = parse_float(amount_raw)

        if buy_price_raw in (None, '') and amount_raw in (None, ''):
            normalized.pop(code, None)
            continue

        if buy_price is None or buy_price <= 0 or amount is None or amount <= 0:
            errors.append(f'{code}: buy_price and amount must be positive numbers')
            continue

        normalized[code] = {
            'buy_price': round(buy_price, 6),
            'amount': round(amount, 2)
        }

    return normalized, errors

def fetch_current_fund_pool(fund_codes):
    funds_with_data = []
    futures = {executor.submit(fetch_fund_info, code): code for code in fund_codes}

    for future in as_completed(futures):
        code = futures[future]
        try:
            fund_info = future.result(timeout=15)
            funds_with_data.append(fund_info)
        except Exception as e:
            print(f"获取基金 {code} 策略数据失败: {e}")
            funds_with_data.append({'code': code, 'success': False, 'error': str(e)})

    funds_with_data.sort(key=lambda x: fund_codes.index(x['code']) if x.get('code') in fund_codes else 999)
    return funds_with_data

def fetch_theme_flow_data():
    """并发拉取 3 周期 x 2 方向共 6 组资金流数据（每次实时请求，不做缓存）"""
    flow_data = {period: {} for period in ('today', '5d', '10d')}
    futures = {
        executor.submit(fetch_sector_money_flow, direction, period): (period, direction)
        for period in ('today', '5d', '10d')
        for direction in ('in', 'out')
    }
    for future in as_completed(futures):
        period, direction = futures[future]
        try:
            flow_data[period][direction] = future.result(timeout=30)
        except Exception as e:
            print(f"获取资金流向 {period}/{direction} 失败: {e}")
            flow_data[period][direction] = []
    return flow_data

@app.route('/api/strategy', methods=['GET'])
def get_strategy():
    """Return portfolio strategy based on saved funds and position inputs."""
    data = load_data()
    fund_codes = data.get('funds', [])
    positions = data.get('positions', {})

    funds_with_data = fetch_current_fund_pool(fund_codes) if fund_codes else []
    flow_data = fetch_theme_flow_data() if fund_codes else {}
    theme_signals = build_theme_signals(fund_codes, flow_data)
    report = build_strategy_report(funds_with_data, positions, theme_signals)

    return jsonify({
        'success': True,
        'positions': positions,
        'theme_signals': theme_signals,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        **report
    })

@app.route('/api/strategy/positions', methods=['POST'])
def save_strategy_positions():
    """Save buy price and invested amount for strategy calculations."""
    payload = request.json or {}
    data = load_data()
    fund_codes = data.get('funds', [])
    existing_positions = data.get('positions', {})

    positions, errors = normalize_strategy_positions(
        payload.get('positions', {}),
        fund_codes,
        existing_positions
    )
    if errors:
        return jsonify({'success': False, 'errors': errors}), 400

    data['positions'] = positions
    save_data(data)

    return jsonify({'success': True, 'positions': positions})

# ==================== 模糊搜索API ====================

def search_funds(keyword):
    """搜索基金（支持名称代码拼音）"""
    try:
        url = "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
        params = {
            "m": 1,
            "key": keyword
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://fund.eastmoney.com/'
        }
        response = http.get(url, params=params, headers=headers, timeout=5)
        data = response.json()

        results = []
        if data.get('Datas'):
            for item in data['Datas'][:10]:  # 最多返回10条
                fund_base = item.get('FundBaseInfo') or {}
                results.append({
                    'code': item.get('CODE', ''),
                    'name': item.get('NAME', ''),
                    'type': 'fund',
                    'fundType': fund_base.get('FTYPE', ''),
                    'display': f"{item.get('NAME', '')} ({item.get('CODE', '')})"
                })
        return results
    except Exception as e:
        print(f"搜索基金失败: {e}")
        return []

def search_stocks(keyword):
    """搜索股票（支持名称代码拼音）"""
    try:
        url = "https://searchapi.eastmoney.com/api/suggest/get"
        params = {
            "input": keyword,
            "type": 14,
            "token": "D43BF722C8E33BDC906FB84D85E326E8",
            "count": 10
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/'
        }
        response = http.get(url, params=params, headers=headers, timeout=5)
        data = response.json()

        results = []
        if data.get('QuotationCodeTable', {}).get('Data'):
            for item in data['QuotationCodeTable']['Data']:
                # 叿留A
                classify = item.get('Classify', '')
                if classify not in ['AStock', 'ABStock']:
                    continue

                code = item.get('Code', '')
                name = item.get('Name', '')
                jys = item.get('JYS', '').lower()  # SH -> sh, SZ -> sz

                if jys in ['sh', 'sz'] and len(code) == 6:
                    results.append({
                        'code': code,
                        'name': name,
                        'type': 'stock',
                        'exchange': jys,
                        'display': f"{name} ({jys.upper()}{code})"
                    })
        return results
    except Exception as e:
        print(f"搜索股票失败: {e}")
        return []

@app.route('/api/search', methods=['GET'])
def search_assets():
    """统一搜索接口 - 同时搜索基金和股?"""
    keyword = request.args.get('keyword', '').strip()

    if not keyword:
        return jsonify({'results': []})

    # 如果昺数字且长度为6，优先精硌
    if keyword.isdigit() and len(keyword) == 6:
        # 并发查
        with ThreadPoolExecutor(max_workers=2) as ex:
            fund_future = ex.submit(search_funds, keyword)
            stock_future = ex.submit(search_stocks, keyword)

            funds = fund_future.result(timeout=10)
            stocks = stock_future.result(timeout=10)

        # 合并结果，股票优先（因为6位数字更參昂票代码）
        results = stocks + funds
    else:
        # 关键词搜紼并发查
        with ThreadPoolExecutor(max_workers=2) as ex:
            fund_future = ex.submit(search_funds, keyword)
            stock_future = ex.submit(search_stocks, keyword)

            funds = fund_future.result(timeout=10)
            stocks = stock_future.result(timeout=10)

        # 合并结果，基金优先（因为基金名称搜索更常见）
        results = funds + stocks

    # 限制总数
    return jsonify({'results': results[:15]})

if __name__ == '__main__':
    # 打印吊信息
    print("="*50)
    print("基金&股票监控系统吊?..")
    print("数据来源：天天基金网 & 东方财富")
    print("访问地址：http://localhost:5002")
    print("="*50)

    app.run(debug=False, host='0.0.0.0', port=5002)
