#!/usr/bin/env python3
"""
translate_with_google_sentence_fullrun.py

Translate Russian ArticleText → English sentence-by-sentence using googletrans,
while skipping (preserving) any URLs inside the text.

Usage:
  source .venv_trans/bin/activate
  python -m pip install pandas googletrans==4.0.0-rc1 tqdm

  python translate_with_google_sentence_fullrun.py \
    --input soros_filtered_scores.csv \
    --output soros_filtered_scores_google_sentence_translated.csv
"""


#!/usr/bin/env python3
"""
translate_with_google_sentence_fullrun.py

Translate Russian 'ArticleText' → English sentence-by-sentence using googletrans,
preserving URLs, with retries, periodic checkpoints, and safe resume.

Usage
-----
source .venv_trans/bin/activate
python -m pip install pandas tqdm googletrans==4.0.0-rc1

python translate_with_google_sentence_fullrun.py \
  --input soros_filtered_scores.csv \
  --output soros_filtered_scores_google_sentence_translated.csv \
  --sleep 0.1 \
  --checkpoint-every 20
"""

import argparse
import os
import re
import sys
import time
from typing import List, Tuple

import pandas as pd
from googletrans import Translator
from tqdm import tqdm

# ---------- Sentence splitting & URL preservation ----------

_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')

_URL_RE = re.compile(
    r'(?P<url>('
    r'(?:https?://|ftp://)\S+|'
    r'(?:www\.)\S+|'
    r'(?:[A-Za-z0-9.-]+\.(?:com|org|net|edu|gov|ru|ua|by|kz|info|biz|io|ai|au|uk|de|fr|it|es|cz|pl|se|no|dk|nl|be|ch|jp|cn|kr|br|in))\S*'
    r'))',
    re.IGNORECASE
)

def split_sentences(text: str) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)
    return [p for p in parts if p.strip()]

def protect_urls(sentence: str) -> Tuple[str, List[Tuple[str, str]]]:
    repls: List[Tuple[str, str]] = []
    idx = 0

    def _sub(m):
        nonlocal idx, repls
        url = m.group('url')
        placeholder = f"URLTOKEN_{idx}_X"
        idx += 1
        repls.append((placeholder, url))
        return placeholder

    return _URL_RE.sub(_sub, sentence), repls

def restore_urls(s: str, repls: List[Tuple[str, str]]) -> str:
    out = s
    for placeholder, url in repls:
        out = out.replace(placeholder, url)
    return out

# ---------- Translation with retries/backoff ----------

def translate_text_with_retry(
    translator: Translator,
    text: str,
    src: str = "ru",
    dest: str = "en",
    max_retries: int = 5,
    base_sleep: float = 0.5,
) -> str:
    attempt = 0
    while True:
        try:
            return translator.translate(text, src=src, dest=dest).text
        except Exception:
            attempt += 1
            if attempt > max_retries:
                return text  # give up, keep original
            time.sleep(base_sleep * (2 ** (attempt - 1)))

def translate_sentence(translator: Translator, sentence: str) -> str:
    if not sentence.strip():
        return sentence
    protected, repls = protect_urls(sentence)
    translated = translate_text_with_retry(translator, protected)
    return restore_urls(translated, repls)

def translate_article_text(
    translator: Translator,
    text: str,
    per_sentence_sleep: float = 0.0,
) -> str:
    sents = split_sentences(text)
    out: List[str] = []
    for s in sents:
        t = translate_sentence(translator, s)
        out.append(t)
        if per_sentence_sleep > 0:
            time.sleep(per_sentence_sleep)
    return " ".join(out)

# ---------- I/O & resume helpers ----------

def load_input(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ArticleID": str}, keep_default_na=False)
    if "ArticleText" not in df.columns:
        raise SystemExit("ERROR: Input CSV must contain 'ArticleText'.")
    if "ArticleID" not in df.columns:
        df = df.copy()
        df["ArticleID"] = df.index.astype(str)
    return df

def load_or_init_output(input_df: pd.DataFrame, out_path: str, overwrite: bool) -> pd.DataFrame:
    # If an output exists, resume from it; else start fresh with needed columns.
    if os.path.exists(out_path):
        try:
            out_df = pd.read_csv(out_path, dtype={"ArticleID": str}, keep_default_na=False)
            # Ensure all input columns exist
            for c in input_df.columns:
                if c not in out_df.columns:
                    out_df[c] = input_df[c]
            # Ensure our output columns exist
            if "ArticleTextEnglish" not in out_df.columns:
                out_df["ArticleTextEnglish"] = ""
            if "TranslationStatus" not in out_df.columns:
                out_df["TranslationStatus"] = ""
            # Reindex to input order by ArticleID if present
            if "ArticleID" in out_df.columns:
                out_df = (
                    out_df.set_index("ArticleID")
                    .reindex(input_df["ArticleID"])
                    .reset_index()
                )
            if overwrite:
                out_df["ArticleTextEnglish"] = ""
                out_df["TranslationStatus"] = ""
            return out_df
        except Exception:
            # Fall back to fresh if the existing file is unreadable
            pass

    out_df = input_df.copy()
    if "ArticleTextEnglish" not in out_df.columns:
        out_df["ArticleTextEnglish"] = ""
    if "TranslationStatus" not in out_df.columns:
        out_df["TranslationStatus"] = ""
    return out_df

def write_checkpoint_safely(df: pd.DataFrame, out_path: str) -> None:
    tmp = out_path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, out_path)

def append_progress(log_path: str, msg: str) -> None:
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")

# ---------- Main ----------

def main():
    ap = argparse.ArgumentParser(description="Translate Russian → English (sentence-by-sentence) with resume & checkpoints.")
    ap.add_argument("--input", "-i", required=True, help="Path to input CSV (needs ArticleText; ArticleID recommended).")
    ap.add_argument("--output", "-o", required=True, help="Path to output CSV.")
    ap.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between sentence requests.")
    ap.add_argument("--checkpoint-every", type=int, default=20, help="Write CSV every N translated articles.")
    ap.add_argument("--overwrite", action="store_true", help="Re-translate all rows even if ArticleTextEnglish exists.")
    ap.add_argument("--start-idx", type=int, default=0, help="Row index to start from after resume logic.")
    ap.add_argument("--max-rows", type=int, default=None, help="Limit number of rows to process this run.")
    args = ap.parse_args()

    in_df = load_input(args.input)
    out_df = load_or_init_output(in_df, args.output, overwrite=args.overwrite)

    # Skip rows already translated unless --overwrite
    if args.overwrite:
        done_mask = pd.Series(False, index=out_df.index)
    else:
        done_mask = out_df["ArticleTextEnglish"].astype(str).str.strip() != ""

    total = len(out_df)
    start = max(args.start_idx, 0)

    end_limit = total if args.max_rows is None else min(start + args.max_rows, total)
    indices = range(start, end_limit)
    total_to_process = end_limit - start

    translator = Translator()
    progress_log = args.output + ".progress.log"
    processed_since_ckpt = 0
    any_changes = False

    pbar = tqdm(indices, total=total_to_process, desc="Articles", unit="article")
    for i in pbar:
        art_id = out_df.at[i, "ArticleID"] if "ArticleID" in out_df.columns else str(i)

        # Respect resume mask
        if not args.overwrite and bool(done_mask.iat[i]):
            pbar.set_postfix_str(f"skip ID={art_id}")
            continue

        src_text = out_df.at[i, "ArticleText"]
        if pd.isna(src_text) or not str(src_text).strip():
            out_df.at[i, "ArticleTextEnglish"] = ""
            out_df.at[i, "TranslationStatus"] = "empty"
            append_progress(progress_log, f"{time.strftime('%Y-%m-%d %H:%M:%S')} ID={art_id} empty")
            any_changes = True
        else:
            try:
                en = translate_article_text(translator, str(src_text), per_sentence_sleep=args.sleep)
                out_df.at[i, "ArticleTextEnglish"] = en
                out_df.at[i, "TranslationStatus"] = "ok"
                append_progress(progress_log, f"{time.strftime('%Y-%m-%d %H:%M:%S')} ID={art_id} ok")
                any_changes = True
            except Exception as e:
                # Hard failure on the article: keep RU text, mark error
                out_df.at[i, "ArticleTextEnglish"] = str(src_text)
                out_df.at[i, "TranslationStatus"] = f"error: {e!s}"
                append_progress(progress_log, f"{time.strftime('%Y-%m-%d %H:%M:%S')} ID={art_id} error {e!s}")

        processed_since_ckpt += 1

        if processed_since_ckpt >= args.checkpoint_every:
            write_checkpoint_safely(out_df, args.output)
            processed_since_ckpt = 0
            any_changes = False  # we just flushed

    if any_changes or not os.path.exists(args.output):
        write_checkpoint_safely(out_df, args.output)

    print(f"\nDone. Output written to {args.output}")
    print(f"Progress log: {progress_log}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)















# Draft
# #!/usr/bin/env python3
# """
# translate_with_google_sentence.py

# Translate Russian ArticleText → English sentence-by-sentence using googletrans,
# while skipping (preserving) any URLs inside the text.

# Usage:
#   source .venv_trans/bin/activate
#   python -m pip install pandas googletrans==4.0.0-rc1 tqdm

#   python translate_with_google_sentence.py \
#     --input soros_filtered_scores.csv \
#     --output soros_filtered_scores_google_sentence_translated.csv
# """

# import argparse
# import re
# import time
# from typing import List, Tuple

# import pandas as pd
# from googletrans import Translator
# from tqdm import tqdm

# # Basic sentence splitter (keeps ., !, ?). Good enough for most Russian prose.
# _SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')

# # URL detector (http/https, www., or bare domains with TLDs and optional paths)
# _URL_RE = re.compile(
#     r'(?P<url>('
#     r'(?:https?://|ftp://)\S+|'
#     r'(?:www\.)\S+|'
#     r'(?:[A-Za-z0-9.-]+\.(?:com|org|net|edu|gov|ru|ua|by|kz|info|biz|io|ai|au|uk|de|fr|it|es|cz|pl|se|no|dk|nl|be|ch|jp|cn|kr|br|in))\S*'
#     r'))',
#     re.IGNORECASE
# )

# def split_sentences(text: str) -> List[str]:
#     text = text.strip()
#     if not text:
#         return []
#     # Don’t break on very short “sentences”
#     parts = _SENT_SPLIT.split(text)
#     return [p for p in parts if p.strip()]

# def protect_urls(sentence: str) -> Tuple[str, List[Tuple[str, str]]]:
#     """
#     Replace each URL with a unique placeholder, return
#     (protected_sentence, replacements) where replacements = [(placeholder, url), ...]
#     """
#     replacements = []
#     idx = 0

#     def _sub(match):
#         nonlocal idx, replacements
#         url = match.group('url')
#         placeholder = f"URLTOKEN_{idx}_X"
#         idx += 1
#         replacements.append((placeholder, url))
#         return placeholder

#     protected = _URL_RE.sub(_sub, sentence)
#     return protected, replacements

# def restore_urls(translated_sentence: str, replacements: List[Tuple[str, str]]) -> str:
#     restored = translated_sentence
#     for placeholder, url in replacements:
#         restored = restored.replace(placeholder, url)
#     return restored

# def translate_sentence(translator: Translator, sentence: str) -> str:
#     # Skip empty/whitespace just in case
#     if not sentence.strip():
#         return sentence
#     # Protect URLs so they aren't sent/changed
#     protected, repl = protect_urls(sentence)
#     # Translate the non-URL content
#     res = translator.translate(protected, src='ru', dest='en')
#     # Put URLs back in place
#     return restore_urls(res.text, repl)

# def main():
#     p = argparse.ArgumentParser(description="Translate Russian ArticleText to English (sentence-by-sentence, preserve URLs).")
#     p.add_argument('--input',  '-i', required=True, help="Path to input CSV (must contain ArticleText column).")
#     p.add_argument('--output', '-o', required=True, help="Path to write output CSV with ArticleTextEnglish.")
#     p.add_argument('--sleep', type=float, default=0.0, help="Seconds to sleep between sentence requests (optional throttle).")
#     args = p.parse_args()

#     df = pd.read_csv(args.input, dtype={'ArticleID': str}, keep_default_na=False)

#     if 'ArticleText' not in df.columns:
#         raise SystemExit("ERROR: Input CSV must contain an 'ArticleText' column.")

#     translator = Translator()

#     out_texts = []
#     for txt in tqdm(df['ArticleText'], desc="Translating", unit="article"):
#         if not isinstance(txt, str) or not txt.strip():
#             out_texts.append("")
#             continue

#         sentences = split_sentences(txt)
#         translated_sentences = []

#         for s in sentences:
#             try:
#                 t = translate_sentence(translator, s)
#             except Exception as e:
#                 # If sentence translation fails, keep original sentence (URLs intact)
#                 t = s  # or t = f"[SentenceError: {e}] {s}"
#             translated_sentences.append(t)
#             if args.sleep > 0:
#                 time.sleep(args.sleep)

#         out_texts.append(" ".join(translated_sentences))

#     df['ArticleTextEnglish'] = out_texts
#     df.to_csv(args.output, index=False)
#     print(f"\nDone. Wrote translations to {args.output}")

# if __name__ == '__main__':
#     main()








# Draft 2
# #!/usr/bin/env python3
# """
# pip show googletrans
# Version: 4.0.0rc1
# pip uninstall googletrans
# pip install googletrans==3.1.0a0


# translate_with_google.py

# Translate Russian ArticleText → English using googletrans + tqdm.
# No transformers / PyTorch required.

# Usage:
#   # Activate your venv:
#   source .venv_trans/bin/activate

#   # Install dependencies (once):
#   python -m pip install pandas googletrans==4.0.0-rc1 tqdm

#   # Run translation:
#   python translate_with_google.py \
#     --input article_28078435.csv \
#     --output soros_28078435_translated.csv
# """
# import argparse
# import pandas as pd
# from googletrans import Translator
# from tqdm import tqdm

# def main():
#     p = argparse.ArgumentParser(
#         description="Translate Russian ArticleText to English"
#     )
#     p.add_argument('--input',  '-i', required=True,
#                    help="Path to soros_with_text_cleaned.csv")
#     p.add_argument('--output', '-o', required=True,
#                    help="Path to write soros_with_text_translated.csv")
#     args = p.parse_args()

#     # Load your cleaned CSV
#     df = pd.read_csv(args.input, dtype={'ArticleID': str})

#     # Initialize the Google translator
#     translator = Translator()

#     # Translate with a live tqdm bar
#     translations = []
#     for txt in tqdm(df['ArticleText'], desc="Translating", unit="article"):
#         if not isinstance(txt, str) or not txt.strip():
#             translations.append("")
#         else:
#             try:
#                 res = translator.translate(txt, src='ru', dest='en')
#                 translations.append(res.text)
#             except Exception as e:
#                 translations.append(f"[Error: {e}]")

#     # Add new column and save
#     df['ArticleTextEnglish'] = translations
#     df.to_csv(args.output, index=False)
#     print(f"\nDone. Wrote translations to {args.output}")

# if __name__ == '__main__':
#     main()
