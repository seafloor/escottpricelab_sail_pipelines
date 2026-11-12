import os
import pandas as pd
from datetime import date
from pyconceptlibraryclient import Client

# paths for data
INPUT_CSV = 'codes/caliber_phenotypes_to_extract.csv'
OUTPUT_CSV = f'codes/caliber_codelist_extracted_{date.today().strftime("%d_%m_%y")}.csv'
SPLIT_BY_PHENOTYPE = True  # If True, saves separate CSVs per phenotype
STRIP_READ_CODES = True  # If True, removes the trailing 0 for read codes with over 5 digits
EXPAND_ICD10 = True  # If True, expands ICD10 codes to include all subcodes

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

def read_icd10_dictionary(f = 'data/icd102019syst_codes.txt'):
    header = [
        'hierarchy_level',       # Field 1: 3/4/5 character level
        'tree_position',         # Field 2: T = terminal, N = non-terminal
        'terminal_node_type',    # Field 3: X = pre-combined, S = derived from subclassification
        'chapter_number',        # Field 4: 2-char chapter number
        'root',                  # Field 5: first three chars of block
        'code_full_padded',      # Field 6: code without possible dagger, up to 6 chars
        'code_full',             # Field 7: like field 6, without possible asterisk or dash
        'code_full_stripped',    # Field 8: like field 7, without dot
        'name_specific',         # Field 9: title
        'name_general',          # Field 10: title with less detail
        'mort_morb_refs_1',      # Field 11
        'mort_morb_refs_2',      # Field 12
        'mort_morb_refs_3',      # Field 13
        'mort_morb_refs_4',      # Field 14
        'mort_morb_refs_5',      # Field 15
        'mort_morb_refs_6',      # Field 16
        'mort_morb_refs_7',      # Field 17
    ]

    icd = (pd.read_csv(f, sep=';', index_col = False, header=None, names=header)
             .loc[:, ['root', 'code_full_stripped', 'name_general', 'name_specific']])

    return icd

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
    print("\n--> Starting Code Extraction")
    # connect to API
    client = Client(public=True)

    # read pre-curated list of phenotypes and corresponding codes to extract
    code_library = pd.read_csv(INPUT_CSV)

    all_codes_df = pd.DataFrame()
    for index, row in code_library.iterrows():
        df_phenotype = pull_codelist(row, client, verbose=True)
        all_codes_df = pd.concat([all_codes_df, df_phenotype], ignore_index=True)

    if STRIP_READ_CODES:
        print("\n--> Stripping trailing 0s from Read codes with over 5 digits")
        # Remove trailing 0 for Read codes with over 5 digits
        def strip_read_code_from_series(s):
            if s['vocabulary'] == 'Read codes v2' and len(s['code']) == 7 and s['code'].endswith('00'):
                return s['code'][:-2]
            else:
                return s['code']

        all_codes_df['code'] = all_codes_df.apply(
            strip_read_code_from_series,
            axis=1
        )

    if EXPAND_ICD10:
        print("\n--> Expanding ICD10 codes to include all subcodes")
        icd10_roots = all_codes_df.loc[all_codes_df['vocabulary'] == 'ICD10 codes']
        n_before = icd10_roots.shape[0]
        icd10_dict = read_icd10_dictionary()

        icd10_expanded_df = pd.DataFrame()
        icd10_expanded_list = []
        for i, root_code in icd10_roots.iterrows():
            new_codes = icd10_dict.loc[icd10_dict['code_full_stripped'].str.startswith(root_code['code']), :]
            new_codes = new_codes.loc[new_codes['code_full_stripped'] != root_code['code'], :]
            d = pd.concat([root_code.copy() for _ in range(new_codes.shape[0]+5)], axis=1).T

            # print(d)
            # pad the root code with common variations to ensure all subcodes are captured
            # X-padding is common for ICD10 codes, as is adding a dash, dot or hash for certain subcodes
            codes_padded = [root_code['code'], root_code['code']+'X', root_code['code']+'-', root_code['code']+'#', root_code['code']+'.']

            # search for all codes that start with the root code, but are not the root code itself
            codes_expanded = new_codes['code_full_stripped'].tolist()
            # print(f"Expanded {root_code['code']} to {len(codes_expanded)} subcodes.")

            # combine and pull the corresponding names for the codes
            codes_full = codes_padded + codes_expanded
            codes_names = [d.disease.iat[0]]*5 + new_codes['name_specific'].tolist()
            # print(f"Root code: {root_code['code']}, Full codes: {codes_full}")

            # update the dataframe with the expanded codes and their names
            d['code'] = codes_full
            d['description'] = codes_names
            icd10_expanded_list.append(d)

        # create a new dataframe with the expanded ICD10 codes and their corresponding names
        if icd10_expanded_list:
            icd10_expanded_df = pd.concat(icd10_expanded_list, ignore_index=True)
            n_after = icd10_expanded_df.shape[0]
            print(f"Expanded {n_before} ICD10 root codes to {n_after} total codes.")

            all_codes_df = pd.concat(
                [all_codes_df.loc[all_codes_df['vocabulary'] != 'ICD10 codes'],
                 icd10_expanded_df], ignore_index=True)
        else:
            print("No ICD10 codes found to expand.")

    # save to CSV
    if not all_codes_df.empty:
        if verbose:
            print(f"\nExtracted {all_codes_df.shape[0]} codes, head:")
        print(all_codes_df.head())
        # all_codes_df = pd.DataFrame({'disease': ['this', 'that'], 'code': ['A123', 'B456']})  # Placeholder for demonstration
        if SPLIT_BY_PHENOTYPE:
            for phenotype, df_group in all_codes_df.groupby('disease'):
                base, ext = os.path.splitext(OUTPUT_CSV)
                phenotype_csv = f"{base}_{phenotype.replace(' ', '_')}{ext}"
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
