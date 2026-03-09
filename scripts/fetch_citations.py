#!/usr/bin/env python3
import json
import os
from scholarly import scholarly

def fetch_citations():
    """Fetch Google Scholar citation count for a specific profile."""
    
    # Your Google Scholar profile ID (from your URL)
    scholar_id = 'b0jYTAUAAAAJ'
    
    try:
        # Fetch the author profile
        author = scholarly.search_author_id(scholar_id)
        author = scholarly.fill(author)
        
        # Get total citations
        citations = author.get('citedby', 0)
        
        # Create the data object
        data = {
            'citations': citations,
            'updated': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
            'profile_url': f'https://scholar.google.com/citations?user={scholar_id}'
        }
        
        # Write to JSON file
        with open('citations.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Updated citations: {citations}")
        return True
        
    except Exception as e:
        print(f"❌ Error fetching citations: {e}")
        # Don't fail the workflow - keep old data
        return False

if __name__ == '__main__':
    fetch_citations()