#!/usr/bin/env python3
"""
新聞爬蟲 - 使用 RSS Feed 取得台灣財經新聞（穩定、不被封鎖）
"""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
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
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; InvestmentDailyBot/1.0)',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        }
        self.keywords = ['台股', 'AI', '半導體', '記憶體', '晶片', 'ETF',
                         '聯發科', '台積電', '法人', '外資', '投信', '自營商',
                         '漲停', '強勢', '主力', '產業', '概念股']

        # RSS feed 來源（穩定、不需解析 HTML）
        self.rss_sources = [
            {
                'url': 'https://news.cnyes.com/rss/cat/tw_stock',
                'name': '鉅亨網',
                'source_url': 'https://news.cnyes.com'
            },
            {
                'url': 'https://news.cnyes.com/rss/cat/tw_etf',
                'name': '鉅亨網ETF',
                'source_url': 'https://news.cnyes.com'
            },
            {
                'url': 'https://www.moneydj.com/rss/moneydj.aspx',
                'name': 'MoneyDJ',
                'source_url': 'https://www.moneydj.com'
            },
        ]

    def fetch_rss(self, source: dict) -> List[NewsArticle]:
        """取得 RSS feed 並解析文章列表"""
        articles = []
        try:
            response = requests.get(source['url'], headers=self.headers, timeout=15)
            response.encoding = 'utf-8'

            root = ET.fromstring(response.content)
            # 支援標準 RSS 2.0 格式
            ns = {'content': 'http://purl.org/rss/1.0/modules/content/'}
            items = root.findall('.//item')

            for item in items[:10]:
                title = item.findtext('title', '').strip()
                link = item.findtext('link', '').strip()
                description = item.findtext('description', '').strip()
                # 清除 HTML 標籤
                description = re.sub(r'<[^>]+>', '', description)[:300]

                if title and len(title) > 5:
                    articles.append(NewsArticle(
                        title=title,
                        summary=description,
                        source=source['name'],
                        source_url=source['source_url'],
                        article_url=link
                    ))

            print(f"  {source['name']}: 取得 {len(articles)} 篇")
        except Exception as e:
            print(f"  {source['name']} RSS 錯誤: {e}")

        return articles

    def fetch_article_content(self, url: str) -> str:
        """取得文章完整內容"""
        if not url:
            return ""
        try:
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }, timeout=15)
            response.encoding = 'utf-8'

            # 移除 script / style / tag
            text = re.sub(r'<script[^>]*>.*?</script>', '', response.text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()

            return text[:3000]
        except Exception as e:
            print(f"  取得文章內容失敗: {e}")
            return ""

    def score_article(self, article: NewsArticle) -> int:
        """根據標題評分文章相關性"""
        score = 0
        title = article.title

        for keyword in self.keywords:
            if keyword in title:
                score += 10

        # 加分項目
        if '台股' in title or '加權' in title:
            score += 5
        if 'AI' in title or '人工智慧' in title:
            score += 8
        if '台積電' in title or 'TSMC' in title:
            score += 6
        if '法人' in title or '外資' in title:
            score += 5

        # 避開過於簡短或廣告性標題
        if len(title) < 10:
            score -= 20

        return score

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

        # 評分排序
        for article in all_articles:
            article.score = self.score_article(article)

        all_articles.sort(key=lambda x: x.score, reverse=True)
        selected = all_articles[0]

        print(f"選中文章: {selected.title}")
        print(f"來源: {selected.source} | 評分: {selected.score}")

        # 取得完整內容
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
