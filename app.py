import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

API_URL_HF = "https://api-inference.huggingface.co/models/ckiplab/bert-base-chinese-ner"
# 🔴 這裡確保從環境變數讀取，若讀不到會變 None
HF_TOKEN = os.environ.get("HF_TOKEN")

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

def query_huggingface(text):
    if not HF_TOKEN:
        return {"error": "HF_TOKEN 尚未在 Render 設定"}
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": text, "options": {"wait_for_model": True}}
    
    try:
        response = requests.post(API_URL_HF, headers=headers, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        return {"error": f"連線至 Hugging Face 失敗: {str(e)}"}

@app.route('/analyze-text', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        if not data or 'chapterName' not in data[0]:
            return jsonify({"error": "輸入資料格式不正確"}), 400

        text = data[0]['chapterName']
        ner_results = query_huggingface(text)

        # 🟢 處理 AI 模型回傳的各種狀況
        if isinstance(ner_results, dict) and "error" in ner_results:
            # 這會把 Hugging Face 的原話（如 Model loading）傳給前端
            return jsonify({
                "error": "AI 模型回報錯誤",
                "details": ner_results["error"]
            }), 502 

        if not isinstance(ner_results, list):
            return jsonify({"error": "AI 回傳格式非列表", "raw": str(ner_results)}), 500

        people = {}
        for ent in ner_results:
            label = ent.get('entity_group') or ent.get('entity')
            if label == "PERSON":
                name = ent['word'].strip().replace(" ", "").replace("#", "")
                if len(name) > 1:
                    people[name] = people.get(name, 0) + 1

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

    except Exception as e:
        # 🟢 如果真的崩潰了，把錯誤訊息印出來
        print(f"Server Error: {str(e)}")
        return jsonify({"error": "伺服器內部錯誤", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)