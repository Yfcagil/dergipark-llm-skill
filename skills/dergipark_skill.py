import requests
from bs4 import BeautifulSoup
import os
import PyPDF2
from transformers import pipeline

# Özetleme modeli
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def search_dergipark(query, max_results=3):
    base_url = "https://dergipark.org.tr/tr/search"
    params = {"q": query}
    response = requests.get(base_url, params=params)
    soup = BeautifulSoup(response.text, "html.parser")

    articles = []
    results = soup.select(".search-results .card-body")[:max_results]

    for result in results:
        title = result.find("a").text.strip()
        link = "https://dergipark.org.tr" + result.find("a")["href"]
        summary = result.find("p").text.strip() if result.find("p") else "Özet bulunamadı"

        # PDF linkini bulmak için detay sayfasına git
        article_page = requests.get(link)
        article_soup = BeautifulSoup(article_page.text, "html.parser")
        pdf_btn = article_soup.find("a", class_="btn-primary", href=True)
        if pdf_btn and pdf_btn['href'].endswith(".pdf"):
            pdf_link = "https://dergipark.org.tr" + pdf_btn['href']
        else:
            pdf_link = None

        articles.append({
            "title": title,
            "summary": summary,
            "link": link,
            "pdf_link": pdf_link
        })

    return articles

def download_and_read_pdf(pdf_url):
    response = requests.get(pdf_url)
    filename = "temp_article.pdf"
    with open(filename, "wb") as f:
        f.write(response.content)

    text = ""
    with open(filename, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""

    os.remove(filename)
    return text

def summarize_text(text, max_tokens=500):
    if not text.strip():
        return "PDF içeriği okunamadı."

    chunks = [text[i:i + 1000] for i in range(0, len(text), 1000)]
    summaries = []
    for chunk in chunks[:2]:
        summary = summarizer(chunk, max_length=130, min_length=30, do_sample=False)[0]['summary_text']
        summaries.append(summary)
    return "\n".join(summaries)

def run_skill(params):
    query = params.get("query", "")
    if not query:
        return "Lütfen bir arama sorgusu belirtin."

    results = search_dergipark(query)

    output = ""
    for i, article in enumerate(results, 1):
        output += f"{i}. {article['title']}\n{article['summary']}\n{article['link']}\n"

        if article["pdf_link"]:
            pdf_text = download_and_read_pdf(article["pdf_link"])
            summary = summarize_text(pdf_text)
            output += f"📄 PDF Özeti:\n{summary}\n"
        else:
            output += "📎 PDF bulunamadı.\n"

        output += "\n" + ("-" * 40) + "\n"

    return output
