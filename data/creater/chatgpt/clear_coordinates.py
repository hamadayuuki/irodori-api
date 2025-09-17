import csv
import os

def clear_coordinate_columns():
    """Clear values in coordinate_review, tops_categorize, bottoms_categorize columns"""
    
    # Define file paths
    men_file = './men/coordinates.csv'
    women_file = './women/coordinates.csv'
    
    files_to_process = [men_file, women_file]
    
    for file_path in files_to_process:
        if os.path.exists(file_path):
            # Read CSV file
            rows = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
                rows.append(headers)
                
                # Find column indices
                coordinate_review_idx = headers.index('coordinate_review') if 'coordinate_review' in headers else -1
                tops_categorize_idx = headers.index('tops_categorize') if 'tops_categorize' in headers else -1
                bottoms_categorize_idx = headers.index('bottoms_categorize') if 'bottoms_categorize' in headers else -1
                
                # Process data rows
                for row in reader:
                    if coordinate_review_idx != -1:
                        row[coordinate_review_idx] = ''
                    if tops_categorize_idx != -1:
                        row[tops_categorize_idx] = ''
                    if bottoms_categorize_idx != -1:
                        row[bottoms_categorize_idx] = ''
                    rows.append(row)
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            
            print(f"Processed: {file_path}")
        else:
            print(f"File not found: {file_path}")

if __name__ == "__main__":
    clear_coordinate_columns()