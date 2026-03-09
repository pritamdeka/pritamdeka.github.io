#!/usr/bin/env python3
import json
import os
import requests
from datetime import datetime, timezone

def fetch_citations():
    scholar_id = 'b0jYTAUAAAAJ'
    api_key = os.environ.get('SERPAPI_KEY')
    
    if not api_key:
        print("❌ SERPAPI_KEY not found!")
        return 172
    
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
            return 172
        
        # ✅ Correct path to citations
        citations = data.get('cited_by', {}).get('table', [{}])[0].get('citations', {}).get('all', 0)
        
        print(f"✅ Citations: {citations}")
        return citations
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 172

def main():
    citations = fetch_citations()
    
    data = {
        'citations': citations,
        'updated': datetime.now(timezone.utc).isoformat(),
        'scholar_url': 'https://scholar.google.com/citations?user=b0jYTAUAAAAJ'
    }
    
    with open('citations.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"📊 Updated: {citations} citations")

if __name__ == '__main__':
    main()