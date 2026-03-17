"""
Debug script to check for duplicate standard items in Firestore
"""

from standard_items_service import StandardItemsService
from collections import defaultdict

def check_duplicates():
    """Check for duplicate standard items"""
    service = StandardItemsService()

    # Get all standard items (no filters)
    print("Fetching all standard items...")
    items = service.get_standard_items(limit=1000)

    print(f"\nTotal items returned: {len(items)}")

    # Check for duplicates by storage_url
    url_map = defaultdict(list)
    filename_map = defaultdict(list)

    for item in items:
        storage_url = item.get('storage_url', '')
        filename = item.get('filename', '')
        item_id = item.get('id', '')

        url_map[storage_url].append(item_id)
        filename_map[filename].append(item_id)

    # Find duplicates
    duplicate_urls = {url: ids for url, ids in url_map.items() if len(ids) > 1}
    duplicate_filenames = {fn: ids for fn, ids in filename_map.items() if len(ids) > 1}

    print(f"\n=== Duplicate Analysis ===")
    print(f"Unique storage_urls: {len(url_map)}")
    print(f"Duplicate storage_urls: {len(duplicate_urls)}")
    print(f"Unique filenames: {len(filename_map)}")
    print(f"Duplicate filenames: {len(duplicate_filenames)}")

    if duplicate_urls:
        print("\n=== Duplicate URLs (showing first 10) ===")
        for i, (url, ids) in enumerate(list(duplicate_urls.items())[:10]):
            print(f"\n{i+1}. URL: {url[:80]}...")
            print(f"   IDs: {ids}")
            # Show details for first duplicate
            for item in items:
                if item['id'] == ids[0]:
                    print(f"   Details: {item['gender']}/{item['main_category']}/{item['sub_category']}/{item['color']}")
                    break

    if duplicate_filenames:
        print("\n=== Duplicate Filenames (showing first 10) ===")
        for i, (fn, ids) in enumerate(list(duplicate_filenames.items())[:10]):
            print(f"\n{i+1}. Filename: {fn}")
            print(f"   IDs: {ids}")

    # Category breakdown
    category_counts = defaultdict(int)
    for item in items:
        category = f"{item['gender']}/{item['main_category']}"
        category_counts[category] += 1

    print("\n=== Category Breakdown ===")
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{category}: {count} items")

if __name__ == "__main__":
    check_duplicates()
