import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ----------------------------------------
# 配置區
# ----------------------------------------
# 透過 API 呼叫模型，不需要在 Render 本地載入
API_URL_HF = "https://api-inference.huggingface.co/models/xlm-roberta-large-finetuned-conll03-english"
# 將你的 Token 放入環境變數或直接暫貼在此 (建議部署時設定在 Render 的 Environment Variables)
HF_TOKEN = os.environ.get("HF_TOKEN", "你的_HF_TOKEN_貼在這裡")
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

def query_huggingface(text):
    """直接呼叫 Hugging Face 的推理 API"""
    payload = {"inputs": text, "options": {"wait_for_model": True}}
    response = requests.post(API_URL_HF, headers=headers, json=payload)
    return response.json()

@app.route('/analyze-text', methods=['POST'])
def analyze():
    data = request.get_json()
    if not data or 'chapterName' not in data[0]:
        return jsonify({"error": "Invalid input"}), 400

    text = data[0]['chapterName']
    
    # 呼叫外部 AI 模型
    ner_results = query_huggingface(text)
    
    # 如果回傳的是錯誤訊息
    if isinstance(ner_results, dict) and "error" in ner_results:
        return jsonify(ner_results), 500

    # 處理並過濾數據 (只保留 Person)
    people = {}
    for ent in ner_results:
        # 英文模型標籤通常是 'entity_group' 或 'entity'
        label = ent.get('entity_group') or ent.get('entity')
        if label in ["PER", "PERSON"]:
            name = ent['word'].strip().replace(" ", "")
            people[name] = people.get(name, 0) + 1

    # 格式化回傳給你的 JS
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
        "total_person_count": total_mentions
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)