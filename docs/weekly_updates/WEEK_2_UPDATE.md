
# Weekly Project Progress Report: Harish Rajkumar
**Date:** 2026-07-17 | **Week Number:** 2 | **Current Phase:** Pipeline Development

---

## Overview & Momentum
This was a very hectic but productive week. I've had to completely rethink what I'm actually doing with my analysis. In week 1, I was really just throwing things at the wall and trying out every API and indicator in existence. I was very much leaning towards overanalysis, with many of the fields I was thinking about doing being redundant or not very useful. 

Now I have cut down my analysis to 23 indicators across 7 different categories - each one clearly laid out and justified in [docs/planning/indicator_catalogue.docx](../planning/indicator_catalogue.docx)

I have also categorised my indicators based on their data source, which has allowed me to architect a clear flow for my scripts and data collection.

My week 1 architecture has had a complete revamp, as most of my scripts have now been absorbed or made redundant via a major Codex refactor. Artifacts from the previous architecture still persist while I finish the refactor, but I will be able to clean up my codebase soon.

Looking ahead I will need to pull data from my less "easy" sources, and restructure my frontend.

---

## Latest Code Base State
* **Latest Git Commit:** `commit 5edfc357128fbde93d50f424359d162de31ea79e (HEAD -> exploration/world-bank-api, origin/exploration/world-bank-api)`
* **Commit Message:** `Major codebase revamp, based on codex suggestions.`

---

## Features & Accomplishments Developed This Week
* [X] **Planning/Finalise indicators** - *Complete overhaul of indicators selected for analysis - each one is now justified within [docs/planning/indicator_catalogue.docx](../planning/indicator_catalogue.docx)*
* [X] **Refactor/Rebuild Pipeline** - *Complete overhaul of data pipeline based on [docs/planning/pipeline_architecture.docx](../planning/pipeline_architecture.docx)*
* [X] **Feature/Frontend Skeleton** - *Full skeleton of frontend fleshed out. 3 pages currently populated, but with data from outdated pipeline.*
* [X] **Task/Collate WBI Data** - *Collected, normalised and cleaned all necessary data from WBI and stored in canonical format within [data/processed](../../data/processed/).*
* [ ] **Task/Collate yfinance Data** - *Collected, normalised and cleaned all necessary data from yfinance and stored in canonical format within [data/processed](../../data/processed/).*

---

## Roadblocks & Key Questions

### Current Blockers
1. **Pipeline overhaul** *Since I'm essentially building my pipeline back from scratch, I need to be very careful about not leaving any functions behind, or overwriting anything.*
2. **Outdated frontend** *Frontend currently expects data in old json format - possibly incompatible with new architecture.*

### Key Questions & Decisions Needed

---

## Plan for Next Week
* **Continue collecting data from "harder" sources.** 
* **Revamp frontend to fit new architecture.** 

---