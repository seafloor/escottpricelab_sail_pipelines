import pandas as pd
from datetime import date
from pyconceptlibraryclient import Client

# paths for data
INPUT_CSV = 'codes/caliber_phenotypes_to_extract.csv'
OUTPUT_CSV = f'codes/caliber_codelist_extracted_{date.today().strftime("%d_%m_%y")}.csv'
SPLIT_BY_PHENOTYPE = True  # If True, saves separate CSVs per phenotype

def parse_json(json_obj):
    parsed_data = []
    for item in json_obj:
        parsed_data.append({
            'phenotype_id': item.get('phenotype_id'),               # e.g., PH152
            'code': item.get('code'),                               # The actual code (e.g. E11.2)
            'disease': item.get('phenotype_name'),                  # e.g., Diabetes
            'description': item.get('description'),                 # The text desc
            'vocabulary': item.get('coding_system').get('name'),    # ICD10 or Read
            'version': item.get('phenotype_version_id')             # e.g., 304
        })

    parsed_data = (pd.DataFrame(parsed_data)
                     .query("vocabulary in ['ICD10 codes', 'Read codes v2']"))
        
    return parsed_data

def pull_codelist(code_info, client, verbose=False):
    phenotype_id = code_info['code']      # e.g., PH152
    version = code_info['version']        # e.g., 304
    category = code_info['category']      # e.g., Diabetes
    
    if verbose:
        print(f"Fetching code: {phenotype_id}, version: {version}, phenotype: {category}")

    try:
        raw_codelist = client.phenotypes.get_codelist(phenotype_id, version_id=version)
        return parse_json(raw_codelist)
    except Exception as e:
        print(f"Error fetching code {phenotype_id} for phenotype {category}: {e}")
        return pd.DataFrame()

def main(verbose=True):
    print("--> Starting Code Extraction\n")
    # connect to API
    client = Client(public=True)

    # read pre-curated list of phenotypes and corresponding codes to extract
    code_library = pd.read_csv(INPUT_CSV)

    all_codes_df = pd.DataFrame()
    for index, row in code_library.iterrows():
        df_phenotype = pull_codelist(row, client, verbose=True)
        all_codes_df = pd.concat([all_codes_df, df_phenotype], ignore_index=True)

    # save to CSV
    if not all_codes_df.empty:
        if verbose:
            print(f"\nExtracted {all_codes_df.shape[0]} codes, head:")
        print(all_codes_df.head())
        if SPLIT_BY_PHENOTYPE:
            for phenotype, df_group in all_codes_df.groupby('disease'):
                base, ext = os.path.splitext(OUTPUT_CSV)
                phenotype_csv = os.path.join(f"{base}_{phenotype.replace(' ', '_')}", ext)
                df_group.to_csv(phenotype_csv, index=False)
                if verbose:
                    print(f"Saved {df_group.shape[0]} codes for {phenotype} to {phenotype_csv}")
        else:
            all_codes_df.to_csv(OUTPUT_CSV, index=False)
            if verbose:
                print(f"\nAll codes saved to {OUTPUT_CSV}")

        if os.path.exists(OUTPUT_CSV):
            print(f"Saved to {OUTPUT_CSV}")
        else:
            print("Error: Output CSV not found after saving.")
    else:
        print("No codes found. Check input CSV or API connection.")

if __name__ == "__main__":
    main()