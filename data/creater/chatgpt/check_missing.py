import pandas as pd

# men/coordinates.csv を読み込み、欠損をチェック
men_df = pd.read_csv('./men/coordinates.csv')
men_missing = men_df[men_df['coordinate_review'].isnull() | (men_df['coordinate_review'] == '') | 
                    men_df['tops_categorize'].isnull() | (men_df['tops_categorize'] == '') |
                    men_df['bottoms_categorize'].isnull() | (men_df['bottoms_categorize'] == '')]
print(f'Men missing rows: {len(men_missing)}')
if len(men_missing) > 0:
    print('Men missing IDs:', men_missing['id'].tolist()[:10])

# women/coordinates.csv を読み込み、欠損をチェック  
women_df = pd.read_csv('./women/coordinates.csv')
women_missing = women_df[women_df['coordinate_review'].isnull() | (women_df['coordinate_review'] == '') | 
                        women_df['tops_categorize'].isnull() | (women_df['tops_categorize'] == '') |
                        women_df['bottoms_categorize'].isnull() | (women_df['bottoms_categorize'] == '')]
print(f'Women missing rows: {len(women_missing)}')
if len(women_missing) > 0:
    print('Women missing IDs:', women_missing['id'].tolist()[:10])