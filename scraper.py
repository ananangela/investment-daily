#!/usr/bin/env python3
"""
新聞爬蟲 - 使用 Yahoo股市官方 RSS Feed 取得台灣財經新聞（穩定、不被封鎖）
"""
import os
import json
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from typing import List, Optional
import time
import re

class NewsArticle:
    def __init__(self, title: str, summary: str, source: str, source_url: str, article_url: str, content: str = ""):
        self.title = title
        self.summary = summary
        self.source = source
        self.source_url = source_url
        self.article_url = article_url
        self.content = content
        self.score = 0

class NewsScraper:
    def __init__(self, articles_json_path: str = 'articles.json'):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.articles_json_path = articles_json_path

        # 關鍵字清單涵蓋更多元的主題類別，避免過度集中在台積電/半導體
        self.keywords = ['台股', 'AI', '半導體', '記憶體', '晶片', 'ETF',
                         '聯發科', '台積電', '法人', '外資', '投信', '自營商',
                         '漲停', '強勢', '主力', '產業', '概念股', '大盤', '加權指數',
                         '面板', '機器人', '重電', '生技', '金融股', '航運', '綠能',
                         '被動元件', '載板', 'PCB', 'IC設計', '封測', '光通訊',
                         '存股', '高股息', '定期定額', '除息', '填權', '新股', 'IPO']

        # 用來偵測「主題重複」的關鍵詞分類，若今天候選文章與昨天文章主題完全重疊，會優先選擇次高分且主題不同的文章
        self.dominant_topics = ['台積電', '半導體', '面板', '機器人', 'ETF', '聯發科',
                                '日月光', '記憶體', 'PCB', '被動元件', '重電', '生技',
                                '金融股', '航運', '綠能', 'IC設計', '載板', '光通訊']

        # Yahoo股市官方 RSS（穩定，官方提供，不易被擋）；涵蓋多個分類以擴大候選文章的主題多樣性
        self.rss_sources = [
            {
                'url': 'https://tw.stock.yahoo.com/rss?category=tw-market',
                'name': 'Yahoo股市',
            },
            {
                'url': 'https://tw.stock.yahoo.com/rss?category=news',
                'name': 'Yahoo股市',
            },
            {
                'url': 'https://tw.stock.yahoo.com/rss?category=personal-finance',
                'name': 'Yahoo股市理財',
            },
            {
                'url': 'https://tw.stock.yahoo.com/rss?category=funds-news',
                'name': 'Yahoo股市基金',
            },
        ]

    def fetch_rss(self, source: dict) -> List[NewsArticle]:
        """取得 RSS feed 並解析文章列表"""
        articles = []
        try:
            response = requests.get(source['url'], headers=self.headers, timeout=15)
            response.encoding = 'utf-8'

            root = ET.fromstring(response.content)
            items = root.findall('.//item')

            for item in items[:20]:
                title = item.findtext('title', '').strip()
                link = item.findtext('link', '').strip()
                description = item.findtext('description', '').strip()
                description = re.sub(r'<[^>]+>', '', description)[:300]

                if title and len(title) > 5:
                    articles.append(NewsArticle(
                        title=title,
                        summary=description,
                        source=source['name'],
                        source_url='https://tw.stock.yahoo.com',
                        article_url=link
                    ))

            print(f"  {source['name']} ({source['url']}): 取得 {len(articles)} 篇")
        except Exception as e:
            print(f"  {source['name']} RSS 錯誤: {e}")

        return articles

    def fetch_article_content(self, url: str) -> str:
        """取得文章完整內容"""
        if not url:
            return ""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')

            # 移除雜訊區塊（導覽列、頁尾、廣告、腳本等），只保留正文
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'iframe']):
                tag.decompose()
            for tag in soup.find_all(attrs={'class': re.compile(r'(nav|menu|footer|sidebar|ad|banner|share|related|comment)', re.I)}):
                tag.decompose()

            # 優先抓文章主體常見容器，找不到再退回整個 body
            article_body = (
                soup.find('article')
                or soup.find(attrs={'class': re.compile(r'(article|content|caas-body|story)', re.I)})
                or soup.find('body')
            )

            if article_body:
                paragraphs = article_body.find_all(['p', 'h1', 'h2', 'h3', 'li'])
                text = '\n'.join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 10)
            else:
                text = soup.get_text(separator='\n', strip=True)

            text = re.sub(r'\n{2,}', '\n', text).strip()

            return text[:6000]
        except Exception as e:
            print(f"  取得文章內容失敗: {e}")
            return ""

    def score_article(self, article: NewsArticle) -> int:
        """根據標題評分文章相關性。刻意不對單一公司（如台積電）額外加碼，
        避免因其新聞量本來就多而長期壟斷選文結果，改用多樣化的關鍵字讓不同主題有公平的競爭機會。"""
        score = 0
        title = article.title

        for keyword in self.keywords:
            if keyword in title:
                score += 10

        # 避開純社會新聞/花邊（離婚、贈與稅等與投資學習較無關的標題）
        noise_words = ['離婚', '監護權', '贈與稅', '婚後', '婚姻']
        for w in noise_words:
            if w in title:
                score -= 30

        if len(title) < 10:
            score -= 20

        return score

    def get_recent_dominant_topics(self, lookback_days: int = 2) -> set:
        """讀取 articles.json 最近幾天的標題，抓出其中出現的主題關鍵字，用來避免今天選文主題重複"""
        topics = set()
        try:
            if not os.path.exists(self.articles_json_path):
                return topics
            with open(self.articles_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            recent_dates = sorted(data.keys(), reverse=True)[:lookback_days]
            for date in recent_dates:
                headline = data[date].get('headline', '') + data[date].get('deck', '')
                for topic in self.dominant_topics:
                    if topic in headline:
                        topics.add(topic)
        except Exception as e:
            print(f"  讀取近期主題失敗（不影響選文）: {e}")
        return topics

    def _article_topics(self, title: str) -> set:
        return {t for t in self.dominant_topics if t in title}

    def scrape_all(self) -> Optional[NewsArticle]:
        """從所有 RSS 來源取得最相關文章"""
        print("開始從 RSS 取得新聞...")
        all_articles = []

        for source in self.rss_sources:
            articles = self.fetch_rss(source)
            all_articles.extend(articles)
            time.sleep(0.5)

        if not all_articles:
            print("未找到任何文章")
            return None

        print(f"共取得 {len(all_articles)} 篇，開始評分...")

        for article in all_articles:
            article.score = self.score_article(article)

        all_articles.sort(key=lambda x: x.score, reverse=True)

        # 主題避重：若最高分文章的主題與最近幾天完全重複，優先挑選次高分且主題不同的文章
        recent_topics = self.get_recent_dominant_topics(lookback_days=2)
        selected = all_articles[0]
        if recent_topics:
            for candidate in all_articles:
                candidate_topics = self._article_topics(candidate.title)
                # 候選文章沒有主題關鍵字，或主題與近期不完全重疊，視為「主題不重複」
                if not candidate_topics or not candidate_topics.issubset(recent_topics):
                    selected = candidate
                    break
            else:
                print(f"  所有候選文章主題都與近期重複（{recent_topics}），選擇最高分文章")

        print(f"選中文章: {selected.title}")
        print(f"來源: {selected.source} | 評分: {selected.score}")
        if recent_topics:
            print(f"近期主題（避重參考）: {recent_topics}")

        if selected.article_url:
            print("取得文章完整內容...")
            selected.content = self.fetch_article_content(selected.article_url)
            if not selected.content and selected.summary:
                selected.content = selected.summary

        return selected


if __name__ == '__main__':
    import json
    scraper = NewsScraper()
    article = scraper.scrape_all()
    if article:
        print(json.dumps({
            'title': article.title,
            'source': article.source,
            'article_url': article.article_url,
            'content_preview': article.content[:200]
        }, ensure_ascii=False, indent=2))
