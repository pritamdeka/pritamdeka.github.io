#!/usr/bin/env python3
import json
import os
import requests

def fetch_citations():
    scholar_id = 'b0jYTAUAAAAJ'
    api_key = os.environ.get('SERPAPI_KEY')
    
    try:
        url = 'https://serpapi.com/search'
        params = {
            'engine': 'google_scholar_author',
            'author_id': scholar_id,
            'api_key': api_key
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        citations = data.get('author', {}).get('cited_by', 0)
        
        result = {
            'citations': citations,
            'updated': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
            'profile_url': f'https://scholar.google.com/citations?user={scholar_id}'
        }
        
        with open('citations.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"✅ Updated citations: {citations}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    fetch_citations()