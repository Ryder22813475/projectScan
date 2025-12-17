import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 讓你的網頁可以跨網域呼叫 API

# ----------------------------------------
# 配置區
# ----------------------------------------
# 使用支援中文的人名辨識模型 (CKIP)
API_URL_HF = "https://api-inference.huggingface.co/models/ckiplab/bert-base-chinese-ner"
HF_TOKEN = os.environ.get("HF_TOKEN")
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

# 1. 新增首頁路徑：讓你訪問網址時不會看到 Not Found
@app.route('/')
def home():
    return "<h1>API 伺服器運作中！</h1><p>請確認在 JS 中使用的網址結尾包含 /analyze-text</p>"

def query_huggingface(text):
    """呼叫 Hugging Face 的推理 API"""
    payload = {"inputs": text, "options": {"wait_for_model": True}}
    response = requests.post(API_URL_HF, headers=headers, json=payload)
    return response.json()

@app.route('/analyze-text', methods=['POST'])
def analyze():
    # 檢查 Token
    if not HF_TOKEN:
        return jsonify({"error": "後端未設定 HF_TOKEN 環境變數"}), 500

    data = request.get_json()
    if not data or 'chapterName' not in data[0]:
        return jsonify({"error": "無效的輸入數據"}), 400

    text = data[0]['chapterName']
    
    # 呼叫 AI 模型
    ner_results = query_huggingface(text)
    
    # 錯誤處理 (例如 API 正在載入)
    if isinstance(ner_results, dict) and "error" in ner_results:
        return jsonify(ner_results), 500

    # 處理並過濾數據 (只保留 PERSON 人名)
    people = {}
    for ent in ner_results:
        # CKIP 模型的標籤通常是 'entity_group'
        label = ent.get('entity_group') or ent.get('entity')
        if label == "PERSON":
            name = ent['word'].strip().replace(" ", "")
            if len(name) > 1: # 避免抓到單個字
                people[name] = people.get(name, 0) + 1

    # 格式化回傳
    named_entities = []
    total_mentions = sum(people.values())
    
    for name, count in people.items():
        named_entities.append({
            "name": name,
            "entity_type": "Person",
            "count": count,
            "importance_score": round(count / total_mentions, 2) if total_mentions > 0 else 0
        })

    return jsonify({
        "document_id": data[0].get('chapterID', '001'),
        "named_entities": named_entities,
        "total_person_count": total_mentions,
        "analysis_status": "Completed"
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)