"""
HAS-BLED Score for Major Bleeding Risk (Atrial Fibrillation)
- Components (1 point each, max 9):
  H: Hypertension (uncontrolled; approximated here as SBP ≥ 160 mmHg)
  A: Abnormal renal function
  A: Abnormal liver function
  S: Stroke history
  B: Bleeding history or predisposition
  L: Labile INR (e.g., TTR < 60% if on warfarin)
  E: Elderly (age > 65 years)
  D: Drugs (antiplatelet/NSAIDs)
  D: Alcohol (excess)
- Output: ANNUAL major bleeding risk (%) using HAS-BLED cohorts (Pisters 2010),
  plus category & recommendations.

Return schema (same as your other classes):
  risk_percentage, risk_category, risk_description, recommendations, explanation, sex, inputs
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class FuzzyHASBLEDRisk:
    def __init__(self):
        """Initialize fuzzy logic system for HAS-BLED (qualitative layer)"""
        self.setup_fuzzy_variables()
        self.setup_membership_functions()
        self.setup_rules()
        self.setup_control_system()

        # Pisters 2010 (Euro Heart Survey) — bleeds per 100 pt-years by HAS-BLED score (Table 5).
        # Note: Sparse counts for ≥6; we conservatively map ≥5 to >=12.5%.
        self._score_to_risk_pct = {
            0: 1.13,
            1: 1.02,
            2: 1.88,
            3: 3.74,
            4: 8.70,
            5: 12.50,
            6: 12.50, 7: 12.50, 8: 12.50, 9: 12.50
        }

    # ---------------------------
    # Fuzzy setup
    # ---------------------------
    def setup_fuzzy_variables(self):
        """Define fuzzy inputs and output (only variables used in rules)"""
        self.age = ctrl.Antecedent(np.arange(18, 101, 1), 'age')
        self.systolic_bp = ctrl.Antecedent(np.arange(90, 221, 1), 'systolic_bp')
        self.renal_abn = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'renal_abn')
        self.liver_abn = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'liver_abn')
        self.prior_stroke = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'prior_stroke')
        self.prior_bleeding = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'prior_bleeding')
        self.labile_inr = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'labile_inr')
        self.drugs = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'drugs')      # antiplatelet/NSAIDs
        self.alcohol = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'alcohol')  # excess

        # Consequent: qualitative major bleeding risk (%/yr) for interpretive plots (0–20)
        self.bleed_risk = ctrl.Consequent(np.arange(0, 20.5, 0.5), 'bleed_risk')

    def setup_membership_functions(self):
        """Define membership functions"""
        # Age (elderly >65)
        self.age['adult']   = fuzz.trapmf(self.age.universe, [18, 18, 55, 65])
        self.age['elderly'] = fuzz.trapmf(self.age.universe, [64, 68, 101, 101])

        # Systolic BP: capture the ≥160 mmHg threshold explicitly
        self.systolic_bp['normal']     = fuzz.trapmf(self.systolic_bp.universe, [90, 90, 120, 130])
        self.systolic_bp['elevated']   = fuzz.trimf(self.systolic_bp.universe, [125, 140, 155])
        self.systolic_bp['very_high']  = fuzz.trapmf(self.systolic_bp.universe, [158, 160, 221, 221])

        # Binary-like factors with soft edges
        for v in (self.renal_abn, self.liver_abn, self.prior_stroke,
                  self.prior_bleeding, self.labile_inr, self.drugs, self.alcohol):
            v['no']  = fuzz.trapmf(v.universe, [0.0, 0.0, 0.2, 0.35])
            v['yes'] = fuzz.trapmf(v.universe, [0.65, 0.8, 1.0, 1.0])

        # Output buckets (annual % for intuition)
        self.bleed_risk['low']       = fuzz.trapmf(self.bleed_risk.universe, [0, 0, 1.0, 3.0])
        self.bleed_risk['moderate']  = fuzz.trimf(self.bleed_risk.universe, [2.0, 4.0, 7.0])
        self.bleed_risk['high']      = fuzz.trimf(self.bleed_risk.universe, [6.0, 9.0, 13.0])
        self.bleed_risk['very_high'] = fuzz.trapmf(self.bleed_risk.universe, [12.0, 15.0, 20.0, 20.0])

    def setup_rules(self):
        """Define fuzzy rules approximating HAS-BLED contributions"""
        R = []

        # Dominant factors
        R.append(ctrl.Rule(self.prior_bleeding['yes'], self.bleed_risk['very_high']))
        R.append(ctrl.Rule(self.renal_abn['yes'] | self.liver_abn['yes'], self.bleed_risk['high']))
        R.append(ctrl.Rule(self.labile_inr['yes'], self.bleed_risk['high']))

        # Hypertension at HAS-BLED threshold
        R.append(ctrl.Rule(self.systolic_bp['very_high'], self.bleed_risk['moderate']))

        # Age effect & stacking
        R.append(ctrl.Rule(self.age['elderly'] & (self.drugs['yes'] | self.alcohol['yes']),
                           self.bleed_risk['moderate']))
        R.append(ctrl.Rule(self.age['elderly'] & (self.renal_abn['yes'] | self.liver_abn['yes']),
                           self.bleed_risk['high']))

        # Stroke history adds risk even without bleeding history
        R.append(ctrl.Rule(self.prior_stroke['yes'] & ~(self.prior_bleeding['yes']),
                           self.bleed_risk['moderate']))

        # Multiple moderate factors -> high
        R.append(ctrl.Rule(
            (self.systolic_bp['very_high'] & (self.drugs['yes'] | self.alcohol['yes'])) |
            (self.systolic_bp['elevated'] & self.age['elderly'] & (self.drugs['yes'] | self.alcohol['yes'])),
            self.bleed_risk['high']
        ))

        self.rules = R

    def setup_control_system(self):
        self.ctrl_sys = ctrl.ControlSystem(self.rules)
        self.sim = ctrl.ControlSystemSimulation(self.ctrl_sys)

    # ---------------------------
    # Helpers / estimators
    # ---------------------------
    def _bool(self, x) -> bool:
        return bool(x)

    def _uncontrolled_htn(self, systolic_bp: float | None, has_htn_flag: bool | None = None) -> bool:
        """HAS-BLED 'H' = uncontrolled SBP ≥ 160 mmHg; if SBP missing, do not award point."""
        return bool(systolic_bp is not None and systolic_bp >= 160.0)

    def _labile_inr_from_ttr(self, inr_ttr: float | None, labile_inr_flag: bool | None) -> bool:
        """HAS-BLED 'L' = labile INR; TTR < 60% if provided, else fallback to flag."""
        if inr_ttr is not None:
            try:
                return float(inr_ttr) < 60.0
            except Exception:
                pass
        return bool(labile_inr_flag)

    # Exact point calculation
    def hasbled_points(self, age, systolic_bp,
                       renal_abn, liver_abn,
                       prior_stroke, prior_bleeding,
                       labile_inr, inr_ttr,
                       drugs, alcohol,
                       hypertension_history=None) -> int:
        score = 0
        # H: uncontrolled hypertension by SBP≥160
        if self._uncontrolled_htn(systolic_bp, hypertension_history):
            score += 1
        # A: renal / liver
        if self._bool(renal_abn): score += 1
        if self._bool(liver_abn): score += 1
        # S: stroke
        if self._bool(prior_stroke): score += 1
        # B: bleeding history/predisposition
        if self._bool(prior_bleeding): score += 1
        # L: labile INR (or TTR < 60%)
        if self._labile_inr_from_ttr(inr_ttr, labile_inr): score += 1
        # E: elderly > 65
        if age is not None and age > 65: score += 1
        # D: drugs and alcohol (1 each)
        if self._bool(drugs): score += 1
        if self._bool(alcohol): score += 1
        return int(max(0, min(9, score)))

    def points_to_annual_risk_pct(self, score: int) -> float:
        return float(self._score_to_risk_pct.get(score, 12.5 if score >= 5 else 1.13))

    # ---------------------------
    # Main API (same structure)
    # ---------------------------
    def calculate_risk(self, age, sex,
                       systolic_bp=None,
                       hypertension=False,
                       kidney_disease=False, liver_disease=False,
                       prior_stroke=False, prior_bleeding=False,
                       labile_inr=False, inr_ttr=None,
                       on_antiplatelet_or_nsaid=False,
                       alcohol_excess=False):
        """
        Compute HAS-BLED ANNUAL major bleeding risk (%).
        Notes on mapping to your DB:
          - hypertension: use SBP to detect uncontrolled (SBP ≥160) for the 'H' point.
          - kidney_disease -> renal_abn
          - alcoholic -> alcohol_excess
          - prevouis_stroke -> prior_stroke
          - drugs: pass True if antiplatelet/NSAID use is present (if known)
          - labile_inr: set True, or supply inr_ttr (<60%) if on warfarin.
        """

        # ---- Fuzzy (qualitative) inputs ----
        self.sim.input['age'] = float(age)
        self.sim.input['systolic_bp'] = float(systolic_bp if systolic_bp is not None else 120.0)
        self.sim.input['renal_abn'] = 1.0 if self._bool(kidney_disease) else 0.0
        self.sim.input['liver_abn'] = 1.0 if self._bool(liver_disease) else 0.0
        self.sim.input['prior_stroke'] = 1.0 if self._bool(prior_stroke) else 0.0
        self.sim.input['prior_bleeding'] = 1.0 if self._bool(prior_bleeding) else 0.0
        self.sim.input['labile_inr'] = 1.0 if self._labile_inr_from_ttr(inr_ttr, labile_inr) else 0.0
        self.sim.input['drugs'] = 1.0 if self._bool(on_antiplatelet_or_nsaid) else 0.0
        self.sim.input['alcohol'] = 1.0 if self._bool(alcohol_excess) else 0.0
        self.sim.compute()
        _qual = float(self.sim.output['bleed_risk'])  # qualitative only

        # ---- Authoritative HAS-BLED points & % ----
        score = self.hasbled_points(
            age=age, systolic_bp=systolic_bp,
            renal_abn=kidney_disease, liver_abn=liver_disease,
            prior_stroke=prior_stroke, prior_bleeding=prior_bleeding,
            labile_inr=labile_inr, inr_ttr=inr_ttr,
            drugs=on_antiplatelet_or_nsaid, alcohol=alcohol_excess,
            hypertension_history=hypertension
        )
        risk_pct = self.points_to_annual_risk_pct(score)

        interp = self.interpret_risk(score, risk_pct)
        explanation = self.generate_explanation(
            age, systolic_bp, kidney_disease, liver_disease, prior_stroke, prior_bleeding,
            self._labile_inr_from_ttr(inr_ttr, labile_inr), on_antiplatelet_or_nsaid, alcohol_excess,
            score, risk_pct
        )

        return {
            'risk_percentage': round(risk_pct, 2),  # annual major bleeding risk (%/yr)
            'risk_category': interp['category'],
            'risk_description': interp['description'],
            'recommendations': interp['recommendations'],
            'explanation': explanation,
            'sex': sex,
            'inputs': {
                'age': age,
                'systolic_bp': systolic_bp,
                'hypertension_history': bool(hypertension),
                'renal_abnormal': bool(kidney_disease),
                'liver_abnormal': bool(liver_disease),
                'prior_stroke': bool(prior_stroke),
                'prior_bleeding': bool(prior_bleeding),
                'labile_inr': bool(self._labile_inr_from_ttr(inr_ttr, labile_inr)),
                'inr_ttr': inr_ttr,
                'drugs_antiplatelet_nsaid': bool(on_antiplatelet_or_nsaid),
                'alcohol_excess': bool(alcohol_excess),
                'has_bled_score': score,
                'qualitative_fuzzy_%': round(_qual, 2)
            }
        }

    # ---------------------------
    # Interpretation & narrative
    # ---------------------------
    def interpret_risk(self, score: int, annual_pct: float):
        """Common use: flag ≥3 as 'High' risk; 2 'Moderate'; 0–1 'Low'."""
        if score <= 1:
            category = 'Low Risk'
            recs = [
                'Continue routine monitoring.',
                'Address lifestyle (alcohol moderation).'
            ]
        elif score == 2:
            category = 'Moderate Risk'
            recs = [
                'Optimize modifiable factors (BP control, avoid NSAIDs/dual antiplatelets if possible).',
                'If on warfarin, improve TTR (>60%) or consider DOAC suitability.'
            ]
        else:
            category = 'High Risk'
            recs = [
                'Intensify follow-up; correct reversible risks (uncontrolled BP, labile INR, alcohol, interacting drugs).',
                'Bleeding risk alone should not preclude anticoagulation—use it to fix risk factors and plan monitoring.'
            ]
        desc = f'HAS-BLED score {score}: estimated annual major bleeding risk ≈ {annual_pct:.2f}% per year.'
        return {'category': category, 'description': desc, 'recommendations': recs}

    def generate_explanation(self, age, systolic_bp, renal_abn, liver_abn,
                             prior_stroke, prior_bleeding, labile_inr,
                             drugs, alcohol, score, annual_pct):
        exp = []
        # Hypertension
        if systolic_bp is not None and systolic_bp >= 160:
            exp.append(f"Uncontrolled systolic BP ≥160 mmHg ({systolic_bp} mmHg) adds 1 point.")
        # Renal/Liver
        if renal_abn: exp.append("Abnormal renal function adds 1 point.")
        if liver_abn: exp.append("Abnormal liver function adds 1 point.")
        # Stroke & Bleeding history
        if prior_stroke: exp.append("Prior stroke adds 1 point.")
        if prior_bleeding: exp.append("Bleeding history/predisposition adds 1 point.")
        # Labile INR
        if labile_inr: exp.append("Labile INR (e.g., TTR <60% on warfarin) adds 1 point.")
        # Age
        if age > 65: exp.append("Age >65 years adds 1 point.")
        # Drugs/Alcohol
        if drugs: exp.append("Concomitant antiplatelet/NSAID use adds 1 point.")
        if alcohol: exp.append("Excess alcohol use adds 1 point.")

        exp.append(f"Total HAS-BLED = {score} → ~{annual_pct:.2f}%/yr major bleeding risk (cohort-dependent).")
        exp.append("Use HAS-BLED to identify & modify risk factors; do not use it alone to withhold anticoagulation.")

        return exp
