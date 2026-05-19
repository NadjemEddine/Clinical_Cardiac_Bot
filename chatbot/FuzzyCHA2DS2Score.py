"""
CHA2DS2-VASc Stroke Risk (AF) — fixed: remove unused sex_female input to avoid
'Unexpected input' error from scikit-fuzzy. Sex is still used for scoring/thresholds.
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class FuzzyCHA2DS2VAScRisk:
    def __init__(self):
        self.setup_fuzzy_variables()
        self.setup_membership_functions()
        self.setup_rules()
        self.setup_control_system()

        # Annual stroke risk (%) table (approximate, cohort-dependent)
        self._score_to_risk_pct = {
            0: 0.2, 1: 0.6, 2: 2.2, 3: 3.2, 4: 4.8,
            5: 7.2, 6: 9.7, 7: 11.2, 8: 10.8, 9: 12.2,
        }

    # ---------------------------
    # Fuzzy setup
    # ---------------------------
    def setup_fuzzy_variables(self):
        """Define fuzzy inputs and output (sex omitted from fuzzy layer)"""
        self.age = ctrl.Antecedent(np.arange(18, 101, 1), 'age')
        self.heart_failure = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'heart_failure')
        self.hypertension  = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'hypertension')
        self.diabetes      = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'diabetes')
        self.stroke_tia_te = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'stroke_tia_te')
        self.vascular_dx   = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'vascular_dx')

        self.stroke_risk   = ctrl.Consequent(np.arange(0, 16.1, 0.1), 'stroke_risk')

    def setup_membership_functions(self):
        self.age['lt65']   = fuzz.trapmf(self.age.universe, [18, 18, 55, 65])
        self.age['65to74'] = fuzz.trimf(self.age.universe, [63, 69, 75])
        self.age['ge75']   = fuzz.trapmf(self.age.universe, [72, 75, 100, 100])

        for v in (self.heart_failure, self.hypertension, self.diabetes,
                  self.stroke_tia_te, self.vascular_dx):
            v['no']  = fuzz.trapmf(v.universe, [0.0, 0.0, 0.2, 0.35])
            v['yes'] = fuzz.trapmf(v.universe, [0.65, 0.8, 1.0, 1.0])

        self.stroke_risk['very_low']  = fuzz.trapmf(self.stroke_risk.universe, [0, 0, 0.5, 1.0])
        self.stroke_risk['low']       = fuzz.trimf(self.stroke_risk.universe, [0.8, 1.5, 3.0])
        self.stroke_risk['moderate']  = fuzz.trimf(self.stroke_risk.universe, [2.0, 4.0, 6.0])
        self.stroke_risk['high']      = fuzz.trimf(self.stroke_risk.universe, [5.0, 8.0, 12.0])
        self.stroke_risk['very_high'] = fuzz.trapmf(self.stroke_risk.universe, [10.0, 12.0, 16.0, 16.0])

    def setup_rules(self):
        R = []
        # Prior stroke/TIA/TE (2 points) -> very high baseline
        R.append(ctrl.Rule(self.stroke_tia_te['yes'], self.stroke_risk['very_high']))

        # Age ≥75 alone -> moderate; escalates with any other factor
        R.append(ctrl.Rule(self.age['ge75'] & self.stroke_tia_te['no'], self.stroke_risk['moderate']))
        R.append(ctrl.Rule(self.age['ge75'] &
                           (self.hypertension['yes'] | self.diabetes['yes'] |
                            self.heart_failure['yes'] | self.vascular_dx['yes']) &
                           self.stroke_tia_te['no'], self.stroke_risk['high']))

        # Age 65–74 + any single non-stroke factor -> moderate
        R.append(ctrl.Rule(self.age['65to74'] &
                           (self.hypertension['yes'] | self.diabetes['yes'] |
                            self.heart_failure['yes'] | self.vascular_dx['yes']) &
                           self.stroke_tia_te['no'], self.stroke_risk['moderate']))

        # Any two non-stroke factors -> moderate
        R.append(ctrl.Rule(
            ((self.hypertension['yes'] & self.diabetes['yes']) |
             (self.hypertension['yes'] & self.heart_failure['yes']) |
             (self.hypertension['yes'] & self.vascular_dx['yes']) |
             (self.diabetes['yes'] & self.heart_failure['yes']) |
             (self.diabetes['yes'] & self.vascular_dx['yes']) |
             (self.heart_failure['yes'] & self.vascular_dx['yes'])) &
            self.stroke_tia_te['no'],
            self.stroke_risk['moderate']
        ))

        # Otherwise very low (esp. <65 with no factors)
        R.append(ctrl.Rule(self.age['lt65'] &
                           ~(self.hypertension['yes'] | self.diabetes['yes'] |
                             self.heart_failure['yes'] | self.vascular_dx['yes']) &
                           self.stroke_tia_te['no'], self.stroke_risk['very_low']))
        self.rules = R

    def setup_control_system(self):
        self.ctrl_sys = ctrl.ControlSystem(self.rules)
        self.sim = ctrl.ControlSystemSimulation(self.ctrl_sys)

    # ---------------------------
    # Helpers
    # ---------------------------
    def _bool(self, x) -> bool:
        return bool(x)

    def cha2ds2vasc_points(self, age, sex, heart_failure, hypertension, diabetes,
                            stroke_tia_te, vascular_disease) -> int:
        """Exact CHA2DS2-VASc points; sex point applies to FEMALE only."""
        score = 0
        if self._bool(heart_failure): score += 1
        if self._bool(hypertension):  score += 1
        if age is not None and age >= 75: score += 2
        elif age is not None and 65 <= age <= 74: score += 1
        if self._bool(diabetes):      score += 1
        if self._bool(stroke_tia_te): score += 2
        if self._bool(vascular_disease): score += 1
        if str(sex).lower() == 'female': score += 1
        return int(max(0, min(9, score)))

    def score_to_annual_risk_pct(self, score: int) -> float:
        return float(self._score_to_risk_pct.get(score, 12.2 if score >= 9 else 0.2))

    # ---------------------------
    # Main API (same structure)
    # ---------------------------
    def calculate_risk(self, age, sex,
                       hypertension=False, diabetes=False, heart_failure=False,
                       stroke_tia_te=False, vascular_disease=False):
        """
        Compute CHA2DS2-VASc ANNUAL stroke risk (%).
        sex: 'male' | 'female'
        """
        # Fuzzy (qualitative only; sex not part of fuzzy layer)
        self.sim.input['age'] = float(age)
        self.sim.input['hypertension']  = 1.0 if self._bool(hypertension) else 0.0
        self.sim.input['diabetes']      = 1.0 if self._bool(diabetes) else 0.0
        self.sim.input['heart_failure'] = 1.0 if self._bool(heart_failure) else 0.0
        self.sim.input['stroke_tia_te'] = 1.0 if self._bool(stroke_tia_te) else 0.0
        self.sim.input['vascular_dx']   = 1.0 if self._bool(vascular_disease) else 0.0
        self.sim.compute()
        _ = float(self.sim.output['stroke_risk'])  # debug-only

        # Authoritative mapping
        score = self.cha2ds2vasc_points(age, sex, heart_failure, hypertension,
                                        diabetes, stroke_tia_te, vascular_disease)
        risk_pct = self.score_to_annual_risk_pct(score)

        # Interpretation (sex-specific thresholds)
        interp = self.interpret_risk(score, risk_pct, sex)
        explanation = self.generate_explanation(
            age, sex, hypertension, diabetes, heart_failure,
            stroke_tia_te, vascular_disease, score, risk_pct
        )

        return {
            'risk_percentage': round(risk_pct, 1),  # annual stroke risk
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
                'stroke_tia_te': bool(stroke_tia_te),
                'vascular_disease': bool(vascular_disease),
                'cha2ds2vasc_score': score
            }
        }

    # ---------------------------
    # Interpretation & narrative
    # ---------------------------
    def interpret_risk(self, score: int, annual_pct: float, sex: str):
        """
        Common thresholds:
          - Men: consider OAC at 1; recommend at >=2
          - Women: sex-only (1) is NOT an indication; consider at 2; recommend at >=3
        """
        s = str(sex).lower()
        if (s == 'male' and score == 0) or (s == 'female' and score == 1):
            category = 'Low Risk'
            recs = [
                'No routine oral anticoagulation (OAC) if no additional risk factors.',
                'Reassess periodically; manage BP/DM and lifestyle.'
            ]
        elif (s == 'male' and score == 1) or (s == 'female' and score == 2):
            category = 'Intermediate Risk'
            recs = [
                'Consider OAC after shared decision-making (weigh bleeding risk).',
                'Optimize BP, diabetes control, and lifestyle; address smoking.'
            ]
        else:
            category = 'High Risk'
            recs = [
                'Oral anticoagulation generally recommended unless contraindicated.',
                'Control BP/DM, treat vascular disease, and mitigate fall/bleed risks.'
            ]
        desc = f'CHA₂DS₂-VASc score {score}: estimated annual stroke risk ≈ {annual_pct:.1f}%.'
        return {'category': category, 'description': desc, 'recommendations': recs}

    def generate_explanation(self, age, sex, hypertension, diabetes,
                             heart_failure, stroke_tia_te, vascular_disease,
                             score, annual_pct):
        exp = []
        if age >= 75:          exp.append("Age ≥75 years contributes 2 points.")
        elif 65 <= age <= 74:  exp.append("Age 65–74 years contributes 1 point.")
        else:                  exp.append("Age <65 years contributes 0 points.")
        if heart_failure:      exp.append("Congestive heart failure/LV dysfunction contributes 1 point.")
        if hypertension:       exp.append("Hypertension contributes 1 point.")
        if diabetes:           exp.append("Diabetes mellitus contributes 1 point.")
        if vascular_disease:   exp.append("Vascular disease (MI/PAD/aortic plaque) contributes 1 point.")
        if stroke_tia_te:      exp.append("Prior stroke/TIA/thromboembolism contributes 2 points (dominant factor).")
        if str(sex).lower() == 'female':
            exp.append("Female sex contributes 1 point (sex-alone is not an OAC indication).")
        exp.append(f"CHA₂DS₂-VASc total = {score} → annual stroke risk ≈ {annual_pct:.1f}% (cohort-dependent).")
        return exp
