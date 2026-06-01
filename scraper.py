#!/usr/bin/env python3
"""
新聞爬蟲 - 從多個財經新聞來源爬取
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import List, Dict, Optional
import time

class NewsArticle:
    def __init__(self, title: str, summary: str, source: str, source_url: str, article_url: str, content: str = ""):
        self.title = title
        self.summary = summary
        self.source = source
        self.source_url = source_url
        self.article_url = article_url
        self.content = content

class NewsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.articles: List[NewsArticle] = []
        self.keywords = ['台股', 'AI', '半導體', '記憶體', '晶片', 'ETF', '個股', '聯發科', '台積電', '面板']

    def scrape_yahoo(self) -> List[NewsArticle]:
        """爬取 Yahoo 股市新聞"""
        try:
            url = "https://tw.stock.yahoo.com/"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            articles = []
            # Yahoo 股市的新聞區塊結構
            news_items = soup.find_all('a', {'class': 'Fz(14px)'})[:5]

            for item in news_items:
                title = item.get_text(strip=True)
                link = item.get('href', '')

                if title and len(title) > 5:
                    article = NewsArticle(
                        title=title,
                        summary="",
                        source="Yahoo股市",
                        source_url="https://tw.stock.yahoo.com",
                        article_url=link if link.startswith('http') else f"https://tw.stock.yahoo.com{link}"
                    )
                    articles.append(article)

            return articles[:3]
        except Exception as e:
            print(f"Yahoo 爬蟲錯誤: {e}")
            return []

    def scrape_cmoney(self) -> List[NewsArticle]:
        """爬取 CMoney 新聞"""
        try:
            url = "https://www.cmoney.tw/news"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            articles = []
            # CMoney 新聞結構
            news_items = soup.find_all('h2', {'class': 'news-title'})[:5]

            for item in news_items:
                title = item.get_text(strip=True)
                link_tag = item.find_parent('a')
                link = link_tag.get('href', '') if link_tag else ''

                if title and len(title) > 5:
                    article = NewsArticle(
                        title=title,
                        summary="",
                        source="CMoney投資新聞",
                        source_url="https://www.cmoney.tw",
                        article_url=link if link.startswith('http') else f"https://www.cmoney.tw{link}"
                    )
                    articles.append(article)

            return articles[:3]
        except Exception as e:
            print(f"CMoney 爬蟲錯誤: {e}")
            return []

    def scrape_udn(self) -> List[NewsArticle]:
        """爬取聯合新聞網"""
        try:
            url = "https://udn.com/news/cate/2085"  # 股市類別
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            articles = []
            # UDN 新聞結構
            news_items = soup.find_all('h2', {'class': 'story-title'})[:5]

            for item in news_items:
                title = item.get_text(strip=True)
                link_tag = item.find_parent('a')
                link = link_tag.get('href', '') if link_tag else ''

                if title and len(title) > 5:
                    article = NewsArticle(
                        title=title,
                        summary="",
                        source="聯合新聞網",
                        source_url="https://udn.com/news/finance",
                        article_url=link
                    )
                    articles.append(article)

            return articles[:3]
        except Exception as e:
            print(f"聯合新聞網爬蟲錯誤: {e}")
            return []

    def scrape_ctee(self) -> List[NewsArticle]:
        """爬取工商時報"""
        try:
            url = "https://www.ctee.com.tw/"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            articles = []
            # 工商時報新聞結構
            news_items = soup.find_all('h2')[:5]

            for item in news_items:
                title = item.get_text(strip=True)
                link_tag = item.find_parent('a')
                link = link_tag.get('href', '') if link_tag else ''

                if title and len(title) > 5 and link:
                    article = NewsArticle(
                        title=title,
                        summary="",
                        source="工商時報",
                        source_url="https://www.ctee.com.tw",
                        article_url=link if link.startswith('http') else f"https://www.ctee.com.tw{link}"
                    )
                    articles.append(article)

            return articles[:3]
        except Exception as e:
            print(f"工商時報爬蟲錯誤: {e}")
            return []

    def fetch_article_content(self, url: str) -> str:
        """獲取文章完整內容"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            # 移除 script 和 style
            for script in soup(['script', 'style']):
                script.decompose()

            # 提取文章內容（根據不同網站調整選擇器）
            content_tags = soup.find_all(['p', 'div'], limit=20)
            content = ' '.join([tag.get_text(strip=True) for tag in content_tags])

            return content[:2000]  # 限制長度
        except Exception as e:
            print(f"獲取文章內容失敗: {e}")
            return ""

    def score_article(self, article: NewsArticle) -> int:
        """根據標題和內容評分文章相關性"""
        score = 0
        title_lower = article.title.lower()

        # 檢查關鍵字
        for keyword in self.keywords:
            if keyword in title_lower:
                score += 10

        # 優先級
        if '台股' in title_lower or '加權' in title_lower:
            score += 5
        if 'AI' in article.title or 'ai' in title_lower:
            score += 8

        return score

    def scrape_all(self) -> Optional[NewsArticle]:
        """爬取所有來源並返回最相關的文章"""
        print("開始爬蟲...")
        all_articles = []

        # 爬取所有來源
        all_articles.extend(self.scrape_yahoo())
        time.sleep(1)
        all_articles.extend(self.scrape_cmoney())
        time.sleep(1)
        all_articles.extend(self.scrape_udn())
        time.sleep(1)
        all_articles.extend(self.scrape_ctee())

        if not all_articles:
            print("未找到文章")
            return None

        # 為每篇文章評分
        for article in all_articles:
            article.score = self.score_article(article)

        # 排序並選擇最高分的文章
        all_articles.sort(key=lambda x: x.score, reverse=True)
        selected = all_articles[0]

        print(f"選中文章: {selected.title}")
        print(f"來源: {selected.source}")

        # 獲取完整內容
        if selected.article_url:
            selected.content = self.fetch_article_content(selected.article_url)

        return selected

def main():
    scraper = NewsScraper()
    article = scraper.scrape_all()

    if article:
        result = {
            'title': article.title,
            'summary': article.summary,
            'source': article.source,
            'source_url': article.source_url,
            'article_url': article.article_url,
            'content': article.content
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    return None

if __name__ == '__main__':
    main()
