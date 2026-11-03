# Business-Model Archetypes and Checklists

Use: classify each company AND each reportable segment into one archetype (plus an optional runner-up).
Every archetype inherits the **Universal Checklist**. Archetype checklists add the questions specific to how
that type of business makes money. Every answer = value + verified quote + source/period, or "not disclosed".

Format per archetype:
- **examples** (tickers for regression tests)
- **SIC hints** (hint only, never decisive alone)
- **cues** (phrases whose frequency in the filing suggests the archetype)
- **checklist** (questions the extractor must answer)
- **expected drivers** (validation: missing ones go to "expected but not found")

---

## 0. Universal Checklist (every company, every archetype)

1. **Segments** — reportable segments with revenue share (of consolidated revenue, after eliminations) and segment profit, from XBRL. Period-labelled.
2. **Revenue model** — how revenue is earned (product sale, fee, royalty, rent, interest, tuition, subscription, contract). Quote it.
3. **Customers** — who pays; customer concentration (any customer >10% of revenue); government as payer.
4. **Who bears key costs** — for each major cost line: company, customer (pass-through/escalation), franchisee/bottler/licensee, or supplier. Use the deterministic pass-through scan.
5. **Geography & FX** — % revenue outside the reporting currency; FX channel = translation (stronger USD = headwind for USD reporters) unless the filing quotes a different mechanism; quoted FX impact from the latest 10-Q/earnings release.
6. **Balance sheet** — net cash vs net debt (XBRL); debt maturities; fixed vs floating; securitisation. Sets interest-rate driver direction (net cash → mild tailwind; net debt/floating → headwind).
7. **Regulators & key rules** — named agencies, laws, licences, pending actions/litigation.
8. **Competitors** — named in the filing's Competition section; tickers validated; else "none named".
9. **Top risk factors specific to this company** — not boilerplate (pandemic/climate only if the filing makes them company-specific).
10. **Latest-quarter update** — from the newest of 10-Q or 8-K earnings exhibit: guidance changes, KPI moves.

---

## A. Resources & Commodities

### commodity_producer
- examples: NEM, B, AU, GOLD, DEC, SQM, ARIS
- SIC hints: 1000–1499 (mining, oil & gas extraction)
- cues: "reserves", "AISC", "production guidance", "realized price", "per ounce", "per Mcfe", "hedge"
- checklist:
  - Main commodities produced and share of revenue
  - Production volume and guidance (units)
  - Unit cost (AISC, lifting cost, cash cost) and trend
  - Realized price vs benchmark (discount/premium, differentials)
  - Hedging: % of next 12–24 months hedged, at what prices
  - Reserve life / depletion; major projects and capex
  - Jurisdiction/political risk (royalties, nationalisation, permits)
- expected drivers: commodity price (futures), unit cost inputs (energy, labour), FX of producing countries, rates (if net debt)

### commodity_processor
- examples: ALTO, DAR, PARR (refiner), GSM
- SIC hints: 2000–2099 (food/ag processing), 2860–2869, 2911 (refining), 3310–3399
- cues: "crush", "crack spread", "margin per gallon", "feedstock", "co-products", "throughput"
- checklist:
  - Main inputs and outputs; margin/spread formula
  - Throughput/capacity and utilisation
  - Hedging of inputs/outputs
  - Co-products and their pricing
  - Policy credits/mandates affecting margin (RFS, tax credits)
- expected drivers: input commodity, output commodity (or its benchmark), energy cost, policy events

### merchant_power_energy
- examples: VST
- SIC hints: 4911, 4931, 4991
- cues: "capacity auction", "spark spread", "hedged generation", "MWh", "merchant"
- checklist:
  - Generation fleet mix (gas, nuclear, coal, renewables) and capacity
  - % of generation hedged and at what prices
  - Power price exposure by market (ERCOT, PJM, etc.); capacity auction results
  - Fuel costs and nuclear/production credits
  - Large contracted offtakes (e.g. data centres)
- expected drivers: power prices, natural gas, capacity prices, policy credits, rates

---

## B. Industrials & Transport

### pass_through_operator (contracted logistics, pipelines, barges, terminals)
- examples: KEX (Marine)
- SIC hints: 4400–4499, 4610–4619, 4920–4925
- cues: "term contracts", "escalation", "utilization", "take-or-pay", "spot", "Jones Act"
- checklist:
  - Term vs spot revenue mix (by sub-business)
  - Escalation/pass-through clauses and lag (scan result)
  - Utilisation rates
  - Contract renewal timing and recent repricing
  - Fleet/asset age, retirements, newbuild supply
  - Protective regulation (e.g. Jones Act)
- expected drivers: volume/utilisation, contract pricing, fuel (partial pass-through), labour (escalators), customer-industry demand

### cyclical_transport (spot-exposed shipping, trucking, airlines)
- examples: SBLK, DSX
- SIC hints: 4210–4231, 4400–4499, 4512–4522
- cues: "charter rates", "TCE", "spot market", "load factor", "fleet supply", "orderbook"
- checklist:
  - Spot vs period/charter mix; forward coverage booked
  - Rate KPI (TCE, yield, rate per mile) and trend
  - Fleet size, age, newbuild deliveries; industry orderbook
  - Fuel cost and recovery (bunker clauses, surcharges)
  - Dividend/capital return policy
- expected drivers: freight/charter rates (BDRY etc.), fuel, trade volumes, geopolitical rerouting

### industrial_cyclical (manufacturers of durable/capital goods)
- examples: CSTM, BLBD, LEA, BWA, JBL, PLXS, KEX (D&S)
- SIC hints: 3300–3699, 3711–3799, 3500–3599
- cues: "backlog", "orders", "OEM", "end markets", "book-to-bill", "metal price lag"
- checklist:
  - End markets and share of revenue (auto, aerospace, energy, construction, data centre, etc.)
  - Backlog/orders and book-to-bill
  - Customer concentration (top customers %)
  - Key input metals/energy and pass-through (scan)
  - Tariff exposure and manufacturing footprint
  - Capacity utilisation and restructuring
- expected drivers: end-market demand, metals (HG=F, ALI=F, steel), energy, tariffs, rates (customer financing)

### defense_government_contractor
- examples: RTX, AMTM, ITA (holdings)
- SIC hints: 3720–3729, 3760–3769, 3812, 8711
- cues: "U.S. Government", "DoD", "backlog", "fixed-price", "cost-plus", "program"
- checklist:
  - % revenue from US government / foreign military sales / commercial
  - Contract type mix (fixed-price vs cost-plus) and margin risk
  - Backlog and funded vs unfunded
  - Largest programs and concentration
  - Budget/appropriation dependence; continuing-resolution risk
- expected drivers: defense budgets (events), program awards, commercial aerospace demand (if any), supply chain/labour

---

## C. Technology

### semiconductor_hardware
- examples: MU, SNDK, TSM, NVDA, DELL, EXTR
- SIC hints: 3570–3579, 3670–3679
- cues: "ASP", "bit growth", "wafer", "inventory", "hyperscaler", "export controls", "gross margin"
- checklist:
  - Product/end-market mix (data centre, PC, mobile, auto)
  - Pricing (ASP) and volume trends; cycle position (inventory days, utilisation)
  - Customer concentration (hyperscalers, OEMs)
  - Capex and capacity additions
  - Export controls / China exposure
  - Supply dependencies (foundry, memory, components)
- expected drivers: AI/cloud capex (peer basket), memory/component prices, SMH, export-control events, FX (Asia revenue)

### software_saas (incl. usage-based infrastructure)
- examples: FSLY, (MSFT segments)
- SIC hints: 7370–7379
- cues: "ARR", "net retention", "RPO", "subscription", "usage-based", "customers >$100k"
- checklist:
  - Subscription vs usage vs services mix
  - ARR/RPO and growth; net revenue retention
  - Customer count and large-customer cohort; concentration
  - Gross margin and its drivers (cloud hosting costs)
  - Stock-based compensation and FCF margin
- expected drivers: IT spending (peer basket), cloud/hosting costs, rates (valuation), competition events

### platform_multi_segment (ad-funded / multi-business platforms)
- examples: GOOGL, META, NTES
- SIC hints: 7370–7379
- cues: "advertising revenue", "traffic acquisition costs", "segments", "capital expenditures", "users"
- checklist:
  - Segment table and weights; per-segment revenue model
  - Per-segment demand drivers (ad spend, cloud demand, game launches, etc.)
  - Major cost lines (TAC, content, capex/depreciation)
  - Capex intensity and guidance
  - Key regulatory/antitrust matters and their status
  - User/engagement KPIs
- expected drivers: ad spending (peer basket), cloud demand, AI capex (NVDA/TSM/SMH), regulatory events, FX

### marketplace_platform (marketplaces, gig, lead-gen, travel, autos)
- examples: UBER, CARG, QNST
- SIC hints: 7370–7379, 7389, 4700–4799
- cues: "gross bookings", "take rate", "GMV", "marketplace", "dealers", "leads", "active users"
- checklist:
  - Gross bookings/GMV and take rate
  - Supply side vs demand side economics (drivers, dealers, advertisers)
  - Active users/customers and frequency
  - Customer/partner concentration (e.g. a few insurance carriers for lead-gen)
  - Regulatory classification risks (worker status, data/privacy)
- expected drivers: consumer activity, partner ad budgets, fuel (gig), regulatory events

### payments_fintech
- examples: XYZ
- SIC hints: 6099, 6141, 7374
- cues: "gross payment volume", "take rate", "transaction losses", "interchange", "merchants"
- checklist:
  - Payment volume and take rate by segment
  - Consumer vs merchant revenue mix
  - Credit exposure (BNPL, loans) and loss rates
  - Bitcoin/crypto revenue (gross vs net)
  - Interchange/regulatory exposure
- expected drivers: consumer spending, credit cycle, rates/funding, crypto prices (if relevant)

---

## D. Consumer

### branded_consumer_staples (franchise/bottler models included)
- examples: KO, PEP, JJSF
- SIC hints: 2000–2099, 2080–2087, 2840–2844
- cues: "price/mix", "unit case volume", "bottling partners", "concentrate", "brands"
- checklist:
  - Brand portfolio and categories
  - Price/mix vs volume contribution to growth
  - Structure: what the company makes vs bottlers/co-packers/licensees; who bears input costs; concentrate/incidence pricing
  - International share and quoted FX impact
  - Health/regulatory demand risks (sugar taxes, labelling, GLP-1 if discussed)
- expected drivers: pricing power (MD&A), input commodities (with cost-bearer), FX (earnings channel), staples rotation (XLP/peers), rates

### franchisor (restaurants, hotels, fitness, services)
- examples: DPZ, HTHT, (YUMC partly), LOCO (partly)
- SIC hints: 5810–5812, 7011, 6794
- cues: "franchisees", "royalty", "system sales", "same-store sales", "net unit growth", "supply chain"
- checklist:
  - % of units franchised vs company-operated (by region)
  - Revenue streams: royalties/fees, company-operated sales, supply chain/distribution, advertising fund
  - System sales, same-store sales, net unit growth
  - Royalty/fee rates
  - Who bears store-level costs (food, labour, delivery) — franchisee vs company; supply-chain pricing to franchisees
  - Franchisee health (closures, unit economics)
  - Leverage/securitisation (whole-business notes)
- expected drivers: consumer spending, same-store sales, commodity costs (through franchisee margins and supply-chain pass-through), labour/minimum wage, delivery aggregators, rates (net debt), FX (international royalties, translation)

### restaurant_operator (mostly company-operated)
- examples: LOCO, (YUMC company stores)
- SIC hints: 5812
- cues: "restaurant-level margin", "food and paper costs", "labor costs as a percentage", "comparable restaurant sales"
- checklist:
  - Comparable sales: traffic vs ticket
  - Food/paper and labour as % of sales
  - Restaurant-level margin and unit economics (AUV, payback)
  - Store growth and closures
  - Commodity basket (chicken, beef, cheese) and contracts
- expected drivers: consumer spending, food commodities, wages, rates (if debt)

### retailer
- examples: LOVE, BNED
- SIC hints: 5200–5999
- cues: "comparable sales", "inventory", "gross margin", "stores", "e-commerce", "tariffs"
- checklist:
  - Comparable sales and drivers (traffic/ticket)
  - Channel mix (stores vs online); store count
  - Gross margin drivers (freight, promotions, sourcing)
  - Inventory levels/turns
  - Import/tariff exposure and sourcing countries
  - Seasonality
- expected drivers: consumer spending/sentiment, tariffs/freight, rates (housing-linked categories), FX (sourcing)

### consumer_discretionary_brand (durables, leisure, toys, apparel, firearms)
- examples: JAKK, SWBI, F (autos)
- SIC hints: 3940–3949, 2300–2399, 3480–3489, 3711
- cues: "retail partners", "licensed properties", "seasonality", "dealer", "tariffs"
- checklist:
  - Channel/customer concentration (major retailers/dealers)
  - Seasonality
  - Licensing dependencies
  - Sourcing/manufacturing countries and tariffs
  - Demand sensitivity (discretionary, event-driven)
- expected drivers: consumer spending, tariffs, input costs, rates (financing for autos/durables)

---

## E. Financials

### bank_deposit_lender
- examples: SHG, HSBC
- SIC hints: 6020–6029, 6035–6036
- cues: "net interest margin", "deposits", "CET1", "loan loss provision", "non-performing"
- checklist:
  - NIM and its rate sensitivity (asset vs liability repricing)
  - Loan book mix and credit quality (NPLs, provisions)
  - Deposit base and cost of deposits
  - Capital ratios (CET1) and shareholder return policy
  - Fee income share
  - Home-market FX/currency (for ADRs)
- expected drivers: policy/short rates, yield curve, credit cycle, local FX, regulatory events

### specialty_lender (consumer/fintech/pawn lenders)
- examples: PGY, EZPW
- SIC hints: 6141, 6153, 6199, 5932 (pawn)
- cues: "funding", "securitization", "forward flow", "charge-offs", "loan balances", "pawn"
- checklist:
  - Funding sources and the benchmark they track (e.g. 2-year Treasury, SOFR)
  - Credit performance (delinquencies, charge-offs) vs expectations
  - Dependence on securitisation/forward-flow markets and spreads
  - Loan pricing (APR) changes
  - Regulation (state/federal lending rules)
  - Counter-cyclical demand? (pawn/consumer stress)
- expected drivers: short-term rates (DGS2), credit spreads, consumer credit health, securitisation market events

### insurer
- examples: (none in current book — include for coverage)
- SIC hints: 6300–6399
- cues: "combined ratio", "reserves", "catastrophe", "net investment income", "premiums written"
- checklist:
  - Lines of business and premium mix
  - Combined ratio and reserve development
  - Catastrophe exposure and reinsurance
  - Investment portfolio yield and duration
  - Rate (pricing) increases
- expected drivers: catastrophe events, interest rates (investment income), pricing cycle

### asset_manager_services (asset managers, external managers, brokers)
- examples: RMR
- SIC hints: 6211, 6282, 6798 (externally managed)
- cues: "assets under management", "management fees", "incentive fees", "managed REITs"
- checklist:
  - AUM and fee rates; base vs incentive fees
  - Client concentration (managed vehicles)
  - Fee sensitivity to client share prices/asset values
  - Contract terms and termination provisions
- expected drivers: asset values of managed vehicles, rates (real estate), flows

---

## F. Healthcare

### single_asset_pharma (commercial, 1–2 products dominate)
- examples: ZVRA, HRMY, ANIP (Cortrophin-led), INDV/SUPN
- SIC hints: 2834, 2836
- cues: "net product revenue", "patients", "exclusivity", "ANDA", "PDUFA", "CHMP"
- checklist:
  - Product revenue concentration
  - Patient/script KPIs and sales ramp
  - Exclusivity/patent expiry and litigation (ANDA filers, settlements)
  - Regulatory dates (PDUFA, EU opinions)
  - Pricing/reimbursement risk (Medicare negotiation, payer access)
  - Cash and runway
- expected drivers: regulatory/patent events, payer policy, pipeline readouts

### clinical_stage_biotech (no meaningful product revenue)
- examples: FDMT, AGEN, CHRS (early commercial), VIR
- SIC hints: 2836, 8731
- cues: "clinical trial", "Phase 2", "topline data", "cash runway", "collaboration revenue"
- checklist:
  - Lead programs, indication, phase
  - Next data readouts / regulatory milestones with dates
  - Cash, burn rate, runway (months)
  - Partnerships and milestone/royalty economics
  - Dilution risk (ATM, shelf)
- expected drivers: trial/regulatory events, financing conditions (XBI, rates)

### diversified_pharma_medtech
- examples: LLY, NBIX, GRFS, NVST, INGN, OPK
- SIC hints: 2834, 2835, 3841–3851
- cues: "product portfolio", "loss of exclusivity", "pipeline", "procedure volumes", "plasma"
- checklist:
  - Revenue by product/franchise; growth drivers
  - Loss-of-exclusivity schedule
  - Pricing pressure (Medicare negotiation, rebates, tariffs on pharma)
  - Pipeline catalysts with dates
  - Manufacturing/supply constraints
  - Leverage (if relevant)
- expected drivers: product launches/approvals (events), pricing policy, procedure volumes, FX

### policy_funded_service (education, healthcare services, government-funded programmes)
- examples: PRDO, STRA, APEI, LOPE, LAUR
- SIC hints: 8200–8299, 8000–8099, 8300–8399
- cues: "Title IV", "tuition", "students", "enrollment", "accreditation", "Department of Education", "90/10", "Medicare", "Medicaid", "reimbursement"
- checklist:
  - Share of revenue from government programmes (e.g. Title IV under 90/10; Medicare/Medicaid payer mix)
  - Key regulators, accreditors and rules; pending rulemaking, reviews, settlements
  - Enrolment/patient volume trends (new vs total) and retention
  - Cyclicality (education enrolment tends to rise with unemployment)
  - Pricing (tuition, reimbursement rates)
  - Customer acquisition / marketing cost
  - Military/employer-funded share (e.g. tuition assistance)
- expected drivers: policy/regulatory events, labour market (FRED UNRATE, lagged), peer sector sentiment basket, rates (by net cash/debt)

---

## G. Communications, Media, Utilities, Real Estate

### subscription_media_royalty
- examples: WMG, NFLX
- SIC hints: 7812–7829, 4841, 2741, 7929
- cues: "subscribers", "ARPU", "streaming revenue", "royalties", "catalog", "churn"
- checklist:
  - Revenue mix (subscription, ads, licensing, royalties)
  - Subscriber/ARPU or streaming growth; price increases
  - Churn/retention (if disclosed)
  - Content/artist cost and amortisation
  - Licensing deal renewals (DSPs, distributors)
  - International share and FX
- expected drivers: consumer subscriptions/pricing, ad market, FX, licensing events

### telecom_operator
- examples: TMUS, TEO, ATNI
- SIC hints: 4810–4899
- cues: "postpaid", "ARPU", "churn", "spectrum", "fiber", "net additions"
- checklist:
  - Subscriber net adds (postpaid/prepaid/broadband) and churn
  - ARPU/ARPA trend and pricing actions
  - Capex intensity and network build (5G, fiber)
  - Spectrum holdings/auctions
  - Leverage and buybacks
  - For non-US operators: inflation/FX/regulated tariffs
- expected drivers: competition/pricing events, rates (net debt), FX/inflation (international), capex cycle

### regulated_utility
- examples: (coverage)
- SIC hints: 4900–4949
- cues: "rate base", "allowed ROE", "rate case", "regulatory commission"
- checklist:
  - Rate base and growth plan
  - Allowed vs earned ROE; pending rate cases
  - Fuel/purchased-power cost recovery mechanisms
  - Load growth (data centres)
  - Leverage and equity issuance needs
- expected drivers: rates (high sensitivity), regulatory decisions, load growth, weather

### real_estate_owner (REITs, developers, agri-land)
- examples: CRESY, IRS
- SIC hints: 6500–6599, 6798
- cues: "occupancy", "leasing spreads", "NOI", "FFO", "cap rate", "land portfolio"
- checklist:
  - Property/asset types and geography
  - Occupancy, rent spreads, NOI growth
  - Debt maturities, fixed/floating, LTV
  - Development pipeline
  - Local macro/FX/inflation (for EM real estate)
- expected drivers: rates, local FX/inflation, property demand, commodity prices (agri-land)

### staffing_business_services
- examples: KELYA, RCMT
- SIC hints: 7360–7363, 8740–8748
- cues: "billable hours", "bill rate", "gross profit per hour", "placements", "clients"
- checklist:
  - Service mix (temp, perm, outsourced, specialty)
  - Bill/pay spread and gross margin
  - Client concentration and end markets
  - Volume indicators (hours, headcount on assignment)
- expected drivers: labour market (payrolls, UNRATE), corporate spending, wage inflation

### diversified_holding (conglomerates, holding companies, sum-of-parts)
- examples: CRESY (agri + real estate), SHG (if treated as group), IRS
- cues: "subsidiaries", "equity method", "holding", multiple unrelated segments
- checklist:
  - Each business line → classify with its own archetype (segment level)
  - Holding-company debt and dividends from subsidiaries
  - Listed stakes and their market values
- expected drivers: roll-up of segment archetype drivers

### other
- No forced checklist; Universal Checklist only. Confidence capped at 0.5. Flag for review and suggest a new archetype.

---

## Classification rules (for the builder)

1. Inputs: SIC code, cue counts per archetype over the full Business section, segment list with weights, net cash/debt.
2. Cue counts and SIC constrain the LLM: if one archetype's cues dominate and the SIC matches, the LLM must pick it or justify otherwise with verified quotes.
3. Classify every reportable segment separately from a segment-specific slice; company archetype = largest revenue-weighted segment; show the mix. Identical labels+confidence across all segments → flag.
4. Weak fit → "ambiguous" with a runner-up; never a high-confidence nearest template. "other" ≤ 0.5 confidence.
5. Universal Checklist always runs, regardless of archetype — this is what catches PRDO-type misses (government payer, regulators, net cash) even if classification fails.
6. Validation: each archetype's expected drivers must be found (with quotes) or listed under "expected but not found".
