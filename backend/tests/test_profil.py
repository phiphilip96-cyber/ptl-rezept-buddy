from datetime import date
from models.profil import ProfilEingabe, kalorienziel_berechnen, proteinziel_berechnen, ziele_auffuellen
from ki.systemprompt import profilblock, systemprompt_bauen
from tests.conftest import PROFIL_LENA


def test_kalorien_fallback_lena():
    p = ProfilEingabe(**PROFIL_LENA)
    kcal = kalorienziel_berechnen(p, 2026)
    # Mifflin: 560 + 1031.25 - 145 - 161 = 1285.25 × 1.55 = 1992 + 250 = 2242 → 2250
    assert kcal == 2250
    assert proteinziel_berechnen(p) == 112


def test_kalorien_fallback_mann_fettabbau():
    p = ProfilEingabe(vorname="Tom", ziel="fettabbau", gewicht_kg=95, groesse_cm=182, geburtsjahr=1985,
                      geschlecht="maennlich", aktivitaet="leicht")
    kcal = kalorienziel_berechnen(p, 2026)
    # 950 + 1137.5 - 205 + 5 = 1887.5 × 1.375 = 2595 - 400 = 2195 → 2200
    assert kcal == 2200
    assert proteinziel_berechnen(p) == 190


def test_coach_werte_haben_vorrang():
    p = ProfilEingabe(**PROFIL_LENA, kalorienziel=1900, proteinziel_g=130)
    assert ziele_auffuellen(p, 2026) == (1900, 130)


def test_profilblock_enthaelt_alles():
    p = ProfilEingabe(**PROFIL_LENA, notizen_coach="trainiert Mo/Mi/Fr abends")
    block = profilblock(p, heute=date(2026, 9, 6))
    for erwartet in ("Lena", "Muskelaufbau", "56 kg", "Alter: 29", "gluten", "Pilze", "2250 kcal", "112 g Protein",
                     "trainiert Mo/Mi/Fr", "06.09.2026"):
        assert erwartet in block


def test_systemprompt_reihenfolge_und_notizen():
    p = ProfilEingabe(**PROFIL_LENA)
    sp = systemprompt_bauen(p, coach_notizen=["mehr Fisch"], regeln="REGELN", heute=date(2026, 9, 6))
    assert sp.index("REGELN") < sp.index("KUNDENPROFIL") < sp.index("NOTIZEN VOM COACH")
    assert "- mehr Fisch" in sp


def test_echte_regeldatei_laedt():
    p = ProfilEingabe(**PROFIL_LENA)
    sp = systemprompt_bauen(p)
    assert "Rezept-Buddy" in sp and "KUNDENPROFIL" in sp
