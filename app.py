import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# 設定 Flask，讓它能從根目錄託管 index.html, JS 與 CSS
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ----------------------------------------
# 配置區
# ----------------------------------------
# 使用 Hugging Face 最新的 Router 網址與中文 NER 模型
API_URL_HF = "https://router.huggingface.co/hf-inference/models/ckiplab/bert-base-chinese-ner"
HF_TOKEN = os.environ.get("HF_TOKEN")

# ----------------------------------------
# 路由 1：首頁 (託管前端)
# ----------------------------------------
@app.route('/')
def index():
    """當訪問網址時，自動讀取並顯示同目錄下的 index.html"""
    return send_from_directory('.', 'index.html')

# ----------------------------------------
# 路由 2：AI 分析介面
# ----------------------------------------
def query_huggingface(text):
    """呼叫 Hugging Face 推理 API"""
    if not HF_TOKEN:
        return {"error": "環境變數中找不到 HF_TOKEN，請檢查 Render 設定"}
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": text, 
        "options": {"wait_for_model": True} # 強制等待模型載入完成
    }
    
    try:
        response = requests.post(API_URL_HF, headers=headers, json=payload, timeout=30)
        # 如果模型還在加載，Hugging Face 會回傳 503
        return response.json()
    except Exception as e:
        return {"error": f"API 連線異常: {str(e)}"}

@app.route('/analyze-text', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        if not data or not isinstance(data, list) or 'chapterName' not in data[0]:
            return jsonify({"error": "輸入資料格式無效"}), 400

        text = data[0]['chapterName']
        print(f"--- 正在處理分析請求: {text[:20]}... ---")

        # 執行 AI 推論
        ner_results = query_huggingface(text)
        print(f"AI 模型回傳: {ner_results}")

        # 錯誤處理 (如果 AI 回傳的是錯誤字典而非結果列表)
        if isinstance(ner_results, dict) and "error" in ner_results:
            return jsonify({
                "error": "AI 模型暫時無法服務",
                "details": ner_results["error"]
            }), 502

        if not isinstance(ner_results, list):
            return jsonify({"error": "AI 回傳格式錯誤", "raw": str(ner_results)}), 500

        # 統計人名 (PERSON)
        people = {}
        for ent in ner_results:
            label = ent.get('entity_group') or ent.get('entity')
            if label == "PERSON":
                # 清除人名中的空格與 ## 符號 (CKIP 模型特性)
                name = ent['word'].strip().replace(" ", "").replace("#", "")
                if len(name) > 1:
                    people[name] = people.get(name, 0) + 1

        # 格式化輸出
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
        print(f"Server Error: {str(e)}")
        return jsonify({"error": "伺服器內部發生預期外錯誤", "message": str(e)}), 500

if __name__ == '__main__':
    # Render 環境預設使用 10000 埠
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)