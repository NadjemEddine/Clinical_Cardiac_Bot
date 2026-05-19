"""
Fuzzy Logic Implementation of QRISK3 10-year CVD Risk
Using scikit-fuzzy for medical decision support systems

Notes:
- Inputs are kept simple to match your DB (booleans for diabetes/smoking, etc.).
- QRISK3-oriented features (TC/HDL ratio, BMI, SBP SD, smoking intensity) are
  estimated inside when not provided.
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class FuzzyQRISK3Risk:
    def __init__(self):
        """Initialize fuzzy logic system for QRISK3 10-year risk"""
        self.setup_fuzzy_variables()
        self.setup_membership_functions()
        self.setup_rules()
        self.setup_control_system()

    # ---------------------------
    # Variables & membership sets
    # ---------------------------
    def setup_fuzzy_variables(self):
        """Define fuzzy input and output variables (QRISK3-style)"""
        # Continuous inputs (QRISK3 typical ranges)
        self.age = ctrl.Antecedent(np.arange(25, 86, 1), 'age')  # QRISK3: 25–84
        self.tc_hdl_ratio = ctrl.Antecedent(np.arange(2.0, 11.1, 0.1), 'tc_hdl_ratio')
        self.systolic_bp = ctrl.Antecedent(np.arange(90, 211, 1), 'systolic_bp')
        self.sbp_sd = ctrl.Antecedent(np.arange(0, 30.5, 0.5), 'sbp_sd')  # SBP variability (SD)
        self.bmi = ctrl.Antecedent(np.arange(16, 51, 0.5), 'bmi')

        # Smoking intensity (QRISK3 has 5 categories)
        # We'll estimate this from simple booleans when needed
        self.smoking_cat = ctrl.Antecedent(np.arange(-0.5, 4.6, 0.1), 'smoking_cat')

        # Binary QRISK3 risk enhancers we can map from your DB (others default False)
        self.diabetes_type = ctrl.Antecedent(np.arange(-0.1, 1.11, 0.01), 'diabetes_type')  # 0=none, ~0.5=T2, 1=T1
        self.ckd = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'ckd')        # CKD stage 3–5
        self.bp_treatment = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'bp_treatment')
        self.prev_stroke = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'prev_stroke')  # from your schema

        # Output: 10-year risk percentage
        self.qrisk3_risk = ctrl.Consequent(np.arange(0, 41, 0.5), 'qrisk3_risk')

    def setup_membership_functions(self):
        """Define membership functions for all variables"""
        # Age
        self.age['young']        = fuzz.trapmf(self.age.universe, [25, 25, 35, 45])
        self.age['middle_aged']  = fuzz.trimf(self.age.universe, [40, 55, 65])
        self.age['old']          = fuzz.trapmf(self.age.universe, [60, 70, 85, 85])

        # TC/HDL ratio
        self.tc_hdl_ratio['good']       = fuzz.trapmf(self.tc_hdl_ratio.universe, [2.0, 2.0, 3.0, 4.0])
        self.tc_hdl_ratio['borderline'] = fuzz.trimf(self.tc_hdl_ratio.universe, [3.5, 4.5, 5.5])
        self.tc_hdl_ratio['high']       = fuzz.trapmf(self.tc_hdl_ratio.universe, [5.0, 6.0, 11.0, 11.0])

        # Systolic BP & variability
        self.systolic_bp['normal']   = fuzz.trapmf(self.systolic_bp.universe, [90, 90, 110, 120])
        self.systolic_bp['elevated'] = fuzz.trimf(self.systolic_bp.universe, [118, 128, 135])
        self.systolic_bp['high']     = fuzz.trapmf(self.systolic_bp.universe, [130, 140, 210, 210])

        self.sbp_sd['stable']   = fuzz.trapmf(self.sbp_sd.universe, [0, 0, 5, 8])
        self.sbp_sd['variable'] = fuzz.trimf(self.sbp_sd.universe, [6, 10, 14])
        self.sbp_sd['labile']   = fuzz.trapmf(self.sbp_sd.universe, [12, 16, 30, 30])

        # BMI
        self.bmi['normal']     = fuzz.trapmf(self.bmi.universe, [16, 16, 20, 25])
        self.bmi['overweight'] = fuzz.trimf(self.bmi.universe, [24, 27, 30])
        self.bmi['obese']      = fuzz.trapmf(self.bmi.universe, [28, 32, 50, 50])

        # Smoking categories (0=non,1=ex,2=light,3=moderate,4=heavy)
        self.smoking_cat['non']      = fuzz.trapmf(self.smoking_cat.universe, [-0.5, -0.5, 0.2, 0.8])
        self.smoking_cat['ex']       = fuzz.trimf(self.smoking_cat.universe, [0.5, 1.0, 1.5])
        self.smoking_cat['light']    = fuzz.trimf(self.smoking_cat.universe, [1.5, 2.0, 2.5])
        self.smoking_cat['moderate'] = fuzz.trimf(self.smoking_cat.universe, [2.5, 3.0, 3.5])
        self.smoking_cat['heavy']    = fuzz.trapmf(self.smoking_cat.universe, [3.4, 3.8, 4.6, 4.6])

        # Diabetes type
        self.diabetes_type['none']  = fuzz.trapmf(self.diabetes_type.universe, [-0.1, -0.1, 0.1, 0.3])
        self.diabetes_type['type2'] = fuzz.trimf(self.diabetes_type.universe, [0.35, 0.5, 0.65])
        self.diabetes_type['type1'] = fuzz.trapmf(self.diabetes_type.universe, [0.7, 0.85, 1.1, 1.1])

        # Binary-ish (soft edges) for enhancers
        for v in (self.ckd, self.bp_treatment, self.prev_stroke):
            v['no']  = fuzz.trapmf(v.universe, [0.0, 0.0, 0.2, 0.35])
            v['yes'] = fuzz.trapmf(v.universe, [0.65, 0.8, 1.0, 1.0])

        # Output risk buckets (NICE flags around 10%, 20%)
        self.qrisk3_risk['very_low']    = fuzz.trapmf(self.qrisk3_risk.universe, [0, 0, 2, 5])
        self.qrisk3_risk['low']         = fuzz.trimf(self.qrisk3_risk.universe, [3, 7, 10])
        self.qrisk3_risk['borderline']  = fuzz.trimf(self.qrisk3_risk.universe, [7, 9, 12])
        self.qrisk3_risk['intermediate']= fuzz.trimf(self.qrisk3_risk.universe, [10, 15, 20])
        self.qrisk3_risk['high']        = fuzz.trapmf(self.qrisk3_risk.universe, [18, 25, 40, 40])

    # ---------------
    # Rule base
    # ---------------
    def setup_rules(self):
        """Define fuzzy rules grounded in QRISK3 factor roles"""
        R = []

        # Protective constellation
        R.append(ctrl.Rule(
            self.age['young'] & self.tc_hdl_ratio['good'] & self.systolic_bp['normal'] &
            self.sbp_sd['stable'] & self.bmi['normal'] & self.smoking_cat['non'] &
            self.diabetes_type['none'] & self.bp_treatment['no'] & self.ckd['no'],
            self.qrisk3_risk['very_low']
        ))

        # Low risk
        R.append(ctrl.Rule(
            self.age['middle_aged'] & self.tc_hdl_ratio['good'] & self.systolic_bp['normal'] &
            (self.smoking_cat['ex'] | self.smoking_cat['light']) & self.diabetes_type['none'],
            self.qrisk3_risk['low']
        ))

        # Borderline (around NICE 10% threshold)
        R.append(ctrl.Rule(
            self.age['middle_aged'] & self.tc_hdl_ratio['borderline'] &
            (self.systolic_bp['elevated'] | self.bmi['overweight'] | self.smoking_cat['moderate']),
            self.qrisk3_risk['borderline']
        ))
        R.append(ctrl.Rule(
            self.bp_treatment['yes'] & self.systolic_bp['elevated'] & self.sbp_sd['variable'],
            self.qrisk3_risk['borderline']
        ))

        # Intermediate (multiple moderate burdens or single strong one in older age)
        R.append(ctrl.Rule(
            self.age['old'] & (self.systolic_bp['elevated'] | self.tc_hdl_ratio['borderline']),
            self.qrisk3_risk['intermediate']
        ))
        R.append(ctrl.Rule(
            self.bmi['obese'] & (self.smoking_cat['ex'] | self.smoking_cat['light']),
            self.qrisk3_risk['intermediate']
        ))
        R.append(ctrl.Rule(
            self.sbp_sd['labile'] & (self.bp_treatment['yes'] | self.age['old']),
            self.qrisk3_risk['intermediate']
        ))

        # High risk (stacked adverse factors; CKD; very high BP; diabetes)
        R.append(ctrl.Rule(
            self.ckd['yes'] | self.prev_stroke['yes'],
            self.qrisk3_risk['high']
        ))
        R.append(ctrl.Rule(
            self.diabetes_type['type1'] |
            (self.diabetes_type['type2'] & (self.tc_hdl_ratio['high'] | self.systolic_bp['high'])),
            self.qrisk3_risk['high']
        ))
        R.append(ctrl.Rule(
            (self.smoking_cat['heavy'] | self.systolic_bp['high']) &
            (self.tc_hdl_ratio['high'] | self.bmi['obese']),
            self.qrisk3_risk['high']
        ))

        self.rules = R

    def setup_control_system(self):
        """Create the fuzzy control system"""
        self.risk_ctrl = ctrl.ControlSystem(self.rules)
        self.risk_simulation = ctrl.ControlSystemSimulation(self.risk_ctrl)

    # ---------------------------
    # Estimators (internal use)
    # ---------------------------
    def estimate_hdl(self, total_chol, sex='male'):
        """Estimate HDL from total cholesterol (heuristic); prefer measured HDL if available."""
        if total_chol is None:
            return None
        factor = 0.27 if str(sex).lower() == 'female' else 0.22
        return float(np.clip(total_chol * factor, 20, 100))

    def estimate_tc_hdl_ratio(self, total_chol=None, hdl=None):
        """Compute/estimate TC/HDL ratio; fall back to conservative population mean (~4.8)."""
        if total_chol and hdl and hdl > 0:
            return float(np.clip(total_chol / hdl, 2.0, 11.0))
        return 4.8

    def estimate_bmi(self, weight_kg=None, height_cm=None):
        """BMI from kg/cm; returns None if insufficient data."""
        if not weight_kg or not height_cm or height_cm <= 0:
            return None
        h_m = height_cm / 100.0
        return round(weight_kg / (h_m * h_m), 1)

    def estimate_sbp_sd(self, recent_sbps=None, default_sd=6.0):
        """
        Estimate SBP variability (SD). If only one value is available, use a mild default (≈6 mmHg),
        consistent with QRISK3’s inclusion of BP variability as an added signal. :contentReference[oaicite:1]{index=1}
        """
        if recent_sbps:
            return recent_sbps
        else: 
            return default_sd

    def map_smoking_bool_to_category(self, smoker=False, e_cigarette=False):
        """
        Map simple booleans -> 5-level smoking category for QRISK3:
        0=non, 1=ex, 2=light, 3=moderate, 4=heavy.
        """
        if not smoker and not e_cigarette:
            return 0
        if not smoker and e_cigarette:
            return 1
        if smoker and not e_cigarette:
            return 3
        return 4  # smoker + e-cig

    def map_diabetes_bool_to_type(self, diabetes=False):
        """Your DB has a single boolean; default assumption: Type 2 if True (adult primary care)."""
        return 'type2' if diabetes else 'none'

    # ---------------------------
    # Inference API (same schema)
    # ---------------------------
    def calculate_risk(self,
                       age, sex,
                       total_chol=None, systolic_bp=None,
                       smoker=False, diabetes=False, on_bp_meds=False,
                       hdl=None, weight=None, height=None,
                       kidney_disease=False, previous_stroke=False,
                       e_cigarette=False,
                       tc_hdl_ratio=None, sbp_sd=None, smoking_category=None,
                       recent_sbps=None):
        """
        Calculate QRISK3-like 10-year CVD risk using fuzzy logic.

        Accepts simple inputs from your DB; estimates missing QRISK3 parameters internally.
        Returns:
          dict with keys:
            risk_percentage, risk_category, risk_description, recommendations, explanation, sex, inputs
        """
        # --- Estimate missing QRISK3 features ---
        if hdl is None:
            hdl = self.estimate_hdl(total_chol, sex)
        if tc_hdl_ratio is None:
            tc_hdl_ratio = self.estimate_tc_hdl_ratio(total_chol, hdl)
        if sbp_sd is None:
            sbp_sd = self.estimate_sbp_sd(recent_sbps or ([systolic_bp] if systolic_bp else None))
        bmi = self.estimate_bmi(weight, height)
        if bmi is None:
            bmi = 27.0  # gentle default

        if smoking_category is None:
            smoking_category = self.map_smoking_bool_to_category(smoker, e_cigarette)
        diab_type = self.map_diabetes_bool_to_type(diabetes)
        diab_code = {'none': 0.0, 'type2': 0.5, 'type1': 1.0}.get(diab_type, 0.0)

        # --- Feed inputs to fuzzy system ---
        self.risk_simulation.input['age'] = age
        self.risk_simulation.input['tc_hdl_ratio'] = float(tc_hdl_ratio)
        self.risk_simulation.input['systolic_bp'] = float(systolic_bp or 120.0)
        self.risk_simulation.input['sbp_sd'] = float(sbp_sd)
        self.risk_simulation.input['bmi'] = float(bmi)
        self.risk_simulation.input['smoking_cat'] = float(smoking_category)
        self.risk_simulation.input['diabetes_type'] = float(diab_code)
        self.risk_simulation.input['bp_treatment'] = 1.0 if on_bp_meds else 0.0
        self.risk_simulation.input['ckd'] = 1.0 if kidney_disease else 0.0
        self.risk_simulation.input['prev_stroke'] = 1.0 if previous_stroke else 0.0

        # --- Compute inference ---
        self.risk_simulation.compute()
        risk_percentage = float(self.risk_simulation.output['qrisk3_risk'])

        # --- Interpret & explain ---
        interp = self.interpret_risk(risk_percentage)
        explanation = self.generate_explanation(
            age, sex, tc_hdl_ratio, systolic_bp or 120.0, sbp_sd, bmi,
            smoking_category, diab_type, on_bp_meds, kidney_disease, previous_stroke,
            risk_percentage, total_chol=total_chol, hdl=hdl
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
                'tc_hdl_ratio': tc_hdl_ratio,
                'systolic_bp': systolic_bp,
                'sbp_sd': sbp_sd,
                'bmi': bmi,
                'smoker': smoker,
                'e_cigarette': e_cigarette,
                'diabetes_type': diab_type,
                'on_bp_medication': on_bp_meds,
                'kidney_disease': kidney_disease,
                'previous_stroke': previous_stroke,
            }
        }

    # ---------------------------
    # Output interpretation
    # ---------------------------
    def interpret_risk(self, risk_percentage):
        """Map numeric risk to categories & recommendations (NICE often flags ≥10%, ≥20%)."""
        if risk_percentage < 5:
            return {
                'category': 'Low Risk',
                'description': 'Estimated 10-year CVD risk is low (<5%).',
                'recommendations': [
                    'Maintain healthy lifestyle (diet, activity, sleep).',
                    'Periodic BP and lipid checks.',
                    'Reassess risk routinely (e.g., every 3–5 years).'
                ]
            }
        elif risk_percentage < 10:
            return {
                'category': 'Borderline Risk',
                'description': 'Estimated 10-year CVD risk is borderline (5–9.9%).',
                'recommendations': [
                    'Optimize lifestyle and weight.',
                    'Address smoking and BP control as needed.',
                    'Consider additional risk enhancers (e.g., CKD, SBP variability) in decisions.'
                ]
            }
        elif risk_percentage < 20:
            return {
                'category': 'Intermediate Risk',
                'description': 'Estimated 10-year CVD risk is intermediate (10–19.9%).',
                'recommendations': [
                    'Intensify lifestyle interventions.',
                    'Discuss statin therapy and BP targets per guidance.',
                    'Follow-up every 3–6 months until control achieved.'
                ]
            }
        else:
            return {
                'category': 'High Risk',
                'description': 'Estimated 10-year CVD risk is high (≥20%).',
                'recommendations': [
                    'Initiate/intensify pharmacotherapy (lipids/BP) per national guidance.',
                    'Strong smoking cessation support and comprehensive lifestyle plan.',
                    'Close follow-up (1–3 months) and manage secondary causes.'
                ]
            }

    def generate_explanation(self, age, sex, tc_hdl_ratio, systolic_bp, sbp_sd, bmi,
                             smoking_category, diabetes_type, on_bp_meds,
                             kidney_disease, previous_stroke,
                             risk_percentage, total_chol=None, hdl=None):
        """Create a human-readable explanation of contributors to risk."""
        exp = []

        # Age
        if age >= 65:
            exp.append(f"Advanced age ({age}) increases baseline CVD risk in QRISK3.")
        elif age >= 45:
            exp.append(f"Middle age ({age}) moderately increases risk.")
        else:
            exp.append(f"Younger age ({age}) is protective.")

        # Lipids via ratio (and optional HDL echo)
        if tc_hdl_ratio >= 6:
            exp.append(f"High TC/HDL ratio ({tc_hdl_ratio:.1f}) is adverse.")
        elif tc_hdl_ratio <= 4:
            exp.append(f"Favorable TC/HDL ratio ({tc_hdl_ratio:.1f}) is protective.")
        if hdl is not None:
            if hdl >= 60:
                exp.append(f"HDL-C {hdl:.0f} mg/dL is protective.")
            elif hdl < 40:
                exp.append(f"Low HDL-C {hdl:.0f} mg/dL increases risk.")

        # Blood pressure level & variability
        if systolic_bp >= 140:
            exp.append(f"High systolic BP ({systolic_bp} mmHg) markedly elevates risk.")
        elif systolic_bp >= 120:
            exp.append(f"Elevated systolic BP ({systolic_bp} mmHg) adds risk.")
        if on_bp_meds:
            exp.append("Being on BP treatment indicates treated hypertension.")
        if sbp_sd >= 12:
            exp.append(f"SBP variability (SD {sbp_sd:.1f} mmHg) is an added QRISK3 risk factor.")

        # BMI
        if bmi >= 30:
            exp.append(f"Obesity (BMI {bmi:.1f}) increases risk.")
        elif bmi >= 25:
            exp.append(f"Overweight (BMI {bmi:.1f}) modestly increases risk.")

        # Smoking category label
        cat_map = {0: "non-smoker", 1: "ex-smoker", 2: "light", 3: "moderate", 4: "heavy"}
        exp.append(f"Smoking exposure: {cat_map.get(int(round(smoking_category)), 'unknown')}.")

        # Conditions
        if diabetes_type == 'type1':
            exp.append("Type 1 diabetes is a major QRISK3 risk factor.")
        elif diabetes_type == 'type2':
            exp.append("Type 2 diabetes increases risk.")
        if kidney_disease:
            exp.append("Chronic kidney disease (stage 3–5) elevates risk.")
        if previous_stroke:
            exp.append("History of stroke/TIA strongly elevates risk signal.")

        # Summary
        exp.append(f"Combined, these factors yielded a fuzzy-estimated 10-year QRISK3 risk of ~{risk_percentage:.1f}%.")

        return exp
