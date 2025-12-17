document.addEventListener('DOMContentLoaded', () => {
    const analyzeButton = document.getElementById('analyze-button');
    const textInput = document.getElementById('text-input');
    const entityList = document.getElementById('entity-list');
    const statusMessage = document.getElementById('status-message');

    const API_URL = '/analyze-text';
    function renderResults(data) {
        entityList.innerHTML = '';
        
        const namedEntities = data.named_entities || [];
        
        // 1. 篩選出所有人物 (Person)
        const people = namedEntities.filter(e => e.entity_type === "Person");

        // 🚨 重新計算：所有「人物」出現的總次數之和，作為新的分母
        const totalPeopleMentions = people.reduce((sum, p) => sum + p.count, 0);

        if (people.length > 0) {
            // 設定 CSS 變數控制 Layout (1~5個並排)
            entityList.style.setProperty('--item-count', people.length);

            people.forEach(person => {
                // 🚨 核心邏輯修改：根據人物總數計算佔比
                const relativeScore = (person.count / totalPeopleMentions) * 100;

                const card = document.createElement('div');
                card.className = 'entity-card';
                card.innerHTML = `
                    <h4>${person.name}</h4>
                    <div class="card-info">
                        <p><strong>RANK:</strong> IDENTIFIED</p>
                        <p><strong>MENTIONS:</strong> ${person.count}</p>
                        <p><strong>SCORE:</strong> ${relativeScore.toFixed(0)}%</p>
                    </div>
                `;
                entityList.appendChild(card);
            });
            statusMessage.textContent = "分析成功：已更新權重計算。";
        } else {
            entityList.innerHTML = '<p class="placeholder-text">未偵測到任何人物實體。</p>';
            statusMessage.textContent = "未發現人物數據。";
        }
    }

    analyzeButton.addEventListener('click', async () => {
        const rawText = textInput.value.trim();
        if (!rawText) {
            statusMessage.textContent = "請輸入文字。";
            return;
        }

        statusMessage.textContent = "正在掃描文本...";
        entityList.innerHTML = '<p class="placeholder-text">SCANNING IN PROGRESS...</p>';
        
        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify([{ "chapterID": "001", "chapterName": rawText }])
            });

            if (response.ok) {
                const data = await response.json();
                renderResults(data);
            } else {
                statusMessage.textContent = "伺服器回應錯誤。";
            }
        } catch (err) {
            statusMessage.textContent = "連線失敗，請檢查 Python 後端。";
        }
    });
});