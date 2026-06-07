import paramiko, time

HOST   = '110.165.16.194'
USER   = 'root'
REMOTE = '/srv/finvoice'

import os
PASS = os.environ.get('DEPLOY_PASS', '')
if not PASS:
    import getpass
    PASS = getpass.getpass('Server password: ')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS)

def run(cmd):
    _, out, err = client.exec_command(cmd)
    o = out.read().decode('utf-8', errors='replace').strip()
    e = err.read().decode('utf-8', errors='replace').strip()
    if o: print(o.encode('ascii', errors='replace').decode())
    if e and 'WARNING' not in e: print('[err]', e[:300].encode('ascii', errors='replace').decode())
    return o

# 1. CSS 업로드
sftp = client.open_sftp()
sftp.put('app/static/style.css', f'{REMOTE}/app/static/style.css')
sftp.close()
print('step1: style.css uploaded')

# 2. 서비스 재시작
run('systemctl restart finvoice')
time.sleep(2)
status = run('systemctl is-active finvoice')
print(f'step2: service = {status}')

# 3. HTTP 확인
code = run('curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/')
print(f'step3: HTTP = {code}')

client.close()
print('=== done ===')
