# --- ASCVD Risk Score Function (Pooled Cohort Equation) ---
import math

import math

def estimate_hdl(chol_total, sex='male'):
    """
    Estimate HDL as a percentage of total cholesterol (rough guess).
    """
    factor = 0.28 if sex.lower() == 'female' else 0.23
    return chol_total * factor

def framingham_risk_score(age, sex, total_chol, systolic_bp, smoker, diabetes, 
                          on_bp_meds=False, hdl=None):
    """
    Framingham 10-year CVD risk calculator based on ATP III guidelines.
    Returns percentage risk.
    """

    if hdl is None:
        hdl = estimate_hdl(total_chol, sex)

    points = 0
    sex = sex.lower()
    print(f"_________________Age = {age}")
    # Age points
    age_points = {
        'male':   [(20, 34, -9), (35, 39, -4), (40, 44, 0), (45, 49, 3), (50, 54, 6), (55, 59, 8), (60, 64, 10), (65, 69, 11), (70, 74, 12), (75, 79, 13)],
        'female': [(20, 34, -7), (35, 39, -3), (40, 44, 0), (45, 49, 3), (50, 54, 6), (55, 59, 8), (60, 64, 10), (65, 69, 12), (70, 74, 14), (75, 79, 16)]
    }

    for (low, high, val) in age_points[sex]:
        if low <= age <= high:
            points += val
            break

    # Total Cholesterol
    print(f"_________________TotCho = {total_chol}")
    print(f"________________Sex:{sex}")
    tc_points = {
        'male':   [(100, 160, 0), (160,199, 4), (200,239, 7), (240,279, 9), (280,999, 11)],
        'female': [(100, 160, 0), (160,199, 4), (200,239, 8), (240,279, 11), (280,999, 13)]
    }

    for (low, high, val) in tc_points[sex]:
        if low <= total_chol <= high:
            points += val
            break

    # Smoking
    if smoker:
        points += 4 if sex == 'male' else 3

    # HDL
    if hdl >= 60:
        points -= 1
    elif 50 <= hdl <= 59:
        points += 0
    elif 40 <= hdl <= 49:
        points += 1
    elif hdl < 40:
        points += 2

    # BP
    print(f"________________BP Medics:{on_bp_meds}")
    
    if on_bp_meds:
        sbp_points = {
            'male':   [(0, 120, 0), (120,129, 1), (130,139, 2), (140,159, 2), (160,999, 3)],
            'female': [(0, 120, 0), (120,129, 3), (130,139, 4), (140,159, 5), (160,999, 6)]
        }
    else:
        sbp_points = {
            'male':   [(0, 120, 0), (120,129, 0), (130,139, 1), (140,159, 1), (160,999, 2)],
            'female': [(0, 120, 0), (120,129, 1), (130,139, 2), (140,159, 3), (160,999, 4)]
        }

    for (low, high, val) in sbp_points[sex]:
        if low <= systolic_bp <= high:
            points += val
            break

    # Diabetes
    if diabetes:
        points += 3 if sex == 'male' else 4

    # Risk estimation
    risk_table = {
        'male':   {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 6: 2, 7: 3, 8: 4, 9: 5, 10: 6,
                   11: 8, 12: 10, 13: 12, 14: 16, 15: 20, 16: 25, 17: 30, 18: 30, 19: 30, 20: 30},
        'female': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 6: 2, 7: 3, 8: 4, 9: 5, 10: 6,
                   11: 8, 12: 11, 13: 14, 14: 17, 15: 22, 16: 27, 17: 30, 18: 30, 19: 30, 20: 30}
    }

    risk = risk_table[sex].get(points, 30)
    return min(risk, 30)



def ascvd_risk(age, sex, race, total_chol, systolic_bp, smoker, diabetes,
               on_bp_meds=False, hdl=None):
    if hdl is None:
        hdl = estimate_hdl(total_chol, sex)

    sex = sex.lower()
    race = race.lower()
    smoker = 1 if smoker else 0
    diabetes = 1 if diabetes else 0
    on_bp_meds = 1 if on_bp_meds else 0

    ln_age = math.log(age)
    ln_total_chol = math.log(total_chol)
    ln_hdl = math.log(hdl)
    ln_sbp = math.log(systolic_bp)

    if sex == 'male' and race == 'white':
        coeffs = {
            'ln_age': 12.344, 'ln_total_chol': 11.853, 'ln_hdl': -7.99,
            'ln_sbp_treated': 1.797, 'ln_sbp_untreated': 1.764,
            'smoker': 7.837, 'diabetes': 0.658,
            'baseline_survival': 0.9144, 'mean_coef': 61.18
        }
    elif sex == 'female' and race == 'white':
        coeffs = {
            'ln_age': -29.799, 'ln_total_chol': 13.540, 'ln_hdl': -13.578,
            'ln_sbp_treated': 2.019, 'ln_sbp_untreated': 1.957,
            'smoker': 7.574, 'diabetes': 0.661,
            'baseline_survival': 0.9665, 'mean_coef': -29.18
        }
    else:
        raise ValueError("Only 'white' race is supported in this version.")

    ln_sbp_coeff = coeffs['ln_sbp_treated'] if on_bp_meds else coeffs['ln_sbp_untreated']

    sum_score = (
        ln_age * coeffs['ln_age'] +
        ln_total_chol * coeffs['ln_total_chol'] +
        ln_hdl * coeffs['ln_hdl'] +
        ln_sbp * ln_sbp_coeff +
        smoker * coeffs['smoker'] +
        diabetes * coeffs['diabetes']
    )

    risk = 1 - (coeffs['baseline_survival'] ** math.exp(sum_score - coeffs['mean_coef']))
    return round(risk * 100, 2)


# --- QRISK3 Score (approximate version) ---
def qrisk3_score(age, sex, smoker, diabetes, systolic_bp, bmi,
                 kidney_disease=False, atrial_fibrillation=False, rheumatoid_arthritis=False,
                 systolic_bp_variability=5):
    """
    Approximate QRISK3 implementation.
    Only uses core variables. Real version includes many more.
    """
    base_risk = 0.01 * age + 0.1 * smoker + 0.5 * diabetes
    base_risk += 0.02 * (systolic_bp - 120) + 0.05 * (bmi - 25)
    base_risk += 0.3 if kidney_disease else 0
    base_risk += 0.3 if atrial_fibrillation else 0
    base_risk += 0.2 if rheumatoid_arthritis else 0
    base_risk += 0.1 * (systolic_bp_variability - 5)

    if sex.lower() == 'male':
        base_risk *= 1.2
    else:
        base_risk *= 1.0

    return round(min(30.0, base_risk), 2)  # Clip at 30% for simplicity


# --- CHADS2 and CHA2DS2-VASc Score ---
def chads2_score(congestive_hf, hypertension, age, diabetes, stroke_history):
    score = 0
    score += 1 if congestive_hf else 0
    score += 1 if hypertension else 0
    score += 1 if diabetes else 0
    score += 2 if stroke_history else 0
    score += 1 if age >= 75 else 0
    return score

def cha2ds2_vasc_score(congestive_hf, hypertension, age, diabetes, stroke_history,
                       vascular_disease, female):
    score = chads2_score(congestive_hf, hypertension, age, diabetes, stroke_history)
    score += 1 if vascular_disease else 0
    score += 1 if 65 <= age <= 74 else 0
    score += 1 if female else 0
    score += 1 if age >= 75 else 1  # CHA2DS2 counts age >= 75 as 2 total
    return score


# --- HAS-BLED Score (Partial) ---
def has_bled_score(hypertension, renal_disease  , stroke_history,
                     age, drugs_alcohol):
    
    liver_disease = False
    bleeding_history = False
    score = 0
    score += 1 if hypertension else 0
    score += 1 if renal_disease else 0
    score += 1 if liver_disease else 0
    score += 1 if stroke_history else 0
    score += 1 if bleeding_history else 0
    score += 1 if age > 65 else 0
    score += 1 if drugs_alcohol else 0  # simplified: either drugs or alcohol excess
    return score
