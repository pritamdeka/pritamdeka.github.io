#!/usr/bin/env python3
import json
import os
import requests
from datetime import datetime, timezone

def fetch_scholar_data():
    scholar_id = 'b0jYTAUAAAAJ'
    api_key = os.environ.get('SERPAPI_KEY')
    
    if not api_key:
        print("❌ SERPAPI_KEY not found!")
        return 174, 0
    
    try:
        url = 'https://serpapi.com/search'
        params = {
            'engine': 'google_scholar_author',
            'author_id': scholar_id,
            'api_key': api_key
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'error' in data:
            print(f"❌ API Error: {data['error']}")
            return 174, 0
        
        # Get citations
        citations = data.get('cited_by', {}).get('table', [{}])[0].get('citations', {}).get('all', 0)
        
        # Get paper count from articles array
        articles = data.get('articles', [])
        paper_count = len(articles)
        
        print(f"✅ Citations: {citations}")
        print(f"✅ Papers: {paper_count}")
        
        return citations, paper_count
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 174, 10  # fallbacks

def main():
    citations, papers = fetch_scholar_data()
    
    data = {
        'citations': citations,
        'papers': papers,
        'updated': datetime.now(timezone.utc).isoformat(),
        'scholar_url': 'https://scholar.google.com/citations?user=b0jYTAUAAAAJ'
    }
    
    with open('citations.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"📊 Updated: {citations} citations, {papers} papers")

if __name__ == '__main__':
    main()