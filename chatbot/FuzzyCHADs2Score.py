"""
Fuzzy/Structured Implementation of CHADS2 Stroke Risk (Atrial Fibrillation)
- CHADS2 components (1 point each): Congestive heart failure, Hypertension,
  Age >= 75, Diabetes mellitus; Prior Stroke/TIA = 2 points.
- Output: estimated ANNUAL stroke risk (%) by CHADS2 table, plus category & guidance.

This mirrors the structure of your previous classes:
- setup_fuzzy_variables / setup_membership_functions / setup_rules / setup_control_system
- calculate_risk(...) -> dict with:
  risk_percentage, risk_category, risk_description, recommendations, explanation, sex, inputs
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class FuzzyCHADS2Risk:
    def __init__(self):
        """Initialize fuzzy logic system for CHADS2 annual stroke risk"""
        self.setup_fuzzy_variables()
        self.setup_membership_functions()
        self.setup_rules()
        self.setup_control_system()

        # Classic CHADS2 annual stroke risk (% per year) reference table
        # (Commonly cited estimates; ranges vary slightly by source/era.)
        self._score_to_risk_pct = {
            0: 1.9,
            1: 2.8,
            2: 4.0,
            3: 5.9,
            4: 8.5,
            5: 12.5,
            6: 18.2,
        }

    # ---------------------------
    # Fuzzy setup
    # ---------------------------
    def setup_fuzzy_variables(self):
        """Define fuzzy inputs and output"""
        self.age = ctrl.Antecedent(np.arange(20, 101, 1), 'age')

        # Binary-like risk factors (soft edges for noise/uncertainty)
        self.hypertension = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'hypertension')
        self.diabetes = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'diabetes')
        self.heart_failure = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'heart_failure')
        self.prior_stroke_tia = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'prior_stroke_tia')

        # Consequent: annual stroke risk percentage (keep 0–20%)
        self.stroke_risk = ctrl.Consequent(np.arange(0, 20.5, 0.5), 'stroke_risk')

    def setup_membership_functions(self):
        """Define membership functions"""

        # Age (CHADS2 threshold is 75 years)
        self.age['lt75'] = fuzz.trapmf(self.age.universe, [20, 20, 60, 75])
        self.age['ge75'] = fuzz.trapmf(self.age.universe, [72, 75, 100, 100])

        # Binary-style factors
        for var in (self.hypertension, self.diabetes, self.heart_failure, self.prior_stroke_tia):
            var['no'] = fuzz.trapmf(var.universe, [0.0, 0.0, 0.2, 0.35])
            var['yes'] = fuzz.trapmf(var.universe, [0.65, 0.8, 1.0, 1.0])

        # Output buckets (annual %)
        self.stroke_risk['very_low']  = fuzz.trapmf(self.stroke_risk.universe, [0, 0, 1.0, 2.5])
        self.stroke_risk['low']       = fuzz.trimf(self.stroke_risk.universe, [2.0, 3.0, 4.5])
        self.stroke_risk['moderate']  = fuzz.trimf(self.stroke_risk.universe, [4.0, 6.0, 8.0])
        self.stroke_risk['high']      = fuzz.trimf(self.stroke_risk.universe, [7.0, 10.0, 13.0])
        self.stroke_risk['very_high'] = fuzz.trapmf(self.stroke_risk.universe, [12.0, 15.0, 20.0, 20.0])

    def setup_rules(self):
        """Define fuzzy rules approximating CHADS2 weighting"""
        R = []

        # Stroke/TIA history dominates (2 points in CHADS2)
        R.append(ctrl.Rule(self.prior_stroke_tia['yes'], self.stroke_risk['very_high']))

        # Age ≥75 alone -> at least moderate
        R.append(ctrl.Rule(self.age['ge75'] & self.prior_stroke_tia['no'],
                           self.stroke_risk['moderate']))

        # Any single non-stroke factor -> low
        R.append(ctrl.Rule(
            (self.hypertension['yes'] | self.diabetes['yes'] | self.heart_failure['yes']) &
            self.age['lt75'] & self.prior_stroke_tia['no'],
            self.stroke_risk['low']
        ))

        # Two non-stroke factors -> moderate
        R.append(ctrl.Rule(
            ( (self.hypertension['yes'] & self.diabetes['yes']) |
              (self.hypertension['yes'] & self.heart_failure['yes']) |
              (self.diabetes['yes'] & self.heart_failure['yes']) ) &
            self.prior_stroke_tia['no'],
            self.stroke_risk['moderate']
        ))

        # Age ≥75 plus any other non-stroke factor -> high
        R.append(ctrl.Rule(
            self.age['ge75'] &
            (self.hypertension['yes'] | self.diabetes['yes'] | self.heart_failure['yes']) &
            self.prior_stroke_tia['no'],
            self.stroke_risk['high']
        ))

        self.rules = R

    def setup_control_system(self):
        """Create the fuzzy control system"""
        self.ctrl_sys = ctrl.ControlSystem(self.rules)
        self.sim = ctrl.ControlSystemSimulation(self.ctrl_sys)

    # ---------------------------
    # Helpers / estimators
    # ---------------------------
    def _bool(self, x) -> bool:
        return bool(x)

    def chads2_points(self, age, hypertension, diabetes, heart_failure, prior_stroke_tia) -> int:
        """Exact CHADS2 point calculation (authoritative)"""
        score = 0
        if self._bool(heart_failure):
            score += 1
        if self._bool(hypertension):
            score += 1
        if age is not None and age >= 75:
            score += 1
        if self._bool(diabetes):
            score += 1
        if self._bool(prior_stroke_tia):
            score += 2
        return int(max(0, min(6, score)))

    def chads2_to_annual_risk_pct(self, score: int) -> float:
        """Map CHADS2 score to annual stroke risk (%)"""
        return float(self._score_to_risk_pct.get(score, 18.2 if score >= 6 else 1.9))

    # ---------------------------
    # Main API
    # ---------------------------
    def calculate_risk(self, age, sex,
                       hypertension=False, diabetes=False, heart_failure=False,
                       prior_stroke_tia=False):
        """
        Compute CHADS2 annual stroke risk.

        Inputs
        ------
        age: int
        sex: 'male' | 'female' (not used by CHADS2 but returned for consistency)
        hypertension, diabetes, heart_failure, prior_stroke_tia: bool

        Returns
        -------
        dict with keys:
          risk_percentage (annual), risk_category, risk_description,
          recommendations, explanation, sex, inputs
        """
        # --- Fuzzy inference (qualitative) ---
        self.sim.input['age'] = float(age)
        self.sim.input['hypertension'] = 1.0 if self._bool(hypertension) else 0.0
        self.sim.input['diabetes'] = 1.0 if self._bool(diabetes) else 0.0
        self.sim.input['heart_failure'] = 1.0 if self._bool(heart_failure) else 0.0
        self.sim.input['prior_stroke_tia'] = 1.0 if self._bool(prior_stroke_tia) else 0.0
        self.sim.compute()
        _fuzzy_percent = float(self.sim.output['stroke_risk'])  # not used for final %; kept for debugging

        # --- Authoritative CHADS2 mapping ---
        score = self.chads2_points(age, hypertension, diabetes, heart_failure, prior_stroke_tia)
        risk_pct = self.chads2_to_annual_risk_pct(score)

        # Interpret & explain
        interp = self.interpret_risk(score, risk_pct)
        explanation = self.generate_explanation(age, hypertension, diabetes, heart_failure,
                                                prior_stroke_tia, score, risk_pct)

        return {
            'risk_percentage': round(risk_pct, 1),  # ANNUAL stroke risk (% per year)
            'risk_category': interp['category'],
            'risk_description': interp['description'],
            'recommendations': interp['recommendations'],
            'explanation': explanation,
            'sex': sex,
            'inputs': {
                'age': age,
                'hypertension': bool(hypertension),
                'diabetes': bool(diabetes),
                'heart_failure': bool(heart_failure),
                'prior_stroke_tia': bool(prior_stroke_tia),
                'chads2_score': score
            }
        }

    # ---------------------------
    # Interpretation & narrative
    # ---------------------------
    def interpret_risk(self, chads2_score: int, annual_pct: float):
        """Category & guidance based on CHADS2 score (classic bins)"""
        if chads2_score == 0:
            category = 'Low Risk'
            desc = f'CHADS₂ score {chads2_score}: estimated annual stroke risk ≈ {annual_pct:.1f}%.'
            recs = [
                'Discuss stroke prevention; consider CHA₂DS₂-VASc for finer stratification.',
                'Optimize blood pressure, glucose, and lifestyle.',
            ]
        elif chads2_score in (1, 2):
            category = 'Moderate Risk'
            desc = f'CHADS₂ score {chads2_score}: estimated annual stroke risk ≈ {annual_pct:.1f}%.'
            recs = [
                'Discuss oral anticoagulation vs bleeding risk (shared decision).',
                'Aggressively manage hypertension/diabetes; lifestyle measures.',
            ]
        else:
            category = 'High Risk'
            desc = f'CHADS₂ score {chads2_score}: estimated annual stroke risk ≈ {annual_pct:.1f}%.'
            recs = [
                'Oral anticoagulation generally recommended unless contraindicated.',
                'Control BP, glucose; address fall/bleed risks; smoking cessation.',
            ]
        return {'category': category, 'description': desc, 'recommendations': recs}

    def generate_explanation(self, age, hypertension, diabetes, heart_failure,
                             prior_stroke_tia, score, annual_pct):
        """Human-readable reasoning"""
        exp = []

        # Components
        if age >= 75:
            exp.append("Age ≥75 years contributes 1 point.")
        else:
            exp.append("Age <75 years contributes 0 points.")

        if heart_failure:
            exp.append("History of heart failure contributes 1 point.")
        if hypertension:
            exp.append("Hypertension contributes 1 point.")
        if diabetes:
            exp.append("Diabetes mellitus contributes 1 point.")
        if prior_stroke_tia:
            exp.append("Prior stroke/TIA contributes 2 points (strongest factor).")

        # Totals
        exp.append(f"CHADS₂ total = {score} → annual stroke risk ≈ {annual_pct:.1f}% based on published estimates.")

        # Context note
        exp.append("Note: Consider using CHA₂DS₂-VASc for contemporary decision-making, especially in low/intermediate CHADS₂ scores.")

        return exp
