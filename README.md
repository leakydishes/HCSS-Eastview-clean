## HCSS-EASTVIEW-CLEAN

#### Data Input
- EastLink cleaned/ Scores: `east_link_original_data_text_cleaned.csv`
- Zavtra cleaned/ Scores: `zavtra_soros_final_01102025.csv`
- Tsargrad cleaned/ Scores: `tsargrad_soros_final_01102025.csv`
- Original EastLink Data crawl: `east_link_original_data.csv`
- EIR data `combined_eir_output_data.csv`
- RT data `final_dataset_updated_rt.csv`


### Cleaned Data
`tsargrad_data.to_csv("tsargrad_soros_final_01102025_clean.csv", index=False)`
`zavtra_data.to_csv("zavtra_soros_final_01102025_clean.csv", index=False)`
`eastview_data.to_csv("eastlink_soros_final_01102025_clean.csv", index=False)`
`eir_data.to_csv("eir_clean.csv", index=False)`


#### Scripts
- Used during cleaning `check_soros_text_cleaning.ipynb`
- Used for analysis `data_analytics_eastview_01102025.ipynb`


### Running Jupyter Notebook for Analysis
1) Create a fresh environment (Conda)
```bash
# open a terminal and cd into your VS Code project directory
# create env (Python 3.10 is a sweet spot for data libs)
conda create -n eastview python=3.10 -y
conda activate eastview
```

2) Install packages
Minimal (what your analytics notebooks use)
```bash
pip install --upgrade pip
pip install jupyterlab ipykernel pandas numpy matplotlib seaborn python-dateutil

* Add the kernel so Jupyter/VS Code can pick it by name:
python -m ipykernel install --user --name eastview --display-name "Python (eastview)"
```

3) Open the notebook from the terminal
```bash
jupyter lab data_analytics_eastview_01102025.ipynb
```

---

### Processing data steps
1. Collected data from russbot or Google Scripts

# Create & activate a venv
```bash
python3 -m venv soros
source soros/bin/activate      # macOS/Linux
# soros\Scripts\Activate.ps1   # Windows PowerShell
# Install python libraries

# Install your packages
pip install --upgrade pip
pip install -r requirements.txt
pip install pyyaml pandas selenium webdriver-manager
# Optional Copy Dependencies `pip freeze > requirements.txt`

# run
python collect_soros_urls.py
python loader.py
```

### Run all PDF Crawls
```bash
pip install pdfplumber Pillow pytesseract chardet
brew install tesseract

# Verify path
which tesseract
# Should print : /opt/homebrew/bin/tesseract
tesseract --version
# tesseract 5.5.1
# run
python extract_text_pdfs.py --download-dir downloads/eastlink --csv-path soros_text.csv --num -1
```

## Translate step performed on some articles
```bash
source .venv_trans/bin/activate
pip install pandas transformers sentencepiece tqdm
pip install torch sacremoses

# Run to translate ArticleText
scoros_google_translator_semantic_batch.py
# or
  python scoros_google_translator_semantic_batch.py \
    --input soros_filtered_scores.csv \
    --output soros_filtered_scores_translated_09082025.csv \
```

## Tested Google Translator (We moved to running as Macros in Google Sheets due to limited API access)
- `translate_with_google.py`
---

### Tips for collecting raw text in-browser
* When viewing articles in browser, right click `inspect` and in `console` you can collect text manually.
- Log and return (so you see it and can copy), you may need to update ` const el = document.querySelector(".article__content")`
```bash
(() => {
  const el = document.querySelector(".article__content");
  if (!el) { console.warn("No .article__content found"); return; }
  const text = el.innerText;
  console.log(text); // prints (you’ll still see "undefined" as the return value)
  return text;       // also renders the full string as the evaluated result
})();
```

```bash
(() => {
const el = document.querySelector(".longread__content");
if (!el) { console.warn("No .article__content found"); return; }
const text = el.innerText;
console.log(text); // prints (you’ll still see "undefined" as the return value)
return text; // also renders the full string as the evaluated result
})();
```

Download as a .txt file (long articles)
```bash
(() => {
  const el = document.querySelector(".article__content");
  if (!el) return console.warn("No .article__content found");
  const text = el.innerText.replace(/\u00A0/g, " ");
  const blob = new Blob([text], {type: "text/plain"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "article.txt";
  a.click();
  URL.revokeObjectURL(a.href);
})();
```
