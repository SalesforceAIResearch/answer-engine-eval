import re

def extract_citations(bullet):
    matches = re.findall(r"\[([\d, ]+)\]", bullet) # matches digits or commas
    ref_ids = []
    for match in matches:
        ref_ids += [int(m.strip()) for m in match.split(",") if len(m.strip()) > 0]
    return ref_ids