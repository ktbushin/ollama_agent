import requests

# Llamaのエンドポイント
url = "http://localhost:11434/api/generate"  # ポートは環境によって異なる場合があります

# プロンプトを指定
prompt = "I would like to make UUV simulator with HLA RTI"

# APIリクエストを送信
response = requests.post(url, json={"prompt": prompt})

if response.status_code == 200:
    # 応答を表示
    result = response.json()
    print(result['text'])
else:
    print(f"Error: {response.status_code}, {response.text}")
