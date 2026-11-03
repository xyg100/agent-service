import requests

key = "sk-1ca2c7ce5cb846cba5a719f6c0865321"
url = "https://api.deepseek.com/user/balance"
headers = {"Authorization": f"Bearer {key}"}


resp = requests.get(url, headers=headers)
print(resp.status_code)
print(resp.text)
