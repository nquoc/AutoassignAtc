import json
import urllib.parse

def run():
    with open('regions.json', 'r', encoding='utf-8') as f:
        regions = json.load(f)

    for r in regions:
        url = r.get("url")
        if not url:
            continue
            
        # Parse URL
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query, keep_blank_values=True)
        
        # Update sorting
        query_params['orderby'] = ['createdtime']
        query_params['sortorder'] = ['ASC']
        
        # Reconstruct query string, urlencode it with doseq=True to handle list values correctly
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        
        # Reconstruct URL
        new_url = urllib.parse.urlunparse(
            (parsed_url.scheme, parsed_url.netloc, parsed_url.path, 
             parsed_url.params, new_query, parsed_url.fragment)
        )
        r["url"] = new_url

    with open('regions.json', 'w', encoding='utf-8') as f:
        json.dump(regions, f, ensure_ascii=False, indent=2)
        
    print(f"Updated {len(regions)} regions.")

if __name__ == "__main__":
    run()
