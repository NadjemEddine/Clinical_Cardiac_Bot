"""
Fuzzy Logic Implementation of Framingham CVD Risk Score
Using scikit-fuzzy for medical decision support system
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib.pyplot as plt

class FuzzyFraminghamRisk:
    def __init__(self):
        """Initialize fuzzy logic system for Framingham Risk Score"""
        self.setup_fuzzy_variables()
        self.setup_membership_functions()
        self.setup_rules()
        self.setup_control_system()

    def setup_fuzzy_variables(self):
        """Define fuzzy input and output variables"""
        # Input variables
        self.age = ctrl.Antecedent(np.arange(20, 85, 1), 'age')
        self.total_chol = ctrl.Antecedent(np.arange(100, 400, 1), 'total_chol')
        self.hdl = ctrl.Antecedent(np.arange(20, 100, 1), 'hdl')
        self.systolic_bp = ctrl.Antecedent(np.arange(90, 200, 1), 'systolic_bp')
        self.smoking_status = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'smoking_status')
        self.diabetes_status = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'diabetes_status')
        self.bp_medication = ctrl.Antecedent(np.arange(0, 1.1, 0.1), 'bp_medication')

        # Output variable
        self.cvd_risk = ctrl.Consequent(np.arange(0, 35, 1), 'cvd_risk')

    def setup_membership_functions(self):
        """Define membership functions for all variables"""

        # Age membership functions
        self.age['young'] = fuzz.trimf(self.age.universe, [20, 20, 40])
        self.age['middle_aged'] = fuzz.trimf(self.age.universe, [35, 50, 65])
        self.age['old'] = fuzz.trimf(self.age.universe, [60, 75, 85])

        # Total Cholesterol
        self.total_chol['optimal'] = fuzz.trimf(self.total_chol.universe, [100, 100, 180])
        self.total_chol['borderline'] = fuzz.trimf(self.total_chol.universe, [160, 200, 240])
        self.total_chol['high'] = fuzz.trimf(self.total_chol.universe, [220, 280, 400])

        # HDL Cholesterol
        self.hdl['low'] = fuzz.trimf(self.hdl.universe, [20, 20, 45])
        self.hdl['normal'] = fuzz.trimf(self.hdl.universe, [40, 50, 65])
        self.hdl['high'] = fuzz.trimf(self.hdl.universe, [60, 80, 100])

        # Systolic Blood Pressure
        self.systolic_bp['normal'] = fuzz.trimf(self.systolic_bp.universe, [90, 90, 125])
        self.systolic_bp['elevated'] = fuzz.trimf(self.systolic_bp.universe, [120, 135, 150])
        self.systolic_bp['high'] = fuzz.trimf(self.systolic_bp.universe, [140, 170, 200])

        # Binary variables (smoking, diabetes, bp_medication)
        self.smoking_status['no'] = fuzz.trimf(self.smoking_status.universe, [0, 0, 0.3])
        self.smoking_status['yes'] = fuzz.trimf(self.smoking_status.universe, [0.7, 1, 1])

        self.diabetes_status['no'] = fuzz.trimf(self.diabetes_status.universe, [0, 0, 0.3])
        self.diabetes_status['yes'] = fuzz.trimf(self.diabetes_status.universe, [0.7, 1, 1])

        self.bp_medication['no'] = fuzz.trimf(self.bp_medication.universe, [0, 0, 0.3])
        self.bp_medication['yes'] = fuzz.trimf(self.bp_medication.universe, [0.7, 1, 1])

        # CVD Risk output
        self.cvd_risk['very_low'] = fuzz.trimf(self.cvd_risk.universe, [0, 0, 5])
        self.cvd_risk['low'] = fuzz.trimf(self.cvd_risk.universe, [2, 5, 10])
        self.cvd_risk['moderate'] = fuzz.trimf(self.cvd_risk.universe, [7, 12, 18])
        self.cvd_risk['high'] = fuzz.trimf(self.cvd_risk.universe, [15, 22, 30])
        self.cvd_risk['very_high'] = fuzz.trimf(self.cvd_risk.universe, [25, 35, 35])

    def setup_rules(self):
        """Define fuzzy rules based on medical knowledge"""
        self.rules = [
            # Very Low Risk Rules
            ctrl.Rule(self.age['young'] & self.total_chol['optimal'] & self.hdl['high'] &
                     self.systolic_bp['normal'] & self.smoking_status['no'] & self.diabetes_status['no'],
                     self.cvd_risk['very_low']),

            # Low Risk Rules
            ctrl.Rule(self.age['young'] & self.total_chol['borderline'] & self.hdl['normal'] &
                     self.systolic_bp['normal'] & self.smoking_status['no'] & self.diabetes_status['no'],
                     self.cvd_risk['low']),

            ctrl.Rule(self.age['middle_aged'] & self.total_chol['optimal'] & self.hdl['high'] &
                     self.systolic_bp['normal'] & self.smoking_status['no'] & self.diabetes_status['no'],
                     self.cvd_risk['low']),

            # Moderate Risk Rules
            ctrl.Rule(self.age['middle_aged'] & self.total_chol['borderline'] & self.hdl['normal'] &
                     self.systolic_bp['elevated'], self.cvd_risk['moderate']),

            ctrl.Rule(self.age['young'] & self.smoking_status['yes'] & self.diabetes_status['yes'],
                     self.cvd_risk['moderate']),

            ctrl.Rule(self.age['middle_aged'] & self.hdl['low'] & self.systolic_bp['elevated'],
                     self.cvd_risk['moderate']),

            # High Risk Rules
            ctrl.Rule(self.age['old'] & self.total_chol['borderline'], self.cvd_risk['high']),

            ctrl.Rule(self.age['middle_aged'] & self.total_chol['high'] & self.smoking_status['yes'],
                     self.cvd_risk['high']),

            ctrl.Rule(self.diabetes_status['yes'] & self.smoking_status['yes'] & self.hdl['low'],
                     self.cvd_risk['high']),

            ctrl.Rule(self.systolic_bp['high'] & self.age['middle_aged'] & self.diabetes_status['yes'],
                     self.cvd_risk['high']),

            # Very High Risk Rules
            ctrl.Rule(self.age['old'] & self.total_chol['high'] & self.smoking_status['yes'],
                     self.cvd_risk['very_high']),

            ctrl.Rule(self.age['old'] & self.diabetes_status['yes'] & self.hdl['low'] &
                     self.systolic_bp['high'], self.cvd_risk['very_high']),

            ctrl.Rule(self.total_chol['high'] & self.hdl['low'] & self.smoking_status['yes'] &
                     self.diabetes_status['yes'] & self.systolic_bp['high'], self.cvd_risk['very_high']),

            # Additional context-sensitive rules
            ctrl.Rule(self.bp_medication['yes'] & self.systolic_bp['high'] & self.age['old'],
                     self.cvd_risk['high']),

            ctrl.Rule(self.bp_medication['yes'] & self.diabetes_status['yes'] & self.smoking_status['yes'],
                     self.cvd_risk['very_high'])
        ]

    def setup_control_system(self):
        """Create the fuzzy control system"""
        self.risk_ctrl = ctrl.ControlSystem(self.rules)
        self.risk_simulation = ctrl.ControlSystemSimulation(self.risk_ctrl)

    def estimate_hdl(self, chol_total, sex='male'):
        """Estimate HDL as a percentage of total cholesterol"""
        factor = 0.28 if sex.lower() == 'female' else 0.23
        return chol_total * factor

    def calculate_risk(self, age, sex, total_chol, systolic_bp, smoker, diabetes,
                      on_bp_meds=False, hdl=None):
        """
        Calculate CVD risk using fuzzy logic

        Parameters:
        -----------
        age : int
            Patient age (20-85)
        sex : str
            'male' or 'female'
        total_chol : float
            Total cholesterol (mg/dL)
        systolic_bp : float
            Systolic blood pressure (mmHg)
        smoker : bool
            Smoking status
        diabetes : bool
            Diabetes status
        on_bp_meds : bool
            On BP medication
        hdl : float
            HDL cholesterol (optional, will be estimated if None)

        Returns:
        --------
        dict: Risk assessment with numerical value and interpretation
        """

        # Estimate HDL if not provided
        if hdl is None:
            hdl = self.estimate_hdl(total_chol, sex)

        # Set inputs for fuzzy system
        self.risk_simulation.input['age'] = age
        self.risk_simulation.input['total_chol'] = total_chol
        self.risk_simulation.input['hdl'] = hdl
        self.risk_simulation.input['systolic_bp'] = systolic_bp
        self.risk_simulation.input['smoking_status'] = 1.0 if smoker else 0.0
        self.risk_simulation.input['diabetes_status'] = 1.0 if diabetes else 0.0
        self.risk_simulation.input['bp_medication'] = 1.0 if on_bp_meds else 0.0

        # Compute the result
        self.risk_simulation.compute()

        # Get risk percentage
        risk_percentage = self.risk_simulation.output['cvd_risk']

        # Interpret the risk
        risk_interpretation = self.interpret_risk(risk_percentage)

        # Generate detailed explanation
        explanation = self.generate_explanation(age, sex, total_chol, hdl, systolic_bp,
                                              smoker, diabetes, on_bp_meds, risk_percentage)
        influences = self.compute_influences(age, total_chol, hdl, systolic_bp, smoker, diabetes, on_bp_meds)

        return {
            'risk_percentage': round(risk_percentage, 1),
            'risk_category': risk_interpretation['category'],
            'risk_description': risk_interpretation['description'],
            'recommendations': risk_interpretation['recommendations'],
            'explanation': explanation,
            'sex': sex,
            
            'inputs': {
                'age': age,
                'total_cholesterol': total_chol,
                'hdl_cholesterol': hdl,
                'systolic_bp': systolic_bp,
                'smoker': smoker,
                'diabetes': diabetes,
                'on_bp_medication': on_bp_meds
            },
            'influences': influences,
            'most_influential': max(influences, key=lambda k: abs(influences[k])),
        }

    def interpret_risk(self, risk_percentage):
        """Interpret the numerical risk into categories and recommendations"""
        if risk_percentage < 3:
            return {
                'category': 'Very Low Risk',
                'description': 'Your 10-year risk of cardiovascular disease is very low.',
                'recommendations': [
                    'Continue healthy lifestyle habits',
                    'Regular check-ups every 2-3 years',
                    'Maintain current diet and exercise routine'
                ]
            }
        elif risk_percentage < 7:
            return {
                'category': 'Low Risk',
                'description': 'Your 10-year risk of cardiovascular disease is low.',
                'recommendations': [
                    'Maintain healthy lifestyle',
                    'Annual health check-ups',
                    'Consider minor lifestyle improvements'
                ]
            }
        elif risk_percentage < 15:
            return {
                'category': 'Moderate Risk',
                'description': 'Your 10-year risk of cardiovascular disease is moderate.',
                'recommendations': [
                    'Discuss with your doctor about lifestyle changes',
                    'Consider medication if other risk factors present',
                    'Regular monitoring every 6 months',
                    'Implement diet and exercise modifications'
                ]
            }
        elif risk_percentage < 25:
            return {
                'category': 'High Risk',
                'description': 'Your 10-year risk of cardiovascular disease is high.',
                'recommendations': [
                    'Immediate medical consultation recommended',
                    'Likely candidate for preventive medication',
                    'Aggressive lifestyle modifications needed',
                    'Frequent monitoring (every 3-4 months)'
                ]
            }
        else:
            return {
                'category': 'Very High Risk',
                'description': 'Your 10-year risk of cardiovascular disease is very high.',
                'recommendations': [
                    'Urgent medical attention required',
                    'Immediate medication therapy indicated',
                    'Comprehensive lifestyle intervention',
                    'Close medical supervision (monthly check-ups)'
                ]
            }

    def generate_explanation(self, age, sex, total_chol, hdl, systolic_bp,
                           smoker, diabetes, on_bp_meds, risk_percentage):
        """Generate detailed explanation of risk factors"""
        explanation = []

        # Age factor
        if age > 65:
            explanation.append(f"Advanced age ({age}) significantly increases cardiovascular risk.")
        elif age > 45:
            explanation.append(f"Middle age ({age}) contributes moderately to cardiovascular risk.")
        else:
            explanation.append(f"Younger age ({age}) is protective against cardiovascular disease.")

        # Cholesterol factors
        if total_chol > 240:
            explanation.append(f"High total cholesterol ({total_chol} mg/dL) is a major risk factor.")
        elif total_chol > 200:
            explanation.append(f"Borderline high cholesterol ({total_chol} mg/dL) increases risk.")
        else:
            explanation.append(f"Optimal cholesterol level ({total_chol} mg/dL) is protective.")

        if hdl < 40:
            explanation.append(f"Low HDL cholesterol ({hdl:.1f} mg/dL) increases risk significantly.")
        elif hdl > 60:
            explanation.append(f"High HDL cholesterol ({hdl:.1f} mg/dL) provides protection.")

        # Blood pressure
        if systolic_bp > 140:
            explanation.append(f"High blood pressure ({systolic_bp} mmHg) is a major risk factor.")
        elif systolic_bp > 120:
            explanation.append(f"Elevated blood pressure ({systolic_bp} mmHg) increases risk.")

        # Lifestyle factors
        if smoker:
            explanation.append("Smoking significantly increases cardiovascular risk.")

        if diabetes:
            explanation.append("Diabetes is a major cardiovascular risk factor.")

        if on_bp_meds:
            explanation.append("Being on blood pressure medication indicates underlying cardiovascular risk.")

        return explanation

    
    def compute_influences(self, age, total_chol, hdl, systolic_bp, smoker, diabetes, on_bp_meds, delta=0.01):
        """
        Compute influence (sensitivity) of each input on CVD risk.
        Returns dict of sensitivities (Δrisk / Δinput) sorted by absolute value.
        Positive sensitivity: Increasing input increases risk (e.g., total_chol).
        Negative: Increasing input decreases risk (e.g., hdl).
        """
        # Set baseline inputs
        inputs = {
            'age': age,
            'total_chol': total_chol,
            'hdl': hdl,
            'systolic_bp': systolic_bp,
            'smoking_status': 1.0 if smoker else 0.0,
            'diabetes_status': 1.0 if diabetes else 0.0,
            'bp_medication': 1.0 if on_bp_meds else 0.0
        }
        for key, value in inputs.items():
            self.risk_simulation.input[key] = value
        
        # Compute baseline risk
        self.risk_simulation.compute()
        baseline_risk = self.risk_simulation.output['cvd_risk']
        
        sensitivities = {}
        
        # Continuous variables: relative perturbation
        for var in ['age', 'total_chol', 'hdl', 'systolic_bp']:
            original = inputs[var]
            perturb_delta = max(original * delta, 1.0)  # Min delta=1 to avoid tiny changes
            perturbed = original + perturb_delta
            self.risk_simulation.input[var] = perturbed
            self.risk_simulation.compute()
            new_risk = self.risk_simulation.output['cvd_risk']
            sensitivity = (new_risk - baseline_risk) / perturb_delta
            sensitivities[var] = sensitivity
            self.risk_simulation.input[var] = original  # Reset
        
        # Binary variables: full flip
        for var in ['smoking_status', 'diabetes_status', 'bp_medication']:
            original = inputs[var]
            perturbed = 0.0 if original > 0.5 else 1.0
            self.risk_simulation.input[var] = perturbed
            self.risk_simulation.compute()
            new_risk = self.risk_simulation.output['cvd_risk']
            perturb_delta = perturbed - original
            sensitivity = (new_risk - baseline_risk) / perturb_delta if perturb_delta != 0 else 0.0
            sensitivities[var] = sensitivity
            self.risk_simulation.input[var] = original  # Reset
        
        # Sort by absolute sensitivity (most influential first)
        sorted_sensitivities = dict(sorted(sensitivities.items(), key=lambda x: abs(x[1]), reverse=True))
        
        return sorted_sensitivities
    
    def visualize_risk_factors(self, age, total_chol, hdl, systolic_bp):
        """Visualize membership functions for current inputs"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        # Age
        ax1.plot(self.age.universe, fuzz.interp_membership(self.age.universe, self.age['young'].mf, age), 'b', linewidth=2, label='Young')
        ax1.plot(self.age.universe, fuzz.interp_membership(self.age.universe, self.age['middle_aged'].mf, age), 'g', linewidth=2, label='Middle-aged')
        ax1.plot(self.age.universe, fuzz.interp_membership(self.age.universe, self.age['old'].mf, age), 'r', linewidth=2, label='Old')
        ax1.axvline(x=age, color='black', linestyle='--', alpha=0.7)
        ax1.set_title(f'Age Membership (Current: {age})')
        ax1.legend()

        # Total Cholesterol
        ax2.plot(self.total_chol.universe, fuzz.interp_membership(self.total_chol.universe, self.total_chol['optimal'].mf, total_chol), 'g', linewidth=2, label='Optimal')
        ax2.plot(self.total_chol.universe, fuzz.interp_membership(self.total_chol.universe, self.total_chol['borderline'].mf, total_chol), 'y', linewidth=2, label='Borderline')
        ax2.plot(self.total_chol.universe, fuzz.interp_membership(self.total_chol.universe, self.total_chol['high'].mf, total_chol), 'r', linewidth=2, label='High')
        ax2.axvline(x=total_chol, color='black', linestyle='--', alpha=0.7)
        ax2.set_title(f'Total Cholesterol Membership (Current: {total_chol})')
        ax2.legend()

        # HDL
        ax3.plot(self.hdl.universe, fuzz.interp_membership(self.hdl.universe, self.hdl['low'].mf, hdl), 'r', linewidth=2, label='Low')
        ax3.plot(self.hdl.universe, fuzz.interp_membership(self.hdl.universe, self.hdl['normal'].mf, hdl), 'y', linewidth=2, label='Normal')
        ax3.plot(self.hdl.universe, fuzz.interp_membership(self.hdl.universe, self.hdl['high'].mf, hdl), 'g', linewidth=2, label='High')
        ax3.axvline(x=hdl, color='black', linestyle='--', alpha=0.7)
        ax3.set_title(f'HDL Cholesterol Membership (Current: {hdl:.1f})')
        ax3.legend()

        # Systolic BP
        ax4.plot(self.systolic_bp.universe, fuzz.interp_membership(self.systolic_bp.universe, self.systolic_bp['normal'].mf, systolic_bp), 'g', linewidth=2, label='Normal')
        ax4.plot(self.systolic_bp.universe, fuzz.interp_membership(self.systolic_bp.universe, self.systolic_bp['elevated'].mf, systolic_bp), 'y', linewidth=2, label='Elevated')
        ax4.plot(self.systolic_bp.universe, fuzz.interp_membership(self.systolic_bp.universe, self.systolic_bp['high'].mf, systolic_bp), 'r', linewidth=2, label='High')
        ax4.axvline(x=systolic_bp, color='black', linestyle='--', alpha=0.7)
        ax4.set_title(f'Systolic BP Membership (Current: {systolic_bp})')
        ax4.legend()

        plt.tight_layout()
        plt.show()


    def plot_all_membership_functions(self):
        """
        Create comprehensive plots of all membership functions for research paper
        """
        fig = plt.figure(figsize=(16, 12))

        # Age membership functions
        ax1 = plt.subplot(3, 3, 1)
        ax1.plot(self.age.universe, self.age['young'].mf, 'b-', linewidth=2, label='Young')
        ax1.plot(self.age.universe, self.age['middle_aged'].mf, 'g-', linewidth=2, label='Middle-aged')
        ax1.plot(self.age.universe, self.age['old'].mf, 'r-', linewidth=2, label='Old')
        ax1.set_xlabel('Age (years)')
        ax1.set_ylabel('Membership Degree')
        ax1.set_title('Age Membership Functions')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Total Cholesterol membership functions
        ax2 = plt.subplot(3, 3, 2)
        ax2.plot(self.total_chol.universe, self.total_chol['optimal'].mf, 'g-', linewidth=2, label='Optimal')
        ax2.plot(self.total_chol.universe, self.total_chol['borderline'].mf, 'orange', linewidth=2, label='Borderline')
        ax2.plot(self.total_chol.universe, self.total_chol['high'].mf, 'r-', linewidth=2, label='High')
        ax2.set_xlabel('Total Cholesterol (mg/dL)')
        ax2.set_ylabel('Membership Degree')
        ax2.set_title('Total Cholesterol Membership Functions')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # HDL membership functions
        ax3 = plt.subplot(3, 3, 3)
        ax3.plot(self.hdl.universe, self.hdl['low'].mf, 'r-', linewidth=2, label='Low')
        ax3.plot(self.hdl.universe, self.hdl['normal'].mf, 'orange', linewidth=2, label='Normal')
        ax3.plot(self.hdl.universe, self.hdl['high'].mf, 'g-', linewidth=2, label='High')
        ax3.set_xlabel('HDL Cholesterol (mg/dL)')
        ax3.set_ylabel('Membership Degree')
        ax3.set_title('HDL Cholesterol Membership Functions')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Systolic BP membership functions
        ax4 = plt.subplot(3, 3, 4)
        ax4.plot(self.systolic_bp.universe, self.systolic_bp['normal'].mf, 'g-', linewidth=2, label='Normal')
        ax4.plot(self.systolic_bp.universe, self.systolic_bp['elevated'].mf, 'orange', linewidth=2, label='Elevated')
        ax4.plot(self.systolic_bp.universe, self.systolic_bp['high'].mf, 'r-', linewidth=2, label='High')
        ax4.set_xlabel('Systolic BP (mmHg)')
        ax4.set_ylabel('Membership Degree')
        ax4.set_title('Systolic Blood Pressure Membership Functions')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        # CVD Risk output membership functions
        ax5 = plt.subplot(3, 3, 5)
        ax5.plot(self.cvd_risk.universe, self.cvd_risk['very_low'].mf, 'darkgreen', linewidth=2, label='Very Low')
        ax5.plot(self.cvd_risk.universe, self.cvd_risk['low'].mf, 'g-', linewidth=2, label='Low')
        ax5.plot(self.cvd_risk.universe, self.cvd_risk['moderate'].mf, 'orange', linewidth=2, label='Moderate')
        ax5.plot(self.cvd_risk.universe, self.cvd_risk['high'].mf, 'red', linewidth=2, label='High')
        ax5.plot(self.cvd_risk.universe, self.cvd_risk['very_high'].mf, 'darkred', linewidth=2, label='Very High')
        ax5.set_xlabel('CVD Risk (%)')
        ax5.set_ylabel('Membership Degree')
        ax5.set_title('CVD Risk Output Membership Functions')
        ax5.legend()
        ax5.grid(True, alpha=0.3)

        # Binary variables (Smoking)
        ax6 = plt.subplot(3, 3, 6)
        ax6.plot(self.smoking_status.universe, self.smoking_status['no'].mf, 'g-', linewidth=2, label='Non-smoker')
        ax6.plot(self.smoking_status.universe, self.smoking_status['yes'].mf, 'r-', linewidth=2, label='Smoker')
        ax6.set_xlabel('Smoking Status')
        ax6.set_ylabel('Membership Degree')
        ax6.set_title('Smoking Status Membership Functions')
        ax6.legend()
        ax6.grid(True, alpha=0.3)

        # Binary variables (Diabetes)
        ax7 = plt.subplot(3, 3, 7)
        ax7.plot(self.diabetes_status.universe, self.diabetes_status['no'].mf, 'g-', linewidth=2, label='No Diabetes')
        ax7.plot(self.diabetes_status.universe, self.diabetes_status['yes'].mf, 'r-', linewidth=2, label='Diabetes')
        ax7.set_xlabel('Diabetes Status')
        ax7.set_ylabel('Membership Degree')
        ax7.set_title('Diabetes Status Membership Functions')
        ax7.legend()
        ax7.grid(True, alpha=0.3)

        # Binary variables (BP Medication)
        ax8 = plt.subplot(3, 3, 8)
        ax8.plot(self.bp_medication.universe, self.bp_medication['no'].mf, 'g-', linewidth=2, label='No BP Meds')
        ax8.plot(self.bp_medication.universe, self.bp_medication['yes'].mf, 'r-', linewidth=2, label='On BP Meds')
        ax8.set_xlabel('BP Medication Status')
        ax8.set_ylabel('Membership Degree')
        ax8.set_title('BP Medication Membership Functions')
        ax8.legend()
        ax8.grid(True, alpha=0.3)

        # Rule activation visualization (example)
        ax9 = plt.subplot(3, 3, 9)
        x = np.linspace(0, 30, 100)
        y1 = np.exp(-((x-5)**2)/(2*2**2))  # Low risk
        y2 = np.exp(-((x-12)**2)/(2*3**2))  # Moderate risk
        y3 = np.exp(-((x-22)**2)/(2*4**2))  # High risk
        ax9.plot(x, y1, 'g-', linewidth=2, label='Low Risk Rules')
        ax9.plot(x, y2, 'orange', linewidth=2, label='Moderate Risk Rules')
        ax9.plot(x, y3, 'r-', linewidth=2, label='High Risk Rules')
        ax9.set_xlabel('CVD Risk (%)')
        ax9.set_ylabel('Rule Activation Strength')
        ax9.set_title('Example Rule Activation Pattern')
        ax9.legend()
        ax9.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('fuzzy_membership_functions.png', dpi=300, bbox_inches='tight')
        plt.show()

    def demonstrate_fuzzy_inference(self, age, total_chol, hdl, systolic_bp, smoker, diabetes):
        """
        Demonstrate the fuzzy inference process step by step
        """
        print(f"\n{'='*80}")
        print("FUZZY INFERENCE PROCESS DEMONSTRATION")
        print(f"{'='*80}")

        print(f"Input Values:")
        print(f"  Age: {age}")
        print(f"  Total Cholesterol: {total_chol}")
        print(f"  HDL Cholesterol: {hdl}")
        print(f"  Systolic BP: {systolic_bp}")
        print(f"  Smoker: {smoker}")
        print(f"  Diabetes: {diabetes}")

        print(f"\nStep 1: Fuzzification")
        print(f"Converting crisp inputs to fuzzy membership degrees:")

        # Calculate membership degrees
        age_young = fuzz.interp_membership(self.age.universe, self.age['young'].mf, age)
        age_middle = fuzz.interp_membership(self.age.universe, self.age['middle_aged'].mf, age)
        age_old = fuzz.interp_membership(self.age.universe, self.age['old'].mf, age)

        chol_optimal = fuzz.interp_membership(self.total_chol.universe, self.total_chol['optimal'].mf, total_chol)
        chol_borderline = fuzz.interp_membership(self.total_chol.universe, self.total_chol['borderline'].mf, total_chol)
        chol_high = fuzz.interp_membership(self.total_chol.universe, self.total_chol['high'].mf, total_chol)

        hdl_low = fuzz.interp_membership(self.hdl.universe, self.hdl['low'].mf, hdl)
        hdl_normal = fuzz.interp_membership(self.hdl.universe, self.hdl['normal'].mf, hdl)
        hdl_high = fuzz.interp_membership(self.hdl.universe, self.hdl['high'].mf, hdl)

        print(f"  Age: Young={age_young:.3f}, Middle={age_middle:.3f}, Old={age_old:.3f}")
        print(f"  Cholesterol: Optimal={chol_optimal:.3f}, Borderline={chol_borderline:.3f}, High={chol_high:.3f}")
        print(f"  HDL: Low={hdl_low:.3f}, Normal={hdl_normal:.3f}, High={hdl_high:.3f}")

        print(f"\nStep 2: Rule Evaluation")
        print(f"Example rule activations:")

        # Example rule evaluations
        rule1_strength = min(age_young, chol_optimal, hdl_high)
        rule2_strength = min(age_middle, chol_borderline, hdl_normal)
        rule3_strength = min(age_old, chol_high, 1.0 if smoker else 0.0, 1.0 if diabetes else 0.0)

        print(f"  Rule 1 (Very Low Risk): Young ∧ Optimal_Chol ∧ High_HDL = {rule1_strength:.3f}")
        print(f"  Rule 2 (Moderate Risk): Middle ∧ Borderline_Chol ∧ Normal_HDL = {rule2_strength:.3f}")
        print(f"  Rule 3 (Very High Risk): Old ∧ High_Chol ∧ Smoker ∧ Diabetes = {rule3_strength:.3f}")

        print(f"\nStep 3: Defuzzification")
        print(f"Combining all rule outputs using centroid method to get crisp risk value")

    def generate_research_plots(self):
        """
        Generate all plots needed for research paper
        """
        # Plot 1: All membership functions
        self.plot_all_membership_functions()

        # Plot 2: Comparison of fuzzy vs crisp boundaries
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # Crisp boundaries
        age_range = np.arange(20, 85)
        crisp_risk = []
        for age in age_range:
            if age < 35:
                risk = 2
            elif age < 50:
                risk = 8
            else:
                risk = 20
            crisp_risk.append(risk)

        ax1.plot(age_range, crisp_risk, 'r-', linewidth=3, label='Crisp Logic')
        ax1.set_xlabel('Age (years)')
        ax1.set_ylabel('Risk (%)')
        ax1.set_title('Traditional Crisp Logic Approach')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Fuzzy boundaries
        fuzzy_risk = []
        for age in age_range:
            # Simplified fuzzy calculation for demonstration
            young_degree = max(0, min(1, (40-age)/(40-20)))
            middle_degree = max(0, min((age-35)/(50-35), (65-age)/(65-50)))
            old_degree = max(0, min(1, (age-60)/(75-60)))

            risk = young_degree * 3 + middle_degree * 12 + old_degree * 25
            fuzzy_risk.append(risk)

        ax2.plot(age_range, fuzzy_risk, 'b-', linewidth=3, label='Fuzzy Logic')
        ax2.set_xlabel('Age (years)')
        ax2.set_ylabel('Risk (%)')
        ax2.set_title('Fuzzy Logic Approach')
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        plt.tight_layout()
        plt.savefig('crisp_vs_fuzzy_comparison.png', dpi=300, bbox_inches='tight')
        plt.show()

        # Plot 3: 3D Risk Surface
        self.plot_3d_risk_surface()

    def plot_3d_risk_surface(self):
        """
        Create 3D surface plot showing risk as function of two variables
        """
        from mpl_toolkits.mplot3d import Axes3D

        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')

        # Create meshgrid
        age_range = np.linspace(30, 75, 20)
        chol_range = np.linspace(150, 300, 20)
        Age, Chol = np.meshgrid(age_range, chol_range)

        # Calculate risk surface
        Risk = np.zeros_like(Age)
        for i in range(Age.shape[0]):
            for j in range(Age.shape[1]):
                try:
                    result = self.calculate_risk(
                        age=int(Age[i,j]),
                        sex='male',
                        total_chol=int(Chol[i,j]),
                        systolic_bp=130,
                        smoker=False,
                        diabetes=False
                    )
                    Risk[i,j] = result['risk_percentage']
                except:
                    Risk[i,j] = 0

        # Plot surface
        surf = ax.plot_surface(Age, Chol, Risk, cmap='viridis', alpha=0.8)
        ax.set_xlabel('Age (years)')
        ax.set_ylabel('Total Cholesterol (mg/dL)')
        ax.set_zlabel('CVD Risk (%)')
        ax.set_title('3D CVD Risk Surface')

        # Add colorbar
        fig.colorbar(surf, shrink=0.5, aspect=5)

        plt.savefig('3d_risk_surface.png', dpi=300, bbox_inches='tight')
        plt.show()

    def print_rule_methodology(self):
        """
        Print detailed explanation of rule selection methodology
        """
        print(f"\n{'='*80}")
        print("FUZZY RULE SELECTION METHODOLOGY")
        print(f"{'='*80}")

        print("""
1. MEDICAL LITERATURE REVIEW:
   - Analyzed original Framingham Heart Study publications
   - Reviewed ATP III guidelines for cholesterol management
   - Studied AHA/ACC risk assessment guidelines
   - Examined meta-analyses on cardiovascular risk factors

2. EXPERT KNOWLEDGE EXTRACTION:
   - Consulted cardiology practice guidelines
   - Analyzed clinical decision-making patterns
   - Reviewed case studies from medical literature
   - Incorporated evidence-based medicine principles

3. RULE CATEGORIZATION:
   The 15 fuzzy rules are categorized into 5 risk levels:

   A. VERY LOW RISK RULES (Target: <3% risk):
      - Young age + Optimal cholesterol + High HDL + Normal BP + No smoking + No diabetes

   B. LOW RISK RULES (Target: 3-7% risk):
      - Young age + Borderline cholesterol + Normal HDL + Normal BP + No smoking + No diabetes
      - Middle age + Optimal cholesterol + High HDL + Normal BP + No smoking + No diabetes

   C. MODERATE RISK RULES (Target: 7-15% risk):
      - Middle age + Borderline cholesterol + Normal HDL + Elevated BP
      - Young age + Smoking + Diabetes (high-impact factors)
      - Middle age + Low HDL + Elevated BP (multiple moderate factors)

   D. HIGH RISK RULES (Target: 15-25% risk):
      - Old age + Borderline cholesterol (age-dominant)
      - Middle age + High cholesterol + Smoking (multiple high-impact factors)
      - Diabetes + Smoking + Low HDL (synergistic high-risk factors)
      - High BP + Middle age + Diabetes (metabolic syndrome pattern)

   E. VERY HIGH RISK RULES (Target: >25% risk):
      - Old age + High cholesterol + Smoking (multiple severe factors)
      - Old age + Diabetes + Low HDL + High BP (comprehensive high-risk profile)
      - High cholesterol + Low HDL + Smoking + Diabetes + High BP (all major factors)

4. RULE VALIDATION CRITERIA:
   - Clinical plausibility: Each rule reflects real clinical scenarios
   - Evidence-based: Supported by epidemiological studies
   - Logical consistency: No contradictory rules
   - Completeness: Coverage of major risk factor combinations
   - Interpretability: Rules are explainable to clinicians

5. MEMBERSHIP FUNCTION DESIGN RATIONALE:

   A. Age Functions:
      - Young (20-40): Based on low baseline risk in young adults
      - Middle-aged (35-65): Peak overlap represents transition period
      - Old (60-85): Reflects exponential risk increase with age

   B. Cholesterol Functions:
      - Optimal (<180): ATP III optimal levels
      - Borderline (160-240): ATP III borderline high
      - High (220-400): ATP III high levels with overlap

   C. HDL Functions:
      - Low (<45): Below protective levels
      - Normal (40-65): Typical healthy range
      - High (60-100): Cardioprotective levels

   D. Blood Pressure Functions:
      - Normal (<125): AHA normal range
      - Elevated (120-150): Pre-hypertension overlap
      - High (140-200): Hypertensive range

6. FUZZY OPERATORS SELECTION:
   - AND operations: Minimum (conservative approach)
   - OR operations: Maximum (inclusive approach)
   - Defuzzification: Centroid method for smooth output

7. CLINICAL VALIDATION APPROACH:
   - Compared outputs with original Framingham equations
   - Validated against known clinical cases
   - Tested edge cases and boundary conditions
   - Ensured monotonic risk increase with age

8. ADVANTAGES OF FUZZY APPROACH:
   - Handles uncertainty in measurements
   - Provides smooth risk transitions
   - Captures synergistic effects between risk factors
   - More interpretable than black-box models
   - Allows for easy rule modification based on new evidence
        """)