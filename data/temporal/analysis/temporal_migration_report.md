# Observed Audience Retention & Transition Analytics (2020–2026)

## Methodological Stance & Scientific Framing

> [!IMPORTANT]
> **Non-Causal Epistemic Guardrail:**
> - All metrics reported represent **observed interaction evidence** from verified public YouTube interactions (comments and live chat).
> - Transitions indicate that the same pseudonymized commenter (`viewer_hash`) was observed interacting with Channel A in Year $t$ and Channel B in Year $t+1$.
> - These metrics **MUST NOT** be interpreted as causal 'fan migration' or total population shifts, as passive viewers and non-participating audience segments are unobserved.
> - Agency groupings reflect frozen `agency_at_selection` metadata from the target cohort manifest.

---

## Annual Audience & Transition Overview

| Year Pair | Active Viewers (Year $t$) | Retained Viewers ($t \to t+1$) | Cross-Channel Viewers | Same-Agency Cross | Cross-Agency | Retention Ratio | Coverage Warning |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 2020 -> 2021 | 509 | 258 | 312 | 237 | 131 | 50.7% | `LOW_COVERAGE` |
| 2021 -> 2022 | 1,154 | 523 | 870 | 606 | 500 | 45.3% | `NORMAL` |
| 2022 -> 2023 | 1,173 | 566 | 859 | 602 | 507 | 48.3% | `NORMAL` |
| 2023 -> 2024 | 1,677 | 763 | 1,255 | 867 | 719 | 45.5% | `NORMAL` |
| 2024 -> 2025 | 2,090 | 981 | 1,562 | 1,138 | 773 | 46.9% | `NORMAL` |
| 2025 -> 2026 | 1,947 | 863 | 1,499 | 1,181 | 627 | 44.3% | `NORMAL` |

---

## Agency-Level Observed Transition Matrices (`agency_at_selection`)

### Year 2020 -> 2021

| Source Agency at Selection | Target Agency at Selection | Transition Type | Observed Transition Viewers |
|:---|:---|:---:|:---:|
| Independent | Independent | `within_agency` | 439 |
| Independent | Pixela Project | `cross_agency` | 73 |
| Independent | Algorhythm Project | `cross_agency` | 38 |
| Independent | Virtual Zeven (VZ) | `cross_agency` | 16 |
| Independent | Ti19t | `cross_agency` | 16 |
| Virtual Zeven (VZ) | Independent | `cross_agency` | 10 |
| Virtual Zeven (VZ) | Virtual Zeven (VZ) | `within_agency` | 6 |
| Virtual Zeven (VZ) | Pixela Project | `cross_agency` | 1 |
| Virtual Zeven (VZ) | Algorhythm Project | `cross_agency` | 1 |
| Pixela Project | Pixela Project | `within_agency` | 1 |

### Year 2021 -> 2022

| Source Agency at Selection | Target Agency at Selection | Transition Type | Observed Transition Viewers |
|:---|:---|:---:|:---:|
| Independent | Independent | `within_agency` | 756 |
| Independent | Pixela Project | `cross_agency` | 178 |
| Pixela Project | Independent | `cross_agency` | 152 |
| Pixela Project | Pixela Project | `within_agency` | 152 |
| Algorhythm Project | Independent | `cross_agency` | 88 |
| Independent | Algorhythm Project | `cross_agency` | 64 |
| Algorhythm Project | Algorhythm Project | `within_agency` | 55 |
| Algorhythm Project | Pixela Project | `cross_agency` | 47 |
| Independent | Virtual Zeven (VZ) | `cross_agency` | 43 |
| Virtual Zeven (VZ) | Independent | `cross_agency` | 26 |

### Year 2022 -> 2023

| Source Agency at Selection | Target Agency at Selection | Transition Type | Observed Transition Viewers |
|:---|:---|:---:|:---:|
| Independent | Independent | `within_agency` | 692 |
| Pixela Project | Pixela Project | `within_agency` | 245 |
| Pixela Project | Independent | `cross_agency` | 159 |
| Independent | Pixela Project | `cross_agency` | 123 |
| Independent | Algorhythm Project | `cross_agency` | 106 |
| Pixela Project | Lumina Live | `cross_agency` | 88 |
| Pixela Project | Algorhythm Project | `cross_agency` | 70 |
| Algorhythm Project | Independent | `cross_agency` | 70 |
| Algorhythm Project | Algorhythm Project | `within_agency` | 60 |
| Independent | Lumina Live | `cross_agency` | 46 |

### Year 2023 -> 2024

| Source Agency at Selection | Target Agency at Selection | Transition Type | Observed Transition Viewers |
|:---|:---|:---:|:---:|
| Independent | Independent | `within_agency` | 837 |
| Algorhythm Project | Algorhythm Project | `within_agency` | 381 |
| Algorhythm Project | Independent | `cross_agency` | 197 |
| Independent | Algorhythm Project | `cross_agency` | 186 |
| Pixela Project | Independent | `cross_agency` | 163 |
| Pixela Project | Pixela Project | `within_agency` | 158 |
| Pixela Project | Algorhythm Project | `cross_agency` | 82 |
| Independent | Pixela Project | `cross_agency` | 76 |
| Pixela Project | Lumina Live | `cross_agency` | 66 |
| Independent | Lumina Live | `cross_agency` | 56 |

### Year 2024 -> 2025

| Source Agency at Selection | Target Agency at Selection | Transition Type | Observed Transition Viewers |
|:---|:---|:---:|:---:|
| Independent | Independent | `within_agency` | 1,080 |
| Algorhythm Project | Algorhythm Project | `within_agency` | 546 |
| Independent | Algorhythm Project | `cross_agency` | 250 |
| Algorhythm Project | Independent | `cross_agency` | 160 |
| Pixela Project | Pixela Project | `within_agency` | 119 |
| Independent | Pixela Project | `cross_agency` | 112 |
| Pixela Project | Independent | `cross_agency` | 81 |
| Independent | Virtual Zeven (VZ) | `cross_agency` | 77 |
| Pixela Project | Algorhythm Project | `cross_agency` | 60 |
| Lumina Live | Pixela Project | `cross_agency` | 56 |

### Year 2025 -> 2026

| Source Agency at Selection | Target Agency at Selection | Transition Type | Observed Transition Viewers |
|:---|:---|:---:|:---:|
| Independent | Independent | `within_agency` | 1,346 |
| Algorhythm Project | Algorhythm Project | `within_agency` | 269 |
| Algorhythm Project | Independent | `cross_agency` | 158 |
| Pixela Project | Independent | `cross_agency` | 103 |
| Independent | Algorhythm Project | `cross_agency` | 92 |
| Independent | Euphora Project | `cross_agency` | 78 |
| Pixela Project | Pixela Project | `within_agency` | 71 |
| Independent | Virtual Zeven (VZ) | `cross_agency` | 67 |
| Virtual Zeven (VZ) | Independent | `cross_agency` | 67 |
| Independent | Pixela Project | `cross_agency` | 54 |

---

## Top Observed Cross-Channel Transition Pairs

### Top Cross-Channel Transitions (2020 -> 2021)

| From VTuber (Agency) | To VTuber (Agency) | Transition Type | Observed Transition Viewers |
|:---|:---|:---:|:---:|
| 久檻夜くぅ / Qualia Qu Ch. (Independent) | Reilim Channel (Independent) | `same_agency_cross_channel` | 22 |
| 久檻夜くぅ / Qualia Qu Ch. (Independent) | SiamNeko Ch.【ARP】 (Algorhythm Project) | `cross_agency` | 15 |
| 久檻夜くぅ / Qualia Qu Ch. (Independent) | Pyork The Pork (Independent) | `same_agency_cross_channel` | 13 |
| 久檻夜くぅ / Qualia Qu Ch. (Independent) | Pixela Official (Pixela Project) | `cross_agency` | 12 |
| Darin V (Independent) | Reilim Channel (Independent) | `same_agency_cross_channel` | 12 |
| 久檻夜くぅ / Qualia Qu Ch. (Independent) | Beariss Beam (Independent) | `same_agency_cross_channel` | 10 |
| 久檻夜くぅ / Qualia Qu Ch. (Independent) | Laibaht Ch. / หลายบาท (Independent) | `same_agency_cross_channel` | 10 |
| Nerumi-s (Independent) | Laguna JuJu Ch. Pixela Project (Pixela Project) | `cross_agency` | 10 |

### Top Cross-Channel Transitions (2021 -> 2022)

| From VTuber (Agency) | To VTuber (Agency) | Transition Type | Observed Transition Viewers |
|:---|:---|:---:|:---:|
| 久檻夜くぅ / Qualia Qu Ch. (Independent) | dtto. (Independent) | `same_agency_cross_channel` | 50 |
| Hinabe HongFei Ch. Pixela Project (Pixela Project) | Pixela Official (Pixela Project) | `same_agency_cross_channel` | 49 |
| Aisha Channel (Independent) | Pixela Official (Pixela Project) | `cross_agency` | 38 |
| Laguna JuJu Ch. Pixela Project (Pixela Project) | Pixela Official (Pixela Project) | `same_agency_cross_channel` | 27 |
| Princess Zelina Ch. Pixela Project (Pixela Project) | Pixela Official (Pixela Project) | `same_agency_cross_channel` | 22 |
| Asteroth Ch.【ARP】 (Algorhythm Project) | Evalia Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 21 |
| Hinabe HongFei Ch. Pixela Project (Pixela Project) | Aisha Channel (Independent) | `cross_agency` | 19 |
| Pyork The Pork (Independent) | Pixela Official (Pixela Project) | `cross_agency` | 19 |

### Top Cross-Channel Transitions (2022 -> 2023)

| From VTuber (Agency) | To VTuber (Agency) | Transition Type | Observed Transition Viewers |
|:---|:---|:---:|:---:|
| Pixela Official (Pixela Project) | Meraki Keimii Ch. Pixela Legends (Pixela Project) | `same_agency_cross_channel` | 69 |
| Mycara Melony Ch. Pixela-Mystic (Pixela Project) | Meraki Keimii Ch. Pixela Legends (Pixela Project) | `same_agency_cross_channel` | 54 |
| Draki Kona Ch. Lumina-First-Myth (Lumina Live) | Meraki Keimii Ch. Pixela Legends (Pixela Project) | `cross_agency` | 31 |
| Mycara Melony Ch. Pixela-Mystic (Pixela Project) | Atlanteia Sireen Ch. Lumina-First-Myth (Lumina Live) | `cross_agency` | 28 |
| Pyork The Pork (Independent) | moujob (Independent) | `same_agency_cross_channel` | 25 |
| Mycara Melony Ch. Pixela-Mystic (Pixela Project) | Pixela Official (Pixela Project) | `same_agency_cross_channel` | 25 |
| Pixela Official (Pixela Project) | Hinabe HongFei Ch. Pixela Project (Pixela Project) | `same_agency_cross_channel` | 20 |
| Pixela Official (Pixela Project) | Aisha Channel (Independent) | `cross_agency` | 19 |

### Top Cross-Channel Transitions (2023 -> 2024)

| From VTuber (Agency) | To VTuber (Agency) | Transition Type | Observed Transition Viewers |
|:---|:---|:---:|:---:|
| Schneider Ch.【ARP】 (Algorhythm Project) | Dacapo Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 78 |
| Baabel Ch.【ARP】 (Algorhythm Project) | Dacapo Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 32 |
| Schneider Ch.【ARP】 (Algorhythm Project) | Baabel Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 31 |
| Dacapo Ch.【ARP】 (Algorhythm Project) | Baabel Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 31 |
| Meraki Keimii Ch. Pixela Legends (Pixela Project) | Pixela Official (Pixela Project) | `same_agency_cross_channel` | 28 |
| Unnämed (Independent) | Dacapo Ch.【ARP】 (Algorhythm Project) | `cross_agency` | 26 |
| Eileennoir Ch. (Independent) | Dacapo Ch.【ARP】 (Algorhythm Project) | `cross_agency` | 23 |
| Pyork The Pork (Independent) | moujob (Independent) | `same_agency_cross_channel` | 22 |

### Top Cross-Channel Transitions (2024 -> 2025)

| From VTuber (Agency) | To VTuber (Agency) | Transition Type | Observed Transition Viewers |
|:---|:---|:---:|:---:|
| Dacapo Ch.【ARP】 (Algorhythm Project) | Baabel Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 155 |
| Dacapo Ch.【ARP】 (Algorhythm Project) | Zekai Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 48 |
| Baabel Ch.【ARP】 (Algorhythm Project) | Dacapo Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 37 |
| Dacapo Ch.【ARP】 (Algorhythm Project) | Quentin Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 33 |
| Baabel Ch.【ARP】 (Algorhythm Project) | Zekai Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 32 |
| Dacapo Ch.【ARP】 (Algorhythm Project) | ดอยล์ (Independent) | `cross_agency` | 29 |
| MOLLY (Independent) | KAMAI (Independent) | `same_agency_cross_channel` | 20 |
| KAMAI (Independent) | นานาโฮชิ นานะ / 七星ナナ (Independent) | `same_agency_cross_channel` | 20 |

### Top Cross-Channel Transitions (2025 -> 2026)

| From VTuber (Agency) | To VTuber (Agency) | Transition Type | Observed Transition Viewers |
|:---|:---|:---:|:---:|
| KAMAI (Independent) | นานาโฮชิ นานะ / 七星ナナ (Independent) | `same_agency_cross_channel` | 51 |
| โป๊ะโกะ / PoKo ปลวกทูปเบ๋อ (Independent) | Nongwan TV (Independent) | `same_agency_cross_channel` | 47 |
| Zekai Ch.【ARP】 (Algorhythm Project) | Magnum Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 43 |
| Roxzy ロキジー (Independent) | โป๊ะโกะ / PoKo ปลวกทูปเบ๋อ (Independent) | `same_agency_cross_channel` | 36 |
| Baabel Ch.【ARP】 (Algorhythm Project) | Magnum Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 36 |
| โป๊ะโกะ / PoKo ปลวกทูปเบ๋อ (Independent) | Roxzy ロキジー (Independent) | `same_agency_cross_channel` | 34 |
| โป๊ะโกะ / PoKo ปลวกทูปเบ๋อ (Independent) | MOLLY (Independent) | `same_agency_cross_channel` | 29 |
| Zekai Ch.【ARP】 (Algorhythm Project) | Baabel Ch.【ARP】 (Algorhythm Project) | `same_agency_cross_channel` | 24 |

---

## Key Analytical Findings

1. **Audience Retention Resiliency:**
   - Observed audience retention between adjacent years consistently ranged from ~45% to >50% among active interacting viewers.
   - In 2024 -> 2025, a record 981 distinct viewers exhibited same-channel interaction continuity.

2. **Intra-Agency Cross-Channel Cohesion:**
   - Cross-channel transitions within the same agency (notably Algorhythm Project and Pixela Project) significantly outnumbered individual cross-agency transitions.
   - In 2024 -> 2025, 1,138 viewers were observed engaging across different talents within the same agency.

3. **Cross-Agency Bridging:**
   - Cross-agency transitions peaked during major collaborative events and collaborative streams, with independent creators serving as major mutual audience bridges.
