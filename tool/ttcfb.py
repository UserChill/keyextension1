import requests, re, os, json, base64, random, uuid, sys, threading, hashlib, platform, subprocess, time, socket
from datetime import datetime, timedelta
from time import sleep
from collections import defaultdict
import math

do = "\033[1;31m"
luc = "\033[1;32m"
vang = "\033[1;33m"
trang = "\033[1;37m"
tim = "\033[1;35m"
xanh = "\033[1;36m"
thanh = f'{do}[{trang}</>{do}] {trang}=> '
dem = 0
listCookie = []
list_nv = []
_uid_list_cached = []
chedo = "cookie"
print_lock = threading.Lock()
stt_lock = threading.Lock()
nhapnick_lock = threading.Lock()
update_xu_lock = threading.Lock()
# Biến toàn cục cho đa TTC
ttc_accounts = []
stt_counter = [0]
totalxu_counter = [0]

# ==== PROXY CONFIG ====
PROXY_FB = None
PROXY_TTC = None
PROXY_BOTH = None
USE_PROXY_FB = False
USE_PROXY_TTC = False
USE_PROXY_BOTH = False

# ==== KEY AUTHENTICATION ====
KEY_VALID = False
KEY_USER = "UNKNOWN"
KEY_EXPIRY = "01/01/1970"
KEY_TYPE = "ngay"  # hoặc "xu"
KEY_XU = 0
KEY_DAYS = 0
KEY_MACHINE = ""
KEY_SIGNATURE = ""

# ==== KEY STORAGE PATHS (ẩn, khó tìm) ====
KEY_STORAGE_PATHS = [
    os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Themes", ".dtpkey"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", ".dtpkey_cache"),
    os.path.join(os.path.expanduser("~"), ".config", "dtp", ".key"),
    os.path.join(os.path.dirname(sys.executable) if hasattr(sys, 'executable') else ".", ".dtpkey"),
    "/tmp/.dtpkey" if os.name != "nt" else None,
    "/var/tmp/.dtpkey" if os.name != "nt" else None
]




def update_xu_on_server(key, xu_nhan, retry_count=3):
    """
    Cập nhật xu lên GitHub thông qua API, có retry khi gặp lỗi 409
    """
    with update_xu_lock:  # Chỉ 1 thread được vào tại 1 thời điểm
        for attempt in range(retry_count):
            try:
                GITHUB_TOKEN = "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"
                REPO = "UserChill/keyextension1"
                FILE_PATH = "keyttcfb.txt"
                
                url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
                headers = {
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                # 1. Lấy file hiện tại
                resp = requests.get(url, headers=headers)
                if resp.status_code != 200:
                    print(f"Lỗi đọc file: {resp.status_code}")
                    continue  # Thử lại
                
                data = resp.json()
                sha = data["sha"]
                content = base64.b64decode(data["content"]).decode("utf-8")
                
                # 2. Cập nhật xu
                lines = content.splitlines()
                new_lines = []
                xu_con_lai = 0
                found = False
                
                for line in lines:
                    parts = line.split("|")
                    if len(parts) >= 3 and parts[0].strip() == key:
                        xu_part = parts[2].strip()
                        if xu_part.lower().startswith("xu"):
                            xu_current = int(xu_part[2:])
                        else:
                            xu_current = int(xu_part)
                        
                        xu_con_lai = max(0, xu_current - xu_nhan)
                        parts[2] = f"xu{xu_con_lai}"
                        new_lines.append("|".join(parts))
                        found = True
                    else:
                        new_lines.append(line)
                
                if not found:
                    print(f"Không tìm thấy key: {key}")
                    return -1
                
                # 3. Ghi file lên GitHub
                new_content = "\n".join(new_lines)
                encoded = base64.b64encode(new_content.encode()).decode()
                
                payload = {
                    "message": f"Update xu: -{xu_nhan}, con lai: {xu_con_lai}",
                    "content": encoded,
                    "sha": sha
                }
                
                resp = requests.put(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    
                    return xu_con_lai
                elif resp.status_code == 409:
                    # Conflict - file đã bị thay đổi, thử lại
                    
                    time.sleep(0.5)  # Chờ trước khi thử lại
                    continue
                else:
                    print(f"Lỗi ghi file: {resp.status_code} - {resp.text}")
                    return -1
                    
            except Exception as e:
                print(f"Lỗi update_xu_api (lần {attempt+1}): {e}")
                time.sleep(0.5)
                continue
        
        print(f"[LỖI] Cập nhật xu thất bại sau {retry_count} lần thử")
        return -1

def fetch_key_from_server():
    try:
        resp = requests.get("https://userchill.github.io/keyextension1/keyttcfb.txt", timeout=30)
        if resp.status_code == 200:
            return parse_key_file(resp.text)
        return None
    except:
        return None

def get_deep_fingerprint():
    """Tạo mã máy cố định, lưu vào file"""
    fingerprint_file = os.path.join(os.path.dirname(sys.executable) if hasattr(sys, 'executable') else ".", ".machine_id")
    
    if os.path.exists(fingerprint_file):
        try:
            with open(fingerprint_file, "r") as f:
                return f.read().strip()
        except:
            pass
    
    try:
        info_parts = []
        
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output("wmic cpu get processorid", shell=True, stderr=subprocess.DEVNULL)
                cpu = output.decode().split()[1] if len(output.decode().split()) > 1 else ""
                info_parts.append(f"CPU:{cpu}")
            else:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "Serial" in line:
                            info_parts.append(f"CPU:{line.split(':')[-1].strip()}")
                            break
        except:
            pass
        
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output("wmic diskdrive get serialnumber", shell=True, stderr=subprocess.DEVNULL)
                serials = output.decode().split()
                for s in serials:
                    if len(s) > 4 and s not in ["SerialNumber", ""]:
                        info_parts.append(f"DISK:{s}")
                        break
            else:
                output = subprocess.check_output("lsblk -o SERIAL", shell=True, stderr=subprocess.DEVNULL)
                serials = output.decode().split()
                for s in serials:
                    if len(s) > 4 and s not in ["SERIAL"]:
                        info_parts.append(f"DISK:{s}")
                        break
        except:
            pass
        
        try:
            import uuid as uuid_lib
            mac = uuid_lib.getnode()
            info_parts.append(f"MAC:{mac:012x}")
        except:
            pass
        
        try:
            info_parts.append(f"HOST:{socket.gethostname()}")
        except:
            pass
        
        info_parts.append(f"OS:{platform.system()}{platform.release()}")
        
        combined = "|".join(info_parts).encode()
        fingerprint = hashlib.sha512(combined).hexdigest()
        
        machine_id = "DTP" + fingerprint[:29].upper()
        
        try:
            with open(fingerprint_file, "w") as f:
                f.write(machine_id)
        except:
            pass
        
        return machine_id
    except:
        machine_id = "DTP" + hashlib.md5(str(time.time()).encode()).hexdigest()[:29].upper()
        try:
            with open(fingerprint_file, "w") as f:
                f.write(machine_id)
        except:
            pass
        return machine_id

def get_machine_id():
    return get_deep_fingerprint()

def get_current_date():
    return datetime.now().strftime("%d/%m/%Y")

def parse_key_file(content):
    """Định dạng:
       - KEY|TEN|SO_NGAY  (key ngày)
       - KEY|TEN|xuXXX    (key xu)
    """
    lines = content.strip().splitlines()
    machine_id_local = get_machine_id()
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) >= 3:
            key = parts[0].strip()
            user = parts[1].strip()
            value = parts[2].strip()
            
            if key.upper() == machine_id_local:
                if value.lower().startswith("xu"):
                    try:
                        xu = int(value[2:])
                    except:
                        xu = 0
                    return {
                        "machine": key,
                        "user": user,
                        "type": "xu",
                        "xu": xu,
                        "valid": True
                    }
                else:
                    try:
                        days = int(value)
                    except:
                        days = 0
                    return {
                        "machine": key,
                        "user": user,
                        "type": "ngay",
                        "days": days,
                        "valid": True
                    }
    return None
import time  # Đảm bảo đã import time ở đầu file

def authenticate():
    global KEY_VALID, KEY_USER, KEY_EXPIRY, KEY_TYPE, KEY_XU, KEY_DAYS, KEY_MACHINE
    print(f"{thanh}{luc}=== XÁC THỰC BẢN QUYỀN DTPPROVIP ===")
    
    # Thêm delay nhẹ trước khi bắt đầu
    time.sleep(0.5)
    
    machine_id = get_machine_id()
    print(f"{thanh}{luc}Mã máy: {vang}{machine_id}")
    print(f"{thanh}{luc}Ngày hiện tại: {vang}{get_current_date()}")
    print(f"{thanh}{luc}Đang kết nối server xác thực...")
    
    # Thêm delay trước khi gọi API
    time.sleep(0.5)
    
    key_data = fetch_key_from_server()
    if not key_data:
        print(f"{do}[LỖI] Không thể lấy key từ server!")
        time.sleep(1)  # Delay trước khi thoát
        return False
    
    # Thêm delay sau khi nhận dữ liệu
    time.sleep(0.3)
    
    if key_data.get("machine", "").upper() != machine_id:
        print(f"{do}[LỖI] Mã máy không khớp!")
        time.sleep(1)
        return False
    
    KEY_MACHINE = key_data.get("machine", "")
    KEY_USER = key_data.get("user", "Unknown")
    KEY_TYPE = key_data.get("type", "")
    
    if KEY_TYPE == "xu":
        KEY_XU = key_data.get("xu", 0)
        KEY_DAYS = 0
        KEY_EXPIRY = f"Số Xu: {KEY_XU}"
        
        if KEY_XU <= 0:
            print(f"{do}[LỖI] Key đã hết xu!")
            time.sleep(1)
            return False
        
        print(f"{luc}[THÀNH CÔNG] Key xu - còn {vang}{KEY_XU}{luc} xu")
        time.sleep(0.3)
        
    elif KEY_TYPE == "ngay":
        days = key_data.get("days", 0)
        KEY_DAYS = days
        KEY_XU = 0
        
        first_run_file = "first_run_date.txt"
        try:
            if os.path.exists(first_run_file):
                with open(first_run_file, "r") as f:
                    first_date = datetime.strptime(f.read().strip(), "%d/%m/%Y")
            else:
                first_date = datetime.now()
                with open(first_run_file, "w") as f:
                    f.write(first_date.strftime("%d/%m/%Y"))
            
            expiry_date = first_date + timedelta(days=days)
            KEY_EXPIRY = expiry_date.strftime('%d/%m/%Y')
            if datetime.now() > expiry_date:
                print(f"{do}[LỖI] Key đã hết hạn! (Hết hạn: {vang}{KEY_EXPIRY})")
                time.sleep(1)
                return False
        except:
            pass
        
        print(f"{luc}[THÀNH CÔNG] Key ngày - còn {vang}{days}{luc} ngày")
        time.sleep(0.3)
    
    else:
        print(f"{do}[LỖI] Loại key không xác định!")
        time.sleep(1)
        return False
    
    KEY_VALID = True
    print(f"{thanh}{luc}Người dùng: {vang}{KEY_USER}")
    time.sleep(1)  # Delay trước khi vào main
    return True

def verify_signature(data):
    return True

def check_expiry(expiry_or_days):
    expiry_str = expiry_or_days.strip()
    
    if expiry_str.isdigit():
        days = int(expiry_str)
        first_run_file = "first_run_date.txt"
        try:
            if os.path.exists(first_run_file):
                with open(first_run_file, "r") as f:
                    first_date = datetime.strptime(f.read().strip(), "%d/%m/%Y")
            else:
                first_date = datetime.now()
                with open(first_run_file, "w") as f:
                    f.write(first_date.strftime("%d/%m/%Y"))
            expiry = first_date + timedelta(days=days)
            today = datetime.now()
            return today <= expiry
        except:
            return True
    
    try:
        expiry = datetime.strptime(expiry_str, "%d/%m/%Y")
        today = datetime.now()
        return today <= expiry
    except:
        return True

# ==== PROXY FUNCTIONS ====
def parse_proxy(proxy_str):
    if not proxy_str or not proxy_str.strip():
        return None
    proxy_str = proxy_str.strip()
    
    if '@' in proxy_str and ':' in proxy_str.split('@')[0]:
        try:
            auth, host = proxy_str.split('@', 1)
            if ':' in auth:
                user, pwd = auth.split(':', 1)
                return {"http": f"http://{user}:{pwd}@{host}", "https": f"http://{user}:{pwd}@{host}"}
        except:
            pass
    
    parts = proxy_str.split(':')
    if len(parts) == 4:
        try:
            ip, port, user, pwd = parts
            int(port)
            return {"http": f"http://{user}:{pwd}@{ip}:{port}", "https": f"http://{user}:{pwd}@{ip}:{port}"}
        except:
            pass
    
    if len(parts) == 2:
        try:
            ip, port = parts
            int(port)
            return {"http": f"http://{ip}:{port}", "https": f"http://{ip}:{port}"}
        except:
            pass
    
    return None

def set_proxy_fb(proxy_str):
    global PROXY_FB, USE_PROXY_FB
    parsed = parse_proxy(proxy_str)
    if parsed:
        PROXY_FB = parsed
        USE_PROXY_FB = True
    else:
        PROXY_FB = None
        USE_PROXY_FB = False

def set_proxy_ttc(proxy_str):
    global PROXY_TTC, USE_PROXY_TTC
    parsed = parse_proxy(proxy_str)
    if parsed:
        PROXY_TTC = parsed
        USE_PROXY_TTC = True
    else:
        PROXY_TTC = None
        USE_PROXY_TTC = False

def set_proxy_both(proxy_str):
    global PROXY_BOTH, USE_PROXY_BOTH
    parsed = parse_proxy(proxy_str)
    if parsed:
        PROXY_BOTH = parsed
        USE_PROXY_BOTH = True
    else:
        PROXY_BOTH = None
        USE_PROXY_BOTH = False

def get_fb_proxy():
    if USE_PROXY_BOTH and PROXY_BOTH:
        return PROXY_BOTH
    if USE_PROXY_FB and PROXY_FB:
        return PROXY_FB
    return None

def get_ttc_proxy():
    if USE_PROXY_BOTH and PROXY_BOTH:
        return PROXY_BOTH
    if USE_PROXY_TTC and PROXY_TTC:
        return PROXY_TTC
    return None

def Delay(value):
    while not(value <= 1):
        value -= 0.123
        print(f'''{trang}[{xanh}DTPVIP{trang}] [{xanh}DELAY{trang}] [{xanh}{str(value)[0:5]}{trang}] [{vang}X    {trang}]''', '               ', end = '\r')
        sleep(0.02)
        print(f'''{trang}[{xanh}DTPVIP{trang}] [{xanh}DELAY{trang}] [{xanh}{str(value)[0:5]}{trang}] [ {vang}X   {trang}]''', '               ', end = '\r')
        sleep(0.02)
        print(f'''{trang}[{xanh}DTPVIP{trang}] [{xanh}DELAY{trang}] [{xanh}{str(value)[0:5]}{trang}] [  {vang}X  {trang}]''', '               ', end = '\r')
        sleep(0.02)
        print(f'''{trang}[{xanh}DTPVIP{trang}] [{xanh}DELAY{trang}] [{xanh}{str(value)[0:5]}{trang}] [   {vang}X {trang}]''', '               ', end = '\r')
        sleep(0.02)
        print(f'''{trang}[{xanh}DTPVIP{trang}] [{xanh}DELAY{trang}] [{xanh}{str(value)[0:5]}{trang}] [    {vang}X{trang}]''', '               ', end = '\r')
        sleep(0.02)

def thanhngang(so):
    for i in range(so):
        print(trang+'-',end ='')
    print('')

def banner():
    global KEY_VALID, KEY_USER, KEY_EXPIRY, KEY_TYPE, KEY_XU
    os.system('cls' if os.name=='nt' else 'clear')
    print(f'''                 {luc}© Bản Quyền DTPVN-TOOL
        
        {do}███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
        {trang}████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
        {do}██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
        {trang}██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
        {do}██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
        {trang}╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝''')
    thanhngang(60)
    print(f'{thanh}{luc}Admin/Mod Tool{trang}: {vang}Đinh Tấn Phát')
    print(f'{thanh}{luc}Code{trang}: {vang}Đàm Hữu Phước')
    print(f'{thanh}{luc}Tool Đang Chạy{trang}: {vang}Tương Tác Chéo Facebook + Page (Đa TTC)')
    
    proxy_status = "TẮT"
    if USE_PROXY_BOTH and PROXY_BOTH:
        proxy_status = f"BOTH: {PROXY_BOTH['http']}"
    elif USE_PROXY_FB and PROXY_FB:
        proxy_status = f"FB: {PROXY_FB['http']}"
        if USE_PROXY_TTC and PROXY_TTC:
            proxy_status += f" | TTC: {PROXY_TTC['http']}"
    elif USE_PROXY_TTC and PROXY_TTC:
        proxy_status = f"TTC: {PROXY_TTC['http']}"
    print(f'{thanh}{luc}Proxy{trang}: {vang}{proxy_status}')
    
    if KEY_VALID:
        if KEY_TYPE == "xu":
            print(f'{thanh}{luc}Key: {vang}{KEY_USER} {trang}| {luc}Số Xu: {vang}{KEY_XU}')
        else:
            print(f'{thanh}{luc}Key: {vang}{KEY_USER} {trang}| {luc}Hết hạn: {vang}{KEY_EXPIRY}')
    else:
        print(f'{thanh}{do}Key: CHƯA XÁC THỰC')
    
    thanhngang(60)

def decode_base64(encoded_str):
    decoded_bytes = base64.b64decode(encoded_str)
    decoded_str = decoded_bytes.decode('utf-8')
    return decoded_str

def encode_to_base64(_data):
    byte_representation = _data.encode('utf-8')
    base64_bytes = base64.b64encode(byte_representation)
    base64_string = base64_bytes.decode('utf-8')
    return base64_string

# ==== FACEBOOK CLASSES ====
class FacebookCookie():
    def __init__(self, cookie):
        try:
            self.fb_dtsg = ''
            self.jazoest = ''
            self.cookie = cookie
            self.token = None
            self.session = requests.Session()
            proxy = get_fb_proxy()
            if proxy:
                self.session.proxies.update(proxy)
            self.id = self.cookie.split('c_user=')[1].split(';')[0]
            self.headers = {
                'authority': 'www.facebook.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-language': 'vi',
                'sec-ch-prefers-color-scheme': 'light',
                'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
                'viewport-width': '1366',
                'Cookie': self.cookie
            }
            url = self.session.get(f'https://www.facebook.com/{self.id}', headers=self.headers).url
            response = self.session.get(url, headers=self.headers).text
            matches = re.findall(r'\["DTSGInitialData",\[\],\{"token":"(.*?)"\}', response)
            if len(matches) > 0:
                self.fb_dtsg += matches[0]
                self.jazoest += re.findall(r'jazoest=(.*?)\"', response)[0]
        except:
            pass

    def info(self):
        try:
            get = self.session.get('https://www.facebook.com/me', headers=self.headers).url
            url = 'https://www.facebook.com/' + get.split('%2F')[-2] + '/' if 'next=' in get else get
            response = self.session.get(url, headers=self.headers, params={"locale": "vi_VN"})
            data_split = response.text.split('"CurrentUserInitialData",[],{')
            json_data = '{' + data_split[1].split('},')[0] + '}'
            parsed_data = json.loads(json_data)
            id = parsed_data.get('USER_ID', '0')
            name = parsed_data.get('NAME', '')
            if id == '0' and name == '': return {'status': 'error', 'mess': 'cookieout'}
            elif '828281030927956' in response.text: return {'status': 'error', 'mess': '956'}
            elif '1501092823525282' in response.text: return {'status': 'error', 'mess': '282'}
            elif '601051028565049' in response.text: return {'status': 'error', 'mess': 'spam'}
            else: id, name = parsed_data.get('USER_ID'), parsed_data.get('NAME')
            return {'status': 'success', 'id': id, 'name': name}
        except:
            return {'status': 'error', 'mess': 'cookieout'}

    def likepage(self, id):
        try:
            data = {'av': self.id, 'fb_dtsg': self.fb_dtsg, 'jazoest': self.jazoest, 'fb_api_caller_class': 'RelayModern', 'fb_api_req_friendly_name': 'PagesCometLikeButtonLikeMutation', 'variables': '{"pageID":"' + id + '","scale":1}', 'server_timestamps': 'true', 'doc_id': '4110311372355541'}
            self.session.post('https://www.facebook.com/api/graphql/', headers=self.headers, data=data)
        except:
            pass

    def follow(self, id):
        return self.addfriend(id)

    def addfriend(self, id):
        try:
            data = {
                'av': self.id,
                'fb_dtsg': self.fb_dtsg,
                'jazoest': self.jazoest,
                'fb_api_caller_class': 'RelayModern',
                'fb_api_req_friendly_name': 'FriendingCometFriendRequestSendMutation',
                'variables': '{"input":{"click_correlation_id":"' + str(int(datetime.now().timestamp()*1000)) + '","click_proof_validation_result":"{\\\"validated\\\":true}","friend_requestee_ids":["' + str(id) + '"],"friending_channel":"PROFILE_BUTTON","warn_ack_for_ids":[],"actor_id":"' + self.id + '","client_mutation_id":"1"},"scale":1}',
                'server_timestamps': 'true',
                'doc_id': '35889183907395315'
            }
            return self.session.post('https://www.facebook.com/api/graphql/', headers=self.headers, data=data)
        except:
            pass

    def camxuc(self, id, type):
        try:
            reac = {"LIKE": "1635855486666999", "LOVE": "1678524932434102", "CARE": "613557422527858", "HAHA": "115940658764963", "WOW": "478547315650144", "SAD": "908563459236466", "ANGRY": "444813342392137"}
            data = {'av': self.id, 'fb_dtsg': self.fb_dtsg, 'jazoest': self.jazoest, 'fb_api_caller_class': 'RelayModern', 'fb_api_req_friendly_name': 'CometUFIFeedbackReactMutation', 'variables': fr'{{"input":{{"attribution_id_v2":"CometHomeRoot.react,comet.home,tap_tabbar,1719027162723,322693,4748854339,,","feedback_id":"{encode_to_base64("feedback:" + str(id))}","feedback_reaction_id":"{reac.get(type)}","feedback_source":"NEWS_FEED","is_tracking_encrypted":true,"tracking":[],"session_id":"{uuid.uuid4()}","actor_id":"{self.id}","client_mutation_id":"3"}},"useDefaultActor":false,"__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider":false}}', 'server_timestamps': 'true', 'doc_id': '7047198228715224'}
            self.session.post('https://www.facebook.com/api/graphql/', headers=self.headers, data=data)
        except:
            pass

    def camxuccmt(self, id, type):
        try:
            reac = {"LIKE": "1635855486666999","LOVE": "1678524932434102","CARE": "613557422527858","HAHA": "115940658764963","WOW": "478547315650144","SAD": "908563459236466","ANGRY": "444813342392137"}
            data = {'av': self.id, 'fb_dtsg': self.fb_dtsg, 'jazoest': self.jazoest, 'fb_api_caller_class': 'RelayModern', 'fb_api_req_friendly_name': 'CometUFIFeedbackReactMutation', 'variables': '{"input":{"attribution_id_v2":"CometVideoHomeNewPermalinkRoot.react,comet.watch.injection,via_cold_start,1719930662698,975645,2392950137,,","feedback_id":"' + encode_to_base64("feedback:" + str(id)) + '","feedback_reaction_id":"' + reac.get(type) + '","feedback_source":"TAHOE","is_tracking_encrypted":true,"tracking":[],"session_id":"' + str(uuid.uuid4()) + '","actor_id":"' + self.id + '","client_mutation_id":"1"},"useDefaultActor":false,"__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider":false}', 'server_timestamps': 'true', 'doc_id': '7616998081714004'}
            self.session.post('https://www.facebook.com/api/graphql/', headers=self.headers, data=data)
        except:
            pass

    def share(self, id):
        try:
            data = {'av': self.id, 'fb_dtsg': self.fb_dtsg, 'jazoest': self.jazoest, 'fb_api_caller_class': 'RelayModern', 'fb_api_req_friendly_name': 'ComposerStoryCreateMutation', 'variables': '{"input":{"composer_entry_point":"share_modal","composer_source_surface":"feed_story","composer_type":"share","idempotence_token":"' + str(uuid.uuid4()) + '_FEED","source":"WWW","attachments":[{"link":{"share_scrape_data":"{\"share_type\":22,\"share_params\":[' + id + ']}"}}],"reshare_original_post":"RESHARE_ORIGINAL_POST","audience":{"privacy":{"allow":[],"base_state":"EVERYONE","deny":[],"tag_expansion_state":"UNSPECIFIED"}},"is_tracking_encrypted":true,"tracking":[null],"logging":{"composer_session_id":"' + str(uuid.uuid4()) + '"},"actor_id":"' + self.id + '","client_mutation_id":"3"},"feedLocation":"NEWSFEED","feedbackSource":1,"focusCommentID":null,"gridMediaWidth":null,"groupID":null,"scale":1,"useDefaultActor":false}', 'server_timestamps': 'true', 'doc_id': '8167261726632010'}
            self.session.post('https://www.facebook.com/api/graphql/', headers=self.headers, data=data)
        except:
            pass

    def sharend(self, id, msg: str):
        try:
            data = {'av': self.id, 'fb_dtsg': self.fb_dtsg, 'jazoest': self.jazoest, 'variables': '{"input":{"composer_entry_point":"share_modal","composer_source_surface":"feed_story","composer_type":"share","idempotence_token":"' + str(uuid.uuid4()) + '_FEED","source":"WWW","attachments":[{"link":{"share_scrape_data":"{\"share_type\":22,\"share_params\":[' + id + ']}"}}],"reshare_original_post":"RESHARE_ORIGINAL_POST","message":{"ranges":[],"text":"' + msg + '"},"audience":{"privacy":{"allow":[],"base_state":"EVERYONE","deny":[],"tag_expansion_state":"UNSPECIFIED"}},"is_tracking_encrypted":true,"tracking":[null],"actor_id":"' + self.id + '","client_mutation_id":"1"},"feedLocation":"NEWSFEED","feedbackSource":1,"scale":1,"useDefaultActor":false}', 'doc_id': '29449903277934341'}
            self.session.post('https://www.facebook.com/api/graphql/', headers=self.headers, data=data)
        except:
            pass

    def group(self, id):
        try:
            data = {'av': self.id, 'fb_dtsg': self.fb_dtsg, 'jazoest': self.jazoest, 'fb_api_caller_class': 'RelayModern', 'fb_api_req_friendly_name': 'GroupCometJoinForumMutation', 'variables': '{"feedType":"DISCUSSION","groupID":"' + id + '","input":{"action_source":"GROUP_MALL","group_id":"' + id + '","actor_id":"' + self.id + '","client_mutation_id":"1"},"scale":2,"source":"GROUP_MALL","renderLocation":"group_mall"}', 'server_timestamps': 'true', 'doc_id': '5853134681430324'}
            self.session.post('https://www.facebook.com/api/graphql/', headers=self.headers, data=data)
        except:
            pass

    def comment(self, id, msg: str):
        try:
            data = {'av': self.id, 'fb_dtsg': self.fb_dtsg, 'jazoest': self.jazoest, 'fb_api_caller_class': 'RelayModern', 'fb_api_req_friendly_name': 'useCometUFICreateCommentMutation', 'variables': fr'{{"feedLocation":"DEDICATED_COMMENTING_SURFACE","feedbackSource":110,"groupID":null,"input":{{"client_mutation_id":"4","actor_id":"{self.id}","attachments":null,"feedback_id":"{encode_to_base64(f"feedback:{id}")}","formatting_style":null,"message":{{"ranges":[],"text":"{msg}"}},"feedback_source":"DEDICATED_COMMENTING_SURFACE","idempotence_token":"client:{uuid.uuid4()}","session_id":"{uuid.uuid4()}"}},"scale":1,"useDefaultActor":false,"focusCommentID":null}}', 'server_timestamps': 'true', 'doc_id': '7994085080671282'}
            self.session.post('https://www.facebook.com/api/graphql/', headers=self.headers, data=data)
        except:
            pass

    def page_review(self, id, msg: str):
        try:
            data = {'av': self.id, 'fb_dtsg': self.fb_dtsg, 'jazoest': self.jazoest, 'variables': '{"input":{"composer_entry_point":"inline_composer","composer_source_surface":"page_recommendation_tab","source":"WWW","audience":{"privacy":{"allow":[],"base_state":"EVERYONE","deny":[],"tag_expansion_state":"UNSPECIFIED"}},"message":{"ranges":[],"text":"' + msg + '"},"page_recommendation":{"page_id":"' + id + '","rec_type":"POSITIVE"},"actor_id":"' + self.id + '","client_mutation_id":"1"},"feedLocation":"PAGE_SURFACE_RECOMMENDATIONS","scale":1}', 'doc_id': '5737011653023776'}
            self.session.post('https://www.facebook.com/api/graphql/', headers=self.headers, data=data)
        except:
            pass


class FacebookToken():
    def __init__(self, token):
        try:
            self.token = token
            self.cookie = None
            self.session = requests.Session()
            proxy = get_fb_proxy()
            if proxy:
                self.session.proxies.update(proxy)
            self.headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }
            me = self.session.get('https://graph.facebook.com/me', params={'access_token': token, 'fields': 'id,name'}).json()
            self.id = me.get('id', '0')
            self.name = me.get('name', '')
            self.fb_dtsg = ''
            self.jazoest = ''
        except:
            pass

    def info(self):
        try:
            me = self.session.get('https://graph.facebook.com/me', params={'access_token': self.token, 'fields': 'id,name'}).json()
            if 'error' in me:
                return {'status': 'error', 'mess': me['error'].get('message', 'tokenout')}
            id = me.get('id', '0')
            name = me.get('name', '')
            if id == '0': return {'status': 'error', 'mess': 'tokenout'}
            self.id = id
            self.name = name
            return {'status': 'success', 'id': id, 'name': name}
        except:
            return {'status': 'error', 'mess': 'tokenout'}

    def likepage(self, id):
        try:
            self.session.post(f'https://graph.facebook.com/{id}/likes', params={'access_token': self.token})
        except:
            pass

    def follow(self, id):
        return self.addfriend(id)

    def addfriend(self, id):
        try:
            return self.session.post(f'https://graph.facebook.com/{id}/friends', params={'access_token': self.token})
        except:
            pass

    def camxuc(self, id, type):
        try:
            type_map = {'LIKE': 'LIKE', 'LOVE': 'LOVE', 'CARE': 'CARE', 'HAHA': 'HAHA', 'WOW': 'WOW', 'SAD': 'SAD', 'ANGRY': 'ANGRY'}
            self.session.post(f'https://graph.facebook.com/{id}/reactions', params={'access_token': self.token, 'type': type_map.get(type, 'LIKE')})
        except:
            pass

    def camxuccmt(self, id, type):
        try:
            type_map = {'LIKE': 'LIKE', 'LOVE': 'LOVE', 'CARE': 'CARE', 'HAHA': 'HAHA', 'WOW': 'WOW', 'SAD': 'SAD', 'ANGRY': 'ANGRY'}
            self.session.post(f'https://graph.facebook.com/{id}/reactions', params={'access_token': self.token, 'type': type_map.get(type, 'LIKE')})
        except:
            pass

    def share(self, id):
        try:
            self.session.post('https://graph.facebook.com/me/feed', params={'access_token': self.token}, json={'link': f'https://www.facebook.com/{id}'})
        except:
            pass

    def sharend(self, id, msg: str):
        try:
            self.session.post('https://graph.facebook.com/me/feed', params={'access_token': self.token}, json={'link': f'https://www.facebook.com/{id}', 'message': msg})
        except:
            pass

    def group(self, id):
        try:
            self.session.post(f'https://graph.facebook.com/{id}/members', params={'access_token': self.token})
        except:
            pass

    def comment(self, id, msg: str):
        try:
            self.session.post(f'https://graph.facebook.com/{id}/comments', params={'access_token': self.token, 'message': msg})
        except:
            pass

    def page_review(self, id, msg: str):
        try:
            self.session.post(f'https://graph.facebook.com/{id}/ratings', params={'access_token': self.token, 'rating': 5, 'review_text': msg})
        except:
            pass


class Facebook_Page:
    def __init__(self, cookie):
        self.session = requests.Session()
        proxy = get_fb_proxy()
        if proxy:
            self.session.proxies.update(proxy)
        self.fb_dtsg = ''
        self.jazoest = ''
        self.id = cookie.split('c_user=')[1].split(';')[0]
        self.cookie = cookie
        self.headers = {
            'authority': 'www.facebook.com', 
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 
            'accept-language': 'vi', 
            'sec-ch-prefers-color-scheme': 'light', 
            'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"', 
            'sec-ch-ua-mobile': '?0', 
            'sec-ch-ua-platform': '"Windows"', 
            'sec-fetch-dest': 'document', 
            'sec-fetch-mode': 'navigate', 
            'sec-fetch-site': 'none', 
            'sec-fetch-user': '?1', 
            'upgrade-insecure-requests': '1', 
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
            'Cookie': self.cookie
        }
        url = self.session.get(f'https://www.facebook.com/{self.id}', headers=self.headers).url
        response = self.session.get(url, headers=self.headers).text
        matches = re.findall(r'\["DTSGInitialData",\[\],\{"token":"(.*?)"\}', response)
        if len(matches) > 0:
            self.fb_dtsg += matches[0]
            self.jazoest += re.findall(r'jazoest=(.*?)\"', response)[0]
        self.headerspage = self.headers.copy()

    def get_profile(self):
        data = {
            'fb_dtsg': self.fb_dtsg,
            'jazoest': self.jazoest,
            'variables': '{"showUpdatedLaunchpointRedesign":true,"useAdminedPagesForActingAccount":false,"useNewPagesYouManage":true}',
            'doc_id': '5300338636681652'
        }
        response = self.session.post('https://www.facebook.com/api/graphql/', headers=self.headers, data=data).json()
        return response
    
    def info_page(self, cookie):
        try:
            self.headerspage = {
                'authority': 'www.facebook.com', 
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 
                'accept-language': 'vi', 
                'sec-ch-prefers-color-scheme': 'light', 
                'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"', 
                'sec-ch-ua-mobile': '?0', 
                'sec-ch-ua-platform': '"Windows"', 
                'sec-fetch-dest': 'document', 
                'sec-fetch-mode': 'navigate', 
                'sec-fetch-site': 'none', 
                'sec-fetch-user': '?1', 
                'upgrade-insecure-requests': '1', 
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
                'Cookie': cookie
            }
            get = self.session.get('https://www.facebook.com/me', headers=self.headerspage).url
            url = 'https://www.facebook.com/' + get.split('%2F')[-2] + '/' if 'next=' in get else get
            response = self.session.get(url, headers=self.headerspage, params={"locale": "vi_VN"})
            data_split = response.text.split('"CurrentUserInitialData",[],{')
            json_data = '{' + data_split[1].split('},')[0] + '}'
            parsed_data = json.loads(json_data)
            id = parsed_data.get('USER_ID', '0')
            name = parsed_data.get('NAME', '')
            if id == '0' and name == '': return 'cookieout'
            elif '828281030927956' in response.text: return '956'
            elif '1501092823525282' in response.text: return '282'
            elif '601051028565049' in response.text: return 'spam'
            else:
                self.actor_id = parsed_data.get('USER_ID')
                self.actor_name = parsed_data.get('NAME')
                try:
                    page_url = self.session.get(f'https://www.facebook.com/{self.actor_id}', headers=self.headerspage).url
                    page_resp = self.session.get(page_url, headers=self.headerspage).text
                    dtsg_matches = re.findall(r'\["DTSGInitialData",\[\],\{"token":"(.*?)"\}', page_resp)
                    if dtsg_matches:
                        self.fb_dtsg = dtsg_matches[0]
                        jaz = re.findall(r'jazoest=(.*?)\"', page_resp)
                        if jaz: self.jazoest = jaz[0]
                except:
                    pass
                return {'status': 'success', 'id': self.actor_id, 'name': self.actor_name}
        except:
            return 'cookieout'

    def info(self, page_id=None):
        try:
            target = page_id if page_id else self.id
            response = self.session.get(f'https://www.facebook.com/{target}', headers=self.headers).text
            if 'error' in response.lower() or len(response) < 100:
                return {'status': 'error', 'mess': 'cookieout'}
            return {'status': 'success'}
        except:
            return {'status': 'error', 'mess': 'cookieout'}

    def camxuc(self, actor_id, id, type):
        try:
            reac = {"LIKE": "1635855486666999","LOVE": "1678524932434102","CARE": "613557422527858","HAHA": "115940658764963","WOW": "478547315650144","SAD": "908563459236466","ANGRY": "444813342392137"}
            data = {'av': actor_id,'fb_dtsg': self.fb_dtsg,'jazoest': self.jazoest,'fb_api_caller_class': 'RelayModern','fb_api_req_friendly_name': 'CometUFIFeedbackReactMutation','variables': fr'{{"input":{{"attribution_id_v2":"CometHomeRoot.react,comet.home,tap_tabbar,1719027162723,322693,4748854339,,","feedback_id":"{encode_to_base64("feedback:"+str(id))}","feedback_reaction_id":"{reac.get(type)}","feedback_source":"NEWS_FEED","is_tracking_encrypted":true,"tracking":["AZWUDdylhKB7Q-Esd2HQq9i7j4CmKRfjJP03XBxVNfpztKO0WSnXmh5gtIcplhFxZdk33kQBTHSXLNH-zJaEXFlMxQOu_JG98LVXCvCqk1XLyQqGKuL_dCYK7qSwJmt89TDw1KPpL-BPxB9qLIil1D_4Thuoa4XMgovMVLAXncnXCsoQvAnchMg6ksQOIEX3CqRCqIIKd47O7F7PYR1TkMNbeeSccW83SEUmtuyO5Jc_wiY0ZrrPejfiJeLgtk3snxyTd-JXW1nvjBRjfbLySxmh69u-N_cuDwvqp7A1QwK5pgV49vJlHP63g4do1q6D6kQmTWtBY7iA-beU44knFS7aCLNiq1aGN9Hhg0QTIYJ9rXXEeHbUuAPSK419ieoaj4rb_4lA-Wdaz3oWiWwH0EIzGs0Zj3srHRqfR94oe4PbJ6gz5f64k0kQ2QRWReCO5kpQeiAd1f25oP9yiH_MbpTcfxMr-z83luvUWMF6K0-A-NXEuF5AiCLkWDapNyRwpuGMs8FIdUJmPXF9TGe3wslF5sZRVTKAWRdFMVAsUn-lFT8tVAZVvd4UtScTnmxc1YOArpHD-_Lzt7NDdbuPQWQohqkGVlQVLMoJNZnF_oRLL8je6-ra17lJ8inQPICnw7GP-ne_3A03eT4zA6YsxCC3eIhQK-xyodjfm1j0cMvydXhB89fjTcuz0Uoy0oPyfstl7Sm-AUoGugNch3Mz2jQAXo0E_FX4mbkMYX2WUBW2XSNxssYZYaRXC4FUIrQoVhAJbxU6lomRQIPY8aCS0Ge9iUk8nHq4YZzJgmB7VnFRUd8Oe1sSSiIUWpMNVBONuCIT9Wjipt1lxWEs4KjlHk-SRaEZc_eX4mLwS0RcycI8eXg6kzw2WOlPvGDWalTaMryy6QdJLjoqwidHO21JSbAWPqrBzQAEcoSau_UHC6soSO9UgcBQqdAKBfJbdMhBkmxSwVoxJR_puqsTfuCT6Aa_gFixolGrbgxx5h2-XAARx4SbGplK5kWMw27FpMvgpctU248HpEQ7zGJRTJylE84EWcVHMlVm0pGZb8tlrZSQQme6zxPWbzoQv3xY8CsH4UDu1gBhmWe_wL6KwZJxj3wRrlle54cqhzStoGL5JQwMGaxdwITRusdKgmwwEQJxxH63GvPwqL9oRMvIaHyGfKegOVyG2HMyxmiQmtb5EtaFd6n3JjMCBF74Kcn33TJhQ1yjHoltdO_tKqnj0nPVgRGfN-kdJA7G6HZFvz6j82WfKmzi1lgpUcoZ5T8Fwpx-yyBHV0J4sGF0qR4uBYNcTGkFtbD0tZnUxfy_POfmf8E3phVJrS__XIvnlB5c6yvyGGdYvafQkszlRrTAzDu9pH6TZo1K3Jc1a-wfPWZJ3uBJ_cku-YeTj8piEmR-cMeyWTJR7InVB2IFZx2AoyElAFbMuPVZVp64RgC3ugiyC1nY7HycH2T3POGARB6wP4RFXybScGN4OGwM8e3W2p-Za1BTR09lHRlzeukops0DSBUkhr9GrgMZaw7eAsztGlIXZ_4"],"session_id":"{uuid.uuid4()}","actor_id":"{actor_id}","client_mutation_id":"3"}},"useDefaultActor":false,"__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider":false}}','server_timestamps': 'true','doc_id': '7047198228715224',}
            self.session.post('https://www.facebook.com/api/graphql/',headers=self.headerspage, data=data)
        except:
            pass

    def camxuccmt(self, actor_id, id, type):
        try:
            reac = {"LIKE": "1635855486666999","LOVE": "1678524932434102","CARE": "613557422527858","HAHA": "115940658764963","WOW": "478547315650144","SAD": "908563459236466","ANGRY": "444813342392137"}
            g_now = datetime.now()
            d = g_now.strftime("%Y-%m-%d %H:%M:%S.%f")
            datetime_object = datetime.strptime(d, "%Y-%m-%d %H:%M:%S.%f")
            timestamp = str(datetime_object.timestamp())
            starttime = timestamp.replace('.', '')
            data = {'av': actor_id,'fb_dtsg': self.fb_dtsg,'jazoest': self.jazoest,'fb_api_caller_class': 'RelayModern','fb_api_req_friendly_name': 'CometUFIFeedbackReactMutation','variables': '{"input":{"attribution_id_v2":"CometVideoHomeNewPermalinkRoot.react,comet.watch.injection,via_cold_start,1719930662698,975645,2392950137,,","feedback_id":"'+encode_to_base64("feedback:"+str(id))+'","feedback_reaction_id":"'+reac.get(type)+'","feedback_source":"TAHOE","is_tracking_encrypted":true,"tracking":[],"session_id":"'+str(uuid.uuid4())+'","downstream_share_session_id":"'+str(uuid.uuid4())+'","downstream_share_session_origin_uri":"https://fb.watch/t3OatrTuqv/?mibextid=Nif5oz","downstream_share_session_start_time":"'+starttime+'","actor_id":"'+actor_id+'","client_mutation_id":"1"},"useDefaultActor":false,"__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider":false}', 'server_timestamps': 'true','doc_id': '7616998081714004',}
            self.session.post('https://www.facebook.com/api/graphql/',headers=self.headerspage, data=data)
        except:
            pass

    def share(self, actor_id, id):
        try:
            data = {'av': actor_id,'fb_dtsg': self.fb_dtsg,'jazoest': self.jazoest,'fb_api_caller_class': 'RelayModern','fb_api_req_friendly_name': 'ComposerStoryCreateMutation','variables': '{"input":{"composer_entry_point":"share_modal","composer_source_surface":"feed_story","composer_type":"share","idempotence_token":"'+str(uuid.uuid4())+'_FEED","source":"WWW","attachments":[{"link":{"share_scrape_data":"{\\"share_type\\":22,\\"share_params\\":['+id+']}"}}],"reshare_original_post":"RESHARE_ORIGINAL_POST","audience":{"privacy":{"allow":[],"base_state":"EVERYONE","deny":[],"tag_expansion_state":"UNSPECIFIED"}},"is_tracking_encrypted":true,"tracking":["AZWWGipYJ1gf83pZebtJYQQ-iWKc5VZxS4JuOcGWLeB-goMh2k74R1JxqgvUTbDVNs-xTyTpCI4vQw_Y9mFCaX-tIEMg2TfN_GKk-PnqI4xMhaignTkV5113HU-3PLFG27m-EEseUfuGXrNitybNZF1fKNtPcboF6IvxizZa5CUGXNVqLISUtAWXNS9Lq-G2ECnfWPtmKGebm2-YKyfMUH1p8xKNDxOcnMmMJcBBZkUEpjVzqvUTSt52Xyp0NETTPTVW4zHpkByOboAqZj12UuYSsG3GEhafpt91ThFhs7UTtqN7F29UsSW2ikIjTgFPy8cOddclinOtUwaoMaFk2OspLF3J9cwr7wPsZ9CpQxU21mcFHxqpz7vZuGrjWqepKQhWX_ZzmHv0LR8K07ZJLu8yl51iv-Ram7er9lKfWDtQsuNeLqbzEOQo0UlRNexaV0V2m8fYke8ubw3kNeR5XsRYiyr958OFwNgZ3RNfy-mNnO9P-4TFEF12NmNNEm4N6h0_DRZ-g74n-X2nGwx9emPv4wuy9kvQGeoCqc636BfKRE-51w2GFSrHAsOUJJ1dDryxZsxQOEGep3HGrVp_rTsVv7Vk3JxKxlzqt3hnBGDgi6suTZnJw69poVOIz6TPCTthRhj7XUu4heyKBSIeHsjBRC2_s3NwuZ4kKNCQ2JkVuBXz_hsRhDmbAnBi6WUFIJhLHO_bGgKbEASuU4vtj4FNKo_G8p-J1kYmCo0Pi72Csi3EikuocfjHFwfSD3cCbetr3V8Yp6OmSGkqX63FkSqzBoAcHFeD-iyCAkn0UJGqU-0o670ZoR-twkUDcSJPXDN2NYQfqiyb9ZknZ7j04w1ZfAyaE7NCiCc-lDt1ic79XyHunjOyLStgXIW30J4OEw_hAn86LlRHbYVhi-zBBTZWWnEl9piuUz0qtnN-qEd002DjNYaMy0aDAbL9oOYDdN8mHvnXq1aKove9I4Jy0WtlxeN8279ayz7NdDZZ9LrajY_YxIJJqdZtJIuRYTunEeDsFrORpu3RYRbFwpGnQbHeSLH1YvwOyOJRXhYYmVLJEGD2N9r5wkPbgbx2HoWsGjWj_DpkEAyg59eBJy4RYPJHvOsetBQABEWmGI7nhUDYTPdhrzVxqB_g4fQ9JkPzIbEhcoEZjmspGZcR4z4JxUDJCNdAz2aK4lR4P5WTkLtj2uXMDD_nzbl8r_DMcj23bjPiSe0Fubu-VIzjwr7JgPNyQ1FYhp5u4lpqkkBkGtfyAaUjCgFhg4FW-H3d3vPVMO--GxbhK9kN0QAcOE3ZqQR2dRz6NbhcvTyNfDxy0dFTRw-f-vxn04gjJB5ZEG3WfSzQv0VbqDYm6-NFYAzIxbDLoiCu34WAa2lckx5qxncXBhQj6Fro2gXGPXo4d32DvqQg7_RHQ-SF_WLqdxRCXF91NIqxYmFZsOJAuQ5m6TafzuNnQoJB3OQFoknv8Uy5O4FKuwazh1rvLrsj-1QEMi3sTrr9KxJkZy9EKXs92ndlb3edgfycLOffTil-gW2BvxeNiMQzqF1xJqFBKHDyatgwpXDX81HDwxkuMEaGPREIeQLuOlBJrL_20RD1e4Gu4tjQD8vRsb29UNG60DqpDvc-H4Z2oxeppm0KIwQNaCTtGUxxmvT807fXMnuVEf5QI5qTx9YRJh56GiWLoHC_zPMhoikMbAybIVWh9HtVgZGgImDmz0l9P4LgtpKNnKbQj_2ZKn2ZhOYKZLdt1P2Jq2Z2z76MtbRQTrpZpFb14zWVnh1LFCSFPAB7sqC1-u-KQOf2_SjEecztPccso8xZB2nkhLetyPn9aFuO-J_LCZydQeiroXx4Z8NxhDpbLoOpw2MbRCVB_TxfnLGNn1QD0To9TTChxK5AHNRRLDaj3xK1e0jd37uSmHTkT6QJVHFHEYMVLBcuV1MQcoy0wsvc1sRb",null],"logging":{"composer_session_id":"'+str(uuid.uuid4())+'"},"navigation_data":{"attribution_id_v2":"FeedsCometRoot.react,comet.most_recent_feed,tap_bookmark,1719641912186,189404,608920319153834,,"},"event_share_metadata":{"surface":"newsfeed"},"actor_id":"'+actor_id+'","client_mutation_id":"3"},"feedLocation":"NEWSFEED","feedbackSource":1,"focusCommentID":null,"gridMediaWidth":null,"groupID":null,"scale":1,"privacySelectorRenderLocation":"COMET_STREAM","checkPhotosToReelsUpsellEligibility":false,"renderLocation":"homepage_stream","useDefaultActor":false,"inviteShortLinkKey":null,"isFeed":true,"isFundraiser":false,"isFunFactPost":false,"isGroup":false,"isEvent":false,"isTimeline":false,"isSocialLearning":false,"isPageNewsFeed":false,"isProfileReviews":false,"isWorkSharedDraft":false,"hashtag":null,"canUserManageOffers":false,"__relay_internal__pv__CometIsAdaptiveUFIEnabledrelayprovider":true,"__relay_internal__pv__CometUFIShareActionMigrationrelayprovider":true,"__relay_internal__pv__IncludeCommentWithAttachmentrelayprovider":true,"__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider":false,"__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider":false,"__relay_internal__pv__IsWorkUserrelayprovider":false,"__relay_internal__pv__IsMergQAPollsrelayprovider":false,"__relay_internal__pv__StoriesArmadilloReplyEnabledrelayprovider":true,"__relay_internal__pv__StoriesRingrelayprovider":false,"__relay_internal__pv__EventCometCardImage_prefetchEventImagerelayprovider":false}','server_timestamps': 'true','doc_id': '8167261726632010'}
            self.session.post("https://www.facebook.com/api/graphql/",headers=self.headerspage, data=data)
        except:
            pass

    def sharend(self, actor_id, id, msg):
        try:
            data = {'av':actor_id,'fb_dtsg': self.fb_dtsg,'jazoest': self.jazoest,'variables': '{"input":{"composer_entry_point":"share_modal","composer_source_surface":"feed_story","composer_type":"share","idempotence_token":"'+str(uuid.uuid4())+'_FEED","source":"WWW","attachments":[{"link":{"share_scrape_data":"{\"share_type\":22,\"share_params\":['+id+']}"}}],"reshare_original_post":"RESHARE_ORIGINAL_POST","audience":{"privacy":{"allow":[],"base_state":"EVERYONE","deny":[],"tag_expansion_state":"UNSPECIFIED"}},"is_tracking_encrypted":true,"tracking":["AZXEWGOa5BgU9Y4vr1ZzQbWSdaLzfI3EMNtpYwO1FzzHdeHKOCyc4dd677vkeHFmNfgBKbJ7vHSB96dnQh4fQ0-dZB3zHFN1qxxhg5F_1K8RShMHcVDNADUhhRzdkG2C6nujeGpnPkw0d1krhlgwq2xFc1lM0OLqo_qr2lW9Oci9BzC3ZkT3Jqt1m8-2vpAKwqUvoSfSrma8Y5zA1x9ZF0HLeHojOeodv_w5-S9hcdgy3gvF5o4lTdzfp3leby36PkwOyJqCOI51h6jp-cH0WUubXMbH2bVM-v9Mv7kHw9_yC8dP5b_tjerx7ggHtnhr1KtOEiolPmCkQiapP5dX9phUaW908T9Kh1aDk4sK7cd7QfVaGj6LSOiHS599VsgvvbHopOVxH80a96LkuhH4t0DLc8QjljGwAmublnMVuvUbVaiChuyjzAIQe-xj2C7yMGzxmOacqR7yaepDUI-fpRZAzkcfVUdumVzbjWtCYGZLJgw4lAKVv6Y37tBedtAGHF7P7EEdQSXOX6ADg0cEYUeusp9Oho1SAbz_rVGiJc-oSkWY6S2XwD5vBXwV9lfdg6vuH3DKDcIDDoua3xXN7sYbVOw3ClcTbxMAmQqE8ClYrlbIXNp-QCW2Rr_3ro3VgYqNo1UkRyDXgCHs8rWUNY6N-bhMWCHI9CPOEebbqXnSRayKmgxYrDOIuHIzyHujUBYLnEikCYIfVwaeEB4X-Et3ZZvgoHdaZAhSO3YNFLYjyimb1tR8A-Pm2KoKwIF6equnjWWLHKoovFhbhQLRmjYYBJUhP4n0yLunWLnPwn8e7ev9h4fsGMREmonEbizxwrsr1bqpDBrHWliiPTPHDdlJNVko7anmeT1txjmTaOrA8oejbs1hDeNEZoEuL2vkN7HdjiJFhLu2yTNw2Rc3WHHOb8FcFlwTOzCDUHGDbv_bV8iAlybhEZFE-3kmoMrw7kXPjwC8D_x4VRW1BQ1wVEsYFjBrLOjk05nsuuU0Xa5D5DJi3zrL3bET2eGIIlbXdXvn57Q2JtCnnS0uRyaB2pHghXTkrT2l_1fPqTJIhJOi6YQDymf2paNIUd1Fe3fDZBp1D4VMsNphQr4mSIANKGHZP29cmWJox94ztH7mrLIhSRiSzs_DrTb5o5YH6AwBkg9XzNdlM7uMxAPB9lbqVAPWXEBANhoAHvYjQI1-61myVarQBrk36dbz15PASG1c5Fina9vATWju6Bfj7PjoqJ4rARcZBJOO011e2eLy4yekMuG8bD5TvEwuiRn_M23iuC-k_w77abKvcW4MJX1f4Gfv9S4C_8N4pSiWOPNRgHPJWEQ6vhhu3euzWVSKYJ5jmfeqA9jFd_U6qVkEXenI0ofFBXw-fzjoWoRHy5y8xBG9qg",null],"message":{"ranges":[],"text":"'+msg+'"},"logging":{"composer_session_id":"'+str(uuid.uuid4())+'"},"navigation_data":{"attribution_id_v2":"CometSinglePostDialogRoot.react,comet.post.single_dialog,via_cold_start,1743945123087,176702,,,"},"event_share_metadata":{"surface":"newsfeed"},"actor_id":"'+actor_id+'","client_mutation_id":"1"},"feedLocation":"NEWSFEED","feedbackSource":1,"focusCommentID":null,"gridMediaWidth":null,"groupID":null,"scale":1,"privacySelectorRenderLocation":"COMET_STREAM","checkPhotosToReelsUpsellEligibility":false,"renderLocation":"homepage_stream","useDefaultActor":false,"inviteShortLinkKey":null,"isFeed":true,"isFundraiser":false,"isFunFactPost":false,"isGroup":false,"isEvent":false,"isTimeline":false,"isSocialLearning":false,"isPageNewsFeed":false,"isProfileReviews":false,"isWorkSharedDraft":false,"hashtag":null,"canUserManageOffers":false,"__relay_internal__pv__CometUFIShareActionMigrationrelayprovider":true,"__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider":false,"__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider":false,"__relay_internal__pv__CometIsReplyPagerDisabledrelayprovider":false,"__relay_internal__pv__IsWorkUserrelayprovider":false,"__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider":false,"__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider":true,"__relay_internal__pv__CometFeedStoryDynamicResolutionPhotoAttachmentRenderer_experimentWidthrelayprovider":500,"__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider":false,"__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider":false,"__relay_internal__pv__IsMergQAPollsrelayprovider":false,"__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider":true,"__relay_internal__pv__StoriesArmadilloReplyEnabledrelayprovider":false,"__relay_internal__pv__CometFeedPYMKHScrollInitialPaginationCountrelayprovider":10,"__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider":true,"__relay_internal__pv__GHLShouldChangeSponsoredAuctionDistanceFieldNamerelayprovider":true}','doc_id': '29449903277934341'}
            self.session.post('https://www.facebook.com/api/graphql/',headers=self.headerspage, data=data)
        except: 
            pass

    def follow(self, actor_id, id):
        return self.addfriend(actor_id, id)

    def addfriend(self, actor_id, id):
        try:
            data = {
                'av': actor_id,
                'fb_dtsg': self.fb_dtsg,
                'jazoest': self.jazoest,
                'fb_api_caller_class': 'RelayModern',
                'fb_api_req_friendly_name': 'FriendingCometFriendRequestSendMutation',
                'variables': '{"input":{"click_correlation_id":"' + str(int(datetime.now().timestamp()*1000)) + '","click_proof_validation_result":"{\\\"validated\\\":true}","friend_requestee_ids":["' + str(id) + '"],"friending_channel":"PROFILE_BUTTON","warn_ack_for_ids":[],"actor_id":"' + str(actor_id) + '","client_mutation_id":"1"},"scale":1}',
                'server_timestamps': 'true',
                'doc_id': '35889183907395315'
            }
            return self.session.post('https://www.facebook.com/api/graphql/', headers=self.headerspage, data=data)
        except:
            pass

    def likepage(self, actor_id, id):
        try:
            data = {'av': actor_id,'fb_dtsg': self.fb_dtsg,'jazoest': self.jazoest,'fb_api_caller_class': 'RelayModern','fb_api_req_friendly_name': 'CometProfilePlusLikeMutation','variables': '{"input":{"is_tracking_encrypted":false,"page_id":"'+str(id)+'","source":null,"tracking":null,"actor_id":"'+str(actor_id)+'","client_mutation_id":"1"},"scale":1}', 'server_timestamps': 'true','doc_id': '6716077648448761',}
            self.session.post('https://www.facebook.com/api/graphql/',headers=self.headerspage, data=data)
        except:
            pass

    def group(self, actor_id, id):
        try:
            data = {'av': actor_id,'fb_dtsg': self.fb_dtsg,'jazoest': self.jazoest,'fb_api_caller_class': 'RelayModern','fb_api_req_friendly_name':'GroupCometJoinForumMutation','variables':'{"feedType":"DISCUSSION","groupID":"'+id+'","input":{"action_source":"GROUP_MALL","group_id":"'+id+'","actor_id":"'+actor_id+'","client_mutation_id":"1"},"scale":2,"source":"GROUP_MALL","renderLocation":"group_mall"}', 'server_timestamps': 'true','doc_id': '5853134681430324',}
            self.session.post('https://www.facebook.com/api/graphql/',headers=self.headerspage, data=data)
        except:
            pass

    def comment(self, actor_id, id, msg: str):
        try:
            data = {'av': actor_id,'fb_dtsg': self.fb_dtsg,'jazoest': self.jazoest,'fb_api_caller_class': 'RelayModern','fb_api_req_friendly_name': 'useCometUFICreateCommentMutation','variables': fr'{{"feedLocation":"DEDICATED_COMMENTING_SURFACE","feedbackSource":110,"groupID":null,"input":{{"client_mutation_id":"4","actor_id":"{actor_id}","attachments":null,"feedback_id":"{encode_to_base64(f"feedback:{id}")}","formatting_style":null,"message":{{"ranges":[],"text":"{msg}"}},"feedback_source":"DEDICATED_COMMENTING_SURFACE","idempotence_token":"client:{uuid.uuid4()}","session_id":"{uuid.uuid4()}"}},"scale":1,"useDefaultActor":false,"focusCommentID":null}}', 'server_timestamps': 'true','doc_id': '7994085080671282',}
            self.session.post('https://www.facebook.com/api/graphql/', headers=self.headerspage, data=data)
        except:
            pass

    def page_review(self, actor_id, id, msg: str):
        try:
            data = {'av': actor_id,'fb_dtsg': self.fb_dtsg,'jazoest': self.jazoest,'variables': '{"input":{"composer_entry_point":"inline_composer","composer_source_surface":"page_recommendation_tab","source":"WWW","audience":{"privacy":{"allow":[],"base_state":"EVERYONE","deny":[],"tag_expansion_state":"UNSPECIFIED"}},"message":{"ranges":[],"text":"' +msg+ '"},"page_recommendation":{"page_id":"'+id+'","rec_type":"POSITIVE"},"actor_id":"'+actor_id+'","client_mutation_id":"1"},"feedLocation":"PAGE_SURFACE_RECOMMENDATIONS","scale":1}', 'doc_id': '5737011653023776'}
            self.session.post('https://www.facebook.com/api/graphql/',headers=self.headerspage, data=data)
        except:
            pass


class TTC_Facebook():
    def __init__(self, token):
        try:
            self.session = requests.Session()
            proxy = get_ttc_proxy()
            if proxy:
                self.session.proxies.update(proxy)
            self.response = self.session.post('https://tuongtaccheo.com/logintoken.php',headers={'Content-type': 'application/x-www-form-urlencoded'},data={'access_token': token})
            self.cookie = self.response.headers['Set-cookie']
            self.thongtin = self.response.json()
            self.headers = {
                'Host': 'tuongtaccheo.com',
                'accept': '*/*',
                'origin': 'https://tuongtaccheo.com',
                'x-requested-with': 'XMLHttpRequest',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                "cookie": self.cookie
            }
        except:
            pass

    def info(self):
        if self.thongtin.get('status') == 'success':
            return self.thongtin
        else:
            return {'status': 'error', 'mess': self.thongtin.get('mess', str(self.thongtin))}
        
    def cauhinh(self, id):
        sleep(3)

        def _nhapnick(link_value: str):
            with nhapnick_lock:
                res = self.session.post(
                    'https://tuongtaccheo.com/cauhinh/nhapnick.php',
                    headers={
                        **self.headers,
                        'sec-ch-ua-platform': '"Android"',
                        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36',
                        'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
                        'sec-ch-ua-mobile': '?1',
                        'sec-fetch-site': 'same-origin',
                        'sec-fetch-mode': 'cors',
                        'sec-fetch-dest': 'empty',
                        'referer': 'https://tuongtaccheo.com/cauhinh/facebook.php',
                    },
                    data={'link': link_value, 'loainick': 'fb', 'recaptcha': '1'}
                ).text.strip()
                if 'Đợi' in res or 'đợi' in res:
                    import re
                    nums = re.findall(r'\d+', res)
                    wait = int(nums[0]) if nums else 5
                    with print_lock:
                        print(f'{trang}[{xanh}TTC{trang}] {vang}Chờ {wait}s...', end='\r')
                    sleep(wait + 1)
                    res = self.session.post(
                        'https://tuongtaccheo.com/cauhinh/nhapnick.php',
                        headers={
                            **self.headers,
                            'sec-ch-ua-platform': '"Android"',
                            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36',
                            'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
                            'sec-ch-ua-mobile': '?1',
                            'sec-fetch-site': 'same-origin',
                            'sec-fetch-mode': 'cors',
                            'sec-fetch-dest': 'empty',
                            'referer': 'https://tuongtaccheo.com/cauhinh/facebook.php',
                        },
                        data={'link': link_value, 'loainick': 'fb', 'recaptcha': '1'}
                    ).text.strip()
                sleep(6)
                return res

        def _datnick_once():
            return self.session.post(
                'https://tuongtaccheo.com/cauhinh/datnick.php',
                headers=self.headers,
                data={'iddat[]': id, 'loai': 'fb'}
            ).text.strip()

        def _datnick_with_retry(tries: int = 4, delay: int = 4):
            print(f'{trang}[{xanh}TTC{trang}] {vang}Đang cấu hình: {xanh}{id}', '          ', end=chr(13))
            last = _datnick_once()
            if last == '1':
                return {'status': 'success', 'id': id}
            if last == '3':
                return {'status': 'yeucau', 'response': '3'}
            for _ in range(max(tries - 1, 0)):
                if last in ('2', '') or 'Vui lòng thao tác chậm lại' in str(last):
                    print(f'{trang}[{xanh}TTC{trang}] {do}Cấu hình chậm lại, thử lại...', '          ', end=chr(13))
                    sleep(delay)
                    delay = min(delay + 2, 12)
                    last = _datnick_once()
                    if last == '1':
                        return {'status': 'success', 'id': id}
                    if last == '3':
                        return {'status': 'yeucau', 'response': '3'}
                else:
                    break
            return {'error': 200, 'response': last}

        print(f'{trang}[{xanh}TTC{trang}] {vang}Nhập nick UID: {xanh}{id}', '          ', end=chr(13))
        r1 = _nhapnick(str(id))
        print(f'{trang}[{xanh}TTC{trang}] {vang}UID {xanh}{id} {do}=> {luc}{r1}')

        if r1 == '1':
            sleep(3)
            d1 = _datnick_with_retry()
            if d1.get('status') == 'success':
                print(f'{trang}[{xanh}TTC{trang}] {vang}{id} {do}-> {luc}Thành Công')
                return d1
            if d1.get('status') == 'yeucau':
                print(f'{trang}[{xanh}TTC{trang}] {do}[{vang}{id}{do}] Nick Chưa Đủ Yêu Cầu')
                return d1
            print(f'{trang}[{xanh}TTC{trang}] {vang}{id} {do}-> {do}Thất Bại {trang}-> {do}{d1.get("response")}')
        elif r1 == '0':
            sleep(3)
            print(f'{trang}[{xanh}TTC{trang}] {vang}UID lỗi, thử Link: {xanh}https://www.facebook.com/{id}', '          ', end=chr(13))
            r2 = _nhapnick(f'https://www.facebook.com/{id}')
            print(f'{trang}[{xanh}TTC{trang}] {vang}Link {xanh}{id} {do}=> {luc}{r2}')
            sleep(3)
            d2 = _datnick_with_retry()
            if d2.get('status') == 'success':
                print(f'{trang}[{xanh}TTC{trang}] {vang}{id} {do}-> {luc}Thành Công')
                return d2
            if d2.get('status') == 'yeucau':
                print(f'{trang}[{xanh}TTC{trang}] {do}[{vang}{id}{do}] Nick Chưa Đủ Yêu Cầu')
                return d2
            print(f'{trang}[{xanh}TTC{trang}] {vang}{id} {do}-> {do}Thất Bại {trang}-> {do}{d2.get("response")}')
        else:
            sleep(3)
            d3 = _datnick_with_retry()
            if d3.get('status') == 'success':
                print(f'{trang}[{xanh}TTC{trang}] {vang}{id} {do}-> {luc}Thành Công')
                return d3
            if d3.get('status') == 'yeucau':
                print(f'{trang}[{xanh}TTC{trang}] {do}[{vang}{id}{do}] Nick Chưa Đủ Yêu Cầu')
                return d3
            print(f'{trang}[{xanh}TTC{trang}] {vang}{id} {do}-> {do}Thất Bại {trang}-> {do}{d3.get("response")}')

        return {'error': 200, 'step': 'cauhinh_failed', 'nhapnick': r1}
        
    def getjob(self, nv, nickchay=None):
        url = f'https://tuongtaccheo.com/kiemtien/{nv}/getpost.php'
        if nickchay:
            url += f'?nickchay={nickchay}'
        response = self.session.get(url, headers=self.headers)
        return response
    
    def nhanxu(self, id, nv, nickchay=None):
        xu_truoc = self.session.get('https://tuongtaccheo.com/home.php', headers=self.headers).text.split('"soduchinh">')[1].split('<')[0]
        data = {'id': id}
        if nickchay:
            data['nickchay'] = nickchay
        response = self.session.post(f'https://tuongtaccheo.com/kiemtien/{nv}/nhantien.php', headers=self.headers, data=data).json()
        xu_sau = self.session.get('https://tuongtaccheo.com/home.php', headers=self.headers).text.split('"soduchinh">')[1].split('<')[0]
        if 'mess' in response and int(xu_sau) > int(xu_truoc):
            parts = response['mess'].split()
            msg = parts[-2]
            return {'status': "success", 'msg': '+'+msg+' Xu', 'xu': xu_sau} 
        else:
            return {'error': response}

# ==================== CÁC HÀM CÒN LẠI ====================

def split_cookies_for_ttc(cookies_list, num_ttc_accounts):
    if not cookies_list or num_ttc_accounts <= 0:
        return {}
    if len(cookies_list) <= num_ttc_accounts:
        result = {}
        for i in range(num_ttc_accounts):
            if i < len(cookies_list):
                result[i] = [cookies_list[i]]
            else:
                result[i] = []
        return result
    cookies_per_ttc = len(cookies_list) // num_ttc_accounts
    remainder = len(cookies_list) % num_ttc_accounts
    result = {}
    start_idx = 0
    for i in range(num_ttc_accounts):
        extra = 1 if i < remainder else 0
        end_idx = start_idx + cookies_per_ttc + extra
        result[i] = cookies_list[start_idx:end_idx]
        start_idx = end_idx
    return result

def split_cookies_by_strategy(cookies_list, ttc_accounts, strategy='balance'):
    num_ttc = len(ttc_accounts)
    if strategy == 'balance':
        split_result = split_cookies_for_ttc(cookies_list, num_ttc)
        result = {}
        for i, ttc_acc in enumerate(ttc_accounts):
            result[ttc_acc['user']] = split_result.get(i, [])
        return result
    elif strategy == 'round_robin':
        result = {acc['user']: [] for acc in ttc_accounts}
        for idx, cookie in enumerate(cookies_list):
            ttc_idx = idx % num_ttc
            result[ttc_accounts[ttc_idx]['user']].append(cookie)
        return result
    elif strategy == 'all':
        result = {acc['user']: cookies_list.copy() for acc in ttc_accounts}
        return result
    else:
        split_result = split_cookies_for_ttc(cookies_list, num_ttc)
        result = {}
        for i, ttc_acc in enumerate(ttc_accounts):
            result[ttc_acc['user']] = split_result.get(i, [])
        return result

def display_split_result(split_result, ttc_accounts, total_cookies):
    thanhngang(60)
    print(f'{luc}=== KẾT QUẢ PHÂN CHIA COOKIE ===')
    total = 0
    for acc in ttc_accounts:
        user = acc['user']
        count = len(split_result.get(user, []))
        total += count
        print(f'{trang}- {vang}{user}{trang}: {xanh}{count} cookie')
        if count > 0:
            sample_cookies = split_result.get(user, [])[:2]
            for c in sample_cookies:
                try:
                    uid = c.split('c_user=')[1].split(';')[0] if 'c_user=' in c else 'unknown'
                    uid_show = uid[:3] + '***' + uid[-3:] if len(uid) > 6 else uid
                    print(f'        {trang}- UID: {xanh}{uid_show}')
                except:
                    pass
            if count > 2:
                print(f'        {trang}... và {count - 2} cookie khác')
    print(f'{trang}{"-"*50}')
    print(f'{trang}Tổng: {vang}{total}/{total_cookies} cookie')
    thanhngang(60)

# ==================== ĐA TÀI KHOẢN TTC ====================

def login_ttc_account(token):
    try:
        ttc_temp = TTC_Facebook(token)
        info = ttc_temp.info()
        if info['status'] == 'success':
            return {
                'ttc': ttc_temp,
                'user': info['data']['user'],
                'coin': info['data']['sodu'],
                'token': token,
                'status': 'success'
            }
        else:
            return {'status': 'error', 'mess': info.get('mess', 'Đăng nhập thất bại')}
    except Exception as e:
        return {'status': 'error', 'mess': str(e)}

def add_multiple_ttc_accounts():
    global ttc_accounts
    print(f'{thanh}{luc}=== THÊM NHIỀU TÀI KHOẢN TTC ===')
    print(f'{thanh}{vang}[1] {luc}Nhập thủ công nhiều token')
    print(f'{thanh}{vang}[2] {luc}Nhập từ file (mỗi dòng 1 token)')
    chon = input(f'{thanh}{luc}Chọn{trang}: {vang}').strip()
    tokens = []
    if chon == '2':
        duongdan = input(f'{thanh}{luc}Nhập đường dẫn file token TTC{trang}: {vang}').strip()
        try:
            with open(duongdan, 'r', encoding='utf-8') as f:
                tokens = [line.strip() for line in f if line.strip()]
            print(f'{thanh}{luc}Đã đọc {vang}{len(tokens)}{luc} token từ file')
        except Exception as e:
            print(f'{do}Lỗi đọc file: {e}')
            return
    else:
        print(f'{thanh}{luc}Nhập token TTC (nhập trống để kết thúc):')
        i = 0
        while True:
            i += 1
            token = input(f'{thanh}{luc}Token {i}{trang}: {vang}').strip()
            if token == '' and i > 1:
                break
            if token:
                tokens.append(token)
    if not tokens:
        print(f'{do}Không có token nào được nhập!')
        return
    print(f'{thanh}{luc}Đang đăng nhập {len(tokens)} tài khoản TTC...')
    thanhngang(60)
    ttc_accounts = []
    for idx, token in enumerate(tokens, 1):
        print(f'{trang}[{idx}/{len(tokens)}] Đang đăng nhập...', end='\r')
        result = login_ttc_account(token)
        if result['status'] == 'success':
            ttc_accounts.append(result)
            print(f'{trang}[{idx}/{len(tokens)}] {luc}✓ {result["user"]} {trang}| Xu: {vang}{format(int(result["coin"]), ",")}          ')
        else:
            print(f'{trang}[{idx}/{len(tokens)}] {do}✗ {token[:20]}... - {result.get("mess", "Lỗi")}          ')
    thanhngang(60)
    print(f'{thanh}{luc}Đăng nhập thành công: {vang}{len(ttc_accounts)}/{len(tokens)}{luc} tài khoản')
    try:
        with open('ttc_accounts.json', 'w', encoding='utf-8') as f:
            save_data = [{'token': acc['token'], 'user': acc['user'], 'coin': acc['coin']} for acc in ttc_accounts]
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        print(f'{thanh}{luc}Đã lưu danh sách tài khoản vào {vang}ttc_accounts.json')
    except Exception as e:
        print(f'{do}Lỗi lưu file: {e}')

def load_saved_ttc_accounts():
    global ttc_accounts
    try:
        with open('ttc_accounts.json', 'r', encoding='utf-8') as f:
            saved = json.load(f)
        ttc_accounts = []
        for acc in saved:
            token = acc.get('token')
            if token:
                result = login_ttc_account(token)
                if result['status'] == 'success':
                    ttc_accounts.append(result)
        if ttc_accounts:
            print(f'{thanh}{luc}Đã tải {vang}{len(ttc_accounts)}{luc} tài khoản TTC')
            for acc in ttc_accounts:
                print(f'    {trang}- {vang}{acc["user"]} {trang}| Xu: {vang}{format(int(acc["coin"]), ",")}')
            return True
        return False
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f'{do}Lỗi tải file: {e}')
        return False

def select_ttc_account():
    global ttc_accounts
    if not ttc_accounts:
        print(f'{do}Chưa có tài khoản TTC nào!')
        return None
    print(f'{thanh}{luc}=== DANH SÁCH TÀI KHOẢN TTC ===')
    for idx, acc in enumerate(ttc_accounts, 1):
        print(f'{thanh}{vang}[{idx}] {luc}{acc["user"]} {trang}| Xu: {vang}{format(int(acc["coin"]), ",")}')
    thanhngang(60)
    print(f'{thanh}{luc}Nhập {do}[{vang}all{do}] {luc}Để Chạy Tất Cả')
    print(f'{thanh}{luc}Có Thể Chọn Nhiều (Cách Nhau Bởi +, Ví Dụ: 1+2+3)')
    print(f'{thanh}{luc}Nhập {do}[{vang}0{do}] {luc}Để Thêm Tài Khoản Mới')
    raw = input(f'{thanh}{luc}Chọn tài khoản{trang}: {vang}').strip().replace(' ', '')
    if raw == '0':
        add_multiple_ttc_accounts()
        return select_ttc_account()
    if raw.lower() == 'all':
        return ttc_accounts.copy()
    if '+' in raw:
        indices = [int(x) for x in raw.split('+') if x.isdigit()]
    else:
        indices = [int(raw)] if raw.isdigit() else []
    selected = []
    for idx in indices:
        if 1 <= idx <= len(ttc_accounts):
            selected.append(ttc_accounts[idx - 1])
        else:
            print(f'{do}Số thứ tự {idx} không hợp lệ!')
    return selected

def setup_ttc_accounts():
    global ttc_accounts
    print(f'{thanh}{luc}=== CẤU HÌNH TÀI KHOẢN TTC ===')
    print(f'{thanh}{vang}[1] {luc}Sử dụng tài khoản đã lưu')
    print(f'{thanh}{vang}[2] {luc}Thêm tài khoản mới')
    chon = input(f'{thanh}{luc}Chọn{trang}: {vang}').strip()
    if chon == '1':
        if load_saved_ttc_accounts():
            return select_ttc_account()
        else:
            print(f'{do}Không tìm thấy tài khoản đã lưu! Vui lòng thêm mới.')
            return setup_ttc_accounts()
    elif chon == '2':
        add_multiple_ttc_accounts()
        return select_ttc_account()
    else:
        print(f'{do}Vui lòng chọn 1 hoặc 2')
        return setup_ttc_accounts()

# ==================== CHẠY TƯƠNG TÁC ====================

def mask_ttc_name(ttc_user, anhttc_flag):
    if anhttc_flag.upper() == 'Y' and len(ttc_user) > 6:
        return ttc_user[:3] + '***' + ttc_user[-3:]
    return ttc_user

def run_single_cookie_with_ttc(cookie, ttc_obj, ttc_user, fb, uid, name):
    global listCookie, stt_counter, totalxu_counter, anhttc, KEY_XU, KEY_TYPE, KEY_MACHINE
    global anhttc
    
    ttc_display = mask_ttc_name(ttc_user, anhttc)
    
    JobFail = 0
    JobSuccess_local = 0
    list_nv_local = list_nv.copy()
    
    while cookie in listCookie:
        random_nv = random.choice(list_nv_local)
        if random_nv == '1': fields = 'likepostvipcheo'
        elif random_nv == '2': fields = 'likepostvipre'
        elif random_nv == '3': fields = 'camxucvipcheo'
        elif random_nv == '4': fields = 'camxuccheo'
        elif random_nv == '5': fields = 'camxuccheobinhluan'
        elif random_nv == '6': fields = 'cmtcheo'
        elif random_nv == '7': fields = 'sharecheo'
        elif random_nv == '8': fields = 'likepagecheo'
        elif random_nv == '9': fields = 'subcheo'
        elif random_nv == '0': fields = 'thamgianhomcheo'
        elif random_nv == 'q': fields = 'danhgiapage'
        elif random_nv == 's': fields = 'sharecheokemnoidung'
        chuyen = False
        try:
            getjob = ttc_obj.getjob(fields, nickchay=uid)
            if "idpost" in getjob.text or "idfb" in getjob.text:
                jobs = getjob.json()
                with print_lock:
                    print(f'{luc}[{ttc_display}] Đã tìm thấy {len(jobs)} nhiệm vụ {fields.title()} cho {name}')
                for x in jobs:
                    nextDelay = False
                    if random_nv in ["1","2"]:
                        fb.camxuc(x['idfb'].split('_')[1] if '_' in x['idfb'] else x['idfb'], "LIKE")
                        id_target = x['idfb'].split('_')[1] if '_' in x['idfb'] else x['idfb']
                        type_action = 'LIKE'
                        post_id = x['idpost']
                    elif random_nv in ["3","4"]:
                        fb.camxuc(x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'], x['loaicx'])
                        type_action = x['loaicx']
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == "5":
                        fb.camxuccmt(x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'], x['loaicx'])
                        type_action = x['loaicx']
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == "6":
                        fb.comment(x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'], json.loads(x["nd"])[0])
                        type_action = 'COMMENT'
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == "7":
                        fb.share(x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'])
                        type_action = 'SHARE'
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == "8":
                        fb.likepage(x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'])
                        type_action = 'LIKEPAGE'
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == "9":
                        fb.follow(x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'])
                        type_action = 'FOLLOW'
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == "0":
                        fb.group(x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'])
                        type_action = 'GROUP'
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == 'q':
                        fb.page_review(x['UID'].split('_')[1] if '_' in x['UID'] else x['UID'], json.loads(x["nd"])[0])
                        type_action = 'REVIEW'
                        post_id = x['UID']
                        id_target = x['UID'].split('_')[1] if '_' in x['UID'] else x['UID']
                    elif random_nv == "s":
                        fb.sharend(x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'], json.loads(x["nd"])[0])
                        type_action = 'SHAREND'
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    
                    nhanxu = ttc_obj.nhanxu(post_id, fields, nickchay=uid)
                    if nhanxu.get('status') == 'success':
                        nextDelay = True
                        msg, xu = nhanxu['msg'], nhanxu['xu']
                        
                        # === CẬP NHẬT XU LÊN SERVER ===
                        if KEY_TYPE == "xu":
                            xu_nhan = int(xu)
                            xu_con_lai = update_xu_on_server(KEY_MACHINE, xu_nhan)
                            if xu_con_lai >= 0:
                                KEY_XU = xu_con_lai
                                with print_lock:
                                    print(f'{trang}[{luc}SERVER{trang}] Xu còn lại: {vang}{KEY_XU}')
                                # === KIỂM TRA XU VỀ 0 ===
                                if KEY_XU <= 0:
                                    with print_lock:
                                        print(f'{do}[{luc}KEY{trang}] Key đã hết xu! Dừng chạy...')
                                    sys.exit(0)
                            else:
                                with print_lock:
                                    print(f'{do}[LỖI] Không thể cập nhật xu lên server!')
                            time.sleep(0.3)
                        # ====================================
                        
                        timejob = datetime.now().strftime('%H:%M:%S')
                        xutotal = msg.replace(' Xu', '')
                        JobSuccess_local += 1
                        JobFail = 0
                        with stt_lock:
                            stt_counter[0] += 1
                            totalxu_counter[0] += int(xutotal)
                            stt_now = stt_counter[0]
                            totalxu_now = totalxu_counter[0]
                        with print_lock:
                            uid_display = uid[:3] + '***' + uid[-3:] if runidfb.upper() == 'Y' and len(uid) > 6 else uid
                            print(f'{do}[{ttc_display}] | {vang}{stt_now}{do} | {xanh}{timejob}{do} | {tim}{uid_display}{do} | {vang}{type_action.upper()}{do} | {trang}{id_target}{do} | {vang}{msg}{do} | {luc}{format(int(xu), ",")} | {trang}{name}')
                            if stt_now % 10 == 0:
                                if KEY_TYPE == "xu":
                                    print(f'{trang}[{luc}Total Coin: {vang}{format(int(totalxu_now), ",")}{trang} | {luc}Key Xu Còn Lại: {vang}{KEY_XU}{trang}]')
                                else:
                                    print(f'{trang}[{luc}Total Coin: {vang}{format(int(totalxu_now), ",")}{trang}]')
                    else:
                        JobFail += 1
                    
                    if JobFail >= 100:
                        check = fb.info()
                        mess = check.get('mess', '') if isinstance(check, dict) else str(check)
                        if 'spam' in mess or '282' in mess or '956' in mess or 'cookieout' in mess:
                            with print_lock:
                                print(f'{do}[{ttc_display}] Tài khoản {name} đã bị block/lỗi, bỏ qua')
                            if cookie in listCookie:
                                listCookie.remove(cookie)
                            return
                        else:
                            if random_nv in list_nv_local:
                                list_nv_local.remove(random_nv)
                            if not list_nv_local:
                                with print_lock:
                                    print(f'{do}[{ttc_display}] Tài khoản {name} đã bị block tất cả tương tác')
                                if cookie in listCookie:
                                    listCookie.remove(cookie)
                                return
                            chuyen = True
                            break
                    
                    if JobSuccess_local != 0 and JobSuccess_local % int(JobBreak) == 0:
                        chuyen = True
                        break
                    
                    if nextDelay and not chuyen:
                        if stt_counter[0] % int(JobbBlock) == 0:
                            Delay(DelayBlock)
                        else:
                            Delay(random.randint(delay_min, delay_max))
                
                if chuyen:
                    break
                else:
                    continue
                    
            else:
                if 'error' in getjob.text:
                    try:
                        cd = getjob.json().get('countdown')
                        if cd:
                            with print_lock:
                                print(f'{do}[{ttc_display}] Countdown: {round(cd, 3)}s cho {name}', end="\r")
                            Delay(cd)
                        else:
                            sleep(1)
                    except:
                        pass
                        
        except Exception as e:
            with print_lock:
                print(f'{do}[{ttc_display}] Lỗi {name}: {str(e)}')
            sleep(1)


def run_cookie_with_ttc_and_cookies(cookie_list, ttc_obj, ttc_user):
    global anhttc
    
    ttc_display = mask_ttc_name(ttc_user, anhttc)
    
    if not cookie_list:
        with print_lock:
            print(f'{do}[{ttc_display}] Không có cookie nào được gán!')
        return
    
    with print_lock:
        print(f'{luc}[{ttc_display}] Bắt đầu chạy với {vang}{len(cookie_list)}{luc} cookie Facebook')
    
    for cookie in cookie_list:
        fb = FacebookToken(cookie) if chedo == 'token' else FacebookCookie(cookie)
        info = fb.info()
        if info.get('status') != 'success':
            with print_lock:
                print(f'{do}[{ttc_display}] Cookie không hợp lệ, bỏ qua')
            continue
        
        name = info['name']
        uid = info['id']
        idrun = uid[:3] + '***' + uid[-3:] if runidfb.upper() == 'Y' and len(uid) > 6 else uid
        
        with print_lock:
            print(f'{luc}[TTC: {ttc_display}] Id Facebook{trang}: {vang}{idrun}{do} | {luc}Tên{trang}: {vang}{name}')
        
        run_single_cookie_with_ttc(cookie, ttc_obj, ttc_user, fb, uid, name)


def run_single_page_with_ttc(cookie, page_id, page_name, ttc_obj, ttc_user, fb_page=None):
    global listCookie, stt_counter, totalxu_counter, anhttc, KEY_XU, KEY_TYPE, KEY_MACHINE
    global anhttc
    
    ttc_display = mask_ttc_name(ttc_user, anhttc)
    
    if fb_page is None:
        fb_page = Facebook_Page(cookie)
    
    JobFail = 0
    JobSuccess_local = 0
    list_nv_local = list_nv.copy()
    
    info = fb_page.info_page(cookie)
    if isinstance(info, dict) and info.get('status') != 'success':
        with print_lock:
            print(f'{do}[{ttc_display}] Page {page_name} không hợp lệ!')
        return
    
    uid = page_id
    name = page_name
    
    while True:
        random_nv = random.choice(list_nv_local)
        if random_nv == '1': fields = 'likepostvipcheo'
        elif random_nv == '2': fields = 'likepostvipre'
        elif random_nv == '3': fields = 'camxucvipcheo'
        elif random_nv == '4': fields = 'camxuccheo'
        elif random_nv == '5': fields = 'camxuccheobinhluan'
        elif random_nv == '6': fields = 'cmtcheo'
        elif random_nv == '7': fields = 'sharecheo'
        elif random_nv == '8': fields = 'likepagecheo'
        elif random_nv == '9': fields = 'subcheo'
        elif random_nv == '0': fields = 'thamgianhomcheo'
        elif random_nv == 'q': fields = 'danhgiapage'
        elif random_nv == 's': fields = 'sharecheokemnoidung'
        chuyen = False
        
        try:
            getjob = ttc_obj.getjob(fields, nickchay=uid)
            if "idpost" in getjob.text or "idfb" in getjob.text:
                jobs = getjob.json()
                with print_lock:
                    print(f'{luc}[{ttc_display}][{name}] Đã tìm thấy {len(jobs)} nhiệm vụ {fields.title()}')
                for x in jobs:
                    nextDelay = False
                    
                    if random_nv in ["1","2"]:
                        fb_page.camxuc(uid, x['idfb'].split('_')[1] if '_' in x['idfb'] else x['idfb'], "LIKE")
                        id_target = x['idfb'].split('_')[1] if '_' in x['idfb'] else x['idfb']
                        type_action = 'LIKE'
                        post_id = x['idpost']
                    elif random_nv in ["3","4"]:
                        fb_page.camxuc(uid, x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'], x['loaicx'])
                        type_action = x['loaicx']
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == "5":
                        fb_page.camxuccmt(uid, x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'], x['loaicx'])
                        type_action = x['loaicx']
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == "6":
                        fb_page.comment(uid, x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'], json.loads(x["nd"])[0])
                        type_action = 'COMMENT'
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == "7":
                        fb_page.share(uid, x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'])
                        type_action = 'SHARE'
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == "8":
                        fb_page.likepage(uid, x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'])
                        type_action = 'LIKEPAGE'
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == "9":
                        fb_page.follow(uid, x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'])
                        type_action = 'FOLLOW'
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == "0":
                        fb_page.group(uid, x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'])
                        type_action = 'GROUP'
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    elif random_nv == 'q':
                        fb_page.page_review(uid, x['UID'].split('_')[1] if '_' in x['UID'] else x['UID'], json.loads(x["nd"])[0])
                        type_action = 'REVIEW'
                        post_id = x['UID']
                        id_target = x['UID'].split('_')[1] if '_' in x['UID'] else x['UID']
                    elif random_nv == "s":
                        fb_page.sharend(uid, x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost'], json.loads(x["nd"])[0])
                        type_action = 'SHAREND'
                        post_id = x['idpost']
                        id_target = x['idpost'].split('_')[1] if '_' in x['idpost'] else x['idpost']
                    
                    nhanxu = ttc_obj.nhanxu(post_id, fields, nickchay=uid)
                    if nhanxu.get('status') == 'success':
                        nextDelay = True
                        msg, xu = nhanxu['msg'], nhanxu['xu']
                        
                        # === CẬP NHẬT XU LÊN SERVER ===
                        if KEY_TYPE == "xu":
                            xu_nhan = int(xu)
                            xu_con_lai = update_xu_on_server(KEY_MACHINE, xu_nhan)
                            if xu_con_lai >= 0:
                                KEY_XU = xu_con_lai
                                with print_lock:
                                    print(f'{trang}[{luc}SERVER{trang}] Xu còn lại: {vang}{KEY_XU}')
                                # === KIỂM TRA XU VỀ 0 ===
                                if KEY_XU <= 0:
                                    with print_lock:
                                        print(f'{do}[{luc}KEY{trang}] Key đã hết xu! Dừng chạy...')
                                    sys.exit(0)
                            else:
                                with print_lock:
                                    print(f'{do}[LỖI] Không thể cập nhật xu lên server!')
                        # ====================================
                        
                        timejob = datetime.now().strftime('%H:%M:%S')
                        xutotal = msg.replace(' Xu', '')
                        JobSuccess_local += 1
                        JobFail = 0
                        with stt_lock:
                            stt_counter[0] += 1
                            totalxu_counter[0] += int(xutotal)
                            stt_now = stt_counter[0]
                            totalxu_now = totalxu_counter[0]
                        with print_lock:
                            uid_display = uid[:3] + '***' + uid[-3:] if runidfb.upper() == 'Y' and len(uid) > 6 else uid
                            print(f'{do}[{ttc_display}][{name}] | {vang}{stt_now}{do} | {xanh}{timejob}{do} | {tim}{uid_display}{do} | {vang}{type_action.upper()}{do} | {trang}{id_target}{do} | {vang}{msg}{do} | {luc}{format(int(xu), ",")}')
                            if stt_now % 10 == 0:
                                if KEY_TYPE == "xu":
                                    print(f'{trang}[{luc}Total Coin: {vang}{format(int(totalxu_now), ",")}{trang} | {luc}Key Xu Còn Lại: {vang}{KEY_XU}{trang}]')
                                else:
                                    print(f'{trang}[{luc}Total Coin: {vang}{format(int(totalxu_now), ",")}{trang}]')
                    else:
                        JobFail += 1
                    
                    if JobFail >= 100:
                        with print_lock:
                            print(f'{do}[{ttc_display}][{name}] Page bị lỗi/spam, chuyển page khác')
                        return
                    
                    if JobSuccess_local != 0 and JobSuccess_local % int(JobBreak) == 0:
                        chuyen = True
                        break
                    
                    if nextDelay and not chuyen:
                        if stt_counter[0] % int(JobbBlock) == 0:
                            Delay(DelayBlock)
                        else:
                            Delay(random.randint(delay_min, delay_max))
                
                if chuyen:
                    break
                else:
                    continue
                    
            else:
                if 'error' in getjob.text:
                    try:
                        cd = getjob.json().get('countdown')
                        if cd:
                            with print_lock:
                                print(f'{do}[{ttc_display}][{name}] Countdown: {round(cd, 3)}s', end="\r")
                            Delay(cd)
                        else:
                            sleep(1)
                    except:
                        pass
                        
        except Exception as e:
            with print_lock:
                print(f'{do}[{ttc_display}][{name}] Lỗi: {str(e)}')
            sleep(1)


def run_cookie_page_with_ttc(cookie_list, ttc_obj, ttc_user):
    global anhttc
    
    ttc_display = mask_ttc_name(ttc_user, anhttc)
    
    if not cookie_list:
        with print_lock:
            print(f'{do}[{ttc_display}] Không có cookie page nào được gán!')
        return
    
    total_pages = 0
    for cookie in cookie_list:
        fb_page = Facebook_Page(cookie)
        profiles = fb_page.get_profile()
        try:
            nodes = profiles['data']['viewer']['actor']['profile_switcher_eligible_profiles']['nodes']
            total_pages += len(nodes)
        except:
            pass
    
    with print_lock:
        print(f'{luc}[{ttc_display}] Bắt đầu chạy với {vang}{len(cookie_list)}{luc} cookie master')
       
    
    all_page_threads = []
    
    for cookie in cookie_list:
        fb_page = Facebook_Page(cookie)
        profiles = fb_page.get_profile()
        try:
            nodes = profiles['data']['viewer']['actor']['profile_switcher_eligible_profiles']['nodes']
        except:
            with print_lock:
                print(f'{do}[{ttc_display}] Không thể lấy danh sách page từ cookie!')
            continue
        
        fb_master = FacebookCookie(cookie)
        info_master = fb_master.info()
        master_name = info_master.get('name', 'Unknown')
        
        with print_lock:
            print(f'{luc}[{ttc_display}] Cookie master: {vang}{master_name}{luc} → {vang}{len(nodes)}{luc} page')
        
        for profile in nodes:
            profile_name = profile['profile']['name']
            profile_id = profile['profile']['id']
            try:
                sb = cookie.split('sb=')[1].split(';')[0] if 'sb=' in cookie else ''
                datr = cookie.split('datr=')[1].split(';')[0] if 'datr=' in cookie else ''
                c_user = cookie.split('c_user=')[1].split(';')[0] if 'c_user=' in cookie else ''
                wd = cookie.split('wd=')[1].split(';')[0] if 'wd=' in cookie else ''
                xs = cookie.split('xs=')[1].split(';')[0] if 'xs=' in cookie else ''
                fr = cookie.split('fr=')[1].split(';')[0] if 'fr=' in cookie else ''
                page_cookie = f'sb={sb}; datr={datr}; c_user={c_user}; wd={wd}; xs={xs}; fr={fr}; i_user={profile_id};'
            except:
                page_cookie = cookie
            
            t = threading.Thread(
                target=run_single_page_with_ttc,
                args=(page_cookie, profile_id, profile_name, ttc_obj, ttc_user, None),
                daemon=True
            )
            t.start()
            all_page_threads.append(t)
            sleep(0.2)
    
    with print_lock:
        print(f'{luc}[{ttc_display}] Đã khởi tạo {len(all_page_threads)} thread page')

# ==================== CÁC HÀM CŨ ====================

def _addcookie_page():
    global _uid_list_cached
    _uid_list_cached = []
    while True:
        cookie = input(f'{thanh}{luc}Nhập Cookie Facebook Chứa Page{trang}: {vang}')
        thanhngang(60)
        print(f'{luc}Đang kiểm tra cookie chứa page...', end='\r')
        fb_master = FacebookCookie(cookie)
        info_master = fb_master.info()
        if info_master.get('status') != 'success':
            print(f'{do}cookie chứa page không hợp lệ hoặc đã hết hạn!')
            print(f'{do}Lỗi: {info_master.get("mess", "Không xác định")}')
            print(f'{do}Vui lòng nhập lại cookie hợp lệ!')
            thanhngang(60)
            continue
        master_name = info_master.get('name', 'Unknown')
        master_id = info_master.get('id', 'Unknown')
        print(f'{luc}cookie chứa page hợp lệ! {trang}Tài khoản: {vang}{master_name} {trang}({xanh}{master_id}{trang})')
        thanhngang(60)
        fb = Facebook_Page(cookie)
        profiles = fb.get_profile()
        try:
            nodes = profiles['data']['viewer']['actor']['profile_switcher_eligible_profiles']['nodes']
        except Exception as e:
            print(f'{do}Không thể lấy danh sách Page! Lỗi: {e}')
            print(f'{do}Cookie này có thể không có quyền quản trị Page nào.')
            print(f'{do}Vui lòng nhập cookie có quyền quản trị page!')
            thanhngang(60)
            continue
        if not nodes:
            print(f'{do}Không tìm thấy Page nào trong tài khoản này!')
            print(f'{do}Tài khoản {master_name} không quản lý page nào.')
            print(f'{do}Vui lòng nhập cookie có quản lý page!')
            thanhngang(60)
            continue
        break
    print(f'{luc}Danh sách Page do {vang}{master_name}{luc} quản lý:')
    thanhngang(60)
    for so, profile in enumerate(nodes, start=1):
        profile_name = profile['profile']['name']
        profile_id = profile['profile']['id']
        print(f'{thanh}{luc}[{vang}{so}{luc}] {vang}{profile_name} {do}| {luc}ID: {xanh}{profile_id}')
    thanhngang(60)
    print(f'{thanh}{luc}Nhập {do}[{vang}all{do}] {luc}Để Chạy Tất Cả Page')
    print(f'{thanh}{xanh}Có Thể Chọn Nhiều Page (Cách Nhau Bởi +, Ví Dụ: 1+2+3+...)')
    raw = input(f'{thanh}{luc}Nhập Page Muốn Chạy{trang}: {vang}').replace(' ', '')
    if '+' in raw:
        chon = raw.split('+')
    else:
        chon = [raw]
    list_page_cookies = []
    try:
        sb = cookie.split('sb=')[1].split(';')[0] if 'sb=' in cookie else ''
        datr = cookie.split('datr=')[1].split(';')[0] if 'datr=' in cookie else ''
        c_user = cookie.split('c_user=')[1].split(';')[0] if 'c_user=' in cookie else ''
        wd = cookie.split('wd=')[1].split(';')[0] if 'wd=' in cookie else ''
        xs = cookie.split('xs=')[1].split(';')[0] if 'xs=' in cookie else ''
        fr = cookie.split('fr=')[1].split(';')[0] if 'fr=' in cookie else ''
    except Exception as e:
        print(f'{do}Lỗi parse cookie: {e}')
        return []
    for i in chon:
        if str(i).lower() == 'all':
            for profile in nodes:
                profile_name = profile['profile']['name']
                profile_id = profile['profile']['id']
                ck_pro5 = f'sb={sb}; datr={datr}; c_user={c_user}; wd={wd}; xs={xs}; fr={fr}; i_user={profile_id};'
                list_page_cookies.append(ck_pro5)
                _uid_list_cached.append((profile_id, profile_name, ck_pro5))
                print(f'{thanh}{luc}Đã thêm Page: {vang}{profile_name}')
            break
        else:
            try:
                index = int(i) - 1
                if 0 <= index < len(nodes):
                    profile = nodes[index]
                    profile_name = profile['profile']['name']
                    profile_id = profile['profile']['id']
                    ck_pro5 = f'sb={sb}; datr={datr}; c_user={c_user}; wd={wd}; xs={xs}; fr={fr}; i_user={profile_id};'
                    list_page_cookies.append(ck_pro5)
                    _uid_list_cached.append((profile_id, profile_name, ck_pro5))
                    print(f'{thanh}{luc}Đã thêm Page: {vang}{profile_name}')
                else:
                    print(f'{do}Số thứ tự {i} không hợp lệ! (1-{len(nodes)})')
            except ValueError:
                print(f'{do}Lựa chọn {i} không hợp lệ!')
    thanhngang(60)
    if not list_page_cookies:
        print(f'{do}Không có page nào được chọn!')
        return []
    print(f'{luc}Đã chọn thành công {len(list_page_cookies)} page')
    for idx, (uid, name, _) in enumerate(_uid_list_cached, 1):
        uid_show = uid[:3] + '***' + uid[-3:] if len(uid) > 6 else uid
        print(f'{trang}{idx}. {vang}{name} {trang}({xanh}{uid_show}{trang})')
    thanhngang(60)
    return list_page_cookies

def addcookie():
    global _uid_list_cached
    if chedo == 'cookie_page':
        _uid_list_cached = []
        result = _addcookie_page()
        if result:
            listCookie.extend(result)
        return
    label = 'Token' if chedo == 'token' else 'Cookie'
    print(f'{thanh}{luc}Chọn cách nhập {label} Facebook:')
    print(f'{thanh}{vang}[1] {luc}Nhập thủ công')
    print(f'{thanh}{vang}[2] {luc}Nhập từ file (mỗi dòng 1 {label.lower()})')
    chon = input(f'{thanh}{luc}Chọn{trang}: {vang}').strip()
    items_to_add = []
    if chon == '2':
        duongdan = input(f'{thanh}{luc}Nhập đường dẫn file {label.lower()}{trang}: {vang}').strip()
        try:
            with open(duongdan, 'r', encoding='utf-8') as f:
                items_to_add = [line.strip() for line in f if line.strip()]
            print(f'{thanh}{luc}Đã đọc {vang}{len(items_to_add)}{luc} {label.lower()} từ file')
        except FileNotFoundError:
            print(f'{do}Không tìm thấy file: {duongdan}')
            return
        except Exception as e:
            print(f'{do}Lỗi đọc file: {e}')
            return
    else:
        i = 0
        while True:
            i += 1
            item = input(f'{thanh}{luc}Nhập {label} Facebook Số{vang} {i}{trang}: {vang}').strip()
            if item == '' and i != 1:
                break
            if item:
                items_to_add.append(item)
    _uid_list_cached = []
    ok, fail = 0, 0
    for idx, item in enumerate(items_to_add, 1):
        print(f'{thanh}{vang}Đang kiểm tra {label.lower()} {idx}/{len(items_to_add)}...', end='\r')
        fb = FacebookToken(item) if chedo == 'token' else FacebookCookie(item)
        info = fb.info()
        if info.get('status') == 'success':
            name = info['name']
            uid = info.get('id', '')
            uid_hidden = uid[:3] + '***' + uid[-3:] if len(uid) > 6 else uid
            print(f'{thanh}{luc}[{idx}] {vang}{name} {luc}=> {label} OK {trang}| UID: {xanh}{uid_hidden}        ')
            thanhngang(60)
            listCookie.append(item)
            _uid_list_cached.append((uid, name, item))
            ok += 1
        else:
            print(f'{do}[{idx}] {label} Die ! {info.get("mess", "")}        ')
            fail += 1
    print(f'{thanh}{luc}Kết quả: {vang}{ok} OK {do}| {vang}{fail} Die')

# ==================== CẤU HÌNH PROXY ====================

def config_proxy():
    global USE_PROXY_FB, USE_PROXY_TTC, USE_PROXY_BOTH
    print(f'{thanh}{luc}=== CẤU HÌNH PROXY ===')
    print(f'{thanh}{vang}[1] {luc}Không dùng proxy')
    print(f'{thanh}{vang}[2] {luc}Proxy riêng cho Facebook')
    print(f'{thanh}{vang}[3] {luc}Proxy riêng cho TTC (getjob/nhantien)')
    print(f'{thanh}{vang}[4] {luc}Proxy chung cho cả Facebook và TTC')
    print(f'{thanh}{vang}[5] {luc}Proxy riêng FB + Proxy riêng TTC')
    chon = input(f'{thanh}{luc}Chọn{trang}: {vang}').strip()
    
    if chon == '1':
        set_proxy_fb('')
        set_proxy_ttc('')
        set_proxy_both('')
        print(f'{thanh}{luc}Đã tắt proxy')
        return
    
    if chon == '2':
        proxy = input(f'{thanh}{luc}Nhập proxy cho Facebook (hỗ trợ ip:port hoặc ip:port:user:pass){trang}: {vang}').strip()
        set_proxy_fb(proxy)
        set_proxy_ttc('')
        set_proxy_both('')
        if USE_PROXY_FB:
            print(f'{thanh}{luc}Đã thiết lập proxy Facebook: {vang}{proxy}')
        else:
            print(f'{do}Proxy Facebook không hợp lệ')
        return
    
    if chon == '3':
        proxy = input(f'{thanh}{luc}Nhập proxy cho TTC (hỗ trợ ip:port hoặc ip:port:user:pass){trang}: {vang}').strip()
        set_proxy_fb('')
        set_proxy_ttc(proxy)
        set_proxy_both('')
        if USE_PROXY_TTC:
            print(f'{thanh}{luc}Đã thiết lập proxy TTC: {vang}{proxy}')
        else:
            print(f'{do}Proxy TTC không hợp lệ')
        return
    
    if chon == '4':
        proxy = input(f'{thanh}{luc}Nhập proxy chung (hỗ trợ ip:port hoặc ip:port:user:pass){trang}: {vang}').strip()
        set_proxy_fb('')
        set_proxy_ttc('')
        set_proxy_both(proxy)
        if USE_PROXY_BOTH:
            print(f'{thanh}{luc}Đã thiết lập proxy chung: {vang}{proxy}')
        else:
            print(f'{do}Proxy chung không hợp lệ')
        return
    
    if chon == '5':
        proxy_fb = input(f'{thanh}{luc}Nhập proxy Facebook (hỗ trợ ip:port hoặc ip:port:user:pass){trang}: {vang}').strip()
        proxy_ttc = input(f'{thanh}{luc}Nhập proxy TTC (hỗ trợ ip:port hoặc ip:port:user:pass){trang}: {vang}').strip()
        set_proxy_fb(proxy_fb)
        set_proxy_ttc(proxy_ttc)
        set_proxy_both('')
        if USE_PROXY_FB:
            print(f'{thanh}{luc}Đã thiết lập proxy Facebook: {vang}{proxy_fb}')
        else:
            print(f'{do}Proxy Facebook không hợp lệ')
        if USE_PROXY_TTC:
            print(f'{thanh}{luc}Đã thiết lập proxy TTC: {vang}{proxy_ttc}')
        else:
            print(f'{do}Proxy TTC không hợp lệ')
        return
    
    print(f'{do}Lựa chọn không hợp lệ, bỏ qua cấu hình proxy')

# ==================== MAIN ====================

# === XÁC THỰC KEY ===
if not authenticate():
    print(f"{do}[LỖI] Xác thực thất bại! Thoát chương trình.")
    sys.exit(1)

banner()
config_proxy()

banner()
selected_ttc = setup_ttc_accounts()
if not selected_ttc:
    print(f'{do}Không có tài khoản TTC nào, thoát chương trình!')
    sys.exit(0)

banner()
print(f'{thanh}{luc}Chọn chế độ đăng nhập Facebook:')
print(f'{thanh}{vang}[1] {luc}Cookie')
print(f'{thanh}{vang}[2] {luc}Token')
print(f'{thanh}{vang}[3] {luc}Cookie Page')
thanhngang(60)
while True:
    chedo_chon = input(f'{thanh}{luc}Chọn{trang}: {vang}').strip()
    if chedo_chon == '1':
        chedo = 'cookie'
        file_luu = 'cookiefb-ttc.json'
        break
    elif chedo_chon == '2':
        chedo = 'token'
        file_luu = 'tokenfb-ttc.json'
        break
    elif chedo_chon == '3':
        chedo = 'cookie_page'
        file_luu = 'cookiepage-ttc.json'
        break
    else:
        print(f'{do}Vui lòng nhập 1, 2 hoặc 3')
thanhngang(60)

anhtk = 'y'
if os.path.exists(file_luu) == False:
    addcookie()
    with open(file_luu,'w') as f:
        json.dump(listCookie, f)
else:
    if chedo == 'cookie_page':
        label = 'Cookie Page'
    else:
        label = 'Token' if chedo == 'token' else 'Cookie'
    print(f'{thanh}{luc}Nhập {do}[{vang}1{do}] {luc}Sử Dụng {label} Đã Lưu')
    print(f'{thanh}{luc}Nhập {do}[{vang}2{do}] {luc}Nhập {label} Mới')
    thanhngang(60)
    while True:
        chon_fb = input(f'{thanh}{luc}Chọn{trang}: {vang}').strip()
        if chon_fb == '1':
            print(f'{luc}Đang Lấy Dữ Liệu Đã Lưu ','          ',end='\r')
            sleep(1)
            listCookie = json.loads(open(file_luu, 'r').read())
            thanhngang(60)
            print(f'{thanh}{luc}Đã tải {vang}{len(listCookie)}{luc} {label}')
            break
        elif chon_fb == '2':
            _uid_list_cached = []
            addcookie()
            with open(file_luu,'w') as f:
                json.dump(listCookie, f)
            break
        else:
            print(f'{do}Vui Lòng Nhập Đúng !!!')

if not listCookie:
    print(f'{do}Không có cookie/page nào! Vui lòng nhập lại...')
    addcookie()

banner()
user_show = '***' if anhtk.upper() == 'Y' else selected_ttc[0]['user'] if selected_ttc else 'Unknown'
coin_show = format(int(selected_ttc[0]['coin']), ",") if selected_ttc else '0'
print(f'{thanh}{luc}Tên Tài Khoản TTC{trang}: {vang}{user_show}')
print(f'{thanh}{luc}Xu Hiện Tại{trang}: {vang}{coin_show}')
print(f'{thanh}{luc}Số Acc Facebook{trang}: {vang}{len(listCookie)}')
print(f'{thanh}{luc}Số Tài Khoản TTC{trang}: {vang}{len(selected_ttc)}')
thanhngang(60)
print(f'{thanh}{luc}Nhập {do}[{vang}1{do}]{luc} Để Chạy Nhiệm Vụ Like Vip')
print(f'{thanh}{luc}Nhập {do}[{vang}2{do}]{luc} Để Chạy Nhiệm Vụ Like Thường')
print(f'{thanh}{luc}Nhập {do}[{vang}3{do}]{luc} Để Chạy Nhiệm Vụ Cảm Xúc Vip')
print(f'{thanh}{luc}Nhập {do}[{vang}4{do}]{luc} Để Chạy Nhiệm Vụ Cảm Xúc Thường')
print(f'{thanh}{luc}Nhập {do}[{vang}5{do}]{luc} Để Chạy Nhiệm Vụ Cảm Xúc Comment')
print(f'{thanh}{luc}Nhập {do}[{vang}6{do}]{luc} Để Chạy Nhiệm Vụ Comment')
print(f'{thanh}{luc}Nhập {do}[{vang}7{do}]{luc} Để Chạy Nhiệm Vụ Share')
print(f'{thanh}{luc}Nhập {do}[{vang}8{do}]{luc} Để Chạy Nhiệm Vụ Like Page')
print(f'{thanh}{luc}Nhập {do}[{vang}9{do}]{luc} Để Chạy Nhiệm Vụ Follow')
print(f'{thanh}{luc}Nhập {do}[{vang}0{do}]{luc} Để Chạy Nhiệm Vụ Group')
print(f'{thanh}{luc}Nhập {do}[{vang}q{do}]{luc} Để Chạy Nhiệm Vụ Review')
print(f'{thanh}{luc}Nhập {do}[{vang}s{do}]{luc} Để Chạy Nhiệm Vụ Share Nội Dung')
print(f'{thanh}{luc}Có Thể Chọn Nhiều Nhiệm Vụ {do}({vang}VD: 123...{do})')
thanhngang(60)

FILE_CAUHINH = 'cauhinh_chay.json'

def nhap_cauhinh():
    nhiemvu = str(input(f'{thanh}{luc}Nhập Số Để Chọn Nhiệm Vụ{trang}: {vang}'))
    list_nv_inp = [x for x in nhiemvu if x.isdigit() or x in ('q','s')]
    while True:
        try:
            delay_min = int(input(f'{thanh}{luc}Nhập Delay Min{trang}: {vang}'))
            delay_max = int(input(f'{thanh}{luc}Nhập Delay Max{trang}: {vang}'))
            if delay_min < 1: delay_min = 1
            if delay_min > delay_max: delay_min = delay_max
            delay_inp = (delay_min, delay_max)
            break
        except:
            print(f'{do}Vui Lòng Nhập Số')
    while True:
        try:
            JobbBlock_inp = int(input(f'{thanh}{luc}Sau Bao Nhiêu Nhiệm Vụ Chống Block{trang}: {vang}'))
            break
        except:
            print(f'{do}Vui Lòng Nhập Số')
    while True:
        try:
            DelayBlock_inp = int(input(f'{thanh}{luc}Sau {vang}{JobbBlock_inp} {luc}Nhiệm Vụ Nghỉ Bao Nhiêu Giây{trang}: {vang}'))
            break
        except:
            print(f'{do}Vui Lòng Nhập Số')
    while True:
        try:
            JobBreak_inp = int(input(f'{thanh}{luc}Sau Bao Nhiêu Nhiệm Vụ Chuyển Acc{trang}: {vang}'))
            break
        except:
            print(f'{do}Vui Lòng Nhập Số')
    runidfb_inp = input(f'{thanh}{luc}Bạn Có Muốn Ẩn UID Trong Log Không? {do}({vang}y/n{do}){luc}: {vang}')
    anhttc_inp = input(f'{thanh}{luc}Bạn Có Muốn Ẩn Tên TTC Trong Log Không? {do}({vang}y/n{do}){luc}: {vang}')
    
    cauhinh_data = {
        'nhiemvu': nhiemvu,
        'list_nv': list_nv_inp,
        'delay_min': delay_inp[0],
        'delay_max': delay_inp[1],
        'JobbBlock': JobbBlock_inp,
        'DelayBlock': DelayBlock_inp,
        'JobBreak': JobBreak_inp,
        'runidfb': runidfb_inp,
        'anhttc': anhttc_inp,
    }
    with open(FILE_CAUHINH, 'w', encoding='utf-8') as f:
        json.dump(cauhinh_data, f, ensure_ascii=False, indent=2)
    print(f'{thanh}{luc}Đã lưu cấu hình vào {vang}{FILE_CAUHINH}')
    return cauhinh_data

if os.path.exists(FILE_CAUHINH):
    try:
        _old = json.loads(open(FILE_CAUHINH, 'r', encoding='utf-8').read())
        print(f'{thanh}{luc}Phát hiện cấu hình cũ đã lưu:')
        print(f'{thanh}{vang}Nhiệm Vụ   {trang}: {vang}{_old.get("nhiemvu","?")}')
        print(f'{thanh}{vang}Delay      {trang}: {vang}{_old.get("delay_min","?")} - {_old.get("delay_max","?")} ')
        print(f'{thanh}{vang}Chống Block{trang}: {vang}Mỗi {_old.get("JobbBlock","?")} job nghỉ {_old.get("DelayBlock","?")}s')
        print(f'{thanh}{vang}Chuyển Acc {trang}: {vang}Mỗi {_old.get("JobBreak","?")} job')
        print(f'{thanh}{vang}Ẩn UID     {trang}: {vang}{_old.get("runidfb","?")}')
        thanhngang(60)
        print(f'{thanh}{luc}Nhập {do}[{vang}1{do}] {luc}Dùng cấu hình cũ')
        print(f'{thanh}{luc}Nhập {do}[{vang}2{do}] {luc}Nhập cấu hình mới')
        thanhngang(60)
        while True:
            _chon_ch = input(f'{thanh}{luc}Chọn{trang}: {vang}').strip()
            if _chon_ch == '1':
                _cfg = _old
                print(f'{thanh}{luc}Đã tải cấu hình cũ thành công!')
                break
            elif _chon_ch == '2':
                _cfg = nhap_cauhinh()
                break
            else:
                print(f'{do}Vui lòng nhập 1 hoặc 2')
    except Exception:
        _cfg = nhap_cauhinh()
else:
    _cfg = nhap_cauhinh()

list_nv = _cfg['list_nv']
delay_min = int(_cfg.get('delay_min', 1))
delay_max = int(_cfg.get('delay_max', 10))
delay = delay_min
JobbBlock = _cfg['JobbBlock']
DelayBlock = _cfg['DelayBlock']
JobBreak = _cfg['JobBreak']
runidfb = _cfg['runidfb']
anhttc = _cfg.get('anhttc', 'y')
thanhngang(60)
stt_counter = [0]
totalxu_counter = [0]

# ========== PHÂN CHIA COOKIE VÀ CHẠY ==========

print(f'{thanh}{luc}=== PHÂN CHIA COOKIE CHO CÁC TÀI KHOẢN TTC ===')
print(f'{thanh}{vang}[1] {luc}Chia đều (balance)')
print(f'{thanh}{vang}[2] {luc}Chia vòng tròn (round robin)')
print(f'{thanh}{vang}[3] {luc}Mỗi TTC chạy tất cả cookie (all)')
strategy_choice = input(f'{thanh}{luc}Chọn chiến lược{trang}: {vang}').strip()
strategy_map = {'1': 'balance', '2': 'round_robin', '3': 'all'}
strategy = strategy_map.get(strategy_choice, 'balance')
split_result = split_cookies_by_strategy(listCookie, selected_ttc, strategy)
display_split_result(split_result, selected_ttc, len(listCookie))

thanhngang(60)
print(f'{thanh}{luc}Bắt đầu khởi tạo luồng...')
thanhngang(60)

all_threads = []

if chedo == 'cookie_page':
    for ttc_acc in selected_ttc:
        ttc_obj = ttc_acc['ttc']
        ttc_user = ttc_acc['user']
        assigned_cookies = split_result.get(ttc_user, [])
        if not assigned_cookies:
            print(f'{do}[{ttc_user}] Không có cookie page nào được gán')
            continue
        print(f'{luc}[{ttc_user}] Khởi tạo với {vang}{len(assigned_cookies)}{luc} cookie master')
        t = threading.Thread(
            target=run_cookie_page_with_ttc,
            args=(assigned_cookies, ttc_obj, ttc_user),
            daemon=True
        )
        t.start()
        all_threads.append(t)
        sleep(1)
else:
    for ttc_acc in selected_ttc:
        ttc_obj = ttc_acc['ttc']
        ttc_user = ttc_acc['user']
        assigned_cookies = split_result.get(ttc_user, [])
        if not assigned_cookies:
            print(f'{do}[{ttc_user}] Không có cookie nào được gán')
            continue
        print(f'{luc}[{ttc_user}] Khởi tạo với {vang}{len(assigned_cookies)}{luc} cookie')
        t = threading.Thread(
            target=run_cookie_with_ttc_and_cookies,
            args=(assigned_cookies, ttc_obj, ttc_user),
            daemon=True
        )
        t.start()
        all_threads.append(t)
        sleep(0.5)

print(f'{thanh}{luc}Đã khởi tạo {len(all_threads)} luồng TTC')
print(f'{thanh}{luc}Tổng số cookie/page đang chạy: {vang}{len(listCookie)}')
thanhngang(60)

try:
    while True:
        alive_threads = [t for t in all_threads if t.is_alive()]
        if len(alive_threads) == 0:
            print(f'{do}Tất cả các luồng đã kết thúc!')
            break
        sleep(10)
except KeyboardInterrupt:
    print(f'\n{do}Đã dừng chương trình!')
    sys.exit(0)