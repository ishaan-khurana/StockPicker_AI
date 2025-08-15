#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 14 16:06:25 2025

@author: ishaankhurana
"""
import os
import datetime
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from newsapi import NewsApiClient
from openai import OpenAI

# ===== Load from Environment Variables =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# ===== Constants =====
SECTORS = ["biotechnology", "bioelectronic medicine", "energy production", "technology"]
MY_STOCKS = ["AAPL", "NVDA", "AVGO", "SMR", "VOO"]
RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "").split(",")  # Add more as needed

# ===== Initialize Clients =====
newsapi = NewsApiClient(api_key=NEWS_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)


# ===== Functions =====
def get_sector_news(portfolio_tickers):
    all_articles = []
    queries = SECTORS + portfolio_tickers
    for query in queries:
        try:
            articles = newsapi.get_everything(q=query, language='en', sort_by='publishedAt', page_size=3)
            all_articles += articles.get("articles", [])
        except Exception as e:
            print(f"❌ Error fetching news for '{query}': {e}")
    return all_articles


def analyze_news_with_gpt(articles, portfolio_tickers):
    titles = [f"- {a['title']}: {a['description']}" for a in articles if a.get('title') and a.get('description')]
    news_input = "\n".join(titles)
    portfolio_list = ", ".join(portfolio_tickers)

    prompt = f"""
You are a professional financial analyst working for a long-term investor.

You are provided with recent financial news headlines and summaries related to various sectors and companies.

1. Based on the news below, identify 3–5 **specific stock tickers** likely to:
   - Secure major contracts,
   - Receive FDA/clinical/regulatory approvals,
   - Benefit from favorable macro or sector-specific trends, or
   - Outperform in the long term.

2. Avoid vague generalities or references to institutions (e.g., "Gates Foundation-backed"). Focus on **public companies**, **tickers**, and **specific drivers**.

3. Separately, analyze the current portfolio: {portfolio_list}
   - Forecast short- to mid-term trends (bullish, bearish, stable)
   - Note catalysts, risks, or signals from the latest news
   - Recommend: Hold, Add, Reduce (with brief rationale)

News:
{news_input}

Provide a clean, structured analyst-style report.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return response.choices[0].message.content.strip()


def analyze_portfolio_stocks(tickers):
    insights = ""
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="6mo")
            if hist.empty:
                insights += f"{ticker} - No recent data available.\n"
                continue
            change = ((hist['Close'][-1] - hist['Close'][0]) / hist['Close'][0]) * 100
            insights += f"{ticker} – 6mo Change: {change:.2f}% | Current Price: ${hist['Close'][-1]:.2f}\n"
        except Exception as e:
            insights += f"{ticker} – Error retrieving data: {e}\n"
    return insights


def send_email(subject, body, recipients):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
            print("✅ Email sent successfully.")
    except smtplib.SMTPAuthenticationError as e:
        print("❌ SMTP Authentication Error:", e)
    except Exception as e:
        print("❌ Failed to send email:", e)


# ===== Main Report Generator =====
def generate_and_send_report():
    try:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        print("📡 Fetching news...")
        articles = get_sector_news(MY_STOCKS)

        print("🧠 GPT analyzing news + portfolio...")
        gpt_analysis = analyze_news_with_gpt(articles, MY_STOCKS)

        print("📊 Analyzing raw stock performance...")
        portfolio_report = analyze_portfolio_stocks(MY_STOCKS)

        full_report = f"""
📈 Daily Stock Insight Report – {today}

🧠 GPT-Powered Market Intelligence:
{gpt_analysis}

💼 Portfolio Snapshot:
{portfolio_report}
"""

        print("📧 Sending report...")
        send_email("📬 Daily Stock Report", full_report, RECIPIENTS)

    except Exception as e:
        print("❌ Error generating or sending report:", e)


# ===== Run Immediately (for GitHub Actions) =====
if __name__ == "__main__":
    generate_and_send_report()
