"""
Fuzzy Logic Implementation of ASCVD (Pooled Cohort) 10-year Risk
Using scikit-fuzzy for medical decision support systems
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class FuzzyASCVDRisk:
    def __init__(self):
        """Initialize fuzzy logic system for ASCVD Risk (Pooled Cohort style)"""
        self.setup_fuzzy_variables()
        self.setup_membership_functions()
        self.setup_rules()
        self.setup_control_system()

    # ---------------------------
    # Variable & membership setup
    # ---------------------------
    def setup_fuzzy_variables(self):
        """Define fuzzy input and output variables"""
        # Inputs (aligned with ACC/AHA Pooled Cohort Equations core factors)
        # PCE training range is ~40–79 years; we allow a wider fuzzy universe for robustness.
        self.age = ctrl.Antecedent(np.arange(20, 86, 1), 'age')
        self.total_chol = ctrl.Antecedent(np.arange(100, 401, 1), 'total_chol')
        self.hdl = ctrl.Antecedent(np.arange(20, 101, 1), 'hdl')
        self.systolic_bp = ctrl.Antecedent(np.arange(90, 211, 1), 'systolic_bp')

        # Binary-like risk factors (soft edges to handle uncertainty)
        self.smoking_status = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'smoking_status')   # 0=no, 1=yes
        self.diabetes_status = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'diabetes_status') # 0=no, 1=yes
        self.bp_medication = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'bp_medication')     # 0=untreated, 1=treated

        # Optional: race effect (ACC/AHA PCEs are race-specific; here a simple binary proxy)
        self.race_black = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'race_black')           # 0=White/Other, 1=Black

        # Output: 10-year ASCVD risk percentage
        self.ascvd_risk = ctrl.Consequent(np.arange(0, 41, 0.5), 'ascvd_risk')

    def setup_membership_functions(self):
        """Define membership functions for all variables"""

        # Age (PCE 40–79; expanded here)
        self.age['young'] = fuzz.trapmf(self.age.universe, [20, 20, 35, 45])
        self.age['middle_aged'] = fuzz.trimf(self.age.universe, [40, 55, 65])
        self.age['old'] = fuzz.trapmf(self.age.universe, [60, 70, 85, 85])

        # Total Cholesterol (descriptive bins; optimal <200, borderline 200–239, high ≥240)
        self.total_chol['optimal'] = fuzz.trapmf(self.total_chol.universe, [100, 100, 160, 200])
        self.total_chol['borderline'] = fuzz.trimf(self.total_chol.universe, [190, 220, 240])
        self.total_chol['high'] = fuzz.trapmf(self.total_chol.universe, [230, 260, 400, 400])

        # HDL-C (protective ≥60; adverse <40)
        self.hdl['low'] = fuzz.trapmf(self.hdl.universe, [20, 20, 35, 40])
        self.hdl['normal'] = fuzz.trimf(self.hdl.universe, [38, 50, 60])
        self.hdl['high'] = fuzz.trapmf(self.hdl.universe, [58, 65, 100, 100])

        # SBP (treated/untreated is modeled via separate input)
        self.systolic_bp['normal'] = fuzz.trapmf(self.systolic_bp.universe, [90, 90, 110, 120])
        self.systolic_bp['elevated'] = fuzz.trimf(self.systolic_bp.universe, [118, 128, 135])
        self.systolic_bp['high'] = fuzz.trapmf(self.systolic_bp.universe, [130, 140, 210, 210])

        # Binary-ish variables (soften edges for noise)
        for var in (self.smoking_status, self.diabetes_status, self.bp_medication, self.race_black):
            var['no'] = fuzz.trapmf(var.universe, [0.0, 0.0, 0.2, 0.35])
            var['yes'] = fuzz.trapmf(var.universe, [0.65, 0.8, 1.0, 1.0])

        # Output risk buckets (ASCVD thresholds often use ~5%, 7.5%, 20% for decision tiers)
        self.ascvd_risk['very_low']  = fuzz.trapmf(self.ascvd_risk.universe, [0, 0, 2, 5])
        self.ascvd_risk['low']       = fuzz.trimf(self.ascvd_risk.universe, [3, 6, 10])
        self.ascvd_risk['borderline'] = fuzz.trimf(self.ascvd_risk.universe, [7, 8.5, 12.5])  # around 7.5%
        self.ascvd_risk['intermediate'] = fuzz.trimf(self.ascvd_risk.universe, [10, 15, 20])
        self.ascvd_risk['high']      = fuzz.trapmf(self.ascvd_risk.universe, [18, 25, 40, 40])

    # ---------------
    # Rule base
    # ---------------
    def setup_rules(self):
        """Define fuzzy rules guided by ACC/AHA PCE factor roles"""
        R = []

        # Very low risk constellation
        R.append(ctrl.Rule(
            self.age['young'] & self.total_chol['optimal'] & self.hdl['high'] &
            self.systolic_bp['normal'] & self.smoking_status['no'] &
            self.diabetes_status['no'] & self.bp_medication['no'],
            self.ascvd_risk['very_low']
        ))

        # Low risk
        R.append(ctrl.Rule(
            self.age['young'] & self.total_chol['borderline'] & self.hdl['normal'] &
            self.systolic_bp['normal'] & self.smoking_status['no'] &
            self.diabetes_status['no'],
            self.ascvd_risk['low']
        ))
        R.append(ctrl.Rule(
            self.age['middle_aged'] & self.total_chol['optimal'] & self.hdl['high'] &
            self.systolic_bp['normal'] & self.smoking_status['no'] &
            self.diabetes_status['no'],
            self.ascvd_risk['low']
        ))

        # Borderline risk (~around 7.5% clinical threshold)
        R.append(ctrl.Rule(
            self.age['middle_aged'] & self.hdl['normal'] & self.total_chol['borderline'] &
            (self.systolic_bp['elevated'] | self.smoking_status['yes']),
            self.ascvd_risk['borderline']
        ))
        R.append(ctrl.Rule(  # treated BP nudges upward vs untreated at the same SBP
            self.bp_medication['yes'] & self.systolic_bp['elevated'] &
            ~self.diabetes_status['yes'] & ~self.smoking_status['yes'],
            self.ascvd_risk['borderline']
        ))

        # Intermediate risk (multiple moderate burdens or single strong one in older age)
        R.append(ctrl.Rule(
            self.age['middle_aged'] & self.total_chol['borderline'] & self.hdl['low'],
            self.ascvd_risk['intermediate']
        ))
        R.append(ctrl.Rule(
            self.age['old'] & (self.systolic_bp['elevated'] | self.total_chol['borderline']) &
            self.smoking_status['no'] & self.diabetes_status['no'],
            self.ascvd_risk['intermediate']
        ))
        R.append(ctrl.Rule(
            self.bp_medication['yes'] & self.systolic_bp['elevated'] & self.age['middle_aged'],
            self.ascvd_risk['intermediate']
        ))

        # High risk (major burdens stacked; or high SBP esp. if treated; diabetes + smoking)
        R.append(ctrl.Rule(
            self.age['old'] & self.total_chol['high'],
            self.ascvd_risk['high']
        ))
        R.append(ctrl.Rule(
            self.hdl['low'] & (self.smoking_status['yes'] | self.diabetes_status['yes']),
            self.ascvd_risk['high']
        ))
        R.append(ctrl.Rule(
            self.systolic_bp['high'] & (self.bp_medication['yes'] | self.age['old']),
            self.ascvd_risk['high']
        ))
        R.append(ctrl.Rule(
            self.diabetes_status['yes'] & self.smoking_status['yes'],
            self.ascvd_risk['high']
        ))

        # Race effect (PCE are race-specific; here we modestly upshift when adverse factors are present)
        R.append(ctrl.Rule(
            self.race_black['yes'] & (self.systolic_bp['elevated'] | self.total_chol['borderline']) &
            (self.smoking_status['yes'] | self.diabetes_status['yes']),
            self.ascvd_risk['intermediate']
        ))
        R.append(ctrl.Rule(
            self.race_black['yes'] & (self.systolic_bp['high'] | self.total_chol['high']) &
            (self.smoking_status['yes'] | self.diabetes_status['yes'] | self.hdl['low']),
            self.ascvd_risk['high']
        ))

        self.rules = R

    def setup_control_system(self):
        """Create the fuzzy control system"""
        self.risk_ctrl = ctrl.ControlSystem(self.rules)
        self.risk_simulation = ctrl.ControlSystemSimulation(self.risk_ctrl)

    # ---------------------------
    # Helper(s)
    # ---------------------------
    def estimate_hdl(self, chol_total, sex='male'):
        """
        Estimate HDL as a fraction of total cholesterol (heuristic).
        Prefer measured HDL when available.
        """
        # Women tend to have higher HDL on average; use conservative factors.
        factor = 0.27 if sex.lower() == 'female' else 0.22
        return float(np.clip(chol_total * factor, 20, 100))

    # ---------------------------
    # Inference
    # ---------------------------
    def calculate_risk(self, age, sex, total_chol, systolic_bp, smoker, diabetes,
                       on_bp_meds=False, hdl=None, race_black=False):
        """
        Calculate 10-year ASCVD risk using fuzzy logic (PCE-style inputs)

        Parameters
        ----------
        age : int                (20–85; PCE calibrated ~40–79)
        sex : str                'male' or 'female' (affects HDL estimate if HDL missing)
        total_chol : float       mg/dL
        systolic_bp : float      mmHg
        smoker : bool
        diabetes : bool
        on_bp_meds : bool        True if SBP is treated (antihypertensive therapy)
        hdl : float or None      mg/dL (use measured value when possible)
        race_black : bool        True for Black race (PCE race-specific consideration)

        Returns
        -------
        dict: {
          'risk_percentage', 'risk_category', 'risk_description',
          'recommendations', 'explanation', 'sex', 'inputs'
        }
        """
        # Estimate HDL if not provided
        if hdl is None:
            hdl = self.estimate_hdl(total_chol, sex)

        # Provide inputs to fuzzy system
        self.risk_simulation.input['age'] = age
        self.risk_simulation.input['total_chol'] = total_chol
        self.risk_simulation.input['hdl'] = hdl
        self.risk_simulation.input['systolic_bp'] = systolic_bp
        self.risk_simulation.input['smoking_status'] = 1.0 if smoker else 0.0
        self.risk_simulation.input['diabetes_status'] = 1.0 if diabetes else 0.0
        self.risk_simulation.input['bp_medication'] = 1.0 if on_bp_meds else 0.0
        self.risk_simulation.input['race_black'] = 1.0 if race_black else 0.0

        # Compute fuzzy inference
        self.risk_simulation.compute()

        # Extract risk %
        risk_percentage = float(self.risk_simulation.output['ascvd_risk'])

        # Interpret risk and build explanation
        interp = self.interpret_risk(risk_percentage)
        explanation = self.generate_explanation(
            age, sex, total_chol, hdl, systolic_bp, smoker, diabetes, on_bp_meds,
            risk_percentage, race_black
        )

        return {
            'risk_percentage': round(risk_percentage, 1),
            'risk_category': interp['category'],
            'risk_description': interp['description'],
            'recommendations': interp['recommendations'],
            'explanation': explanation,
            'sex': sex,
            'inputs': {
                'age': age,
                'total_cholesterol': total_chol,
                'hdl_cholesterol': hdl,
                'systolic_bp': systolic_bp,
                'smoker': smoker,
                'diabetes': diabetes,
                'on_bp_medication': on_bp_meds,
                'race_black': race_black
            }
        }

    def interpret_risk(self, risk_percentage):
        """
        Map numeric risk to ASCVD-oriented categories (consistent with common ACC/AHA cutoffs)
        ~<5% low, 5–7.4% borderline, 7.5–19.9% intermediate, >=20% high
        """
        if risk_percentage < 5:
            return {
                'category': 'Low Risk',
                'description': 'Estimated 10-year ASCVD risk is low (<5%).',
                'recommendations': [
                    'Maintain healthy lifestyle (diet, activity, sleep).',
                    'Periodic monitoring of BP and lipids.',
                    'Reassess risk at routine visits.'
                ]
            }
        elif risk_percentage < 7.5:
            return {
                'category': 'Borderline Risk',
                'description': 'Estimated 10-year ASCVD risk is borderline (5–7.4%).',
                'recommendations': [
                    'Reinforce lifestyle optimization.',
                    'Consider risk-enhancing factors and coronary calcium if decision uncertain.',
                    'Discuss pros/cons of pharmacotherapy as appropriate.'
                ]
            }
        elif risk_percentage < 20:
            return {
                'category': 'Intermediate Risk',
                'description': 'Estimated 10-year ASCVD risk is intermediate (7.5–19.9%).',
                'recommendations': [
                    'Intensify lifestyle interventions.',
                    'Shared decision-making on statin therapy and BP control.',
                    'Monitor every ~3–6 months until risk factors controlled.'
                ]
            }
        else:
            return {
                'category': 'High Risk',
                'description': 'Estimated 10-year ASCVD risk is high (≥20%).',
                'recommendations': [
                    'Initiate/intensify pharmacotherapy per guidelines (e.g., statins, BP agents).',
                    'Comprehensive lifestyle program and close follow-up (every 1–3 months).',
                    'Address smoking cessation and diabetes management urgently.'
                ]
            }

    def generate_explanation(self, age, sex, total_chol, hdl, systolic_bp,
                             smoker, diabetes, on_bp_meds, risk_percentage, race_black):
        """Create a human-readable explanation of the contributors to ASCVD risk"""
        explanation = []

        # Age
        if age >= 65:
            explanation.append(f"Advanced age ({age}) increases baseline ASCVD risk.")
        elif age >= 45:
            explanation.append(f"Middle age ({age}) moderately increases risk.")
        else:
            explanation.append(f"Younger age ({age}) is protective.")

        # Lipids
        if total_chol >= 240:
            explanation.append(f"High total cholesterol ({total_chol} mg/dL) adds substantial risk.")
        elif total_chol >= 200:
            explanation.append(f"Borderline total cholesterol ({total_chol} mg/dL) adds risk.")
        else:
            explanation.append(f"Optimal total cholesterol ({total_chol} mg/dL) is protective.")

        if hdl < 40:
            explanation.append(f"Low HDL-C ({hdl:.1f} mg/dL) increases risk.")
        elif hdl >= 60:
            explanation.append(f"High HDL-C ({hdl:.1f} mg/dL) is protective.")

        # Blood pressure and treatment
        if systolic_bp >= 140:
            explanation.append(f"High systolic BP ({systolic_bp} mmHg) markedly elevates risk.")
        elif systolic_bp >= 120:
            explanation.append(f"Elevated systolic BP ({systolic_bp} mmHg) contributes to risk.")

        if on_bp_meds:
            explanation.append("Treated hypertension (on BP medication) carries residual risk in PCEs.")

        # Lifestyle/conditions
        if smoker:
            explanation.append("Current smoking substantially increases ASCVD risk.")
        if diabetes:
            explanation.append("Diabetes is a major ASCVD risk factor in the PCE model.")

        # Race effect
        if race_black:
            explanation.append("Race (Black) considered in Pooled Cohort Equations; risk may be higher for similar profiles.")

        explanation.append(f"Combined, these factors yielded a fuzzy-estimated 10-year ASCVD risk of ~{risk_percentage:.1f}%.")

        return explanation
