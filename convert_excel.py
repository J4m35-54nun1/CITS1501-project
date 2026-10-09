import os
import pandas as pd

excel_files = [
    "Data (Database)/Australia.xlsx",
    "Data (Database)/New South Wales.xlsx",
    "Data (Database)/Victoria.xlsx",
    "Data (Database)/Queensland.xlsx",
    "Data (Database)/South Australia.xlsx",
    "Data (Database)/Western Australia.xlsx",
    "Data (Database)/Tasmania.xlsx",
    "Data (Database)/Northern Territory.xlsx",
    "Data (Database)/Australian Capital Territory.xlsx",
    "Data (Database)/Remoteness.xlsx",
    "Data (Database)/Empowered Communities.xlsx"
]

for file_path in excel_files:
    if os.path.exists(file_path):
        all_sheets = pd.read_excel(file_path, sheet_name=None)
        
        file_base_name = os.path.splitext(os.path.basename(file_path))[0]
        clean_file_name = file_base_name.lower().replace(" ", "_")

        for sheet_name, df in all_sheets.items():
            clean_sheet_name = str(sheet_name).strip().lower().replace(" ", "_")
            csv_path = f"Data (Database)/{clean_file_name}_{clean_sheet_name}.csv"
            
            df.to_csv(csv_path, index=False)
            print(f"Extracted '{sheet_name}' from '{file_base_name}' -> Saved to {csv_path} ({len(df)} rows)")
    else:
        print(f"Skipped: {file_path} not found in Data (Database)/ directory.")
