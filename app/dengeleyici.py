import json
from pathlib import Path

ARSHETIP_KEYS = ["merak", "cesaret", "kontrol", "empati"]

def dengele_etki(etki, idx):
    # etki tek anahtar ise ({"merak":2} gibi), bunu {"merak":1, "kontrol":1} gibi yap
    if not isinstance(etki, dict) or len(etki) != 1:
        return etki

    (k, v), = etki.items()
    try:
        v = int(v)
    except:
        return etki

    if v <= 1:
        return etki

    # ikinci arketipi seç (deterministik, indeksle döndür)
    others = [x for x in ARSHETIP_KEYS if x != k]
    ikinci = others[idx % len(others)]

    # 2 puanı ikiye böl: 1+1
    return {k: v - 1, ikinci: 1}

def main():
    dosya = Path(__file__).parent / "sorular.json"
    data = json.loads(dosya.read_text(encoding="utf-8"))

    secenek_index = 0
    for soru in data:
        for s in soru.get("secenekler", []):
            s["etki"] = dengele_etki(s.get("etki"), secenek_index)
            secenek_index += 1

    dosya.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK: sorular.json dengelendi.")

if __name__ == "__main__":
    main()
