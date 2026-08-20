import requests
import random
import time
import threading
import queue
from flask import Flask, request, jsonify, render_template
from fake_useragent import UserAgent

app = Flask(__name__)

# === CẤU HÌNH API PROXY (giống như web proxy) ===
PROXY_APIS = {
    'http': 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
    'socks4': 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt',
    'socks5': 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt'
}

def fetch_proxies_from_api(protocol='http', count=10, custom_url=None):
    """Lấy danh sách proxy từ API hoặc URL tùy chỉnh"""
    url = custom_url or PROXY_APIS.get(protocol)
    if not url:
        return []
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            lines = resp.text.split('\n')
            proxies = [line.strip() for line in lines if line.strip()]
            # Lấy ngẫu nhiên count proxy
            if len(proxies) > count:
                return random.sample(proxies, count)
            return proxies
    except Exception as e:
        print(f"Lỗi lấy proxy: {e}")
    return []

# === TASK QUEUE ===
task_queue = queue.Queue()
result_store = {}

def buff_view(url, count, proxy_list):
    success = 0
    ua = UserAgent()
    for i in range(count):
        proxy = random.choice(proxy_list) if proxy_list else None
        headers = {'User-Agent': ua.random}
        try:
            resp = requests.get(url, headers=headers,
                                proxies={'http': proxy, 'https': proxy} if proxy else None,
                                timeout=10, allow_redirects=False)
            if resp.status_code in [200, 301, 302]:
                success += 1
            time.sleep(random.uniform(0.5, 1.2))
        except Exception as e:
            print(f"View error: {e}")
            continue
    return success

def buff_like(post_id, count, proxy_list, access_token=None, cookie=None):
    if not access_token and not cookie:
        return 0, "Thiếu token/cookie"
    url = f"https://graph.facebook.com/v18.0/{post_id}/likes"
    params = {}
    headers = {'User-Agent': UserAgent().random}
    if access_token:
        params['access_token'] = access_token
    else:
        headers['Cookie'] = cookie
    success = 0
    for i in range(count):
        proxy = random.choice(proxy_list) if proxy_list else None
        try:
            resp = requests.post(url, params=params, headers=headers,
                                 proxies={'http': proxy, 'https': proxy} if proxy else None,
                                 timeout=10)
            if resp.status_code == 200:
                success += 1
            time.sleep(random.uniform(1, 2))
        except:
            continue
    return success, ""

def worker():
    while True:
        task_id, task_data = task_queue.get()
        if task_data is None:
            break
        try:
            action = task_data['action']
            url = task_data.get('url', '')
            post_id = task_data.get('post_id', '')
            count = task_data.get('count', 5)
            proxy_list = task_data.get('proxy_list', [])
            if action == 'view':
                result = buff_view(url, count, proxy_list)
                result_store[task_id] = {'status': 'done', 'success': result, 'total': count}
            elif action == 'like':
                token = task_data.get('access_token')
                cookie = task_data.get('cookie')
                success, msg = buff_like(post_id, count, proxy_list, token, cookie)
                result_store[task_id] = {'status': 'done', 'success': success, 'total': count, 'message': msg}
        except Exception as e:
            result_store[task_id] = {'status': 'error', 'message': str(e)}
        finally:
            task_queue.task_done()

for _ in range(3):
    threading.Thread(target=worker, daemon=True).start()

# === ROUTES ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/proxies', methods=['GET'])
def get_proxies():
    """Endpoint lấy proxy – tích hợp với web proxy của bạn"""
    protocol = request.args.get('protocol', 'http')
    count = int(request.args.get('count', 10))
    custom_url = request.args.get('url', '')
    proxies = fetch_proxies_from_api(protocol, count, custom_url)
    return jsonify({'proxies': proxies})

@app.route('/buff', methods=['POST'])
def buff():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON'}), 400
    
    action = data.get('action', 'view')
    url = data.get('url', '')
    post_id = data.get('post_id', '')
    count = int(data.get('count', 5))
    use_auto_proxy = data.get('use_auto_proxy', True)
    protocol = data.get('protocol', 'http')
    custom_proxy_url = data.get('custom_proxy_url', '')
    manual_proxy_list = data.get('proxy_list', [])
    
    # Lấy proxy
    proxy_list = []
    if use_auto_proxy:
        proxy_list = fetch_proxies_from_api(protocol, count * 2, custom_proxy_url)
        if not proxy_list:
            return jsonify({'error': 'Không lấy được proxy tự động, vui lòng nhập thủ công'}), 400
    else:
        proxy_list = manual_proxy_list
    
    if not proxy_list:
        return jsonify({'error': 'Danh sách proxy trống'}), 400
    
    task_id = str(int(time.time() * 1000)) + str(random.randint(100, 999))
    task_data = {
        'action': action,
        'url': url,
        'post_id': post_id,
        'count': count,
        'proxy_list': proxy_list,
        'access_token': data.get('access_token', ''),
        'cookie': data.get('cookie', '')
    }
    task_queue.put((task_id, task_data))
    return jsonify({'task_id': task_id, 'status': 'queued'})

@app.route('/status/<task_id>')
def status(task_id):
    res = result_store.get(task_id)
    if res:
        return jsonify(res)
    return jsonify({'status': 'pending'}), 202

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
