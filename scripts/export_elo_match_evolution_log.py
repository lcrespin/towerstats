#!/usr/bin/env python3
"""Écrit l'évolution de l'Elo match (fin de journée) dans un fichier texte."""

from __future__ import annotations

import argparse
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from src.data_manager import SessionDataManager
from src.stats_manager import SessionStatsManager


def main() -> None:
    p = argparse.ArgumentParser(
        description="Exporte l'évolution Elo match, jour par jour, vers un fichier."
    )
    p.add_argument(
        "-o",
        "--output",
        default="elo_match_evolution.log",
        help="Fichier de sortie (défaut: elo_match_evolution.log à la racine du projet).",
    )
    p.add_argument(
        "--csv",
        dest="local_csv",
        default=None,
        help="Chemin vers un CSV local (sinon source depuis la config / URL).",
    )
    p.add_argument(
        "--date-start", default=None, help="YYYY-MM-DD inclus (filtre des sessions)."
    )
    p.add_argument(
        "--date-end", default=None, help="YYYY-MM-DD inclus (filtre des sessions)."
    )
    p.add_argument("--initial-elo", type=float, default=1500.0)
    p.add_argument("--k-factor", type=float, default=32.0)
    args = p.parse_args()

    dm = SessionDataManager(local_file=args.local_csv) if args.local_csv else SessionDataManager()
    dm.load_all()
    sessions = dm.get_sessions()
    stats = SessionStatsManager(
        sessions, date_start=args.date_start, date_end=args.date_end
    )
    out = os.path.abspath(args.output)
    stats.write_elo_match_evolution_log(
        out, initial_elo=args.initial_elo, k_factor=args.k_factor
    )
    print(f"Écrit: {out}")


if __name__ == "__main__":
    main()
