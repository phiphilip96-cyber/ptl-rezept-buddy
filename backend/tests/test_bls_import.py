from pathlib import Path
from scripts.bls_import import zeilen_lesen


def test_csv_wird_tolerant_gelesen(tmp_path: Path):
    f = tmp_path / "bls.csv"
    f.write_text("SBLS;Lebensmittelname;Energie (kcal);Eiweiß (g);Fett (g);Kohlenhydrate (g);Hauptgruppe\n"
                 "C100000;Haferflocken;370;13,5;7,0;58,7;Getreide\n", encoding="utf-8")
    z = list(zeilen_lesen(f))
    assert z[0]["bls_code"] == "C100000" and z[0]["kcal_100g"] == 370 and z[0]["protein_g"] == 13.5
    assert z[0]["kategorie"] == "Getreide" and z[0]["ballaststoffe_g"] is None
