#!/usr/bin/env python3
"""
投資日報自動更新主程式
流程：爬取新聞 → 生成分析 → 更新 JSON → 提交 Git
"""
import subprocess
import json
import sys
from scraper import NewsScraper
from generate_article import generate_article, update_articles_json

def main():
    print("=" * 50)
    print("投資日報自動更新")
    print("=" * 50)

    # Step 1: 爬取新聞
    print("\n[1/3] 爬取最新新聞...")
    scraper = NewsScraper()
    article = scraper.scrape_all()

    if not article:
        print("✗ 爬蟲失敗，無法獲取新聞")
        sys.exit(1)

    news_data = {
        'title': article.title,
        'summary': article.summary,
        'source': article.source,
        'source_url': article.source_url,
        'article_url': article.article_url,
        'content': article.content
    }

    # Step 2: 使用 Claude 生成文章
    print("\n[2/3] 使用 Claude 生成分析...")
    result = generate_article(news_data)

    if not result:
        print("✗ 文章生成失敗")
        sys.exit(1)

    # Step 3: 更新 articles.json
    print("\n[3/3] 更新 articles.json...")
    update_articles_json(result)

    print("\n" + "=" * 50)
    print("✓ 更新完成！")
    print("=" * 50)
    print(f"日期: {result['date']}")
    print(f"標題: {result['article']['headline']}")
    print(f"來源: {result['article']['source']}")

    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n✗ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
