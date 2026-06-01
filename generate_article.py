#!/usr/bin/env python3
"""
使用 Claude API 生成投資日報文章
"""
import json
from datetime import datetime
from anthropic import Anthropic

client = Anthropic()

def generate_article(news_data: dict) -> dict:
    """
    根據爬蟲取得的新聞內容，使用 Claude 生成完整的投資日報文章
    """

    title = news_data.get('title', '')
    content = news_data.get('content', '')
    source = news_data.get('source', '')
    source_url = news_data.get('source_url', '')
    article_url = news_data.get('article_url', '')

    if not content:
        print("錯誤：無法獲取文章內容")
        return None

    # 第一步：生成摘要、重點和名詞解釋
    prompt = f"""我需要你幫我分析以下投資新聞，並生成投資日報的內容。

【新聞標題】
{title}

【新聞內容】
{content}

請以 JSON 格式回應，包含以下字段（務必是有效的 JSON）：
{{
  "headline": "新聞標題（20-30字，吸引人的版本）",
  "deck": "新聞摘要（50-80字，概括重點）",
  "summary": "詳細摘要（150-200字，包含 <strong> 標籤強調關鍵字）",
  "keypoints": ["重點1（初學者視角，20-40字）", "重點2", "重點3", "重點4", "重點5"],
  "tags": [
    {{"t": "stock", "l": "個股"}},
    {{"t": "industry", "l": "產業名稱"}},
    {{"t": "etf", "l": "ETF"}} 或其他
  ],
  "difficulty": "beginner 或 intermediate",
  "difficultyLabel": "初級 或 進階",
  "terms": [
    {{
      "name": "名詞1",
      "en": "English Name",
      "short": "簡短定義（20-30字）",
      "full": "完整說明（80-120字）",
      "eg": "💡 例子說明"
    }}
  ]
}}

重要規則：
1. tags 應根據內容選擇最多3個，優先選 stock/etf/industry
2. keypoints 應該有 5 個，避免冗長，使用簡白的財經術語
3. terms 應該選 3-5 個最重要的名詞，每個名詞都要有詳細說明
4. summary 中應使用 <strong> 標籤強調 2-3 個關鍵數字或概念
5. 語氣應該適合初學投資者理解
6. 完全禁止輸出 markdown 代碼塊或任何格式化符號，直接輸出 JSON"""

    print("正在使用 Claude 生成文章內容...")

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = response.content[0].text

    # 清理 JSON（移除可能的 markdown 包裝）
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

    # 取得今天的日期
    today = datetime.now().strftime('%Y-%m-%d')

    # 組合最終文章數據
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
    # 讀取現有數據
    try:
        with open('articles.json', 'r', encoding='utf-8') as f:
            articles = json.load(f)
    except FileNotFoundError:
        articles = {}

    date = new_article_data['date']
    article = new_article_data['article']

    # 檢查日期是否已存在
    if date in articles:
        print(f"警告：{date} 已有文章，將被覆蓋")

    articles[date] = article

    # 寫入文件
    with open('articles.json', 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"✓ 文章已保存到 articles.json: {date}")
    return articles

def main():
    # 讀取爬蟲的輸出
    import sys
    if len(sys.argv) > 1:
        # 從命令行參數讀取
        news_data = json.loads(sys.argv[1])
    else:
        # 從標準輸入讀取（用於管道）
        news_data = json.load(sys.stdin)

    # 生成文章
    result = generate_article(news_data)

    if result:
        # 更新 JSON 文件
        update_articles_json(result)
        print("完成！")
        return result
    else:
        print("生成失敗")
        return None

if __name__ == '__main__':
    main()
