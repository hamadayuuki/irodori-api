import csv

def merge_csv_files():
    # Read urls.csv
    urls_data = {}
    with open('urls.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header
        for i, row in enumerate(reader, 1):
            if len(row) >= 2:
                urls_data[i] = [row[0], row[1]]  # image_url, pin_url_guess
            else:
                urls_data[i] = ['', '']
    
    # Read coordinates.csv and create new merged file
    output_rows = []
    with open('coordinates.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        # Create new header: id, image_url, pin_url_guess, then original columns 2-6
        new_header = [header[0]] + ['image_url', 'pin_url_guess'] + header[1:]
        output_rows.append(new_header)
        
        for i, row in enumerate(reader, 1):
            # Get URLs for this row (default to empty if not found)
            urls = urls_data.get(i, ['', ''])
            
            # Create new row: id, image_url, pin_url_guess, then original columns 2-6
            new_row = [row[0]] + urls + row[1:]
            output_rows.append(new_row)
    
    # Write the merged data back to coordinates.csv
    with open('coordinates.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(output_rows)
    
    print(f"Successfully merged files. Added {len(urls_data)} URL entries to coordinates.csv")

if __name__ == "__main__":
    merge_csv_files()