import requests

BASE = 'http://localhost:5000'

print('=============================================')
print('VERIFYING SKILLBRIDGE LIVE BACKEND ENDPOINTS')
print('=============================================')

# 1. Base API check
r = requests.get(f'{BASE}/')
assert r.status_code == 200, f'Root failed: {r.status_code}'
print('[+] Root API is live (200 OK)')

# 2. Student Session
s_stud = requests.Session()
r = s_stud.post(f'{BASE}/api/auth/login', json={'email': 'ayeshamads@gmail.com', 'password': 'teststudent123'})
assert r.status_code == 200, f'Student login failed: {r.status_code}'
stud_data = r.json()['student']
print(f'[+] Student login succeeded (Name: {stud_data["name"]}, Role: {stud_data["role"]})')

# Student APIs
endpoints = [
    ('/api/student/skills', 'Skills list'),
    ('/api/student/readiness_breakdown', 'Readiness breakdown'),
    ('/api/student/career_insights', 'Career insights'),
    ('/api/student/career_recommendations', 'Career recommendations'),
    ('/api/student/badges', 'Badges list'),
    ('/api/student/progress_history', 'Progress history'),
    ('/api/student/privacy_info', 'Privacy info'),
    ('/api/student/get_roadmap', 'Roadmap')
]
for ep, name in endpoints:
    res = s_stud.get(f'{BASE}{ep}')
    assert res.status_code == 200, f'{name} failed: {res.status_code}'
    print(f'    [+] Student {name}: 200 OK')

# Salary Simulator
res = s_stud.post(f'{BASE}/api/student/simulate_salary', json={'additional_skills': ['Docker', 'AWS']})
assert res.status_code == 200, f'Salary sim failed: {res.status_code}'
print('    [+] Salary simulator: 200 OK')

# Student Security Checks (should be 403 Forbidden)
res = s_stud.get(f'{BASE}/api/admin/stats')
assert res.status_code == 403, f'Expected 403 on admin stats, got {res.status_code}'
print('    [+] Security Check: Student denied from /api/admin/stats (403 Forbidden)')

res = s_stud.post(f'{BASE}/api/admin/federated/train')
assert res.status_code == 403, f'Expected 403 on FL train, got {res.status_code}'
print('    [+] Security Check: Student denied from /api/admin/federated/train (403 Forbidden)')

# 3. Admin Session
s_admin = requests.Session()
r = s_admin.post(f'{BASE}/api/auth/login', json={'email': 'admin@skillbridge.edu', 'password': 'admin123'})
assert r.status_code == 200, f'Admin login failed: {r.status_code}'
admin_data = r.json()['student']
print(f'[+] Admin login succeeded (Name: {admin_data["name"]}, Role: {admin_data["role"]})')

admin_endpoints = [
    ('/api/admin/stats', 'Platform Stats'),
    ('/api/admin/students', 'Student Cohort'),
    ('/api/admin/federated/nodes', 'FL Nodes'),
    ('/api/admin/federated/rounds', 'FL Rounds'),
    ('/api/admin/federated/status', 'FL Status')
]
for ep, name in admin_endpoints:
    res = s_admin.get(f'{BASE}{ep}')
    assert res.status_code == 200, f'Admin {name} failed: {res.status_code}'
    print(f'    [+] Admin {name}: 200 OK')

# Trigger FL round as Admin
res = s_admin.post(f'{BASE}/api/admin/federated/train')
assert res.status_code == 200, f'Admin FL train failed: {res.status_code}'
train_info = res.json()['data']
print(f'[+] Admin triggered FL Round #{train_info["round_number"]} successfully!')
print(f'    Global Accuracy: {train_info["global_accuracy"]} | Privacy: {train_info["privacy_guarantee"]}')

print('\n=============================================')
print('ALL BACKEND SYSTEMS ARE WORKING PERFECTLY!')
print('=============================================')
