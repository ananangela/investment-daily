#!/usr/bin/env python3
"""
使用 GitHub Models（免費 AI 推論）生成投資日報文章
文件: https://docs.github.com/en/github-models
"""
import os
import json
import requests
from datetime import datetime

GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"
GITHUB_MODELS_MODEL = "openai/gpt-4o"  # 用完整版 gpt-4o（非 mini），品質更接近 Claude Opus 的原始水準


def _call_github_models(prompt: str) -> str:
    """呼叫 GitHub Models API（免費，使用 GITHUB_TOKEN 認證）"""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("找不到 GITHUB_TOKEN 環境變數，請確認 workflow 已設定")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GITHUB_MODELS_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 3500,
    }

    response = requests.post(GITHUB_MODELS_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def generate_article(news_data: dict) -> dict:
    """
    根據爬蟲取得的新聞內容，使用 GitHub Models 生成完整的投資日報文章
    """

    title = news_data.get('title', '')
    content = news_data.get('content', '')
    source = news_data.get('source', '')
    source_url = news_data.get('source_url', '')
    article_url = news_data.get('article_url', '')

    if not content:
        print("錯誤：無法獲取文章內容")
        return None

    prompt = f"""你是「投資日報」的專欄作者，專門把當日財經新聞改寫成給投資小白看的深度教學文章。你的讀者完全不懂股市術語，需要你把每個概念講到「聽得懂、記得住、學得會判斷」。

【新聞標題】
{title}

【新聞內容】
{content}

請以 JSON 格式回應，包含以下字段（務必是有效的 JSON，不要包含任何 markdown 標記）：
{{
  "headline": "新聞標題（20-35字，吸引人且包含具體數字）",
  "deck": "新聞摘要（50-80字，概括重點，包含至少1個具體數字）",
  "summary": "詳細摘要（180-250字，使用 <strong> 標籤密集強調關鍵數字、公司名稱、重要概念，至少標記5-6處）",
  "keypoints": ["重點1", "重點2", "重點3", "重點4", "重點5"],
  "tags": [
    {{"t": "stock", "l": "個股"}},
    {{"t": "industry", "l": "產業名稱"}},
    {{"t": "etf", "l": "ETF"}}
  ],
  "difficulty": "beginner 或 intermediate",
  "difficultyLabel": "初級 或 進階",
  "terms": [
    {{
      "name": "名詞1",
      "en": "English Name",
      "short": "簡短定義（20-30字）",
      "full": "完整說明（100-150字）",
      "eg": "💡 生活化比喻，用讀者日常經驗類比這個金融概念"
    }}
  ]
}}

品質標準（非常重要，請嚴格遵守，你的輸出會被拿去跟過去的高品質文章比較）：

1. keypoints 每一點不是單純複述新聞事實，而是要「解讀意義」——說明這個現象代表什麼、對投資人有什麼啟示。範例對比：
   - ❌ 差的寫法：「台積電上漲15元，帶動市場信心。」（只是複述數字）
   - ✅ 好的寫法：「台積電漲15元領軍——護國神山續強代表外資對AI晶片需求信心不減，通常會帶動其他權值股跟漲。」（解讀+因果+啟示）
   每一點應該是 30-60 字，包含「發生了什麼」+「為什麼重要/代表什麼」。

2. terms 絕對不要選「台積電」「加權指數」「通膨」這種讀者早就知道的基本詞彙。應該選新聞中出現的、真正需要解釋的專業術語或市場黑話，例如：資金輪動、籌碼面、法人買超/賣超、本益比、除息填權、主力進出、產業鏈受惠、催化劑、評價調整、軋空等。如果新聞內容本身沒有專業術語，你可以選擇與新聞情境最相關的投資觀念名詞（例如「權值股」「成交量」「多頭排列」等），但仍要避開過於基礎的常識詞。
   每個名詞的 full 說明要有 100-150 字，具體連結到今天新聞的情境（不要寫成通用教科書定義），並給初學者具體的行動啟示（該注意什麼、該怎麼做）。
   eg 範例要用「生活化情境」做類比（吃飯、爬山、夜市、演唱會門票等），不要只是重複解釋一次名詞。

3. summary 中的 <strong> 標籤要密集覆蓋所有關鍵數字（漲跌點數、百分比、股價、成交量）與重要名詞，讓讀者一眼掃過就能抓到重點，不要只標記1-2處。

4. tags 應根據內容選擇最多3個，優先選 stock/etf/industry，industry 的 l 欄位要填具體產業名稱（如「半導體」「面板」）而非「產業」兩字。

5. 完全禁止輸出 markdown 代碼塊或任何格式化符號，直接輸出 JSON。

6. 如果新聞內容資訊量較少，你仍然要主動延伸：可以補充該產業/公司的背景脈絡、與其他相關新聞的關聯、對大盤的可能影響，讓文章保持應有的深度，不要因為原始新聞短就交出空泛的內容。"""

    print(f"正在使用 GitHub Models（{GITHUB_MODELS_MODEL}）生成文章內容...")

    response_text = _call_github_models(prompt)

    # 清理 JSON（移除可能的 markdown 包裝）
    response_text = response_text.strip()
    if response_text.startswith('```'):
        response_text = response_text.split('```')[1]
        if response_text.startswith('json'):
            response_text = response_text[4:]
    response_text = response_text.strip()

    try:
        article_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"JSON 解析錯誤: {e}")
        print(f"原始回應: {response_text[:500]}")
        return None

    today = datetime.now().strftime('%Y-%m-%d')

    article = {
        "headline": article_data.get('headline', title),
        "deck": article_data.get('deck', ''),
        "source": source,
        "sourceUrl": source_url,
        "readingTime": 4,
        "difficulty": article_data.get('difficulty', 'beginner'),
        "difficultyLabel": article_data.get('difficultyLabel', '初級'),
        "tags": article_data.get('tags', [{"t": "stock", "l": "個股"}]),
        "summary": article_data.get('summary', ''),
        "keypoints": article_data.get('keypoints', []),
        "terms": article_data.get('terms', [])
    }

    return {
        "date": today,
        "article": article,
        "article_url": article_url
    }


def update_articles_json(new_article_data: dict):
    """
    將新文章添加到 articles.json
    """
    try:
        with open('articles.json', 'r', encoding='utf-8') as f:
            articles = json.load(f)
    except FileNotFoundError:
        articles = {}

    date = new_article_data['date']
    article = new_article_data['article']

    if date in articles:
        print(f"警告：{date} 已有文章，將被覆蓋")

    articles[date] = article

    with open('articles.json', 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"✓ 文章已保存到 articles.json: {date}")
    return articles


def main():
    import sys
    if len(sys.argv) > 1:
        news_data = json.loads(sys.argv[1])
    else:
        news_data = json.load(sys.stdin)

    result = generate_article(news_data)

    if result:
        update_articles_json(result)
        print("完成！")
        return result
    else:
        print("生成失敗")
        return None


if __name__ == '__main__':
    main()
